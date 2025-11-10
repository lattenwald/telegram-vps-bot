"""Tests for Telegram API client."""

import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
import responses
from requests.exceptions import Timeout

from telegram_client import TelegramClient, TelegramError


@pytest.fixture
def telegram_client():
    """Create a Telegram client for testing."""
    return TelegramClient(bot_token="test-bot-token-123")


@responses.activate
def test_send_message_success(telegram_client):
    """Test successful message sending."""
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-bot-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 123}},
        status=200,
    )

    result = telegram_client.send_message(chat_id=123456789, text="Test message")
    assert result is True


@responses.activate
def test_send_message_with_parse_mode(telegram_client):
    """Test sending message with parse mode."""
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-bot-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 123}},
        status=200,
    )

    result = telegram_client.send_message(
        chat_id=123456789, text="*Bold text*", parse_mode="Markdown"
    )
    assert result is True


@responses.activate
def test_send_message_api_error(telegram_client):
    """Test message sending with API error."""
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-bot-token-123/sendMessage",
        json={"ok": False, "description": "Chat not found"},
        status=400,
    )

    with pytest.raises(TelegramError, match="Chat not found"):
        telegram_client.send_message(chat_id=999999999, text="Test message")


def test_send_message_timeout(telegram_client):
    """Test message sending timeout."""
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.POST,
            "https://api.telegram.org/bottest-bot-token-123/sendMessage",
            body=Timeout(),
        )

        with pytest.raises(TelegramError, match="timed out"):
            telegram_client.send_message(chat_id=123456789, text="Test message")


@responses.activate
def test_send_error_message(telegram_client):
    """Test sending error message."""
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-bot-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 123}},
        status=200,
    )

    result = telegram_client.send_error_message(
        chat_id=123456789, error_message="Test error"
    )
    assert result is True

    # Verify the message was formatted correctly
    assert len(responses.calls) == 1
    request_body = responses.calls[0].request.body
    assert b"Error: Test error" in request_body


@responses.activate
def test_send_success_message(telegram_client):
    """Test sending success message."""
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-bot-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 123}},
        status=200,
    )

    result = telegram_client.send_success_message(
        chat_id=123456789, message="Operation completed"
    )
    assert result is True

    # Verify the message was formatted correctly
    assert len(responses.calls) == 1
    request_body = responses.calls[0].request.body
    assert b"Operation completed" in request_body


@responses.activate
def test_send_error_message_fails_gracefully(telegram_client):
    """Test that send_error_message handles failures gracefully."""
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-bot-token-123/sendMessage",
        json={"ok": False, "description": "Bad request"},
        status=400,
    )

    # Should return False but not raise exception
    result = telegram_client.send_error_message(
        chat_id=123456789, error_message="Test error"
    )
    assert result is False


@responses.activate
def test_set_my_commands_success(telegram_client):
    """Test successful setMyCommands call."""
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-bot-token-123/setMyCommands",
        json={"ok": True, "result": True},
        status=200,
    )

    commands = [
        {"command": "help", "description": "Show available commands"},
        {"command": "id", "description": "Get your chat ID"},
    ]

    result = telegram_client.set_my_commands(commands)
    assert result is True


@responses.activate
def test_set_my_commands_with_scope(telegram_client):
    """Test setMyCommands with specific scope."""
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-bot-token-123/setMyCommands",
        json={"ok": True, "result": True},
        status=200,
    )

    commands = [
        {"command": "help", "description": "Show available commands"},
        {"command": "reboot", "description": "Reboot a server"},
    ]
    scope = {"type": "chat", "chat_id": 123456789}

    result = telegram_client.set_my_commands(commands, scope=scope)
    assert result is True

    # Verify request payload
    import json

    request_body = json.loads(responses.calls[0].request.body)
    assert request_body["commands"] == commands
    assert request_body["scope"] == scope
    assert request_body["language_code"] == "en"


@responses.activate
def test_set_my_commands_api_error_graceful(telegram_client):
    """Test setMyCommands handles API errors gracefully (non-critical)."""
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-bot-token-123/setMyCommands",
        json={"ok": False, "description": "User not found"},
        status=400,
    )

    commands = [{"command": "help", "description": "Show help"}]
    scope = {"type": "chat", "chat_id": 999999999}

    # Should return False but not raise exception (non-critical failure)
    result = telegram_client.set_my_commands(commands, scope=scope)
    assert result is False


def test_set_my_commands_timeout_graceful(telegram_client):
    """Test setMyCommands handles timeouts gracefully."""
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.POST,
            "https://api.telegram.org/bottest-bot-token-123/setMyCommands",
            body=Timeout(),
        )

        commands = [{"command": "help", "description": "Show help"}]

        # Should return False but not raise exception (non-critical failure)
        result = telegram_client.set_my_commands(commands)
        assert result is False
