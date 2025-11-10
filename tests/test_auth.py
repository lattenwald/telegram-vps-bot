"""Tests for authorization logic."""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from auth import is_authorized, get_authorized_chat_ids


def test_is_authorized_with_authorized_id(mock_env_vars):
    """Test that authorized chat ID returns True."""
    import importlib
    import auth as auth_module
    importlib.reload(auth_module)
    from auth import is_authorized
    assert is_authorized(123456789) is True


def test_is_authorized_with_unauthorized_id(mock_env_vars):
    """Test that unauthorized chat ID returns False."""
    assert is_authorized(999999999) is False


def test_is_authorized_with_multiple_authorized_ids(mock_env_vars):
    """Test that both authorized chat IDs return True."""
    import importlib
    import auth as auth_module
    importlib.reload(auth_module)
    from auth import is_authorized
    assert is_authorized(123456789) is True
    assert is_authorized(987654321) is True


def test_is_authorized_with_no_config():
    """Test that authorization fails when no chat IDs are configured."""
    # Clear environment variable
    os.environ.pop('AUTHORIZED_CHAT_IDS', None)

    # Need to reload config to pick up new env vars
    import importlib
    import config as config_module
    config_module.Config._ssm_cache = {}
    importlib.reload(config_module)

    # Reload auth module too
    import auth as auth_module
    importlib.reload(auth_module)
    from auth import is_authorized

    assert is_authorized(123456789) is False


def test_get_authorized_chat_ids(mock_env_vars):
    """Test getting the set of authorized chat IDs."""
    import importlib
    import auth as auth_module
    importlib.reload(auth_module)
    from auth import get_authorized_chat_ids
    authorized_ids = get_authorized_chat_ids()
    assert isinstance(authorized_ids, set)
    assert 123456789 in authorized_ids
    assert 987654321 in authorized_ids
    assert len(authorized_ids) == 2


def test_is_authorized_with_empty_string(mock_env_vars):
    """Test authorization with empty environment variable."""
    os.environ['AUTHORIZED_CHAT_IDS'] = ''

    # Reload config
    import importlib
    import config as config_module
    config_module.Config._ssm_cache = {}
    importlib.reload(config_module)

    # Reload auth module too
    import auth as auth_module
    importlib.reload(auth_module)
    from auth import is_authorized

    assert is_authorized(123456789) is False


def test_is_authorized_with_invalid_format(mock_env_vars):
    """Test authorization with invalid chat ID format."""
    os.environ['AUTHORIZED_CHAT_IDS'] = 'invalid,not-a-number'

    # Reload config
    import importlib
    import config as config_module
    config_module.Config._ssm_cache = {}
    importlib.reload(config_module)

    # Reload auth module too
    import auth as auth_module
    importlib.reload(auth_module)
    from auth import is_authorized

    # Should handle invalid format gracefully and return False
    assert is_authorized(123456789) is False
