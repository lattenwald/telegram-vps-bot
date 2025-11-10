#!/usr/bin/env python3
"""Setup Telegram bot commands via setMyCommands API.

This script registers bot commands with Telegram, setting different command sets for:
- Default scope (all users): /id, /help
- Authorized users (specific chat IDs): /id, /help, /reboot

Usage:
    python scripts/setup_commands.py

Environment Variables:
    TELEGRAM_BOT_TOKEN: Telegram bot token (or read from AWS SSM)
    AUTHORIZED_CHAT_IDS: Comma-separated list of authorized chat IDs
    AWS_REGION: AWS region for SSM (default: us-east-1)
"""

import logging
import os
import sys

# Add src directory to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import config
from telegram_client import TelegramClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_default_commands(client: TelegramClient) -> bool:
    """Set commands for all users (default scope).

    Args:
        client: TelegramClient instance.

    Returns:
        bool: True if successful, False otherwise.
    """
    commands = [
        {"command": "id", "description": "Get your Telegram chat ID"},
        {"command": "help", "description": "Show available commands"},
    ]

    logger.info("Setting default commands for all users...")
    return client.set_my_commands(commands)


def setup_authorized_commands(client: TelegramClient, chat_id: int) -> bool:
    """Set commands for authorized users (specific chat scope).

    Args:
        client: TelegramClient instance.
        chat_id: Authorized chat ID.

    Returns:
        bool: True if successful, False otherwise.
    """
    commands = [
        {"command": "id", "description": "Get your Telegram chat ID"},
        {"command": "help", "description": "Show available commands"},
        {"command": "reboot", "description": "Reboot a server"},
    ]

    scope = {"type": "chat", "chat_id": chat_id}

    logger.info(f"Setting authorized commands for chat_id: {chat_id}...")
    return client.set_my_commands(commands, scope=scope)


def main():
    """Main entry point for command setup."""
    try:
        bot_token = config.telegram_token
        if not bot_token:
            logger.error("TELEGRAM_TOKEN not found in environment or SSM")
            sys.exit(1)

        authorized_chat_ids = config.authorized_chat_ids
        if not authorized_chat_ids:
            logger.warning(
                "No AUTHORIZED_CHAT_IDS configured - skipping authorized commands"
            )
        else:
            logger.info(f"Found {len(authorized_chat_ids)} authorized chat IDs")

        client = TelegramClient(bot_token)

        success_default = setup_default_commands(client)
        if success_default:
            logger.info("✓ Default commands set successfully")
        else:
            logger.warning("⚠ Failed to set default commands (non-critical)")

        success_count = 0
        for chat_id in authorized_chat_ids:
            if setup_authorized_commands(client, chat_id):
                success_count += 1
                logger.info(f"✓ Authorized commands set for chat_id: {chat_id}")
            else:
                logger.warning(
                    f"⚠ Failed to set authorized commands for chat_id: {chat_id} "
                    f"(user may not have chatted with bot yet)"
                )

        logger.info("\n" + "=" * 50)
        logger.info("Command Setup Summary:")
        logger.info(
            f"  Default commands: {'✓ Success' if success_default else '⚠ Failed'}"
        )
        logger.info(
            f"  Authorized chats: {success_count}/{len(authorized_chat_ids)} successful"
        )
        logger.info("=" * 50)

        # Exit with success even if some authorized commands failed (non-critical)
        sys.exit(0)

    except Exception as e:
        logger.error(f"Unexpected error during command setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
