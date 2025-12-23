"""Tests for Kamatera API client."""

import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
import responses
from requests.exceptions import Timeout

from providers import KamateraClient, ProviderError


@pytest.fixture
def kamatera_client():
    """Create a Kamatera client for testing."""
    return KamateraClient(
        client_id="test-client-id",
        secret="test-secret",
        base_url="https://cloudcli.cloudwm.com",
    )


@pytest.fixture
def sample_kamatera_servers():
    """Sample Kamatera servers response."""
    return [
        {
            "id": "kam-123",
            "name": "test-kamatera-1",
            "power": "on",
            "datacenter": "EU",
        },
        {
            "id": "kam-456",
            "name": "test-kamatera-2",
            "power": "on",
            "datacenter": "US-NY",
        },
    ]


@responses.activate
def test_get_servers_success(kamatera_client, sample_kamatera_servers):
    """Test successful server list retrieval."""
    responses.add(
        responses.GET,
        "https://cloudcli.cloudwm.com/service/servers",
        json=sample_kamatera_servers,
        status=200,
    )

    servers = kamatera_client.get_servers()
    assert len(servers) == 2
    assert servers[0]["name"] == "test-kamatera-1"
    assert servers[1]["name"] == "test-kamatera-2"


@responses.activate
def test_get_servers_authentication_failure(kamatera_client):
    """Test server list retrieval with authentication failure."""
    responses.add(
        responses.GET,
        "https://cloudcli.cloudwm.com/service/servers",
        json={"error": "Unauthorized"},
        status=401,
    )

    with pytest.raises(ProviderError, match="Authentication failed"):
        kamatera_client.get_servers()


@responses.activate
def test_get_servers_forbidden(kamatera_client):
    """Test server list retrieval with access forbidden."""
    responses.add(
        responses.GET,
        "https://cloudcli.cloudwm.com/service/servers",
        json={"error": "Forbidden"},
        status=403,
    )

    with pytest.raises(ProviderError, match="Access forbidden"):
        kamatera_client.get_servers()


@responses.activate
def test_get_servers_rate_limit(kamatera_client):
    """Test server list retrieval with rate limiting."""
    responses.add(
        responses.GET,
        "https://cloudcli.cloudwm.com/service/servers",
        json={"error": "Rate limit exceeded"},
        status=429,
    )

    with pytest.raises(ProviderError, match="Rate limit exceeded"):
        kamatera_client.get_servers()


@responses.activate
def test_get_servers_api_error(kamatera_client):
    """Test server list retrieval with API error."""
    responses.add(
        responses.GET,
        "https://cloudcli.cloudwm.com/service/servers",
        json={"error": "Internal error"},
        status=500,
    )

    with pytest.raises(ProviderError, match="API error: 500"):
        kamatera_client.get_servers()


def test_get_servers_timeout(kamatera_client):
    """Test server list retrieval timeout."""
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            "https://cloudcli.cloudwm.com/service/servers",
            body=Timeout(),
        )

        with pytest.raises(ProviderError, match="timed out"):
            kamatera_client.get_servers()


@responses.activate
def test_find_server_by_name_success(kamatera_client):
    """Test finding a server by name using server-side filtering."""
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/info",
        json=[{"id": "kam-123", "name": "test-kamatera-1", "power": "on"}],
        status=200,
    )

    server = kamatera_client.find_server_by_name("test-kamatera-1")
    assert server is not None
    assert server["id"] == "kam-123"
    assert server["name"] == "test-kamatera-1"


@responses.activate
def test_find_server_by_name_not_found(kamatera_client):
    """Test finding a server that doesn't exist."""
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/info",
        json=[],
        status=200,
    )

    server = kamatera_client.find_server_by_name("non-existent-server")
    assert server is None


@responses.activate
def test_find_server_by_name_auth_failure(kamatera_client):
    """Test finding a server with authentication failure."""
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/info",
        json={"error": "Unauthorized"},
        status=401,
    )

    with pytest.raises(ProviderError, match="Authentication failed"):
        kamatera_client.find_server_by_name("test-server")


@responses.activate
def test_find_server_by_name_forbidden(kamatera_client):
    """Test finding a server with access forbidden."""
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/info",
        json={"error": "Forbidden"},
        status=403,
    )

    with pytest.raises(ProviderError, match="Access forbidden"):
        kamatera_client.find_server_by_name("test-server")


def test_find_server_by_name_timeout(kamatera_client):
    """Test finding a server timeout."""
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.POST,
            "https://cloudcli.cloudwm.com/service/server/info",
            body=Timeout(),
        )

        with pytest.raises(ProviderError, match="timed out"):
            kamatera_client.find_server_by_name("test-server")


@responses.activate
def test_reboot_server_success(kamatera_client):
    """Test successful server reboot."""
    # Mock find server
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/info",
        json=[{"id": "kam-123", "name": "test-kamatera-1", "power": "on"}],
        status=200,
    )

    # Mock reboot endpoint
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/reboot",
        json={"status": "rebooting"},
        status=200,
    )

    result = kamatera_client.reboot_server("test-kamatera-1")
    assert result is True


@responses.activate
def test_reboot_server_not_found(kamatera_client):
    """Test rebooting a server that doesn't exist."""
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/info",
        json=[],
        status=200,
    )

    with pytest.raises(ProviderError, match="not found"):
        kamatera_client.reboot_server("non-existent-server")


@responses.activate
def test_reboot_server_api_error(kamatera_client):
    """Test reboot with API error."""
    # Mock find server
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/info",
        json=[{"id": "kam-123", "name": "test-kamatera-1", "power": "on"}],
        status=200,
    )

    # Mock reboot endpoint failure
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/reboot",
        json={"error": "Server error"},
        status=500,
    )

    with pytest.raises(ProviderError, match="API error"):
        kamatera_client.reboot_server("test-kamatera-1")


