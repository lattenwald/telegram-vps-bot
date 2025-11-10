variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "telegram-vps-bot"
}

variable "authorized_chat_ids" {
  description = "Comma-separated list of authorized Telegram chat IDs"
  type        = string
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 256
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 30
}

variable "ssm_telegram_token_path" {
  description = "SSM Parameter Store path for Telegram bot token"
  type        = string
  default     = "/telegram-vps-bot/telegram-token"
}

variable "ssm_bitlaunch_api_key_path" {
  description = "SSM Parameter Store path for BitLaunch API key"
  type        = string
  default     = "/telegram-vps-bot/bitlaunch-api-key"
}

variable "bitlaunch_api_base_url" {
  description = "BitLaunch API base URL"
  type        = string
  default     = "https://app.bitlaunch.io/api"
}

variable "log_level" {
  description = "Logging level for Lambda function"
  type        = string
  default     = "INFO"
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention in days"
  type        = number
  default     = 7
}
