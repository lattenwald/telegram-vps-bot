"""AWS Lambda handler for Telegram VPS Management Bot.

Main entry point for processing Telegram webhook requests.
"""

import json
import logging
from typing import Any, Dict, Optional

from auth import get_user_providers, is_admin, is_authorized
from config import config
from providers import PROVIDERS, ProviderClient, ProviderError, create_provider_client
from telegram_client import TelegramClient, TelegramError

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_server_arg(arg: str) -> tuple[Optional[str], str]:
    """Parse server argument with optional provider prefix.

    Supports formats:
    - "server_name" -> (None, "server_name")
    - "provider:server_name" -> ("provider", "server_name")

    Args:
        arg: Server argument from command.

    Returns:
        tuple: (provider_name or None, server_name)
    """
    if ":" in arg:
        parts = arg.split(":", 1)
        provider = parts[0].lower().strip()
        server = parts[1].strip()
        if provider and server:
            return (provider, server)
    return (None, arg.strip())


def get_allowed_providers(chat_id: int) -> list[str]:
    """Get list of providers the user can access.

    Args:
        chat_id: Telegram chat ID.

    Returns:
        list[str]: Provider names. For admins, returns all available providers.
    """
    if is_admin(chat_id):
        return list(PROVIDERS.keys())
    return get_user_providers(chat_id)


def find_server_across_providers(
    chat_id: int, server_name: str
) -> Optional[tuple[ProviderClient, dict]]:
    """Find a server across all providers the user has access to.

    Tries each provider in order and returns the first match.

    Args:
        chat_id: Telegram chat ID.
        server_name: Name of the server to find.

    Returns:
        tuple: (provider_client, server_info) if found, None otherwise.
    """
    providers = get_allowed_providers(chat_id)
    logger.info(f"Searching for server '{server_name}' across providers: {providers}")

    for provider_name in providers:
        try:
            provider = create_provider_client(provider_name)
            server = provider.find_server_by_name(server_name)
            if server:
                logger.info(f"Found server '{server_name}' on {provider_name}")
                return (provider, server)
        except (ProviderError, ValueError) as e:
            logger.warning(f"Error searching {provider_name}: {e}")
            continue

    logger.info(f"Server '{server_name}' not found on any provider")
    return None


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram Markdown.

    Args:
        text: Text to escape.

    Returns:
        str: Escaped text safe for Markdown parse mode.
    """
    escape_chars = ["_", "*", "`", "["]
    for char in escape_chars:
        text = text.replace(char, f"\\{char}")
    return text


def parse_telegram_update(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse Telegram update from API Gateway event.

    Args:
        event: AWS Lambda event from API Gateway.

    Returns:
        dict: Parsed Telegram update, or None if parsing fails.
    """
    try:
        if "body" not in event:
            logger.error("No body in event")
            return None

        body = event["body"]
        if isinstance(body, str):
            body = json.loads(body)

        return body

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON body: {e}")
        return None


