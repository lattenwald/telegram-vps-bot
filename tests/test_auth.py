"""Tests for ACL-based authorization logic."""

import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


from auth import get_user_providers, is_admin, is_authorized


class TestIsAuthorized:
    """Tests for is_authorized function."""

    def test_admin_has_full_access(self, mock_env_vars, mock_ssm):
        """Test that admin has access to everything."""
        import importlib

        import config as config_module

        config_module.Config._ssm_cache = {}
        config_module.config._acl_cache = None
        importlib.reload(config_module)
        config_module.config._acl_cache = None

        import auth as auth_module

        importlib.reload(auth_module)

        # Admin (123456789) has full access
        assert is_authorized(123456789) is True
        assert is_authorized(123456789, provider="bitlaunch") is True
        assert is_authorized(123456789, provider="kamatera") is True
        assert (
            is_authorized(123456789, provider="bitlaunch", server="any-server") is True
        )

    def test_user_has_provider_access(self, mock_env_vars, mock_ssm):
        """Test that user has access to their configured provider."""
        import importlib

        import config as config_module

        config_module.Config._ssm_cache = {}
        config_module.config._acl_cache = None
        importlib.reload(config_module)
        config_module.config._acl_cache = None

        import auth as auth_module

        importlib.reload(auth_module)

        # User (987654321) has bitlaunch access
        assert is_authorized(987654321) is True
        assert is_authorized(987654321, provider="bitlaunch") is True
        assert (
            is_authorized(987654321, provider="bitlaunch", server="any-server") is True
        )

    def test_user_denied_other_provider(self, mock_env_vars, mock_ssm):
        """Test that user is denied access to unconfigured providers."""
        import importlib

        import config as config_module

        config_module.Config._ssm_cache = {}
        config_module.config._acl_cache = None
        importlib.reload(config_module)
        config_module.config._acl_cache = None

        import auth as auth_module

        importlib.reload(auth_module)

        # User (987654321) has NO kamatera access
        assert is_authorized(987654321, provider="kamatera") is False

    def test_unauthorized_user_denied(self, mock_env_vars, mock_ssm):
        """Test that unauthorized user is denied."""
        import importlib

        import config as config_module

        config_module.Config._ssm_cache = {}
        config_module.config._acl_cache = None
        importlib.reload(config_module)
        config_module.config._acl_cache = None

        import auth as auth_module

        importlib.reload(auth_module)

        # Unknown user
        assert is_authorized(999999999) is False
        assert is_authorized(999999999, provider="bitlaunch") is False


class TestIsAdmin:
    """Tests for is_admin function."""

    def test_admin_is_admin(self, mock_env_vars, mock_ssm):
        """Test that admin is recognized as admin."""
        import importlib

        import config as config_module

        config_module.Config._ssm_cache = {}
        config_module.config._acl_cache = None
        importlib.reload(config_module)
        config_module.config._acl_cache = None

        import auth as auth_module

        importlib.reload(auth_module)

        assert is_admin(123456789) is True

    def test_user_is_not_admin(self, mock_env_vars, mock_ssm):
        """Test that regular user is not admin."""
        import importlib

        import config as config_module

        config_module.Config._ssm_cache = {}
        config_module.config._acl_cache = None
        importlib.reload(config_module)
        config_module.config._acl_cache = None

        import auth as auth_module

        importlib.reload(auth_module)

        assert is_admin(987654321) is False
        assert is_admin(999999999) is False


class TestGetUserProviders:
    """Tests for get_user_providers function."""

    def test_admin_returns_empty_list(self, mock_env_vars, mock_ssm):
        """Test that admin returns empty list (has access to all)."""
        import importlib

        import config as config_module

        config_module.Config._ssm_cache = {}
        config_module.config._acl_cache = None
        importlib.reload(config_module)
        config_module.config._acl_cache = None

        import auth as auth_module

        importlib.reload(auth_module)

        # Admins return empty list - they have access to everything
        assert get_user_providers(123456789) == []

    def test_user_returns_providers(self, mock_env_vars, mock_ssm):
        """Test that user returns their allowed providers."""
        import importlib

        import config as config_module

        config_module.Config._ssm_cache = {}
        config_module.config._acl_cache = None
        importlib.reload(config_module)
        config_module.config._acl_cache = None

        import auth as auth_module

        importlib.reload(auth_module)

        providers = get_user_providers(987654321)
        assert "bitlaunch" in providers

    def test_unknown_user_returns_empty(self, mock_env_vars, mock_ssm):
        """Test that unknown user returns empty list."""
        import importlib

        import config as config_module

        config_module.Config._ssm_cache = {}
        config_module.config._acl_cache = None
        importlib.reload(config_module)
        config_module.config._acl_cache = None

        import auth as auth_module

        importlib.reload(auth_module)

        assert get_user_providers(999999999) == []


class TestACLConfigDataclasses:
    """Tests for ACL config dataclasses."""

    def test_provider_access_all_servers(self):
        """Test ProviderAccess with all servers allowed."""
        from config import ProviderAccess

        access = ProviderAccess(servers=None)
        assert access.can_access_server("any-server") is True

    def test_provider_access_specific_servers(self):
        """Test ProviderAccess with specific servers."""
        from config import ProviderAccess

        access = ProviderAccess(servers=["server-a", "server-b"])
        assert access.can_access_server("server-a") is True
        assert access.can_access_server("server-b") is True
        assert access.can_access_server("server-c") is False

    def test_provider_access_no_servers(self):
        """Test ProviderAccess with no servers (explicit deny)."""
        from config import ProviderAccess

        access = ProviderAccess(servers=[])
        assert access.can_access_server("any-server") is False

    def test_acl_config_is_admin(self):
        """Test ACLConfig.is_admin method."""
        from config import ACLConfig

        acl = ACLConfig(admins={100, 200})
        assert acl.is_admin(100) is True
        assert acl.is_admin(200) is True
        assert acl.is_admin(300) is False

    def test_acl_config_can_access(self):
        """Test ACLConfig.can_access method."""
        from config import ACLConfig, ProviderAccess

        acl = ACLConfig(
            admins={100},
            users={
                200: {"bitlaunch": ProviderAccess(servers=None)},
                300: {"bitlaunch": ProviderAccess(servers=["prod"])},
            },
        )

        # Admin has full access
        assert acl.can_access(100) is True
        assert acl.can_access(100, provider="anything") is True

        # User 200 has bitlaunch access
        assert acl.can_access(200) is True
        assert acl.can_access(200, provider="bitlaunch") is True
        assert acl.can_access(200, provider="kamatera") is False

        # User 300 has limited bitlaunch access
        assert acl.can_access(300, provider="bitlaunch", server="prod") is True
        assert acl.can_access(300, provider="bitlaunch", server="dev") is False

        # Unknown user
        assert acl.can_access(999) is False
