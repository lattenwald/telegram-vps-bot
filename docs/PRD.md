# Product Requirements Document: Telegram VPS Management Bot

**Version:** 1.0
**Date:** 2025-11-10
**Status:** Draft
**Author:** System Architecture Team

---

## 1. Executive Summary

### 1.1 Product Overview
A serverless Telegram bot deployed on AWS Lambda that enables authorized users to manage VPS instances through the BitLaunch.io API via simple chat commands. The bot provides secure, cost-effective VPS management directly from Telegram.

### 1.2 Business Goals
- Automate VPS management tasks through a convenient Telegram interface
- Eliminate manual login to BitLaunch.io dashboard for routine operations
- Provide secure, authorized-only access to sensitive infrastructure operations
- Maintain zero operational costs using AWS Free Tier

### 1.3 Success Metrics
- Bot response time < 3 seconds for all commands
- 100% uptime during AWS service availability
- Zero monthly costs within AWS Free Tier limits
- Zero unauthorized command executions

---

## 2. User Requirements

### 2.1 Target Users
- **Primary**: VPS owners with BitLaunch.io accounts
- **Secondary**: DevOps engineers managing multiple VPS instances
- **Tertiary**: Small teams sharing VPS infrastructure management

### 2.2 User Stories

#### US-001: Get Chat ID
**As a** new user
**I want to** retrieve my Telegram chat ID
**So that** I can request authorization from the bot administrator

**Acceptance Criteria:**
- Any user can send `/id` command
- Bot responds with the user's chat ID
- Response time < 1 second
- No authorization required

#### US-002: Reboot VPS
**As an** authorized user
**I want to** reboot my VPS by server name
**So that** I can quickly restart services without accessing the dashboard

**Acceptance Criteria:**
- Only authorized users can execute command
- Command format: `/reboot <server_name>`
- Bot validates server name exists in BitLaunch account
- Bot calls BitLaunch API to trigger reboot
- Bot confirms successful reboot initiation
- Bot reports errors clearly (invalid server, API failure, etc.)

#### US-003: Unauthorized Access Prevention
**As a** bot administrator
**I want to** prevent unauthorized users from executing management commands
**So that** my infrastructure remains secure

**Acceptance Criteria:**
- Unauthorized users receive "Access denied" message
- All unauthorized attempts are logged
- No sensitive information is revealed in error messages
- Authorization list is maintained separately from code

---

## 3. Functional Requirements

### 3.1 Command Interface

#### 3.1.1 Unauthorized Commands
| Command | Parameters | Response | Authorization |
|---------|------------|----------|---------------|
| `/id` | None | Your chat ID: `<chat_id>` | Not required |
| `/help` | None | Available commands list | Not required |

#### 3.1.2 Authorized Commands
| Command | Parameters | Response | Authorization |
|---------|------------|----------|---------------|
| `/reboot` | `<server_name>` | Rebooting server `<server_name>`... ✓ | Required |

### 3.2 Authorization Mechanism

**Requirements:**
- Chat ID-based authorization
- Configurable authorization list
- No hardcoded chat IDs in source code
- Support for 1-50 authorized users

**Implementation:**
- Phase 1: Environment variable with comma-separated chat IDs
- Phase 2 (future): DynamoDB table for dynamic management

### 3.3 BitLaunch.io API Integration

**Required API Endpoints:**
- `GET /servers` - List available servers
- `POST /servers/{id}/reboot` - Reboot specific server

**Error Handling:**
- Invalid server name → "Server not found"
- API authentication failure → "Configuration error"
- Network timeout → "BitLaunch API unavailable"
- Rate limiting → "Too many requests, try again later"

### 3.4 Security Requirements

#### 3.4.1 Secret Management
- Telegram Bot Token stored in AWS SSM Parameter Store (SecureString)
- BitLaunch API Key stored in AWS SSM Parameter Store (SecureString)
- No secrets in code, logs, or environment variables (except chat IDs)

#### 3.4.2 Access Control
- Least-privilege IAM roles for Lambda function
- Lambda can only read specific SSM parameters
- No write access to any AWS resources
- CloudWatch logging with sensitive data redaction

#### 3.4.3 API Security
- Telegram webhook signature validation
- HTTPS-only communication
- Request timeout limits (30 seconds max)

---

## 4. Non-Functional Requirements

