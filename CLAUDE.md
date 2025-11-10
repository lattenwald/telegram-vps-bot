# Claude Development Instructions - Telegram VPS Bot

## Project Context

This is a serverless Telegram bot for managing VPS instances via BitLaunch.io API, deployed on AWS Lambda.

**Tech Stack**: Python 3.13, AWS Lambda, Terraform, Boto3, Requests
**Architecture**: Telegram → API Gateway → Lambda → BitLaunch API
**Testing**: Pytest with 82% coverage
**Deployment**: Terraform IaC, AWS Free Tier ($0/month target)

---

## Navigator Workflow

### Session Management
When starting work, load Navigator documentation:
```
Read .agent/DEVELOPMENT-README.md
```

### Task Documentation
For new features or significant changes:
1. Create task plan in `.agent/tasks/`
2. Document implementation steps
3. Archive when complete

### Save Progress
Before breaks or risky changes:
```
Create context marker: "Description of current state"
```

### Document Solutions
After solving novel issues:
```
Create SOP in .agent/sops/[category]/
```

---

## Development Rules

### Code Quality
- ✅ Maintain >80% test coverage
- ✅ Use Python type hints throughout
- ✅ Follow existing code patterns
- ✅ Keep functions small and focused
- ✅ Format code with ruff before committing
- ❌ Never commit secrets to git

### Code Formatting
```bash
# Format all Python code
ruff format .

# Fix import sorting
ruff check --select I --fix .

# Run both before committing
ruff format . && ruff check --select I --fix .
```

### Security Requirements
- All secrets in AWS SSM Parameter Store
- Chat ID-based authorization only
- No secrets in logs or environment variables
- Validate all user inputs
- Use least-privilege IAM roles

### Testing Requirements
```bash
# Before committing
pytest tests/ -v --cov=src --cov-report=term

# Coverage must be >80%
# All tests must pass
```

### File Organization
```
src/          - Lambda source code (keep imports clean)
tests/        - Pytest tests (mock AWS with moto)
infrastructure/ - Terraform only (no manual AWS changes)
docs/         - Markdown documentation
.agent/       - Navigator workflow documentation
```

---

## Common Patterns

### Adding New Commands

**1. Update Handler**
```python
# src/handler.py
def handle_new_command(telegram, bitlaunch, chat_id, arg):
    if not is_authorized(chat_id):
        telegram.send_error_message(chat_id, "Access denied")
        return
    # Implementation
```

**2. Add Tests**
```python
# tests/test_handler.py
def test_lambda_handler_new_command_authorized(...):
    # Test authorized access

def test_lambda_handler_new_command_unauthorized(...):
    # Test unauthorized access
```

**3. Update Documentation**
- README.md - Add to commands table
- docs/API.md - Document API usage
- docs/PRD.md - Update if changing requirements

### Environment Variables
```python
# Always use config module
from config import config

# Never use os.environ directly in business logic
```

### Error Handling
```python
# User-friendly messages
telegram.send_error_message(chat_id, "Server 'xyz' not found")

# Log technical details
logger.error(f"BitLaunch API error: {error_code}")
```

---

## Deployment Workflow

### Local Testing
```bash
# 1. Run tests
pytest tests/ -v

# 2. Check code formatting
black src/ tests/ --check
flake8 src/ tests/

# 3. Manual smoke test (optional)
python -c "from handler import lambda_handler; print('Import OK')"
```

### Deploy to AWS
```bash
cd infrastructure
terraform plan
terraform apply
```

### Verify Deployment
```bash
# Check Lambda function
aws lambda get-function --function-name telegram-vps-bot

# View logs
aws logs tail /aws/lambda/telegram-vps-bot --follow

# Test bot
# Send /id to bot in Telegram
```

---

## Troubleshooting

### Tests Failing
1. Check if modules need reloading (config caching)
2. Verify mock fixtures are applied
3. Check AWS_DEFAULT_REGION is set in tests

### Lambda Errors
```bash
# View CloudWatch logs
aws logs tail /aws/lambda/telegram-vps-bot --follow

# Check SSM parameters exist
aws ssm get-parameter --name /telegram-vps-bot/telegram-token --with-decryption

# Verify IAM permissions
aws iam get-role-policy --role-name telegram-vps-bot-lambda-role \
  --policy-name telegram-vps-bot-ssm-access
```

### Bot Not Responding
1. Check webhook is set: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`
2. Verify API Gateway endpoint exists
3. Check Lambda function logs for errors
4. Ensure chat ID is in authorized list

---

## References

- **PRD**: [docs/PRD.md](docs/PRD.md) - Product requirements
- **Setup**: [docs/SETUP.md](docs/SETUP.md) - Deployment guide
- **API**: [docs/API.md](docs/API.md) - API documentation
- **Navigator**: [.agent/DEVELOPMENT-README.md](.agent/DEVELOPMENT-README.md) - Workflow guide

---

## Quick Commands

```bash
# Start dev session
source .venv/bin/activate

# Run tests
pytest tests/ -v

# Format code
black src/ tests/

# Deploy
cd infrastructure && terraform apply

# View logs
aws logs tail /aws/lambda/telegram-vps-bot --follow
```
