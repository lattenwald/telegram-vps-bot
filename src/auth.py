"""Authorization logic for Telegram VPS Bot.

Handles chat ID-based authorization for bot commands.
"""

import logging
from typing import Set

from config import config

logger = logging.getLogger(__name__)


def is_authorized(chat_id: int) -> bool:
    """Check if a chat ID is authorized to execute commands.

    Args:
        chat_id: Telegram chat ID to check.

    Returns:
        bool: True if the chat ID is authorized, False otherwise.
    """
    authorized_ids = config.authorized_chat_ids

    if not authorized_ids:
        logger.warning("No authorized chat IDs configured - denying access")
        return False

    is_auth = chat_id in authorized_ids

    if is_auth:
        logger.info(f"Authorized access for chat_id: {chat_id}")
    else:
        logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")

    return is_auth


def get_authorized_chat_ids() -> Set[int]:
    """Get the set of authorized chat IDs.

    Returns:
        Set[int]: Set of authorized chat IDs.
    """
    return config.authorized_chat_ids
