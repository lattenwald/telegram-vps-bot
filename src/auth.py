"""Authorization logic for Telegram VPS Bot.

Handles ACL-based authorization for bot commands.
Supports admin access, per-user provider access, and per-server restrictions.
"""

import logging

from config import config

logger = logging.getLogger(__name__)


def is_authorized(
    chat_id: int, provider: str | None = None, server: str | None = None
) -> bool:
    """Check if a chat ID is authorized to execute commands.

    Args:
        chat_id: Telegram chat ID to check.
        provider: Optional provider name to check access for.
        server: Optional server name to check access for.

    Returns:
        bool: True if the chat ID is authorized, False otherwise.
    """
    acl = config.acl_config

    # Check ACL-based authorization
    is_auth = acl.can_access(chat_id, provider, server)

    if is_auth:
        context = f"chat_id={chat_id}"
        if provider:
            context += f", provider={provider}"
        if server:
            context += f", server={server}"
        logger.info(f"Authorized access: {context}")
    else:
        context = f"chat_id={chat_id}"
        if provider:
            context += f", provider={provider}"
        if server:
            context += f", server={server}"
        logger.warning(f"Unauthorized access attempt: {context}")

    return is_auth


def is_admin(chat_id: int) -> bool:
    """Check if a chat ID has admin privileges.

    Args:
        chat_id: Telegram chat ID to check.

    Returns:
        bool: True if the chat ID is an admin, False otherwise.
    """
    return config.acl_config.is_admin(chat_id)


def get_user_providers(chat_id: int) -> list[str]:
    """Get list of providers the user has access to.

    Args:
        chat_id: Telegram chat ID.

    Returns:
        list[str]: List of provider names the user can access.
                   Empty list for admins (they have access to all).
    """
    return config.acl_config.get_user_providers(chat_id)
