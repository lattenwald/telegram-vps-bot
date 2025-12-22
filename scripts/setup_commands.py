#!/usr/bin/env python3
"""Setup Telegram bot commands via setMyCommands API.

This script registers bot commands with Telegram, setting different command sets for:
- Default scope (all users): /id, /help
- Authorized users (admins and users from ACL): /id, /help, /find, /reboot

Usage:
    python scripts/setup_commands.py

Environment Variables:
    AWS_REGION: AWS region for SSM (default: us-east-1)
"""

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import config
from telegram_client import TelegramClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Command definitions
DEFAULT_COMMANDS = [
    {"command": "id", "description": "Get your Telegram chat ID"},
    {"command": "help", "description": "Show available commands"},
]

AUTHORIZED_COMMANDS = [
    {"command": "id", "description": "Get your Telegram chat ID"},
    {"command": "help", "description": "Show available commands"},
    {"command": "find", "description": "Find a server by name"},
    {"command": "reboot", "description": "Reboot a server"},
]


def setup_default_commands(client: TelegramClient) -> bool:
    """Set commands for all users (default scope).

    Args:
        client: TelegramClient instance.

    Returns:
        bool: True if successful, False otherwise.
    """
    logger.info("Setting default commands for all users...")
    return client.set_my_commands(DEFAULT_COMMANDS)


def setup_user_commands(client: TelegramClient, chat_id: int) -> bool:
    """Set commands for an authorized user (specific chat scope).

    Args:
        client: TelegramClient instance.
        chat_id: Authorized chat ID.

    Returns:
        bool: True if successful, False otherwise.
    """
    scope = {"type": "chat", "chat_id": chat_id}

    logger.info(f"Setting authorized commands for chat_id: {chat_id}...")
    return client.set_my_commands(AUTHORIZED_COMMANDS, scope=scope)


def get_all_authorized_chat_ids() -> set[int]:
    """Get all authorized chat IDs from ACL config.

    Returns:
        set[int]: All chat IDs that have any access (admins + users).
    """
    acl = config.acl_config
    all_ids = set(acl.admins)
    all_ids.update(acl.users.keys())
    return all_ids


def main():
    """Main entry point for command setup."""
    try:
        bot_token = config.telegram_token
        if not bot_token:
            logger.error("Telegram token not found in SSM")
            sys.exit(1)

        authorized_ids = get_all_authorized_chat_ids()
        acl = config.acl_config

        logger.info(f"Found {len(acl.admins)} admin(s)")
        logger.info(f"Found {len(acl.users)} user(s)")
        logger.info(f"Total authorized chat IDs: {len(authorized_ids)}")

        if not authorized_ids:
            logger.warning(
                "No authorized chat IDs in ACL - only setting default commands"
            )

        client = TelegramClient(bot_token)

        success_default = setup_default_commands(client)
        if success_default:
            logger.info("✓ Default commands set successfully")
        else:
            logger.warning("⚠ Failed to set default commands (non-critical)")

        success_count = 0
        for chat_id in authorized_ids:
            user_type = "admin" if chat_id in acl.admins else "user"
            if setup_user_commands(client, chat_id):
                success_count += 1
                logger.info(f"✓ Commands set for {user_type} chat_id: {chat_id}")
            else:
                logger.warning(
                    f"⚠ Failed to set commands for {user_type} chat_id: {chat_id} "
                    f"(user may not have chatted with bot yet)"
                )

        logger.info("\n" + "=" * 50)
        logger.info("Command Setup Summary:")
        logger.info(
            f"  Default commands: {'✓ Success' if success_default else '⚠ Failed'}"
        )
        logger.info(f"  Admins: {len(acl.admins)}")
        logger.info(f"  Users: {len(acl.users)}")
        logger.info(
            f"  Authorized chats configured: {success_count}/{len(authorized_ids)}"
        )
        logger.info("=" * 50)

        sys.exit(0)

    except Exception as e:
        logger.error(f"Unexpected error during command setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