### 4.1 Performance
- Cold start latency: < 2 seconds
- Warm invocation latency: < 500ms
- API response time: < 3 seconds end-to-end
- Maximum concurrent users: 10

### 4.2 Availability
- Uptime: 99.9% (excluding AWS service outages)
- No scheduled downtime for deployments
- Graceful degradation on BitLaunch API failures

### 4.3 Scalability
- Support 1,000 requests/month (within free tier)
- Horizontal scaling via Lambda auto-scaling
- No performance degradation up to 100 concurrent requests

### 4.4 Monitoring & Observability
- All commands logged to CloudWatch
- Error tracking with stack traces
- Unauthorized access attempt logging
- API call success/failure metrics

### 4.5 Cost Constraints
- **Hard Requirement**: Stay within AWS Free Tier
- Monthly cost target: $0
- Alert if approaching free tier limits

---

## 5. Technical Architecture

### 5.1 AWS Components

```
Telegram API → API Gateway → Lambda Function → BitLaunch API
                                ↓
                          SSM Parameter Store
                          CloudWatch Logs
```

### 5.2 Technology Stack

| Component | Technology | Justification |
|-----------|------------|---------------|
| Runtime | Python 3.13 | Latest LTS, native AWS SDK, simple syntax, rich ecosystem, supported until 2029 |
| HTTP Client | `requests` | Standard, reliable, well-documented |
| Infrastructure | Terraform | Infrastructure as Code, version control, reproducibility |
| Deployment | AWS CLI / Terraform | Free tier compatible, automated |
| Testing | pytest | Python standard, comprehensive |

### 5.3 Data Flow

1. User sends command via Telegram
2. Telegram forwards to API Gateway webhook
3. API Gateway triggers Lambda function
4. Lambda validates Telegram signature
5. Lambda checks user authorization
6. Lambda retrieves secrets from SSM
7. Lambda calls BitLaunch API
8. Lambda responds to Telegram API
9. User receives response in Telegram

### 5.4 Error Handling Strategy

| Error Type | Handling | User Message |
|------------|----------|--------------|
| Unauthorized access | Log + reject | "Access denied. Use /id to get your chat ID." |
| Invalid command format | Parse error | "Usage: /reboot <server_name>" |
| Server not found | Validate server list | "Server '<name>' not found" |
| BitLaunch API error | Retry once, then fail | "Unable to reboot server. Try again later." |
| Network timeout | Timeout after 30s | "Request timed out" |

---

## 6. Infrastructure Requirements

### 6.1 AWS Resources

**Lambda Function:**
- Runtime: Python 3.13
- Memory: 256 MB
- Timeout: 30 seconds
- Concurrent executions: 10
- Reserved concurrency: Not required

**API Gateway:**
- Type: REST API
- Endpoint: Regional
- Stage: `prod`
- Throttling: 100 requests/second

**SSM Parameter Store:**
- `/telegram-vps-bot/telegram-token` (SecureString)
- `/telegram-vps-bot/bitlaunch-api-key` (SecureString)

**IAM Role:**
- Service: lambda.amazonaws.com
- Policies:
  - `AWSLambdaBasicExecutionRole` (CloudWatch Logs)
  - Custom policy for SSM parameter read access

**CloudWatch Log Group:**
- Name: `/aws/lambda/telegram-vps-bot`
- Retention: 7 days
- Log level: INFO

### 6.2 Configuration Parameters

**Environment Variables:**
```
AUTHORIZED_CHAT_IDS=<comma-separated-list>
BITLAUNCH_API_BASE_URL=https://api.bitlaunch.io/v1
SSM_TELEGRAM_TOKEN_PATH=/telegram-vps-bot/telegram-token
SSM_BITLAUNCH_API_KEY_PATH=/telegram-vps-bot/bitlaunch-api-key
LOG_LEVEL=INFO
```

---

## 7. Development & Deployment

### 7.1 Project Structure

```
telegram-vps-bot/
├── src/
│   ├── handler.py              # Lambda entry point
│   ├── telegram_client.py      # Telegram API wrapper
│   ├── bitlaunch_client.py     # BitLaunch API wrapper
│   ├── auth.py                 # Authorization logic
│   └── config.py               # Configuration management
├── infrastructure/
│   ├── main.tf                 # Terraform main config
│   ├── variables.tf            # Terraform variables
│   ├── outputs.tf              # Terraform outputs
│   └── iam.tf                  # IAM roles and policies
├── tests/
│   ├── test_handler.py
│   ├── test_bitlaunch_client.py
│   └── test_auth.py
├── docs/
│   ├── PRD.md                  # This document
│   ├── SETUP.md                # Deployment guide
│   └── API.md                  # API documentation
├── requirements.txt            # Python dependencies
├── requirements-dev.txt        # Development dependencies
├── .gitignore
└── README.md
```

