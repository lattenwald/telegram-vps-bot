"""Telegram API client for sending messages.

Provides methods to interact with the Telegram Bot API.
"""

import logging
from typing import Any, Dict, List, Optional

import requests
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)


class TelegramError(Exception):
    """Base exception for Telegram API errors."""

    pass


class TelegramClient:
    """Client for interacting with the Telegram Bot API."""

    def __init__(self, bot_token: str):
        """Initialize Telegram API client.

        Args:
            bot_token: Telegram bot token from BotFather.
        """
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.timeout = 30  # 30 second timeout

    def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: Optional[str] = None,
        reply_to_message_id: Optional[int] = None,
    ) -> bool:
        """Send a message to a Telegram chat.

        Args:
            chat_id: Telegram chat ID to send the message to.
            text: Text content of the message.
            parse_mode: Optional parse mode (Markdown, HTML).
            reply_to_message_id: Optional message ID to reply to.

        Returns:
            bool: True if message was sent successfully, False otherwise.

        Raises:
            TelegramError: If the API request fails.
        """
        url = f"{self.base_url}/sendMessage"

        payload: Dict[str, Any] = {"chat_id": chat_id, "text": text}

        if parse_mode:
            payload["parse_mode"] = parse_mode

        if reply_to_message_id:
            payload["reply_parameters"] = {"message_id": reply_to_message_id}

        try:
            logger.info(f"Sending message to chat_id: {chat_id}")
            response = requests.post(url, json=payload, timeout=self.timeout)

            if response.status_code == 200:
                logger.info(f"Successfully sent message to chat_id: {chat_id}")
                return True

            else:
                error_data = response.json() if response.text else {}
                error_description = error_data.get("description", "Unknown error")
                logger.error(
                    f"Telegram API error: {response.status_code} - {error_description}"
                )
                raise TelegramError(f"Failed to send message: {error_description}")

        except Timeout:
            logger.error("Telegram API request timed out")
            raise TelegramError("Request timed out - Telegram API unavailable")

        except RequestException as e:
            logger.error(f"Telegram API request failed: {e}")
            raise TelegramError("Network error - Telegram API unavailable")

    def send_error_message(
        self,
        chat_id: int,
        error_message: str,
        parse_mode: Optional[str] = None,
        reply_to_message_id: Optional[int] = None,
    ) -> bool:
        """Send an error message to a Telegram chat.

        Args:
            chat_id: Telegram chat ID to send the error message to.
            error_message: Error message to send.
            parse_mode: Optional parse mode ("Markdown" or "HTML").
            reply_to_message_id: Optional message ID to reply to.

        Returns:
            bool: True if message was sent successfully, False otherwise.
        """
        try:
            return self.send_message(
                chat_id,
                f"❌ Error: {error_message}",
                parse_mode=parse_mode,
                reply_to_message_id=reply_to_message_id,
            )
        except TelegramError as e:
            logger.error(f"Failed to send error message: {e}")
            return False

    def send_success_message(
        self,
        chat_id: int,
        message: str,
        parse_mode: Optional[str] = None,
        reply_to_message_id: Optional[int] = None,
    ) -> bool:
        """Send a success message to a Telegram chat.

        Args:
            chat_id: Telegram chat ID to send the success message to.
            message: Success message to send.
            parse_mode: Optional parse mode ("Markdown" or "HTML").
            reply_to_message_id: Optional message ID to reply to.

        Returns:
            bool: True if message was sent successfully, False otherwise.
        """
        try:
            return self.send_message(
                chat_id,
                f"✓ {message}",
                parse_mode=parse_mode,
                reply_to_message_id=reply_to_message_id,
            )
        except TelegramError as e:
            logger.error(f"Failed to send success message: {e}")
            return False

    def set_my_commands(
        self,
        commands: List[Dict[str, str]],
        scope: Optional[Dict[str, Any]] = None,
        language_code: str = "en",
    ) -> bool:
        """Set the list of bot commands visible in Telegram client.

        Note: This operation is not critical. If it fails (e.g., user hasn't chatted with bot yet),
        it logs a warning but doesn't raise an exception.

        Args:
            commands: List of bot commands, each containing 'command' and 'description'.
                     Example: [{"command": "help", "description": "Show available commands"}]
            scope: Optional scope of commands (default, all_private_chats, all_group_chats,
                   all_chat_administrators, chat, chat_administrators, chat_member).
                   Example: {"type": "chat", "chat_id": 123456789}
            language_code: Language code (ISO 639-1), defaults to 'en'.

        Returns:
            bool: True if commands were set successfully, False otherwise.
        """
        url = f"{self.base_url}/setMyCommands"

        payload = {"commands": commands, "language_code": language_code}

        if scope:
            payload["scope"] = scope

        try:
            logger.info(f"Setting bot commands: {commands}, scope: {scope}")
            response = requests.post(url, json=payload, timeout=self.timeout)

            if response.status_code == 200:
                logger.info("Successfully set bot commands")
                return True
            else:
                error_data = response.json() if response.text else {}
                error_description = error_data.get("description", "Unknown error")
                logger.warning(
                    f"Failed to set bot commands: {response.status_code} - {error_description}. "
                    f"This is non-critical and may occur if user hasn't chatted with bot yet."
                )
                return False

        except Timeout:
            logger.warning(
                "Telegram API request timed out while setting commands (non-critical)"
            )
            return False

        except RequestException as e:
            logger.warning(f"Network error while setting commands (non-critical): {e}")
            return False
