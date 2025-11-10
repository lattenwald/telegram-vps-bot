# Build Lambda deployment package with dependencies
resource "null_resource" "build_lambda" {
  triggers = {
    # Rebuild when source code or dependencies change
    src_hash      = sha1(join("", [for f in fileset("${path.module}/../src", "**") : filesha1("${path.module}/../src/${f}")]))
    requirements  = filesha1("${path.module}/../requirements.txt")
  }

  provisioner "local-exec" {
    command     = "${path.module}/build_lambda.sh"
    working_dir = path.module
  }
}

# Archive the built Lambda package
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_build"
  output_path = "${path.module}/lambda_deployment.zip"
  excludes    = ["__pycache__", "*.pyc", "*.pyo"]

  depends_on = [null_resource.build_lambda]
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.project_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Name    = "${var.project_name}-logs"
    Project = var.project_name
  }
}

# Lambda Function
resource "aws_lambda_function" "telegram_bot" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = var.project_name
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.13"
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout

  environment {
    variables = {
      AUTHORIZED_CHAT_IDS           = var.authorized_chat_ids
      BITLAUNCH_API_BASE_URL        = var.bitlaunch_api_base_url
      SSM_TELEGRAM_TOKEN_PATH       = var.ssm_telegram_token_path
      SSM_BITLAUNCH_API_KEY_PATH    = var.ssm_bitlaunch_api_key_path
      LOG_LEVEL                     = var.log_level
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs,
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy.ssm_parameter_access
  ]

  tags = {
    Name    = var.project_name
    Project = var.project_name
  }
}

# API Gateway REST API
resource "aws_api_gateway_rest_api" "telegram_webhook" {
  name        = "${var.project_name}-api"
  description = "API Gateway for Telegram webhook"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = {
    Name    = "${var.project_name}-api"
    Project = var.project_name
  }
}

# API Gateway Resource
resource "aws_api_gateway_resource" "webhook" {
  rest_api_id = aws_api_gateway_rest_api.telegram_webhook.id
  parent_id   = aws_api_gateway_rest_api.telegram_webhook.root_resource_id
  path_part   = "webhook"
}

# API Gateway Method (POST)
resource "aws_api_gateway_method" "webhook_post" {
  rest_api_id   = aws_api_gateway_rest_api.telegram_webhook.id
  resource_id   = aws_api_gateway_resource.webhook.id
  http_method   = "POST"
  authorization = "NONE"
}

# API Gateway Integration with Lambda
resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id             = aws_api_gateway_rest_api.telegram_webhook.id
  resource_id             = aws_api_gateway_resource.webhook.id
  http_method             = aws_api_gateway_method.webhook_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.telegram_bot.invoke_arn
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "webhook_deployment" {
  rest_api_id = aws_api_gateway_rest_api.telegram_webhook.id

  depends_on = [
    aws_api_gateway_integration.lambda_integration
  ]

  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway Stage
resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.webhook_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.telegram_webhook.id
  stage_name    = "prod"

  tags = {
    Name    = "${var.project_name}-prod"
    Project = var.project_name
  }
}

# Lambda Permission for API Gateway
resource "aws_lambda_permission" "api_gateway_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.telegram_bot.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.telegram_webhook.execution_arn}/*/*"
}

# Setup Telegram bot commands
resource "null_resource" "setup_bot_commands" {
  triggers = {
    # Re-run when Lambda function changes or authorized chat IDs change
    lambda_version        = aws_lambda_function.telegram_bot.version
    authorized_chat_ids   = var.authorized_chat_ids
    script_hash           = filesha1("${path.module}/../scripts/setup_commands.py")
  }

  provisioner "local-exec" {
    command = "cd ${path.module}/.. && uv run python scripts/setup_commands.py"
    environment = {
      AUTHORIZED_CHAT_IDS = var.authorized_chat_ids
      AWS_REGION         = var.aws_region
    }
  }

  depends_on = [
    aws_lambda_function.telegram_bot
  ]
}
