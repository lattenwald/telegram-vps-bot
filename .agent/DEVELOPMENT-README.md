# telegram-vps-bot Development Guide

**Project**: Telegram VPS Management Bot
**Tech Stack**: Python 3.13, AWS Lambda, Terraform, Boto3, Requests
**Initialized**: 2025-11-10

---

## Quick Start

### Start Development Session
```
Start my Navigator session
```

### Common Commands
- Create task plan: `Create task for [feature]`
- Document solution: `Create SOP for [issue]`
- Save progress: `Create context marker`
- Compact context: `Compact conversation`

---

## Project Overview

A serverless Telegram bot deployed on AWS Lambda that enables authorized users to manage VPS instances through the BitLaunch.io API via simple chat commands.

### Key Features
- `/id` - Get Telegram chat ID (no auth required)
- `/reboot <server_name>` - Reboot VPS server (auth required)
- Chat ID-based authorization
- AWS SSM Parameter Store for secrets
- Comprehensive test coverage (82%)

### Architecture
```
Telegram API → API Gateway → Lambda Function → BitLaunch API
                                ↓
                          SSM Parameter Store
                          CloudWatch Logs
```

---

## Directory Structure

```
telegram-vps-bot/
├── .agent/                 # Navigator documentation
│   ├── tasks/             # Implementation plans
│   ├── system/            # Architecture docs
│   ├── sops/              # Standard Operating Procedures
│   └── grafana/           # Metrics dashboard
├── src/                   # Lambda function source code
│   ├── handler.py         # Lambda entry point
│   ├── telegram_client.py # Telegram API wrapper
│   ├── bitlaunch_client.py# BitLaunch API wrapper
│   ├── auth.py            # Authorization logic
│   └── config.py          # Configuration management
├── infrastructure/        # Terraform configuration
├── tests/                 # Pytest test suite
└── docs/                  # Documentation
    ├── PRD.md            # Product Requirements
    ├── SETUP.md          # Deployment guide
    └── API.md            # API reference
```

---

## Development Workflow

### 1. Setup Environment
```bash
# Install Python 3.13 with asdf
asdf install python 3.13.1
asdf local python 3.13.1

# Create virtual environment with uv
uv venv --python 3.13
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
uv pip install -r requirements-dev.txt
```

### 2. Run Tests
```bash
# Run all tests with coverage
pytest tests/ -v --cov=src --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v

# View coverage report
open htmlcov/index.html
```

### 3. Deploy to AWS
```bash
# Store secrets in SSM
aws ssm put-parameter --name /telegram-vps-bot/telegram-token \
  --value "YOUR_TOKEN" --type SecureString

aws ssm put-parameter --name /telegram-vps-bot/bitlaunch-api-key \
  --value "YOUR_KEY" --type SecureString

# Configure Terraform
cd infrastructure
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your chat IDs

# Deploy
terraform init
terraform plan
terraform apply

# Set Telegram webhook
WEBHOOK_URL=$(terraform output -raw api_gateway_webhook_url)
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=${WEBHOOK_URL}"
```

---

## Testing Strategy

### Test Coverage
- **Overall**: 82% (exceeds 80% requirement)
- **auth.py**: 100%
- **config.py**: 97%
- **telegram_client.py**: 89%
- **bitlaunch_client.py**: 81%

### Test Categories
1. **Unit Tests**: Authorization, config parsing, API clients
2. **Integration Tests**: Lambda handler, end-to-end flows
3. **Mocked Services**: AWS SSM (moto), HTTP requests (responses)

---

## Common Tasks

### Add New Command
1. Create task: `Create task for adding /status command`
2. Update `src/handler.py` - Add command handler
3. Update `tests/test_handler.py` - Add test cases
4. Run tests: `pytest tests/test_handler.py -v`
5. Deploy: `terraform apply`

### Update Dependencies
```bash
# Update package
uv pip install --upgrade boto3

# Freeze requirements
uv pip freeze > requirements.txt

# Run tests to ensure compatibility
pytest tests/ -v
```

### Debug Lambda Function
```bash
# View recent logs
aws logs tail /aws/lambda/telegram-vps-bot --follow

# Filter for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/telegram-vps-bot \
  --filter-pattern "ERROR"
```

---

## Active Tasks

| Task | Description | Status | Depends On |
|------|-------------|--------|------------|
| [TASK-001](tasks/TASK-001-multi-provider-acl.md) | Multi-provider ACL with Kamatera support | ✅ Deployed | - |
| [TASK-002](tasks/TASK-002-dynamodb-caching.md) | DynamoDB caching for server-provider mapping | ⏸️ Postponed | TASK-001 |
| [TASK-003](tasks/TASK-003-bot-admin-commands.md) | Bot admin commands for ACL management | ⏸️ Postponed | TASK-001 |

---

## Navigator Workflow

### Task Management
Tasks are stored in `.agent/tasks/` with format:
```
TASK-001-multi-provider-acl.md
TASK-002-dynamodb-caching.md
```

### SOPs (Standard Operating Procedures)
Documented solutions in `.agent/sops/`:
- `integrations/` - Third-party integrations
- `debugging/` - Common issues and fixes
- `development/` - Development patterns
- `deployment/` - Deployment procedures

### Context Markers
Before major changes or breaks:
```
Create context marker: "Before adding multi-server support"
```

---

## Resources

- [Product Requirements](../docs/PRD.md)
- [Setup Guide](../docs/SETUP.md)
- [API Documentation](../docs/API.md)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [BitLaunch API](https://www.bitlaunch.io/api)
- [AWS Lambda Python](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)

---

## Notes

- All secrets must be in AWS SSM Parameter Store
- Test coverage must stay above 80%
- Follow Python type hints throughout
- Lambda timeout: 30 seconds
- Target cost: $0/month (AWS Free Tier)
