"""Tests for Lambda handler."""

import sys
import os
import json

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import responses
from unittest.mock import Mock, patch


@pytest.fixture
def lambda_context():
    """Mock Lambda context."""
    context = Mock()
    context.function_name = 'telegram-vps-bot'
    context.memory_limit_in_mb = 256
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:telegram-vps-bot'
    return context


@responses.activate
def test_lambda_handler_id_command(sample_api_gateway_event, lambda_context, mock_env_vars, mock_ssm):
    """Test /id command handling."""
    from handler import lambda_handler

    # Mock Telegram send_message
    responses.add(
        responses.POST,
        'https://api.telegram.org/bottest-telegram-token-123/sendMessage',
        json={'ok': True, 'result': {'message_id': 1}},
        status=200
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response['statusCode'] == 200
    assert 'ok' in response['body']


@responses.activate
def test_lambda_handler_reboot_command_authorized(sample_api_gateway_event, lambda_context,
                                                   mock_env_vars, mock_ssm, sample_bitlaunch_servers):
    """Test /reboot command with authorized user."""
    from handler import lambda_handler

    # Update event with reboot command
    update = json.loads(sample_api_gateway_event['body'])
    update['message']['text'] = '/reboot test-server-1'
    sample_api_gateway_event['body'] = json.dumps(update)

    # Mock Telegram send_message (2 calls: acknowledgment + success)
    responses.add(
        responses.POST,
        'https://api.telegram.org/bottest-telegram-token-123/sendMessage',
        json={'ok': True, 'result': {'message_id': 1}},
        status=200
    )
    responses.add(
        responses.POST,
        'https://api.telegram.org/bottest-telegram-token-123/sendMessage',
        json={'ok': True, 'result': {'message_id': 2}},
        status=200
    )

    # Mock BitLaunch API
    responses.add(
        responses.GET,
        'https://api.bitlaunch.io/v1/servers',
        json=sample_bitlaunch_servers,
        status=200
    )
    responses.add(
        responses.POST,
        'https://api.bitlaunch.io/v1/servers/server-123/reboot',
        json={'status': 'rebooting'},
        status=200
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response['statusCode'] == 200


@responses.activate
def test_lambda_handler_reboot_command_unauthorized(sample_api_gateway_event, lambda_context,
                                                     mock_env_vars, mock_ssm):
    """Test /reboot command with unauthorized user."""
    from handler import lambda_handler

    # Update event with unauthorized user and reboot command
    update = json.loads(sample_api_gateway_event['body'])
    update['message']['chat']['id'] = 999999999  # Unauthorized chat ID
    update['message']['text'] = '/reboot test-server-1'
    sample_api_gateway_event['body'] = json.dumps(update)

    # Mock Telegram send_message (access denied message)
    responses.add(
        responses.POST,
        'https://api.telegram.org/bottest-telegram-token-123/sendMessage',
        json={'ok': True, 'result': {'message_id': 1}},
        status=200
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response['statusCode'] == 200
    # Verify access denied message was sent
    assert len(responses.calls) == 1
    request_body = json.loads(responses.calls[0].request.body)
    assert 'Access denied' in request_body['text']


@responses.activate
def test_lambda_handler_reboot_invalid_format(sample_api_gateway_event, lambda_context,
                                               mock_env_vars, mock_ssm, authorized_chat_id):
    """Test /reboot command with invalid format (no server name)."""
    # Reload modules to ensure env vars are picked up
    import importlib
    import config, auth, handler as handler_module
    importlib.reload(config)
    importlib.reload(auth)
    importlib.reload(handler_module)
    from handler import lambda_handler

    # Update event with reboot command without server name from authorized user
    update = json.loads(sample_api_gateway_event['body'])
    update['message']['text'] = '/reboot'
    update['message']['chat']['id'] = authorized_chat_id  # Use authorized chat ID
    sample_api_gateway_event['body'] = json.dumps(update)

    # Mock Telegram send_message (usage message)
    responses.add(
        responses.POST,
        'https://api.telegram.org/bottest-telegram-token-123/sendMessage',
        json={'ok': True, 'result': {'message_id': 1}},
        status=200
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response['statusCode'] == 200
    # Verify usage message was sent
    assert len(responses.calls) == 1
    request_body = json.loads(responses.calls[0].request.body)
    assert 'Usage:' in request_body['text']


@responses.activate
def test_lambda_handler_unknown_command(sample_api_gateway_event, lambda_context, mock_env_vars, mock_ssm):
    """Test unknown command handling."""
    from handler import lambda_handler

    # Update event with unknown command
    update = json.loads(sample_api_gateway_event['body'])
    update['message']['text'] = '/unknown'
    sample_api_gateway_event['body'] = json.dumps(update)

    # Mock Telegram send_message
    responses.add(
        responses.POST,
        'https://api.telegram.org/bottest-telegram-token-123/sendMessage',
        json={'ok': True, 'result': {'message_id': 1}},
        status=200
    )

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response['statusCode'] == 200
    # Verify unknown command message was sent
    assert len(responses.calls) == 1
    request_body = json.loads(responses.calls[0].request.body)
    assert 'Unknown command' in request_body['text']


def test_lambda_handler_non_command_message(sample_api_gateway_event, lambda_context, mock_env_vars, mock_ssm):
    """Test non-command message (should be ignored)."""
    from handler import lambda_handler

    # Update event with non-command text
    update = json.loads(sample_api_gateway_event['body'])
    update['message']['text'] = 'Hello bot'
    sample_api_gateway_event['body'] = json.dumps(update)

    response = lambda_handler(sample_api_gateway_event, lambda_context)

    assert response['statusCode'] == 200
    # No Telegram API calls should be made
    assert len(responses.calls) == 0


def test_lambda_handler_invalid_request(lambda_context, mock_env_vars, mock_ssm):
    """Test handler with invalid request."""
    from handler import lambda_handler

    invalid_event = {'body': 'invalid-json'}

    response = lambda_handler(invalid_event, lambda_context)

    assert response['statusCode'] == 400


def test_lambda_handler_no_message(lambda_context, mock_env_vars, mock_ssm):
    """Test handler with update containing no message."""
    from handler import lambda_handler

    event = {
        'body': json.dumps({'update_id': 123})
    }

    response = lambda_handler(event, lambda_context)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['status'] == 'ignored'
