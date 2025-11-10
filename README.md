# Telegram VPS Management Bot

A serverless Telegram bot deployed on AWS Lambda that enables authorized users to manage VPS instances through the BitLaunch.io API via simple chat commands.

## Features

- **Secure Authorization**: Chat ID-based access control
- **Simple Commands**: Manage VPS through Telegram chat
- **Serverless**: Zero-cost deployment using AWS Free Tier
- **Infrastructure as Code**: Reproducible Terraform configuration

## Commands

| Command | Description | Authorization |
|---------|-------------|---------------|
| `/id` | Get your Telegram chat ID | Not required |
| `/help` | Show available commands | Not required |
| `/reboot <server_name>` | Reboot a VPS server | Required |

**Note:** The `/help` command shows different commands based on authorization:
- **Unauthorized users** see: `/id`, `/help`
- **Authorized users** see: `/id`, `/help`, `/reboot`

All other commands (including `/start`) are silently ignored.

## Architecture

```
Telegram API → API Gateway → Lambda Function → BitLaunch API
                                ↓
                          SSM Parameter Store
                          CloudWatch Logs
```

## Prerequisites

- AWS account with CLI configured
- Terraform >= 1.0
- Python 3.13
- BitLaunch.io account with API key
- Telegram bot token from [@BotFather](https://t.me/BotFather)

## Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd telegram-vps-bot
```

### 2. Create Virtual Environment and Install Dependencies

**Option A: Using `uv` (Recommended - Fast)**

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment with Python 3.13
uv venv --python 3.13

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies (much faster than pip!)
uv pip install -r requirements.txt
uv pip install -r requirements-dev.txt  # For development/testing
```

**Option B: Using traditional venv + pip**

```bash
# Create virtual environment
python3.13 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development/testing
```

### 3. Configure AWS Secrets

Store your Telegram bot token and BitLaunch API key in AWS SSM Parameter Store:

```bash
aws ssm put-parameter \
  --name /telegram-vps-bot/telegram-token \
  --value "YOUR_TELEGRAM_BOT_TOKEN" \
  --type SecureString

aws ssm put-parameter \
  --name /telegram-vps-bot/bitlaunch-api-key \
  --value "YOUR_BITLAUNCH_API_KEY" \
  --type SecureString
```

### 4. Configure Terraform Variables

```bash
cd infrastructure
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your authorized chat IDs
```

### 5. Deploy Infrastructure

```bash
terraform init
terraform plan
terraform apply
```

### 6. Set Telegram Webhook

After deployment, set your Telegram webhook to the API Gateway URL:

```bash
WEBHOOK_URL=$(terraform output -raw api_gateway_webhook_url)
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=${WEBHOOK_URL}"
```

### 7. Test

Send `/id` to your bot to verify it's working.

## Development

### Run Tests

```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Run all tests with coverage
pytest tests/ -v --cov=src

# Run specific test file
pytest tests/test_auth.py -v

# Generate HTML coverage report
pytest --cov=src --cov-report=html --cov-report=term

# View coverage report (opens in browser)
open htmlcov/index.html  # macOS
# xdg-open htmlcov/index.html  # Linux
```

### Code Formatting

```bash
black src/ tests/
flake8 src/ tests/
```

## Project Structure

```
telegram-vps-bot/
├── src/                    # Lambda function source code
│   ├── handler.py          # Lambda entry point
│   ├── telegram_client.py  # Telegram API wrapper
│   ├── bitlaunch_client.py # BitLaunch API wrapper
│   ├── auth.py             # Authorization logic
│   └── config.py           # Configuration management
├── infrastructure/         # Terraform configuration
│   ├── main.tf             # Main infrastructure
│   ├── variables.tf        # Input variables
│   ├── outputs.tf          # Output values
│   └── iam.tf              # IAM roles and policies
├── tests/                  # Unit and integration tests
├── docs/                   # Documentation
│   ├── PRD.md              # Product Requirements Document
│   ├── SETUP.md            # Detailed setup guide
│   └── API.md              # API documentation
├── requirements.txt        # Python dependencies
└── requirements-dev.txt    # Development dependencies
```

## Documentation

- [Product Requirements Document](docs/PRD.md)
- [Setup Guide](docs/SETUP.md)
- [API Documentation](docs/API.md)

## Security

- All secrets stored in AWS SSM Parameter Store (encrypted)
- Chat ID-based authorization
- No hardcoded credentials
- Least-privilege IAM roles
- HTTPS-only communication

## Cost

This bot is designed to run within AWS Free Tier limits:
- Lambda: 1M requests/month free
- API Gateway: 1M requests/month free (first 12 months)
- CloudWatch Logs: 5GB ingestion free
- SSM Parameter Store: Unlimited standard parameters free

**Target monthly cost: $0**

## Troubleshooting

### Bot doesn't respond
- Check CloudWatch Logs: `/aws/lambda/telegram-vps-bot`
- Verify webhook is set correctly
- Ensure Lambda has permissions to read SSM parameters

### "Access denied" message
- Use `/id` to get your chat ID
- Add your chat ID to `authorized_chat_ids` in Terraform variables
- Redeploy: `terraform apply`

### "Server not found" error
- Verify server name exists in BitLaunch dashboard
- Check server name spelling (case-sensitive)

## License

MIT

## Support

For issues and questions, please open an issue in the GitHub repository.
