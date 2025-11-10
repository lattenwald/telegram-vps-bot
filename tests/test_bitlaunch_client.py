"""Tests for BitLaunch API client."""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import responses
from requests.exceptions import Timeout
from bitlaunch_client import BitLaunchClient, BitLaunchError


@pytest.fixture
def bitlaunch_client():
    """Create a BitLaunch client for testing."""
    return BitLaunchClient(api_key='test-api-key', base_url='https://api.bitlaunch.io/v1')


@responses.activate
def test_get_servers_success(bitlaunch_client, sample_bitlaunch_servers):
    """Test successful server list retrieval."""
    responses.add(
        responses.GET,
        'https://api.bitlaunch.io/v1/servers',
        json=sample_bitlaunch_servers,
        status=200
    )

    servers = bitlaunch_client.get_servers()
    assert len(servers) == 2
    assert servers[0]['name'] == 'test-server-1'
    assert servers[1]['name'] == 'test-server-2'


@responses.activate
def test_get_servers_authentication_failure(bitlaunch_client):
    """Test server list retrieval with authentication failure."""
    responses.add(
        responses.GET,
        'https://api.bitlaunch.io/v1/servers',
        json={'error': 'Unauthorized'},
        status=401
    )

    with pytest.raises(BitLaunchError, match='Authentication failed'):
        bitlaunch_client.get_servers()


@responses.activate
def test_get_servers_rate_limit(bitlaunch_client):
    """Test server list retrieval with rate limiting."""
    responses.add(
        responses.GET,
        'https://api.bitlaunch.io/v1/servers',
        json={'error': 'Rate limit exceeded'},
        status=429
    )

    with pytest.raises(BitLaunchError, match='Rate limit exceeded'):
        bitlaunch_client.get_servers()


@responses.activate
def test_find_server_by_name_success(bitlaunch_client, sample_bitlaunch_servers):
    """Test finding a server by name."""
    responses.add(
        responses.GET,
        'https://api.bitlaunch.io/v1/servers',
        json=sample_bitlaunch_servers,
        status=200
    )

    server = bitlaunch_client.find_server_by_name('test-server-1')
    assert server is not None
    assert server['id'] == 'server-123'
    assert server['name'] == 'test-server-1'


@responses.activate
def test_find_server_by_name_not_found(bitlaunch_client, sample_bitlaunch_servers):
    """Test finding a server that doesn't exist."""
    responses.add(
        responses.GET,
        'https://api.bitlaunch.io/v1/servers',
        json=sample_bitlaunch_servers,
        status=200
    )

    server = bitlaunch_client.find_server_by_name('non-existent-server')
    assert server is None


@responses.activate
def test_reboot_server_success(bitlaunch_client, sample_bitlaunch_servers):
    """Test successful server reboot."""
    # Mock get servers
    responses.add(
        responses.GET,
        'https://api.bitlaunch.io/v1/servers',
        json=sample_bitlaunch_servers,
        status=200
    )

    # Mock reboot endpoint
    responses.add(
        responses.POST,
        'https://api.bitlaunch.io/v1/servers/server-123/reboot',
        json={'status': 'rebooting'},
        status=200
    )

    result = bitlaunch_client.reboot_server('test-server-1')
    assert result is True


@responses.activate
def test_reboot_server_not_found(bitlaunch_client, sample_bitlaunch_servers):
    """Test rebooting a server that doesn't exist."""
    responses.add(
        responses.GET,
        'https://api.bitlaunch.io/v1/servers',
        json=sample_bitlaunch_servers,
        status=200
    )

    with pytest.raises(BitLaunchError, match='not found'):
        bitlaunch_client.reboot_server('non-existent-server')


@responses.activate
def test_reboot_server_api_error(bitlaunch_client, sample_bitlaunch_servers):
    """Test reboot with API error."""
    responses.add(
        responses.GET,
        'https://api.bitlaunch.io/v1/servers',
        json=sample_bitlaunch_servers,
        status=200
    )

    responses.add(
        responses.POST,
        'https://api.bitlaunch.io/v1/servers/server-123/reboot',
        json={'error': 'Server error'},
        status=500
    )

    with pytest.raises(BitLaunchError, match='API error'):
        bitlaunch_client.reboot_server('test-server-1')


def test_get_servers_timeout(bitlaunch_client):
    """Test server list retrieval timeout."""
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            'https://api.bitlaunch.io/v1/servers',
            body=Timeout()
        )

        with pytest.raises(BitLaunchError, match='timed out'):
            bitlaunch_client.get_servers()
