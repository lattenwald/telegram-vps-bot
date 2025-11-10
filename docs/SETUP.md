# Setup Guide: Telegram VPS Management Bot

This guide will walk you through deploying the Telegram VPS Management Bot to AWS Lambda.

## Prerequisites

Before you begin, ensure you have:

1. **AWS Account** with CLI configured
2. **Terraform** >= 1.0 installed
3. **Python 3.13** installed
4. **BitLaunch.io Account** with API key
5. **Telegram Bot Token** from @BotFather

## Step 1: Create Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Follow the prompts to create your bot
4. Save the bot token (format: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

## Step 2: Get Your BitLaunch API Key

1. Log in to your [BitLaunch.io](https://bitlaunch.io) account
2. Navigate to Account Settings → API
3. Generate a new API key
4. Save the API key securely

## Step 3: Configure AWS CLI

If you haven't already, configure the AWS CLI:

```bash
aws configure
```

Enter your:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., `us-east-1`)
- Default output format (e.g., `json`)

## Step 4: Store Secrets in AWS SSM Parameter Store

Store your sensitive credentials in AWS Systems Manager Parameter Store:

```bash
# Store Telegram bot token
aws ssm put-parameter \
  --name /telegram-vps-bot/telegram-token \
  --value "YOUR_TELEGRAM_BOT_TOKEN" \
  --type SecureString \
  --description "Telegram bot token for VPS management bot"

# Store BitLaunch API key
aws ssm put-parameter \
  --name /telegram-vps-bot/bitlaunch-api-key \
  --value "YOUR_BITLAUNCH_API_KEY" \
  --type SecureString \
  --description "BitLaunch API key for VPS management"
```

Verify the parameters were created:

```bash
aws ssm describe-parameters \
  --filters "Key=Name,Values=/telegram-vps-bot/"
```

## Step 5: Get Your Telegram Chat ID

You need your chat ID to authorize yourself:

1. Start a conversation with your bot in Telegram
2. Send any message to the bot
3. Visit this URL in your browser (replace `YOUR_BOT_TOKEN`):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
4. Look for `"chat":{"id":123456789}` in the response
5. Save your chat ID (the number)

Alternatively, after deploying (Step 8), you can send `/id` to your bot.

## Step 6: Clone Repository and Install Dependencies

```bash
# Clone the repository
git clone <repository-url>
cd telegram-vps-bot

# Create virtual environment with uv (Python 3.13)
uv venv --python 3.13
source .venv/bin/activate

# Install dependencies with uv
uv pip install -r requirements.txt

# Install development dependencies (optional, for testing)
uv pip install -r requirements-dev.txt
```

**Note**: This project uses [uv](https://github.com/astral-sh/uv) for faster dependency management. If you prefer standard pip, replace `uv pip install` with `pip install`.

## Step 7: Configure Terraform Variables

```bash
cd infrastructure

# Copy the example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit the file with your settings
nano terraform.tfvars
```

Update the following in `terraform.tfvars`:

```hcl
# Replace with your Telegram chat ID(s)
authorized_chat_ids = "123456789"

# Optional: Add multiple chat IDs separated by commas
# authorized_chat_ids = "123456789,987654321"

# Optional: Change region if needed
# aws_region = "us-east-1"
```

## Step 8: Build Lambda Deployment Package

Before deploying with Terraform, build the Lambda package with dependencies:

```bash
cd infrastructure

# Build Lambda deployment package (includes dependencies)
./build_lambda.sh
```

This script installs Python dependencies (boto3, requests) and packages them with your code.

## Step 9: Deploy Infrastructure with Terraform

```bash
# Initialize Terraform (if not already done)
terraform init

# Review the deployment plan
terraform plan

# Apply the configuration
terraform apply
```

Type `yes` when prompted to confirm the deployment.

**Note**: On first deployment, if Terraform fails with "missing directory" error, run `./build_lambda.sh` manually before `terraform apply`.

The deployment will create:
- Lambda function
- API Gateway REST API
- IAM roles and policies
- CloudWatch Log Group

## Step 10: Set Telegram Webhook

After deployment completes, set the Telegram webhook:

```bash
# Get the API Gateway webhook URL
WEBHOOK_URL=$(terraform output -raw api_gateway_webhook_url)

# Set the webhook (replace YOUR_BOT_TOKEN with your actual token)
curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook?url=${WEBHOOK_URL}"
```

You should see a response like:
```json
{"ok":true,"result":true,"description":"Webhook was set"}
```

Verify the webhook is set:

```bash
curl "https://api.telegram.org/botYOUR_BOT_TOKEN/getWebhookInfo"
```

## Step 11: Test the Bot

1. Open Telegram and find your bot
2. Send `/id` - you should receive your chat ID
3. Send `/reboot <your-server-name>` - you should receive an appropriate response

## Verification Checklist

- [ ] SSM parameters created and encrypted
- [ ] Terraform apply completed successfully
- [ ] API Gateway endpoint created
- [ ] Lambda function deployed
- [ ] Telegram webhook set correctly
- [ ] Bot responds to `/id` command
- [ ] Authorized users can execute `/reboot` command
- [ ] Unauthorized users receive "Access denied" message

## Monitoring and Logs

View Lambda logs in CloudWatch:

```bash
# View recent logs
aws logs tail /aws/lambda/telegram-vps-bot --follow

# Filter for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/telegram-vps-bot \
  --filter-pattern "ERROR"
```

## Updating the Bot

To update the bot code:

```bash
# Make your changes to src/ files

# Redeploy with Terraform
cd infrastructure
terraform apply
```

Terraform will detect the code changes and update the Lambda function.

## Adding More Authorized Users

1. Get the new user's chat ID (have them send `/id` to the bot)
2. Update `terraform.tfvars`:
   ```hcl
   authorized_chat_ids = "123456789,987654321,111222333"
   ```
3. Redeploy:
   ```bash
   terraform apply
   ```

## Troubleshooting

### Bot doesn't respond

1. Check CloudWatch Logs:
   ```bash
   aws logs tail /aws/lambda/telegram-vps-bot --follow
   ```

2. Verify webhook is set:
   ```bash
   curl "https://api.telegram.org/botYOUR_BOT_TOKEN/getWebhookInfo"
   ```

3. Check Lambda function exists:
   ```bash
   aws lambda get-function --function-name telegram-vps-bot
   ```

### "Access denied" for authorized user

1. Verify your chat ID in Terraform:
   ```bash
   terraform output
   ```

2. Check environment variables in Lambda:
   ```bash
   aws lambda get-function-configuration --function-name telegram-vps-bot
   ```

3. Ensure you redeployed after updating chat IDs

### "Configuration error" message

1. Verify SSM parameters exist:
   ```bash
   aws ssm get-parameter --name /telegram-vps-bot/telegram-token --with-decryption
   aws ssm get-parameter --name /telegram-vps-bot/bitlaunch-api-key --with-decryption
   ```

2. Check Lambda IAM role has SSM permissions:
   ```bash
   aws iam get-role-policy --role-name telegram-vps-bot-lambda-role --policy-name telegram-vps-bot-ssm-access
   ```

### Lambda timeout errors

Check CloudWatch Logs for timeout errors. If BitLaunch API is slow, you may need to increase the timeout:

```hcl
# In terraform.tfvars
lambda_timeout = 60  # Increase from 30 to 60 seconds
```

Then redeploy: `terraform apply`

## Cleanup / Uninstall

To remove all resources:

```bash
# Delete Terraform resources
cd infrastructure
terraform destroy

# Delete SSM parameters
aws ssm delete-parameter --name /telegram-vps-bot/telegram-token
aws ssm delete-parameter --name /telegram-vps-bot/bitlaunch-api-key

# Remove webhook from Telegram
curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/deleteWebhook"
```

## Cost Optimization

This bot is designed to run within AWS Free Tier:

- **Lambda**: 1M requests/month free
- **API Gateway**: 1M requests/month free (first 12 months)
- **CloudWatch Logs**: 5GB free
- **SSM Parameter Store**: Free for standard parameters

To monitor costs:

```bash
# Set up billing alarm
aws cloudwatch put-metric-alarm \
  --alarm-name telegram-vps-bot-billing \
  --alarm-description "Alert when costs exceed $1" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold 1.0 \
  --comparison-operator GreaterThanThreshold
```

## Security Best Practices

1. **Never commit secrets** to git
2. **Rotate API keys** regularly
3. **Use least-privilege IAM roles** (already configured)
4. **Enable CloudTrail** for audit logging
5. **Review CloudWatch Logs** for unauthorized access attempts
6. **Keep chat IDs confidential**
7. **Update dependencies** regularly

## Next Steps

- Review [API Documentation](API.md)
- Read the [Product Requirements Document](PRD.md)
- Customize error messages in `src/handler.py`
- Add more commands (see PRD Future Enhancements)

## Support

For issues and questions:
- Check CloudWatch Logs first
- Review this troubleshooting section
- Open an issue on GitHub
