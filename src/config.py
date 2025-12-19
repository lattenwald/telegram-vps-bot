"""Configuration management for Telegram VPS Bot.

Handles loading environment variables and retrieving secrets from AWS SSM Parameter Store.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

SSM_ACL_PATH = "/telegram-vps-bot/acl-config"


@dataclass
class ProviderAccess:
    """Access configuration for a single provider."""

    servers: list[str] | None = None  # None = all servers, [] = no access

    def can_access_server(self, server_name: str) -> bool:
        """Check if user can access a specific server."""
        if self.servers is None:
            return True  # All servers allowed
        if not self.servers:
            return False  # Empty list = no access
        return server_name in self.servers


@dataclass
class ACLConfig:
    """Access Control List configuration."""

    admins: set[int] = field(default_factory=set)
    users: dict[int, dict[str, ProviderAccess]] = field(default_factory=dict)

    def is_admin(self, chat_id: int) -> bool:
        """Check if chat_id is an admin."""
        return chat_id in self.admins

    def get_user_providers(self, chat_id: int) -> list[str]:
        """Get list of providers the user has access to."""
        if self.is_admin(chat_id):
            return []  # Admins handled separately - have access to all
        return list(self.users.get(chat_id, {}).keys())

    def can_access(
        self, chat_id: int, provider: str | None = None, server: str | None = None
    ) -> bool:
        """Check if user can access provider/server."""
        # Admins have full access
        if self.is_admin(chat_id):
            return True

        # Check user permissions
        user_providers = self.users.get(chat_id)
        if not user_providers:
            return False

        # No provider specified - check if user has any access
        if provider is None:
            return bool(user_providers)

        # Check provider access
        provider_access = user_providers.get(provider)
        if provider_access is None:
            return False

        # No server specified - user has provider access
        if server is None:
            return True

        # Check server access
        return provider_access.can_access_server(server)


class Config:
    """Configuration manager for the bot."""

    # Cache for SSM parameters to reduce API calls
    _ssm_cache = {}

    def __init__(self):
        """Initialize configuration from environment variables."""
        self.authorized_chat_ids = self._parse_authorized_chat_ids()
        self.bitlaunch_api_base_url = os.environ.get(
            "BITLAUNCH_API_BASE_URL", "https://api.bitlaunch.io/v1"
        )
        self.ssm_telegram_token_path = os.environ.get(
            "SSM_TELEGRAM_TOKEN_PATH", "/telegram-vps-bot/telegram-token"
        )
        self.ssm_bitlaunch_api_key_path = os.environ.get(
            "SSM_BITLAUNCH_API_KEY_PATH", "/telegram-vps-bot/bitlaunch-api-key"
        )
        self.ssm_credentials_prefix = os.environ.get(
            "SSM_CREDENTIALS_PREFIX", "/telegram-vps-bot/credentials/"
        )
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")

        self._ssm_client = None
        self._credentials_cache: dict[str, dict] = {}
        self._acl_cache: ACLConfig | None = None

    def _parse_authorized_chat_ids(self) -> set:
        """Parse comma-separated authorized chat IDs from environment variable.

        Returns:
            set: Set of authorized chat IDs as integers.
        """
        chat_ids_str = os.environ.get("AUTHORIZED_CHAT_IDS", "")
        if not chat_ids_str:
            logger.warning("No authorized chat IDs configured")
            return set()

        chat_ids = []
        for chat_id_str in chat_ids_str.split(","):
            chat_id_str = chat_id_str.strip()
            if not chat_id_str:
                continue
            try:
                chat_ids.append(int(chat_id_str))
            except ValueError:
                logger.error(f"Invalid chat ID format (skipping): {chat_id_str}")

        return set(chat_ids)

    @property
    def ssm_client(self):
        """Lazy-load SSM client.

        Returns:
            boto3.client: SSM client instance.
        """
        if self._ssm_client is None:
            self._ssm_client = boto3.client("ssm")
        return self._ssm_client

    def get_ssm_parameter(
        self, parameter_name: str, with_decryption: bool = True
    ) -> Optional[str]:
        """Retrieve parameter from AWS SSM Parameter Store with caching.

        Args:
            parameter_name: Name of the SSM parameter.
            with_decryption: Whether to decrypt SecureString parameters.

        Returns:
            str: Parameter value, or None if retrieval fails.
        """
        if parameter_name in self._ssm_cache:
            return self._ssm_cache[parameter_name]

        try:
            response = self.ssm_client.get_parameter(
                Name=parameter_name, WithDecryption=with_decryption
            )
            value = response["Parameter"]["Value"]

            self._ssm_cache[parameter_name] = value

            logger.info(f"Retrieved SSM parameter: {parameter_name}")
            return value

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            logger.error(
                f"Failed to retrieve SSM parameter {parameter_name}: {error_code}"
            )
            return None

    @property
    def telegram_token(self) -> Optional[str]:
        """Get Telegram bot token from SSM.

        Returns:
            str: Telegram bot token, or None if retrieval fails.
        """
        return self.get_ssm_parameter(self.ssm_telegram_token_path)

    @property
    def bitlaunch_api_key(self) -> Optional[str]:
        """Get BitLaunch API key from SSM.

        Returns:
            str: BitLaunch API key, or None if retrieval fails.
        """
        return self.get_ssm_parameter(self.ssm_bitlaunch_api_key_path)

    def get_provider_credentials(self, provider: str) -> dict:
        """Get credentials for a provider from SSM.

        Credentials are stored as JSON in SSM at:
        {ssm_credentials_prefix}{provider}

        Example for BitLaunch:
        /telegram-vps-bot/credentials/bitlaunch -> {"api_key": "..."}

        Example for Kamatera:
        /telegram-vps-bot/credentials/kamatera -> {"client_id": "...", "secret": "..."}

        Args:
            provider: Provider name (e.g., 'bitlaunch', 'kamatera').

        Returns:
            dict: Credentials dictionary, or empty dict if not found.
        """
        if provider in self._credentials_cache:
            return self._credentials_cache[provider]

        param_path = f"{self.ssm_credentials_prefix}{provider}"
        json_str = self.get_ssm_parameter(param_path)

        if not json_str:
            logger.warning(f"No credentials found for provider: {provider}")
            return {}

        try:
            credentials = json.loads(json_str)
            self._credentials_cache[provider] = credentials
            return credentials
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in credentials for {provider}: {e}")
            return {}

    @property
    def acl_config(self) -> ACLConfig:
        """Get ACL configuration from SSM.

        Returns:
            ACLConfig: Parsed ACL configuration.
        """
        if self._acl_cache is not None:
            return self._acl_cache

        json_str = self.get_ssm_parameter(SSM_ACL_PATH)
        if not json_str:
            logger.warning("No ACL config found in SSM, returning empty ACL")
            self._acl_cache = ACLConfig()
            return self._acl_cache

        try:
            data = json.loads(json_str)
            self._acl_cache = self._parse_acl(data)
            logger.info("Loaded ACL config from SSM")
            return self._acl_cache
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Invalid ACL config in SSM: {e}")
            self._acl_cache = ACLConfig()
            return self._acl_cache

    def _parse_acl(self, data: dict) -> ACLConfig:
        """Parse ACL JSON data into ACLConfig object.

        Args:
            data: Raw ACL data from SSM.

        Returns:
            ACLConfig: Parsed configuration.
        """
        admins = set(data.get("admins", []))

        users: dict[int, dict[str, ProviderAccess]] = {}
        for user_id_str, providers in data.get("users", {}).items():
            user_id = int(user_id_str)
            users[user_id] = {}
            for provider_name, provider_config in providers.items():
                if provider_config is None:
                    users[user_id][provider_name] = ProviderAccess()
                else:
                    servers = provider_config.get("servers")
                    users[user_id][provider_name] = ProviderAccess(servers=servers)

        return ACLConfig(admins=admins, users=users)

    def validate(self) -> bool:
        """Validate that all required configuration is present.

        Returns:
            bool: True if configuration is valid, False otherwise.
        """
        is_valid = True

        if not self.telegram_token:
            logger.error("Failed to retrieve Telegram token from SSM")
            is_valid = False

        # Check for BitLaunch credentials in new format
        bitlaunch_creds = self.get_provider_credentials("bitlaunch")
        if not bitlaunch_creds.get("api_key"):
            logger.error("Failed to retrieve BitLaunch credentials from SSM")
            is_valid = False

        # Check ACL config
        acl = self.acl_config
        if not acl.admins and not acl.users:
            logger.warning("No users configured in ACL")

        return is_valid


# Global configuration instance
config = Config()
