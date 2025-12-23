"""Tests for Lambda handler."""

import json
import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import Mock

import pytest
import responses


@pytest.fixture
def lambda_context():
    """Mock Lambda context."""
    context = Mock()
    context.function_name = "telegram-vps-bot"
    context.memory_limit_in_mb = 256
    context.invoked_function_arn = (
        "arn:aws:lambda:us-east-1:123456789012:function:telegram-vps-bot"
    )
    return context


@responses.activate
def test_lambda_handler_id_command(
    sample_api_gateway_event, lambda_context, mock_env_vars, mock_ssm
):
    """Test /id command handling."""
    from handler import lambda_handler

    # Mock Telegram send_message
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    assert "ok" in response["body"]


@responses.activate
def test_lambda_handler_reboot_command_authorized(
    sample_api_gateway_event,
    lambda_context,
    mock_env_vars,
    mock_ssm,
    sample_bitlaunch_servers,
):
    """Test /reboot command with authorized user."""
    from handler import lambda_handler

    # Update event with reboot command
    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/reboot test-server-1"
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message (2 calls: acknowledgment + success)
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 2}},
        status=200,
    )

    # Mock BitLaunch API
    responses.add(
        responses.GET,
        "https://api.bitlaunch.io/v1/servers",
        json=sample_bitlaunch_servers,
        status=200,
    )
    # BitLaunch API uses /restart endpoint, not /reboot
    responses.add(
        responses.POST,
        "https://api.bitlaunch.io/v1/servers/server-123/restart",
        json={"status": "rebooting"},
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200


@responses.activate
def test_lambda_handler_reboot_command_unauthorized(
    sample_api_gateway_event, lambda_context, mock_env_vars, mock_ssm
):
    """Test /reboot command with unauthorized user."""
    from handler import lambda_handler

    # Update event with unauthorized user and reboot command
    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["chat"]["id"] = 999999999  # Unauthorized chat ID
    update["message"]["text"] = "/reboot test-server-1"
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message (access denied message)
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    # Verify access denied message was sent
    assert len(responses.calls) == 1
    request_body = json.loads(responses.calls[0].request.body)
    assert "Access denied" in request_body["text"]


@responses.activate
def test_lambda_handler_reboot_invalid_format(
    sample_api_gateway_event,
    lambda_context,
    mock_env_vars,
    mock_ssm,
    authorized_chat_id,
):
    """Test /reboot command with invalid format (no server name)."""
    # Reload modules to ensure env vars are picked up
    import importlib

    import auth
    import config
    import handler as handler_module

    importlib.reload(config)
    importlib.reload(auth)
    importlib.reload(handler_module)
    from handler import lambda_handler

    # Update event with reboot command without server name from authorized user
    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/reboot"
    update["message"]["chat"]["id"] = authorized_chat_id  # Use authorized chat ID
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message (usage message)
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    # Verify usage message was sent
    assert len(responses.calls) == 1
    request_body = json.loads(responses.calls[0].request.body)
    assert "Usage:" in request_body["text"]


@responses.activate
def test_lambda_handler_help_command_authorized(
    sample_api_gateway_event,
    lambda_context,
    mock_env_vars,
    mock_ssm,
    authorized_chat_id,
):
    """Test /help command with authorized user."""
    from handler import lambda_handler

    # Update event with help command from authorized user
    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/help"
    update["message"]["chat"]["id"] = authorized_chat_id
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    # Verify help message was sent with authorized commands
    assert len(responses.calls) == 1
    request_body = json.loads(responses.calls[0].request.body)
    assert "/id" in request_body["text"]
    assert "/help" in request_body["text"]
    assert "/find" in request_body["text"]
    assert "/reboot" in request_body["text"]


@responses.activate
def test_lambda_handler_help_command_unauthorized(
    sample_api_gateway_event,
    lambda_context,
    mock_env_vars,
    mock_ssm,
    unauthorized_chat_id,
):
    """Test /help command with unauthorized user."""
    from handler import lambda_handler

    # Update event with help command from unauthorized user
    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/help"
    update["message"]["chat"]["id"] = unauthorized_chat_id
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    # Verify help message was sent with unauthorized commands only
    assert len(responses.calls) == 1
    request_body = json.loads(responses.calls[0].request.body)
    assert "/id" in request_body["text"]
    assert "/help" in request_body["text"]
    assert "/find" not in request_body["text"]
    assert "/reboot" not in request_body["text"]


def test_lambda_handler_unknown_command_ignored(
    sample_api_gateway_event, lambda_context, mock_env_vars, mock_ssm
):
    """Test unknown command is silently ignored."""
    from handler import lambda_handler

    # Update event with unknown command
    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/unknown"
    sample_api_gateway_event["body"] = json.dumps(update)

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    # Verify no Telegram API calls were made (silent ignore)
    assert len(responses.calls) == 0


def test_lambda_handler_start_command_ignored(
    sample_api_gateway_event, lambda_context, mock_env_vars, mock_ssm
):
    """Test /start command is silently ignored."""
    from handler import lambda_handler

    # Update event with /start command
    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/start"
    sample_api_gateway_event["body"] = json.dumps(update)

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    # Verify no Telegram API calls were made (silent ignore)
    assert len(responses.calls) == 0


def test_lambda_handler_non_command_message(
    sample_api_gateway_event, lambda_context, mock_env_vars, mock_ssm
):
    """Test non-command message (should be ignored)."""
    from handler import lambda_handler

    # Update event with non-command text
    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "Hello bot"
    sample_api_gateway_event["body"] = json.dumps(update)

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    # No Telegram API calls should be made
    assert len(responses.calls) == 0


def test_lambda_handler_invalid_request(lambda_context, mock_env_vars, mock_ssm):
    """Test handler with invalid request."""
    from handler import lambda_handler

    invalid_event = {"body": "invalid-json"}

    response = lambda_handler(invalid_event, lambda_context)

    assert response["statusCode"] == 400


def test_lambda_handler_no_message(lambda_context, mock_env_vars, mock_ssm):
    """Test handler with update containing no message."""
    from handler import lambda_handler

    event = {"body": json.dumps({"update_id": 123})}

    response = lambda_handler(event, lambda_context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["status"] == "ignored"


@responses.activate
def test_lambda_handler_find_command_authorized_found(
    sample_api_gateway_event,
    lambda_context,
    mock_env_vars,
    mock_ssm,
    sample_bitlaunch_servers,
):
    """Test /find command with authorized user - server found."""
    from handler import lambda_handler

    # Update event with find command
    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/find test-server-1"
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message (success message)
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    # Mock BitLaunch API
    responses.add(
        responses.GET,
        "https://app.bitlaunch.io/api/servers",
        json=sample_bitlaunch_servers,
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    # Verify success message was sent
    assert len(responses.calls) == 2  # BitLaunch + Telegram
    # BitLaunch call is first (index 0), Telegram is second (index 1)
    request_body = json.loads(responses.calls[1].request.body)
    assert "found" in request_body["text"].lower()


@responses.activate
def test_lambda_handler_find_command_authorized_not_found(
    sample_api_gateway_event,
    lambda_context,
    mock_env_vars,
    mock_ssm,
    sample_bitlaunch_servers,
):
    """Test /find command with authorized user - server not found."""
    from handler import lambda_handler

    # Update event with find command for non-existent server
    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/find nonexistent-server"
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message (error message)
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    # Mock BitLaunch API
    responses.add(
        responses.GET,
        "https://app.bitlaunch.io/api/servers",
        json=sample_bitlaunch_servers,
        status=200,
    )

    # Mock Kamatera API (new: multi-provider search)
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/info",
        json=[],  # Empty result = not found
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    # Verify error message was sent (searches both providers)
    assert len(responses.calls) == 3  # BitLaunch + Kamatera + Telegram
    # Last call is Telegram
    request_body = json.loads(responses.calls[-1].request.body)
    assert "not found" in request_body["text"].lower()


@responses.activate
def test_lambda_handler_find_command_unauthorized(
    sample_api_gateway_event, lambda_context, mock_env_vars, mock_ssm
):
    """Test /find command with unauthorized user."""
    from handler import lambda_handler

    # Update event with unauthorized user and find command
    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["chat"]["id"] = 999999999  # Unauthorized chat ID
    update["message"]["text"] = "/find test-server-1"
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message (access denied message)
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    # Verify access denied message was sent
    assert len(responses.calls) == 1
    request_body = json.loads(responses.calls[0].request.body)
    assert "Access denied" in request_body["text"]


@responses.activate
def test_lambda_handler_find_invalid_format(
    sample_api_gateway_event,
    lambda_context,
    mock_env_vars,
    mock_ssm,
    authorized_chat_id,
):
    """Test /find command with invalid format (no server name)."""
    import importlib

    import auth
    import config
    import handler as handler_module

    importlib.reload(config)
    importlib.reload(auth)
    importlib.reload(handler_module)
    from handler import lambda_handler

    # Update event with find command without server name from authorized user
    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/find"
    update["message"]["chat"]["id"] = authorized_chat_id
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message (usage message)
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    # Verify usage message was sent for /find
    assert len(responses.calls) == 1
    request_body = json.loads(responses.calls[0].request.body)
    assert "Usage:" in request_body["text"]


# Tests for parse_server_arg function
def test_parse_server_arg_simple_name():
    """Test parsing simple server name without provider."""
    from handler import parse_server_arg

    provider, server = parse_server_arg("my-server")
    assert provider is None
    assert server == "my-server"


def test_parse_server_arg_with_provider():
    """Test parsing provider:server format."""
    from handler import parse_server_arg

    provider, server = parse_server_arg("bitlaunch:my-server")
    assert provider == "bitlaunch"
    assert server == "my-server"


def test_parse_server_arg_provider_uppercase():
    """Test parsing provider:server with uppercase provider."""
    from handler import parse_server_arg

    provider, server = parse_server_arg("KAMATERA:my-server")
    assert provider == "kamatera"  # Should be lowercased
    assert server == "my-server"


def test_parse_server_arg_with_spaces():
    """Test parsing with spaces around components."""
    from handler import parse_server_arg

    provider, server = parse_server_arg(" bitlaunch : my-server ")
    assert provider == "bitlaunch"
    assert server == "my-server"


def test_parse_server_arg_empty_provider():
    """Test parsing with empty provider (just :server)."""
    from handler import parse_server_arg

    provider, server = parse_server_arg(":my-server")
    assert provider is None
    assert server == ":my-server"


def test_parse_server_arg_empty_server():
    """Test parsing with empty server (provider:)."""
    from handler import parse_server_arg

    provider, server = parse_server_arg("bitlaunch:")
    assert provider is None
    assert server == "bitlaunch:"


def test_get_allowed_providers_admin(mock_env_vars, mock_ssm):
    """Test get_allowed_providers for admin user."""
    import importlib

    import auth
    import config
    import handler as handler_module

    importlib.reload(config)
    importlib.reload(auth)
    importlib.reload(handler_module)
    from handler import get_allowed_providers

    # 123456789 is an admin in the test ACL
    providers = get_allowed_providers(123456789)
    assert "bitlaunch" in providers
    assert "kamatera" in providers


def test_get_allowed_providers_regular_user(mock_env_vars, mock_ssm):
    """Test get_allowed_providers for regular user."""
    import importlib

    import auth
    import config
    import handler as handler_module

    importlib.reload(config)
    importlib.reload(auth)
    importlib.reload(handler_module)
    from handler import get_allowed_providers

    # 987654321 only has bitlaunch access in the test ACL
    providers = get_allowed_providers(987654321)
    assert providers == ["bitlaunch"]


@responses.activate
def test_lambda_handler_find_with_explicit_provider(
    sample_api_gateway_event,
    lambda_context,
    mock_env_vars,
    mock_ssm,
    sample_bitlaunch_servers,
):
    """Test /find command with explicit provider:server syntax."""
    import importlib

    import auth
    import config
    import handler as handler_module

    importlib.reload(config)
    importlib.reload(auth)
    importlib.reload(handler_module)
    from handler import lambda_handler

    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/find bitlaunch:test-server-1"
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message (success message)
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    # Mock BitLaunch API
    responses.add(
        responses.GET,
        "https://app.bitlaunch.io/api/servers",
        json=sample_bitlaunch_servers,
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    # Should only call BitLaunch (explicit provider)
    assert len(responses.calls) == 2  # BitLaunch + Telegram
    request_body = json.loads(responses.calls[-1].request.body)
    assert "found on bitlaunch" in request_body["text"].lower()


@responses.activate
def test_lambda_handler_find_unknown_provider(
    sample_api_gateway_event,
    lambda_context,
    mock_env_vars,
    mock_ssm,
):
    """Test /find command with unknown provider."""
    import importlib

    import auth
    import config
    import handler as handler_module

    importlib.reload(config)
    importlib.reload(auth)
    importlib.reload(handler_module)
    from handler import lambda_handler

    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/find unknown:my-server"
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message (error message)
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    assert len(responses.calls) == 1  # Only Telegram error message
    request_body = json.loads(responses.calls[0].request.body)
    assert "unknown provider" in request_body["text"].lower()


# Tests for /list command


@responses.activate
def test_lambda_handler_list_command_admin_all_providers(
    sample_api_gateway_event,
    lambda_context,
    mock_env_vars,
    mock_ssm,
    sample_bitlaunch_servers,
):
    """Test /list command with admin - shows all providers grouped."""
    import importlib

    import auth
    import config
    import handler as handler_module

    importlib.reload(config)
    importlib.reload(auth)
    importlib.reload(handler_module)
    from handler import lambda_handler

    # Admin chat ID from ACL config
    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/list"
    update["message"]["chat"]["id"] = 123456789  # Admin
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    # Mock BitLaunch API
    responses.add(
        responses.GET,
        "https://app.bitlaunch.io/api/servers",
        json=sample_bitlaunch_servers,
        status=200,
    )

    # Mock Kamatera API - list endpoint returns basic info only
    responses.add(
        responses.GET,
        "https://cloudcli.cloudwm.com/service/servers",
        json=[{"id": "kam-1", "name": "kam-server", "power": "on"}],
        status=200,
    )
    # Mock Kamatera API - info endpoint returns networks with IP
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/info",
        json=[
            {
                "id": "kam-1",
                "name": "kam-server",
                "networks": [{"network": "wan-eu", "ips": ["9.10.11.12"]}],
            }
        ],
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    # Admin sees all providers with actual server data
    request_body = json.loads(responses.calls[-1].request.body)
    assert "bitlaunch" in request_body["text"].lower()
    assert "kamatera" in request_body["text"].lower()
    assert "test-server-1" in request_body["text"]
    assert "`1.2.3.4`" in request_body["text"]
    assert "kam-server" in request_body["text"]
    assert "`9.10.11.12`" in request_body["text"]


@responses.activate
def test_lambda_handler_list_command_specific_provider(
    sample_api_gateway_event,
    lambda_context,
    mock_env_vars,
    mock_ssm,
    sample_bitlaunch_servers,
):
    """Test /list command with specific provider."""
    import importlib

    import auth
    import config
    import handler as handler_module

    importlib.reload(config)
    importlib.reload(auth)
    importlib.reload(handler_module)
    from handler import lambda_handler

    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/list bitlaunch"
    update["message"]["chat"]["id"] = 123456789  # Admin
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    # Mock BitLaunch API only
    responses.add(
        responses.GET,
        "https://app.bitlaunch.io/api/servers",
        json=sample_bitlaunch_servers,
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    # Only BitLaunch should be queried
    assert len(responses.calls) == 2  # BitLaunch + Telegram
    request_body = json.loads(responses.calls[-1].request.body)
    assert "bitlaunch" in request_body["text"].lower()
    assert "kamatera" not in request_body["text"].lower()


@responses.activate
def test_lambda_handler_list_command_unauthorized(
    sample_api_gateway_event,
    lambda_context,
    mock_env_vars,
    mock_ssm,
):
    """Test /list command with unauthorized user."""
    from handler import lambda_handler

    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["chat"]["id"] = 999999999  # Unauthorized
    update["message"]["text"] = "/list"
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    request_body = json.loads(responses.calls[0].request.body)
    assert "Access denied" in request_body["text"]


@responses.activate
def test_lambda_handler_list_command_unknown_provider(
    sample_api_gateway_event,
    lambda_context,
    mock_env_vars,
    mock_ssm,
):
    """Test /list command with unknown provider."""
    import importlib

    import auth
    import config
    import handler as handler_module

    importlib.reload(config)
    importlib.reload(auth)
    importlib.reload(handler_module)
    from handler import lambda_handler

    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/list unknown"
    update["message"]["chat"]["id"] = 123456789  # Admin
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    request_body = json.loads(responses.calls[0].request.body)
    assert "unknown provider" in request_body["text"].lower()
    assert "bitlaunch" in request_body["text"].lower()


@responses.activate
def test_lambda_handler_list_command_user_sees_only_allowed(
    sample_api_gateway_event,
    lambda_context,
    mock_env_vars,
    mock_ssm,
    sample_bitlaunch_servers,
):
    """Test /list command - user sees only allowed providers."""
    import importlib

    import auth
    import config
    import handler as handler_module

    importlib.reload(config)
    importlib.reload(auth)
    importlib.reload(handler_module)
    from handler import lambda_handler

    # User 987654321 only has bitlaunch access
    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/list"
    update["message"]["chat"]["id"] = 987654321
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    # Mock BitLaunch API only (user doesn't have kamatera access)
    responses.add(
        responses.GET,
        "https://app.bitlaunch.io/api/servers",
        json=sample_bitlaunch_servers,
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    # Only BitLaunch should be in response
    request_body = json.loads(responses.calls[-1].request.body)
    assert "bitlaunch" in request_body["text"].lower()
    # Kamatera should not appear
    assert "kamatera" not in request_body["text"].lower()


@responses.activate
def test_lambda_handler_list_command_user_denied_provider(
    sample_api_gateway_event,
    lambda_context,
    mock_env_vars,
    mock_ssm,
):
    """Test /list command - user denied access to specific provider."""
    import importlib

    import auth
    import config
    import handler as handler_module

    importlib.reload(config)
    importlib.reload(auth)
    importlib.reload(handler_module)
    from handler import lambda_handler

    # User 987654321 only has bitlaunch access, trying to list kamatera
    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/list kamatera"
    update["message"]["chat"]["id"] = 987654321
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    request_body = json.loads(responses.calls[0].request.body)
    assert "access denied" in request_body["text"].lower()


@responses.activate
def test_lambda_handler_list_command_provider_error(
    sample_api_gateway_event,
    lambda_context,
    mock_env_vars,
    mock_ssm,
    sample_bitlaunch_servers,
):
    """Test /list command - partial results when one provider fails."""
    import importlib

    import auth
    import config
    import handler as handler_module

    importlib.reload(config)
    importlib.reload(auth)
    importlib.reload(handler_module)
    from handler import lambda_handler

    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/list"
    update["message"]["chat"]["id"] = 123456789  # Admin
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    # BitLaunch succeeds
    responses.add(
        responses.GET,
        "https://app.bitlaunch.io/api/servers",
        json=sample_bitlaunch_servers,
        status=200,
    )

    # Kamatera fails
    responses.add(
        responses.GET,
        "https://cloudcli.cloudwm.com/service/servers",
        json={"error": "Server error"},
        status=500,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    request_body = json.loads(responses.calls[-1].request.body)
    # Should show BitLaunch results
    assert "bitlaunch" in request_body["text"].lower()
    assert "test-server-1" in request_body["text"]
    # Should show Kamatera error
    assert "kamatera" in request_body["text"].lower()
    assert "unable to fetch" in request_body["text"].lower()


@responses.activate
def test_lambda_handler_list_command_empty_results(
    sample_api_gateway_event,
    lambda_context,
    mock_env_vars,
    mock_ssm,
):
    """Test /list command - no servers found."""
    import importlib

    import auth
    import config
    import handler as handler_module

    importlib.reload(config)
    importlib.reload(auth)
    importlib.reload(handler_module)
    from handler import lambda_handler

    # User 987654321 only has bitlaunch access
    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/list"
    update["message"]["chat"]["id"] = 987654321
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    # BitLaunch returns empty list
    responses.add(
        responses.GET,
        "https://app.bitlaunch.io/api/servers",
        json=[],
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    request_body = json.loads(responses.calls[-1].request.body)
    assert "no servers found" in request_body["text"].lower()


@responses.activate
def test_lambda_handler_list_command_admin_empty_provider(
    sample_api_gateway_event,
    lambda_context,
    mock_env_vars,
    mock_ssm,
):
    """Test /list command - admin sees empty provider message."""
    import importlib

    import auth
    import config
    import handler as handler_module

    importlib.reload(config)
    importlib.reload(auth)
    importlib.reload(handler_module)
    from handler import lambda_handler

    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/list bitlaunch"
    update["message"]["chat"]["id"] = 123456789  # Admin
    sample_api_gateway_event["body"] = json.dumps(update)

    # Mock Telegram send_message
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    # BitLaunch returns empty list
    responses.add(
        responses.GET,
        "https://app.bitlaunch.io/api/servers",
        json=[],
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    request_body = json.loads(responses.calls[-1].request.body)
    # Admin should see "0 servers" message
    assert "bitlaunch" in request_body["text"].lower()
    assert "0 server" in request_body["text"].lower()


@responses.activate
def test_lambda_handler_help_command_shows_list(
    sample_api_gateway_event,
    lambda_context,
    mock_env_vars,
    mock_ssm,
    authorized_chat_id,
):
    """Test /help command shows /list for authorized users."""
    from handler import lambda_handler

    update = json.loads(sample_api_gateway_event["body"])
    update["message"]["text"] = "/help"
    update["message"]["chat"]["id"] = authorized_chat_id
    sample_api_gateway_event["body"] = json.dumps(update)

    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest-telegram-token-123/sendMessage",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response["statusCode"] == 200
    request_body = json.loads(responses.calls[0].request.body)
    assert "/list" in request_body["text"]
