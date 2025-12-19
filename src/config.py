"""Configuration management for Telegram VPS Bot.

Handles loading environment variables and retrieving secrets from AWS SSM Parameter Store.
"""

import json
import logging
import os
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


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

        if not self.authorized_chat_ids:
            logger.warning("No authorized chat IDs configured")

        return is_valid


# Global configuration instance
config = Config()
