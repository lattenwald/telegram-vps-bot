"""Pytest fixtures for testing Telegram VPS Bot."""

import json
import os
import sys

import pytest
from moto import mock_aws


@pytest.fixture
def mock_env_vars():
    """Set up mock environment variables."""
    os.environ["AUTHORIZED_CHAT_IDS"] = "123456789,987654321"
    os.environ["BITLAUNCH_API_BASE_URL"] = "https://api.bitlaunch.io/v1"
    os.environ["SSM_TELEGRAM_TOKEN_PATH"] = "/telegram-vps-bot/telegram-token"
    os.environ["SSM_BITLAUNCH_API_KEY_PATH"] = "/telegram-vps-bot/bitlaunch-api-key"
    os.environ["SSM_CREDENTIALS_PREFIX"] = "/telegram-vps-bot/credentials/"
    os.environ["LOG_LEVEL"] = "INFO"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    # Clear config cache and reload module
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    import config as config_module

    config_module.Config._ssm_cache = {}
    import importlib

    importlib.reload(config_module)
    # Clear credentials and ACL cache on the reloaded config instance
    config_module.config._credentials_cache = {}
    config_module.config._acl_cache = None

    yield

    # Cleanup
    for key in [
        "AUTHORIZED_CHAT_IDS",
        "BITLAUNCH_API_BASE_URL",
        "SSM_TELEGRAM_TOKEN_PATH",
        "SSM_BITLAUNCH_API_KEY_PATH",
        "SSM_CREDENTIALS_PREFIX",
        "LOG_LEVEL",
        "AWS_DEFAULT_REGION",
    ]:
        os.environ.pop(key, None)

    # Clear cache again
    config_module.Config._ssm_cache = {}
    config_module.config._credentials_cache = {}
    config_module.config._acl_cache = None


@pytest.fixture
def mock_ssm():
    """Mock AWS SSM Parameter Store."""
    with mock_aws():
        import boto3

        ssm = boto3.client("ssm", region_name="us-east-1")

        # Create test parameters
        ssm.put_parameter(
            Name="/telegram-vps-bot/telegram-token",
            Value="test-telegram-token-123",
            Type="SecureString",
        )
        ssm.put_parameter(
            Name="/telegram-vps-bot/bitlaunch-api-key",
            Value="test-bitlaunch-key-456",
            Type="SecureString",
        )
        # New format: provider credentials as JSON
        ssm.put_parameter(
            Name="/telegram-vps-bot/credentials/bitlaunch",
            Value=json.dumps({"api_key": "test-bitlaunch-key-456"}),
            Type="SecureString",
        )
        # ACL config
        ssm.put_parameter(
            Name="/telegram-vps-bot/acl-config",
            Value=json.dumps(
                {
                    "admins": [123456789],
                    "users": {"987654321": {"bitlaunch": {"servers": None}}},
                }
            ),
            Type="SecureString",
        )

        yield ssm


@pytest.fixture
def sample_telegram_update():
    """Sample Telegram webhook update."""
    return {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser",
            },
            "chat": {
                "id": 123456789,
                "first_name": "Test",
                "username": "testuser",
                "type": "private",
            },
            "date": 1234567890,
            "text": "/id",
        },
    }


@pytest.fixture
def sample_api_gateway_event(sample_telegram_update):
    """Sample API Gateway event with Telegram update."""
    return {
        "resource": "/webhook",
        "path": "/webhook",
        "httpMethod": "POST",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(sample_telegram_update),
        "isBase64Encoded": False,
    }


@pytest.fixture
def sample_bitlaunch_servers():
    """Sample BitLaunch servers response."""
    return [
        {
            "id": "server-123",
            "name": "test-server-1",
            "status": "running",
            "ip": "1.2.3.4",
        },
        {
            "id": "server-456",
            "name": "test-server-2",
            "status": "running",
            "ip": "5.6.7.8",
        },
    ]


@pytest.fixture
def authorized_chat_id():
    """Authorized chat ID for testing."""
    return 123456789


@pytest.fixture
def unauthorized_chat_id():
    """Unauthorized chat ID for testing."""
    return 999999999
