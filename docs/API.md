# API Documentation

This document describes the external APIs used by the Telegram VPS Management Bot.

## Telegram Bot API

The bot uses the Telegram Bot API to receive updates and send messages.

### Base URL
```
https://api.telegram.org/bot<TOKEN>/
```

### Authentication
- Authentication is done via the bot token in the URL
- Token format: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

### Endpoints Used

#### setWebhook
Set the webhook URL for receiving updates.

**Method:** POST

**Endpoint:** `/setWebhook`

**Parameters:**
- `url` (string, required): HTTPS URL to send updates to

**Example:**
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://example.com/webhook"
```

**Response:**
```json
{
  "ok": true,
  "result": true,
  "description": "Webhook was set"
}
```

#### sendMessage
Send a text message to a chat.

**Method:** POST

**Endpoint:** `/sendMessage`

**Parameters:**
- `chat_id` (integer, required): Unique identifier for the target chat
- `text` (string, required): Text of the message
- `parse_mode` (string, optional): "Markdown" or "HTML"

**Example:**
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": 123456789,
    "text": "Hello, world!",
    "parse_mode": "Markdown"
  }'
```

**Response:**
```json
{
  "ok": true,
  "result": {
    "message_id": 123,
    "from": {...},
    "chat": {...},
    "date": 1234567890,
    "text": "Hello, world!"
  }
}
```

#### setMyCommands
Set the list of bot commands visible in the Telegram client.

**Method:** POST

**Endpoint:** `/setMyCommands`

**Parameters:**
- `commands` (array, required): Array of bot commands with `command` and `description`
- `scope` (object, optional): Scope of commands (default, chat, etc.)
- `language_code` (string, optional): Two-letter ISO 639-1 language code

**Example:**
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setMyCommands" \
  -H "Content-Type: application/json" \
  -d '{
    "commands": [
      {"command": "help", "description": "Show available commands"},
      {"command": "id", "description": "Get your chat ID"}
    ]
  }'
```

**Example with scope (specific chat):**
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setMyCommands" \
  -H "Content-Type: application/json" \
  -d '{
    "commands": [
      {"command": "help", "description": "Show available commands"},
      {"command": "reboot", "description": "Reboot a server"}
    ],
    "scope": {"type": "chat", "chat_id": 123456789}
  }'
```

**Response:**
```json
{
  "ok": true,
  "result": true
}
```

**Note:** Setting commands for specific chat IDs may fail if the user hasn't chatted with the bot yet. This is non-critical.

#### getUpdates
Get updates from Telegram (used for debugging, not in production).

**Method:** GET

**Endpoint:** `/getUpdates`

**Example:**
```bash
curl "https://api.telegram.org/bot<TOKEN>/getUpdates"
```

### Webhook Update Format

When Telegram sends an update to the webhook, it uses this format:

```json
{
  "update_id": 123456789,
  "message": {
    "message_id": 1,
    "from": {
      "id": 123456789,
      "is_bot": false,
      "first_name": "John",
      "username": "johndoe"
    },
    "chat": {
      "id": 123456789,
      "first_name": "John",
      "username": "johndoe",
      "type": "private"
    },
    "date": 1234567890,
    "text": "/id"
  }
}
```

### Error Responses

**Format:**
```json
{
  "ok": false,
  "error_code": 400,
  "description": "Bad Request: chat not found"
}
```

**Common Error Codes:**
- `400`: Bad Request
- `401`: Unauthorized (invalid bot token)
- `404`: Not Found
- `429`: Too Many Requests (rate limited)

### Rate Limits
- No official rate limit documented
- Recommended: Max 30 messages per second per chat

### Documentation
- Official Docs: https://core.telegram.org/bots/api
- Webhook Guide: https://core.telegram.org/bots/webhooks

---

## BitLaunch API

The bot uses the BitLaunch API to manage VPS instances.

### Base URL
```
https://api.bitlaunch.io/v1
```

### Authentication
- Authentication uses Bearer token in the Authorization header
- Header format: `Authorization: Bearer <API_KEY>`

### Endpoints Used

#### List Servers
Get a list of all VPS servers in the account.

**Method:** GET

**Endpoint:** `/servers`

**Headers:**
```
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

**Example:**
```bash
curl -X GET "https://api.bitlaunch.io/v1/servers" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json"
```

**Response:**
```json
[
  {
    "id": "server-123",
    "name": "my-vps-server",
    "status": "running",
    "ip": "192.0.2.1",
    "created": "2024-01-15T10:30:00Z",
    "host": {
      "id": "linode",
      "name": "Linode"
    },
    "plan": {
      "id": "nanode-1",
      "name": "Nanode 1GB"
    },
    "region": {
      "id": "us-east",
      "name": "Newark, NJ"
    }
  }
]
```

#### Reboot Server
Reboot a specific VPS server.

**Method:** POST

**Endpoint:** `/servers/{id}/reboot`

**Headers:**
```
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

**URL Parameters:**
- `id` (string, required): Server ID

**Example:**
```bash
curl -X POST "https://api.bitlaunch.io/v1/servers/server-123/reboot" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "status": "rebooting",
  "message": "Server is rebooting"
}
```

### Error Responses

**Format:**
```json
{
  "error": "Not Found",
  "message": "Server with ID 'xyz' not found"
}
```