### 7.2 Development Workflow

1. Local development with mocked AWS services
2. Unit tests with pytest (>80% coverage)
3. Integration tests with LocalStack
4. Terraform plan review
5. Deploy to AWS
6. Set Telegram webhook
7. Manual smoke testing

### 7.3 Deployment Process

**Prerequisites:**
- AWS account with CLI configured
- Terraform installed
- Python 3.13 installed
- BitLaunch.io account with API key
- Telegram bot token from @BotFather

**Steps:**
1. Clone repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure SSM parameters (Telegram token, BitLaunch API key)
4. Update `terraform.tfvars` with chat IDs
5. Run `terraform plan`
6. Run `terraform apply`
7. Set Telegram webhook to API Gateway URL
8. Test with `/id` command

---

## 8. Testing Strategy

### 8.1 Unit Tests
- Command parsing logic
- Authorization checks
- BitLaunch API client mocking
- Error handling paths
- **Target Coverage**: 85%

### 8.2 Integration Tests
- End-to-end webhook simulation
- SSM parameter retrieval
- BitLaunch API interaction (staging environment)

### 8.3 Security Tests
- Unauthorized access attempts
- Invalid Telegram signatures
- SQL injection in server names
- Secret exposure in logs

### 8.4 Performance Tests
- Cold start measurement
- Concurrent request handling
- Timeout scenarios

---

## 9. Future Enhancements (Out of Scope for v1.0)

### 9.1 Additional Commands
- `/status <server_name>` - Check server status
- `/list` - List all servers
- `/start <server_name>` - Start stopped server
- `/stop <server_name>` - Stop running server

### 9.2 Advanced Features
- Multiple VPS provider support (DigitalOcean, AWS EC2)
- Scheduled reboots
- Server health monitoring with alerts
- Usage statistics and cost tracking
- Multi-language support

### 9.3 Infrastructure Improvements
- DynamoDB for dynamic user management
- Lambda@Edge for global distribution
- SQS for async operations
- Step Functions for complex workflows

---

## 10. Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Exceeding AWS Free Tier | High | Low | CloudWatch billing alarms at $1 |
| BitLaunch API changes | High | Medium | Version API endpoints, error handling |
| Unauthorized access | Critical | Low | Multi-layer authorization, audit logging |
| Lambda cold starts | Medium | High | Keep function warm with scheduled pings |
| Secret exposure | Critical | Low | SSM encryption, no logging of secrets |

---

## 11. Success Criteria

### 11.1 Launch Criteria
- ✅ All unit tests passing
- ✅ Integration tests passing
- ✅ Security review completed
- ✅ Documentation complete
- ✅ Terraform deployment successful
- ✅ Manual testing of all commands

### 11.2 Post-Launch Metrics (30 days)
- Zero security incidents
- 99.9% uptime
- <3s average response time
- $0 AWS costs
- Zero unauthorized command executions

---

## 12. Appendices

### 12.1 BitLaunch API Reference
- Documentation: https://www.bitlaunch.io/api
- Authentication: Bearer token
- Rate Limits: 100 requests/minute

### 12.2 Telegram Bot API Reference
- Documentation: https://core.telegram.org/bots/api
- Webhook setup: https://core.telegram.org/bots/webhooks

### 12.3 AWS Free Tier Limits
- Lambda: 1M requests/month, 400K GB-seconds
- API Gateway: 1M requests/month (first 12 months)
- CloudWatch Logs: 5GB ingestion
- SSM Parameter Store: Unlimited standard parameters

### 12.4 Glossary
- **VPS**: Virtual Private Server
- **SSM**: AWS Systems Manager
- **IAM**: Identity and Access Management
- **API Gateway**: AWS managed API gateway service
- **Cold Start**: Initial Lambda invocation latency

---

## 13. Approval & Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product Owner | - | - | - |
| Tech Lead | - | - | - |
| Security Review | - | - | - |

---

**Document Status:** Ready for Implementation
**Next Review Date:** 2025-12-10
**Change History:**
- 2025-11-10: Initial draft created