def extract_message_info(update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract message information from Telegram update.

    Args:
        update: Telegram update dictionary.

    Returns:
        dict: Message info with chat_id, text, and message_id, or None if extraction fails.
    """
    try:
        message = update.get("message", {})

        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        message_id = message.get("message_id")

        if not chat_id or not text:
            logger.error("Missing chat_id or text in message")
            return None

        return {"chat_id": chat_id, "text": text.strip(), "message_id": message_id}

    except Exception as e:
        logger.error(f"Failed to extract message info: {e}")
        return None


def handle_id_command(
    telegram: TelegramClient, chat_id: int, message_id: Optional[int] = None
) -> None:
    """Handle /id command - return user's chat ID.

    Args:
        telegram: TelegramClient instance.
        chat_id: Telegram chat ID.
        message_id: Optional message ID to reply to.
    """
    logger.info(f"Handling /id command for chat_id: {chat_id}")
    try:
        telegram.send_message(
            chat_id,
            f"Your chat ID: `{chat_id}`",
            parse_mode="Markdown",
            reply_to_message_id=message_id,
        )
    except TelegramError as e:
        logger.error(f"Failed to send chat ID: {e}")


def handle_help_command(
    telegram: TelegramClient, chat_id: int, message_id: Optional[int] = None
) -> None:
    """Handle /help command - show available commands.

    Shows different command lists based on authorization:
    - Unauthorized users: /id, /help
    - Authorized users: /id, /help, /reboot

    Args:
        telegram: TelegramClient instance.
        chat_id: Telegram chat ID.
        message_id: Optional message ID to reply to.
    """
    logger.info(f"Handling /help command for chat_id: {chat_id}")

    authorized = is_authorized(chat_id)

    if authorized:
        help_text = (
            "Available commands:\n"
            "/id - Get your chat ID\n"
            "/help - Show this help message\n"
            "/find <server_name> - Find a server\n"
            "/reboot <server_name> - Reboot a server"
        )
    else:
        help_text = (
            "Available commands:\n"
            "/id - Get your chat ID\n"
            "/help - Show this help message"
        )

    try:
        telegram.send_message(chat_id, help_text, reply_to_message_id=message_id)
    except TelegramError as e:
        logger.error(f"Failed to send help message: {e}")


def handle_find_command(
    telegram: TelegramClient,
    chat_id: int,
    server_arg: str,
    message_id: Optional[int] = None,
) -> None:
    """Handle /find command - find a server by name.

    Supports formats:
    - /find server_name - searches all allowed providers
    - /find provider:server_name - searches specific provider

    Args:
        telegram: TelegramClient instance.
        chat_id: Telegram chat ID.
        server_arg: Server argument (optionally with provider prefix).
        message_id: Optional message ID to reply to.
    """
    if not server_arg:
        try:
            telegram.send_message(
                chat_id,
                "❌ Usage: /find <server\\_name> or /find <provider:server\\_name>",
                parse_mode="Markdown",
                reply_to_message_id=message_id,
            )
        except TelegramError:
            pass
        return

    provider_name, server_name = parse_server_arg(server_arg)
    logger.info(
        f"Handling /find command: provider={provider_name}, server={server_name}"
    )

    escaped_name = escape_markdown(server_name)

    if provider_name:
        if provider_name not in PROVIDERS:
            telegram.send_error_message(
                chat_id,
                f"Unknown provider `{provider_name}`. Available: {', '.join(PROVIDERS.keys())}",
                parse_mode="Markdown",
                reply_to_message_id=message_id,
            )
            return

        if not is_authorized(chat_id, provider=provider_name):
            logger.warning(f"Unauthorized /find attempt from chat_id: {chat_id}")
            telegram.send_error_message(
                chat_id,
                f"❌ Access denied for provider `{provider_name}`",
                parse_mode="Markdown",
                reply_to_message_id=message_id,
            )
            return

        try:
            provider = create_provider_client(provider_name)
            server = provider.find_server_by_name(server_name)
            if server:
                telegram.send_success_message(
                    chat_id,
                    f"Server `{escaped_name}` found on {provider_name}",
                    parse_mode="Markdown",
                    reply_to_message_id=message_id,
                )
            else:
                telegram.send_error_message(
                    chat_id,
                    f"Server `{escaped_name}` not found on {provider_name}",
                    parse_mode="Markdown",
                    reply_to_message_id=message_id,
                )
        except ProviderError as e:
            _handle_provider_error(telegram, chat_id, e, message_id)

    else:
        if not is_authorized(chat_id):
            logger.warning(f"Unauthorized /find attempt from chat_id: {chat_id}")
            telegram.send_error_message(
                chat_id,
                "❌ Access denied. Use /id to get your chat ID and request authorization.",
                reply_to_message_id=message_id,
            )
            return

        result = find_server_across_providers(chat_id, server_name)
        if result:
            provider, server = result
            telegram.send_success_message(
                chat_id,
                f"Server `{escaped_name}` found on {provider.name}",
                parse_mode="Markdown",
                reply_to_message_id=message_id,
            )
        else:
            providers = get_allowed_providers(chat_id)
            telegram.send_error_message(
                chat_id,
                f"Server `{escaped_name}` not found on any provider ({', '.join(providers)})",
                parse_mode="Markdown",
                reply_to_message_id=message_id,
            )


def _handle_provider_error(
    telegram: TelegramClient,
    chat_id: int,
    e: ProviderError,
    message_id: Optional[int] = None,
) -> None:
    """Handle provider errors with user-friendly messages."""
    error_message = str(e)
    logger.error(f"Provider error: {error_message}")

    if "authentication" in error_message.lower():
        telegram.send_error_message(
            chat_id,
            "Configuration error - contact administrator",
            reply_to_message_id=message_id,
        )
    elif "rate limit" in error_message.lower():
        telegram.send_error_message(
            chat_id,
            "Too many requests - try again later",
            reply_to_message_id=message_id,
        )
    else:
        telegram.send_error_message(
            chat_id,
            "Unable to complete request - try again later",
            reply_to_message_id=message_id,
        )


def handle_reboot_command(
    telegram: TelegramClient,
    chat_id: int,
    server_arg: str,
    message_id: Optional[int] = None,
) -> None:
    """Handle /reboot command - reboot a VPS server.

    Supports formats:
    - /reboot server_name - finds server across all allowed providers
    - /reboot provider:server_name - reboots on specific provider

    Args:
        telegram: TelegramClient instance.
        chat_id: Telegram chat ID.
        server_arg: Server argument (optionally with provider prefix).
        message_id: Optional message ID to reply to.
    """
    if not server_arg:
        try:
            telegram.send_message(
                chat_id,
                "❌ Usage: /reboot <server\\_name> or /reboot <provider:server\\_name>",
                parse_mode="Markdown",
                reply_to_message_id=message_id,
            )
        except TelegramError:
            pass
        return

    provider_name, server_name = parse_server_arg(server_arg)
    logger.info(
        f"Handling /reboot command: provider={provider_name}, server={server_name}"
    )

    escaped_name = escape_markdown(server_name)

    if provider_name:
        if provider_name not in PROVIDERS:
            telegram.send_error_message(
                chat_id,
                f"Unknown provider `{provider_name}`. Available: {', '.join(PROVIDERS.keys())}",
                parse_mode="Markdown",
                reply_to_message_id=message_id,
            )
            return

        if not is_authorized(chat_id, provider=provider_name):
            logger.warning(f"Unauthorized /reboot attempt from chat_id: {chat_id}")
            telegram.send_error_message(
                chat_id,
                f"❌ Access denied for provider `{provider_name}`",
                parse_mode="Markdown",
                reply_to_message_id=message_id,
            )
            return

        try:
            telegram.send_message(
                chat_id,
                f"Rebooting `{escaped_name}` on {provider_name}...",
                parse_mode="Markdown",
                reply_to_message_id=message_id,
            )
        except TelegramError:
            pass

        try:
            provider = create_provider_client(provider_name)
            provider.reboot_server(server_name)
            telegram.send_success_message(
                chat_id,
                f"Server `{escaped_name}` is rebooting on {provider_name}",
                parse_mode="Markdown",
                reply_to_message_id=message_id,
            )
            logger.info(
                f"Successfully rebooted server: {server_name} on {provider_name}"
            )
        except ProviderError as e:
            _handle_reboot_error(telegram, chat_id, server_name, e, message_id)

    else:
        if not is_authorized(chat_id):
            logger.warning(f"Unauthorized /reboot attempt from chat_id: {chat_id}")
            telegram.send_error_message(
                chat_id,
                "❌ Access denied. Use /id to get your chat ID and request authorization.",
                reply_to_message_id=message_id,
            )
            return

        result = find_server_across_providers(chat_id, server_name)
        if not result:
            providers = get_allowed_providers(chat_id)
            telegram.send_error_message(
                chat_id,
                f"Server `{escaped_name}` not found on any provider ({', '.join(providers)})",
                parse_mode="Markdown",
                reply_to_message_id=message_id,
            )
            return

        provider, server = result

        try:
            telegram.send_message(
                chat_id,
                f"Rebooting `{escaped_name}` on {provider.name}...",
                parse_mode="Markdown",
                reply_to_message_id=message_id,
            )
        except TelegramError:
            pass

        try:
            provider.reboot_server(server_name)
            telegram.send_success_message(
                chat_id,
                f"Server `{escaped_name}` is rebooting on {provider.name}",
                parse_mode="Markdown",
                reply_to_message_id=message_id,
            )
            logger.info(
                f"Successfully rebooted server: {server_name} on {provider.name}"
            )
        except ProviderError as e:
            _handle_reboot_error(telegram, chat_id, server_name, e, message_id)


def _handle_reboot_error(
    telegram: TelegramClient,
    chat_id: int,
    server_name: str,
    e: ProviderError,
    message_id: Optional[int] = None,
) -> None:
    """Handle reboot-specific provider errors."""
    error_message = str(e)
    logger.error(f"Provider error during reboot: {error_message}")

    if "not found" in error_message.lower():
        telegram.send_error_message(
            chat_id,
            f"Server '{server_name}' not found",
            reply_to_message_id=message_id,
        )
    elif "authentication" in error_message.lower():
        telegram.send_error_message(
            chat_id,
            "Configuration error - contact administrator",
            reply_to_message_id=message_id,
        )
    elif "rate limit" in error_message.lower():
        telegram.send_error_message(
            chat_id,
            "Too many requests - try again later",
            reply_to_message_id=message_id,
        )
    else:
        telegram.send_error_message(
            chat_id,
            "Unable to reboot server - try again later",
            reply_to_message_id=message_id,
        )


def process_command(
    telegram: TelegramClient, chat_id: int, text: str, message_id: Optional[int] = None
) -> None:
    """Process a command from a Telegram message.

    Only whitelisted commands (/id, /help, /find, /reboot) are processed.
    All other commands are silently ignored.

    Args:
        telegram: TelegramClient instance.
        chat_id: Telegram chat ID.
        text: Message text containing the command.
        message_id: Optional message ID to reply to.
    """
    parts = text.split(maxsplit=1)
    command = parts[0].lower()

    if command == "/id":
        handle_id_command(telegram, chat_id, message_id)

    elif command == "/help":
        handle_help_command(telegram, chat_id, message_id)

    elif command == "/find":
        server_arg = parts[1] if len(parts) > 1 else ""
        handle_find_command(telegram, chat_id, server_arg, message_id)

    elif command == "/reboot":
        server_arg = parts[1] if len(parts) > 1 else ""
        handle_reboot_command(telegram, chat_id, server_arg, message_id)

    else:
        logger.info(f"Ignoring non-whitelisted command: {command}")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda handler function.

    Args:
        event: Lambda event from API Gateway.
        context: Lambda context object.

    Returns:
        dict: API Gateway response.
    """
    logger.info("Lambda function invoked")

    try:
        if not config.validate():
            logger.error("Configuration validation failed")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Configuration error"}),
            }

        telegram = TelegramClient(config.telegram_token)

        update = parse_telegram_update(event)
        if not update:
            logger.error("Failed to parse Telegram update")
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid request"})}

        message_info = extract_message_info(update)
        if not message_info:
            logger.warning("No message in update - ignoring")
            return {"statusCode": 200, "body": json.dumps({"status": "ignored"})}

        chat_id = message_info["chat_id"]
        text = message_info["text"]
        message_id = message_info["message_id"]

        logger.info(f"Processing message from chat_id: {chat_id}")

        if text.startswith("/"):
            process_command(telegram, chat_id, text, message_id)
        else:
            logger.info("Non-command message - ignoring")

        return {"statusCode": 200, "body": json.dumps({"status": "ok"})}

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
        }
