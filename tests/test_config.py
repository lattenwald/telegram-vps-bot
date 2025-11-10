"""Tests for configuration management."""

import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest


def test_config_authorized_chat_ids(mock_env_vars):
    """Test parsing authorized chat IDs from environment."""
    from config import Config

    config = Config()
    assert 123456789 in config.authorized_chat_ids
    assert 987654321 in config.authorized_chat_ids
    assert len(config.authorized_chat_ids) == 2


def test_config_with_empty_chat_ids():
    """Test config with empty authorized chat IDs."""
    os.environ["AUTHORIZED_CHAT_IDS"] = ""
    from config import Config

    config = Config()
    assert len(config.authorized_chat_ids) == 0


def test_config_with_invalid_chat_ids():
    """Test config with invalid chat ID format."""
    os.environ["AUTHORIZED_CHAT_IDS"] = "invalid,not-a-number,123"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    # Reload config
    import importlib

    import config as config_module

    config_module.Config._ssm_cache = {}
    importlib.reload(config_module)
    from config import Config

    config = Config()
    # Should only include the valid ID (invalid ones are skipped with error logged)
    assert 123 in config.authorized_chat_ids


def test_config_default_values(mock_env_vars):
    """Test default configuration values."""
    from config import Config

    config = Config()
    assert config.bitlaunch_api_base_url == "https://api.bitlaunch.io/v1"
    assert config.ssm_telegram_token_path == "/telegram-vps-bot/telegram-token"
    assert config.ssm_bitlaunch_api_key_path == "/telegram-vps-bot/bitlaunch-api-key"
    assert config.log_level == "INFO"


def test_get_ssm_parameter(mock_env_vars, mock_ssm):
    """Test retrieving SSM parameter."""
    from config import Config

    config = Config()
    token = config.get_ssm_parameter("/telegram-vps-bot/telegram-token")
    assert token == "test-telegram-token-123"


def test_get_ssm_parameter_caching(mock_env_vars, mock_ssm):
    """Test that SSM parameters are cached."""
    from config import Config

    config = Config()

    # First call - should fetch from SSM
    token1 = config.get_ssm_parameter("/telegram-vps-bot/telegram-token")

    # Second call - should use cache
    token2 = config.get_ssm_parameter("/telegram-vps-bot/telegram-token")

    assert token1 == token2
    assert token1 == "test-telegram-token-123"


def test_get_ssm_parameter_not_found(mock_env_vars, mock_ssm):
    """Test retrieving non-existent SSM parameter."""
    from config import Config

    config = Config()
    value = config.get_ssm_parameter("/non-existent-parameter")
    assert value is None


def test_telegram_token_property(mock_env_vars, mock_ssm):
    """Test telegram_token property."""
    from config import Config

    config = Config()
    assert config.telegram_token == "test-telegram-token-123"


def test_bitlaunch_api_key_property(mock_env_vars, mock_ssm):
    """Test bitlaunch_api_key property."""
    from config import Config

    config = Config()
    assert config.bitlaunch_api_key == "test-bitlaunch-key-456"


def test_validate_success(mock_env_vars, mock_ssm):
    """Test configuration validation success."""
    from config import Config

    config = Config()
    assert config.validate() is True


def test_validate_missing_telegram_token(mock_env_vars, mock_ssm):
    """Test validation fails when Telegram token is missing."""
    from config import Config

    # Change the path to a non-existent parameter
    os.environ["SSM_TELEGRAM_TOKEN_PATH"] = "/non-existent"

    config = Config()
    assert config.validate() is False


def test_validate_missing_bitlaunch_key(mock_env_vars, mock_ssm):
    """Test validation fails when BitLaunch API key is missing."""
    from config import Config

    # Change the path to a non-existent parameter
    os.environ["SSM_BITLAUNCH_API_KEY_PATH"] = "/non-existent"

    config = Config()
    assert config.validate() is False