**HTTP Status Codes:**
- `200`: Success
- `401`: Unauthorized (invalid API key)
- `404`: Not Found (server doesn't exist)
- `429`: Too Many Requests (rate limited)
- `500`: Internal Server Error

### Rate Limits
- **Rate Limit:** 100 requests per minute
- **Header:** `X-RateLimit-Remaining` shows remaining requests

### Server Status Values
- `running`: Server is running
- `stopped`: Server is stopped
- `rebooting`: Server is rebooting
- `creating`: Server is being created
- `deleting`: Server is being deleted

### Documentation
- Official Docs: https://www.bitlaunch.io/api
- API Reference: https://developers.bitlaunch.io

---

## AWS Services

The bot uses several AWS services for operation.

### AWS Systems Manager (SSM) Parameter Store

Used for storing encrypted secrets.

**Parameters Used:**
- `/telegram-vps-bot/telegram-token` (SecureString)
- `/telegram-vps-bot/bitlaunch-api-key` (SecureString)

**Python Example:**
```python
import boto3

ssm = boto3.client('ssm')
response = ssm.get_parameter(
    Name='/telegram-vps-bot/telegram-token',
    WithDecryption=True
)
token = response['Parameter']['Value']
```

### AWS Lambda

Serverless function that runs the bot code.

**Event Format (from API Gateway):**
```json
{
  "resource": "/webhook",
  "path": "/webhook",
  "httpMethod": "POST",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": "{\"update_id\":123,\"message\":{...}}",
  "isBase64Encoded": false
}
```

**Response Format:**
```json
{
  "statusCode": 200,
  "body": "{\"status\":\"ok\"}"
}
```

### Amazon API Gateway

Provides HTTPS endpoint for Telegram webhook.

**Endpoint Format:**
```
https://{api-id}.execute-api.{region}.amazonaws.com/prod/webhook
```

**Integration:** Lambda Proxy Integration

### Amazon CloudWatch Logs

Stores Lambda function logs.

**Log Group:** `/aws/lambda/telegram-vps-bot`

**Log Format:**
```
2024-01-15 10:30:00 INFO Processing message from chat_id: 123456789
2024-01-15 10:30:01 INFO Handling /reboot command for server: test-server
2024-01-15 10:30:02 INFO Successfully rebooted server: test-server
```

---

## Environment Variables

The Lambda function uses these environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `AUTHORIZED_CHAT_IDS` | Comma-separated authorized chat IDs | `123456789,987654321` |
| `BITLAUNCH_API_BASE_URL` | BitLaunch API base URL | `https://api.bitlaunch.io/v1` |
| `SSM_TELEGRAM_TOKEN_PATH` | SSM parameter path for bot token | `/telegram-vps-bot/telegram-token` |
| `SSM_BITLAUNCH_API_KEY_PATH` | SSM parameter path for API key | `/telegram-vps-bot/bitlaunch-api-key` |
| `LOG_LEVEL` | Logging level | `INFO` |

---

## Bot Commands

The bot supports these Telegram commands:

### /id
Get your Telegram chat ID.

**Authorization:** Not required

**Format:** `/id`

**Response:**
```
Your chat ID: `123456789`
```

### /help
Show available commands (different for authorized vs unauthorized users).

**Authorization:** Not required

**Format:** `/help`

**Response (unauthorized users):**
```
Available commands:
/id - Get your chat ID
/help - Show this help message
```

**Response (authorized users):**
```
Available commands:
/id - Get your chat ID
/help - Show this help message
/reboot <server_name> - Reboot a server
```

### /reboot
Reboot a VPS server by name.

**Authorization:** Required

**Format:** `/reboot <server_name>`

**Example:** `/reboot my-vps-server`

**Responses:**
- **Success:** `✓ Server 'my-vps-server' is rebooting`
- **Not Found:** `❌ Error: Server 'xyz' not found`
- **Unauthorized:** `❌ Access denied. Use /id to get your chat ID and request authorization.`
- **Invalid Format:** `❌ Usage: /reboot <server_name>`
- **API Error:** `❌ Error: Unable to reboot server - try again later`

### Unknown Commands
All other commands (including `/start`) are silently ignored with no response.

---

## Security Considerations

### Secrets Management
- All secrets stored in AWS SSM Parameter Store
- Parameters encrypted with AWS KMS
- No secrets in code or environment variables (except chat IDs)

### Authorization
- Chat ID-based authorization
- Unauthorized users cannot execute management commands
- All unauthorized attempts logged

### Network Security
- HTTPS only for all communications
- Telegram webhook signature validation (future enhancement)
- API Gateway throttling enabled

### Logging
- All commands logged to CloudWatch
- Sensitive data redacted from logs
- Unauthorized access attempts recorded

---

## Testing APIs

### Test Telegram Bot Locally

```python
import requests

# Send message
response = requests.post(
    'https://api.telegram.org/bot<TOKEN>/sendMessage',
    json={
        'chat_id': 123456789,
        'text': 'Test message'
    }
)
print(response.json())
```

### Test BitLaunch API

```python
import requests

# List servers
response = requests.get(
    'https://api.bitlaunch.io/v1/servers',
    headers={
        'Authorization': 'Bearer YOUR_API_KEY',
        'Content-Type': 'application/json'
    }
)
print(response.json())
```

### Test Lambda Function Locally

```bash
# Using AWS SAM CLI
sam local invoke telegram-vps-bot -e test-event.json

# Or using Python
python -c "
from handler import lambda_handler
import json

event = {
    'body': json.dumps({
        'message': {
            'chat': {'id': 123456789},
            'text': '/id'
        }
    })
}
result = lambda_handler(event, None)
print(result)
"
```

---

## Monitoring and Metrics

### CloudWatch Metrics
- Lambda invocations
- Lambda errors
- Lambda duration
- API Gateway requests
- API Gateway 4XX errors
- API Gateway 5XX errors

### Useful Queries

**Recent errors:**
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/telegram-vps-bot \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000
```

**Unauthorized access attempts:**
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/telegram-vps-bot \
  --filter-pattern "Unauthorized"
```
