"""AWS Lambda handler for Telegram VPS Management Bot.

Main entry point for processing Telegram webhook requests.
"""

import json
import logging
from typing import Dict, Any, Optional
from config import config
from auth import is_authorized
from telegram_client import TelegramClient, TelegramError
from bitlaunch_client import BitLaunchClient, BitLaunchError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_telegram_update(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse Telegram update from API Gateway event.

    Args:
        event: AWS Lambda event from API Gateway.

    Returns:
        dict: Parsed Telegram update, or None if parsing fails.
    """
    try:
        if 'body' not in event:
            logger.error("No body in event")
            return None

        body = event['body']
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
        message = update.get('message', {})

        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '')
        message_id = message.get('message_id')

        if not chat_id or not text:
            logger.error("Missing chat_id or text in message")
            return None

        return {
            'chat_id': chat_id,
            'text': text.strip(),
            'message_id': message_id
        }

    except Exception as e:
        logger.error(f"Failed to extract message info: {e}")
        return None


def handle_id_command(telegram: TelegramClient, chat_id: int) -> None:
    """Handle /id command - return user's chat ID.

    Args:
        telegram: TelegramClient instance.
        chat_id: Telegram chat ID.
    """
    logger.info(f"Handling /id command for chat_id: {chat_id}")
    try:
        telegram.send_message(chat_id, f"Your chat ID: `{chat_id}`", parse_mode='Markdown')
    except TelegramError as e:
        logger.error(f"Failed to send chat ID: {e}")


def handle_help_command(telegram: TelegramClient, chat_id: int) -> None:
    """Handle /help command - show available commands.

    Shows different command lists based on authorization:
    - Unauthorized users: /id, /help
    - Authorized users: /id, /help, /reboot

    Args:
        telegram: TelegramClient instance.
        chat_id: Telegram chat ID.
    """
    logger.info(f"Handling /help command for chat_id: {chat_id}")

    # Check if user is authorized
    authorized = is_authorized(chat_id)

    if authorized:
        help_text = (
            "Available commands:\n"
            "/id - Get your chat ID\n"
            "/help - Show this help message\n"
            "/reboot <server_name> - Reboot a server"
        )
    else:
        help_text = (
            "Available commands:\n"
            "/id - Get your chat ID\n"
            "/help - Show this help message"
        )

    try:
        telegram.send_message(chat_id, help_text)
    except TelegramError as e:
        logger.error(f"Failed to send help message: {e}")


def handle_reboot_command(
    telegram: TelegramClient,
    bitlaunch: BitLaunchClient,
    chat_id: int,
    server_name: str
) -> None:
    """Handle /reboot command - reboot a VPS server.

    Args:
        telegram: TelegramClient instance.
        bitlaunch: BitLaunchClient instance.
        chat_id: Telegram chat ID.
        server_name: Name of the server to reboot.
    """
    logger.info(f"Handling /reboot command for server: {server_name}")

    # Check authorization
    if not is_authorized(chat_id):
        logger.warning(f"Unauthorized /reboot attempt from chat_id: {chat_id}")
        try:
            telegram.send_message(
                chat_id,
                "❌ Access denied. Use /id to get your chat ID and request authorization."
            )
        except TelegramError:
            pass
        return

    # Validate server name
    if not server_name:
        try:
            telegram.send_message(chat_id, "❌ Usage: /reboot <server_name>")
        except TelegramError:
            pass
        return

    # Send acknowledgment
    try:
        telegram.send_message(chat_id, f"Rebooting server `{server_name}`...", parse_mode='Markdown')
    except TelegramError:
        pass

    # Reboot server
    try:
        bitlaunch.reboot_server(server_name)
        telegram.send_success_message(chat_id, f"Server `{server_name}` is rebooting")
        logger.info(f"Successfully rebooted server: {server_name}")

    except BitLaunchError as e:
        error_message = str(e)
        logger.error(f"BitLaunch error: {error_message}")

        # Send user-friendly error message
        if "not found" in error_message.lower():
            telegram.send_error_message(chat_id, f"Server '{server_name}' not found")
        elif "authentication" in error_message.lower():
            telegram.send_error_message(chat_id, "Configuration error - contact administrator")
        elif "rate limit" in error_message.lower():
            telegram.send_error_message(chat_id, "Too many requests - try again later")
        else:
            telegram.send_error_message(chat_id, "Unable to reboot server - try again later")


def process_command(
    telegram: TelegramClient,
    bitlaunch: BitLaunchClient,
    chat_id: int,
    text: str
) -> None:
    """Process a command from a Telegram message.

    Only whitelisted commands (/id, /help, /reboot) are processed.
    All other commands are silently ignored.

    Args:
        telegram: TelegramClient instance.
        bitlaunch: BitLaunchClient instance.
        chat_id: Telegram chat ID.
        text: Message text containing the command.
    """
    parts = text.split(maxsplit=1)
    command = parts[0].lower()

    if command == '/id':
        handle_id_command(telegram, chat_id)

    elif command == '/help':
        handle_help_command(telegram, chat_id)

    elif command == '/reboot':
        server_name = parts[1] if len(parts) > 1 else ''
        handle_reboot_command(telegram, bitlaunch, chat_id, server_name)

    else:
        # Silently ignore all other commands (including /start)
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
        # Validate configuration
        if not config.validate():
            logger.error("Configuration validation failed")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Configuration error'})
            }

        # Initialize clients
        telegram = TelegramClient(config.telegram_token)
        bitlaunch = BitLaunchClient(config.bitlaunch_api_key, config.bitlaunch_api_base_url)

        # Parse Telegram update
        update = parse_telegram_update(event)
        if not update:
            logger.error("Failed to parse Telegram update")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid request'})
            }

        # Extract message info
        message_info = extract_message_info(update)
        if not message_info:
            logger.warning("No message in update - ignoring")
            return {
                'statusCode': 200,
                'body': json.dumps({'status': 'ignored'})
            }

        chat_id = message_info['chat_id']
        text = message_info['text']

        logger.info(f"Processing message from chat_id: {chat_id}")

        # Process command
        if text.startswith('/'):
            process_command(telegram, bitlaunch, chat_id, text)
        else:
            logger.info("Non-command message - ignoring")

        return {
            'statusCode': 200,
            'body': json.dumps({'status': 'ok'})
        }

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
