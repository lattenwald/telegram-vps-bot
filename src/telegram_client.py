"""Telegram API client for sending messages.

Provides methods to interact with the Telegram Bot API.
"""

import logging
from typing import Optional
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

    def send_message(self, chat_id: int, text: str, parse_mode: Optional[str] = None) -> bool:
        """Send a message to a Telegram chat.

        Args:
            chat_id: Telegram chat ID to send the message to.
            text: Text content of the message.
            parse_mode: Optional parse mode (Markdown, HTML).

        Returns:
            bool: True if message was sent successfully, False otherwise.

        Raises:
            TelegramError: If the API request fails.
        """
        url = f"{self.base_url}/sendMessage"

        payload = {
            'chat_id': chat_id,
            'text': text
        }

        if parse_mode:
            payload['parse_mode'] = parse_mode

        try:
            logger.info(f"Sending message to chat_id: {chat_id}")
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                logger.info(f"Successfully sent message to chat_id: {chat_id}")
                return True

            else:
                error_data = response.json() if response.text else {}
                error_description = error_data.get('description', 'Unknown error')
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

    def send_error_message(self, chat_id: int, error_message: str) -> bool:
        """Send an error message to a Telegram chat.

        Args:
            chat_id: Telegram chat ID to send the error message to.
            error_message: Error message to send.

        Returns:
            bool: True if message was sent successfully, False otherwise.
        """
        try:
            return self.send_message(chat_id, f"❌ Error: {error_message}")
        except TelegramError as e:
            logger.error(f"Failed to send error message: {e}")
            return False

    def send_success_message(self, chat_id: int, message: str) -> bool:
        """Send a success message to a Telegram chat.

        Args:
            chat_id: Telegram chat ID to send the success message to.
            message: Success message to send.

        Returns:
            bool: True if message was sent successfully, False otherwise.
        """
        try:
            return self.send_message(chat_id, f"✓ {message}")
        except TelegramError as e:
            logger.error(f"Failed to send success message: {e}")
            return False