@responses.activate
def test_reboot_server_auth_failure(kamatera_client):
    """Test reboot with authentication failure."""
    # Mock find server
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/info",
        json=[{"id": "kam-123", "name": "test-kamatera-1", "power": "on"}],
        status=200,
    )

    # Mock reboot endpoint auth failure
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/reboot",
        json={"error": "Unauthorized"},
        status=401,
    )

    with pytest.raises(ProviderError, match="Authentication failed"):
        kamatera_client.reboot_server("test-kamatera-1")


@responses.activate
def test_reboot_server_forbidden(kamatera_client):
    """Test reboot with access forbidden."""
    # Mock find server
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/info",
        json=[{"id": "kam-123", "name": "test-kamatera-1", "power": "on"}],
        status=200,
    )

    # Mock reboot endpoint forbidden
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/reboot",
        json={"error": "Forbidden"},
        status=403,
    )

    with pytest.raises(ProviderError, match="Access forbidden"):
        kamatera_client.reboot_server("test-kamatera-1")


@responses.activate
def test_reboot_server_not_found_404(kamatera_client):
    """Test reboot with 404 from reboot endpoint."""
    # Mock find server
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/info",
        json=[{"id": "kam-123", "name": "test-kamatera-1", "power": "on"}],
        status=200,
    )

    # Mock reboot endpoint 404
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/reboot",
        json={"error": "Not found"},
        status=404,
    )

    with pytest.raises(ProviderError, match="not found"):
        kamatera_client.reboot_server("test-kamatera-1")


@responses.activate
def test_reboot_server_rate_limit(kamatera_client):
    """Test reboot with rate limit."""
    # Mock find server
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/info",
        json=[{"id": "kam-123", "name": "test-kamatera-1", "power": "on"}],
        status=200,
    )

    # Mock reboot endpoint rate limit
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/reboot",
        json={"error": "Rate limit"},
        status=429,
    )

    with pytest.raises(ProviderError, match="Rate limit exceeded"):
        kamatera_client.reboot_server("test-kamatera-1")


def test_reboot_server_timeout(kamatera_client):
    """Test reboot timeout."""
    with responses.RequestsMock() as rsps:
        # Mock find server
        rsps.add(
            responses.POST,
            "https://cloudcli.cloudwm.com/service/server/info",
            json=[{"id": "kam-123", "name": "test-kamatera-1", "power": "on"}],
            status=200,
        )

        # Mock reboot timeout
        rsps.add(
            responses.POST,
            "https://cloudcli.cloudwm.com/service/server/reboot",
            body=Timeout(),
        )

        with pytest.raises(ProviderError, match="timed out"):
            kamatera_client.reboot_server("test-kamatera-1")


def test_client_name(kamatera_client):
    """Test provider name property."""
    assert kamatera_client.name == "kamatera"


def test_client_headers(kamatera_client):
    """Test authentication headers."""
    headers = kamatera_client._get_headers()
    assert headers["AuthClientId"] == "test-client-id"
    assert headers["AuthSecret"] == "test-secret"
    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "application/json"


@responses.activate
def test_list_servers_returns_normalized_format(kamatera_client):
    """Test list_servers returns normalized server info with status mapping."""
    # Basic list endpoint (no networks)
    responses.add(
        responses.GET,
        "https://cloudcli.cloudwm.com/service/servers",
        json=[
            {"id": "kam-1", "name": "server-on", "power": "on"},
            {"id": "kam-2", "name": "server-off", "power": "off"},
        ],
        status=200,
    )
    # Detailed info endpoint returns networks
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/info",
        json=[
            {
                "id": "kam-1",
                "name": "server-on",
                "networks": [{"network": "wan-eu", "ips": ["1.2.3.4"]}],
            }
        ],
        status=200,
    )
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/info",
        json=[
            {
                "id": "kam-2",
                "name": "server-off",
                "networks": [{"network": "wan-us", "ips": ["5.6.7.8"]}],
            }
        ],
        status=200,
    )

    servers = kamatera_client.list_servers()
    assert len(servers) == 2
    assert servers[0] == {"name": "server-on", "status": "running", "ip": "1.2.3.4"}
    assert servers[1] == {"name": "server-off", "status": "stopped", "ip": "5.6.7.8"}


@responses.activate
def test_list_servers_handles_missing_networks(kamatera_client):
    """Test list_servers handles servers without networks in detailed info."""
    responses.add(
        responses.GET,
        "https://cloudcli.cloudwm.com/service/servers",
        json=[{"id": "kam-1", "name": "no-ip-server", "power": "on"}],
        status=200,
    )
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/info",
        json=[{"id": "kam-1", "name": "no-ip-server"}],
        status=200,
    )

    servers = kamatera_client.list_servers()
    assert len(servers) == 1
    assert servers[0] == {"name": "no-ip-server", "status": "running", "ip": None}


@responses.activate
def test_list_servers_handles_private_network_only(kamatera_client):
    """Test list_servers handles servers with only private network (no wan-)."""
    responses.add(
        responses.GET,
        "https://cloudcli.cloudwm.com/service/servers",
        json=[{"id": "kam-1", "name": "private-only", "power": "on"}],
        status=200,
    )
    responses.add(
        responses.POST,
        "https://cloudcli.cloudwm.com/service/server/info",
        json=[
            {
                "id": "kam-1",
                "name": "private-only",
                "networks": [{"network": "lan-internal", "ips": ["10.0.0.5"]}],
            }
        ],
        status=200,
    )

    servers = kamatera_client.list_servers()
    assert len(servers) == 1
    assert servers[0] == {"name": "private-only", "status": "running", "ip": None}
