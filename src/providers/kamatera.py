"""Kamatera API client for managing VPS instances.

Provides methods to interact with the Kamatera CloudCLI API.
"""

import logging
from typing import Dict, List, Optional

import requests
from requests.exceptions import RequestException, Timeout

from providers.base import ProviderClient, ProviderError

logger = logging.getLogger(__name__)


class KamateraClient(ProviderClient):
    """Client for interacting with the Kamatera API."""

    def __init__(
        self,
        client_id: str,
        secret: str,
        base_url: str = "https://cloudcli.cloudwm.com",
    ):
        """Initialize Kamatera API client.

        Args:
            client_id: Kamatera API client ID for authentication.
            secret: Kamatera API secret for authentication.
            base_url: Base URL for the Kamatera CloudCLI API.
        """
        self.client_id = client_id
        self.secret = secret
        self.base_url = base_url.rstrip("/")
        self.timeout = 30

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "kamatera"

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests.

        Returns:
            dict: HTTP headers including authentication.
        """
        return {
            "AuthClientId": self.client_id,
            "AuthSecret": self.secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def get_servers(self) -> List[Dict]:
        """Retrieve list of all servers.

        Returns:
            list: List of server dictionaries.

        Raises:
            ProviderError: If the API request fails.
        """
        url = f"{self.base_url}/service/servers"

        try:
            logger.info("Fetching server list from Kamatera API")
            response = requests.get(
                url, headers=self._get_headers(), timeout=self.timeout
            )

            if response.status_code == 200:
                servers = response.json()
                logger.info(f"Successfully retrieved {len(servers)} servers")
                return servers

            elif response.status_code == 401:
                logger.error("Kamatera API authentication failed")
                raise ProviderError("Authentication failed - check API credentials")

            elif response.status_code == 403:
                logger.error("Kamatera API access forbidden")
                raise ProviderError("Access forbidden - check API permissions")

            elif response.status_code == 429:
                logger.error("Kamatera API rate limit exceeded")
                raise ProviderError("Rate limit exceeded - try again later")

            else:
                logger.error(f"Kamatera API error: {response.status_code}")
                raise ProviderError(f"API error: {response.status_code}")

        except Timeout:
            logger.error("Kamatera API request timed out")
            raise ProviderError("Request timed out - Kamatera API unavailable")

        except RequestException as e:
            logger.error(f"Kamatera API request failed: {e}")
            raise ProviderError("Network error - Kamatera API unavailable")

    def find_server_by_name(self, server_name: str) -> Optional[Dict]:
        """Find a server by its name.

        Uses server-side filtering via POST /service/server/info.

        Args:
            server_name: Name of the server to find.

        Returns:
            dict: Server information if found, None otherwise.

        Raises:
            ProviderError: If the API request fails.
        """
        url = f"{self.base_url}/service/server/info"

        try:
            logger.info(f"Looking up server: {server_name}")
            response = requests.post(
                url,
                headers=self._get_headers(),
                json={"name": server_name},
                timeout=self.timeout,
            )

            if response.status_code == 200:
                servers = response.json()
                if servers and len(servers) > 0:
                    server = servers[0]
                    logger.info(f"Found server: {server_name} (ID: {server.get('id')})")
                    return server
                logger.warning(f"Server not found: {server_name}")
                return None

            elif response.status_code == 401:
                logger.error("Kamatera API authentication failed")
                raise ProviderError("Authentication failed - check API credentials")

            elif response.status_code == 403:
                logger.error("Kamatera API access forbidden")
                raise ProviderError("Access forbidden - check API permissions")

            elif response.status_code == 429:
                logger.error("Kamatera API rate limit exceeded")
                raise ProviderError("Rate limit exceeded - try again later")

            else:
                logger.error(f"Kamatera API error: {response.status_code}")
                raise ProviderError(f"API error: {response.status_code}")

        except Timeout:
            logger.error("Kamatera API request timed out")
            raise ProviderError("Request timed out - Kamatera API unavailable")

        except RequestException as e:
            logger.error(f"Kamatera API request failed: {e}")
            raise ProviderError("Network error - Kamatera API unavailable")

    def reboot_server(self, server_name: str) -> bool:
        """Reboot a server by name.

        Args:
            server_name: Name of the server to reboot.

        Returns:
            bool: True if reboot was initiated successfully.

        Raises:
            ProviderError: If the server is not found or API request fails.
        """
        server = self.find_server_by_name(server_name)

        if not server:
            raise ProviderError(f"Server '{server_name}' not found")

        server_id = server.get("id")
        url = f"{self.base_url}/service/server/reboot"

        try:
            logger.info(f"Rebooting server: {server_name} (ID: {server_id})")
            response = requests.post(
                url,
                headers=self._get_headers(),
                json={"id": server_id},
                timeout=self.timeout,
            )

            if response.status_code == 200:
                logger.info(f"Successfully initiated reboot for server: {server_name}")
                return True

            elif response.status_code == 401:
                logger.error("Kamatera API authentication failed")
                raise ProviderError("Authentication failed - check API credentials")

            elif response.status_code == 403:
                logger.error("Kamatera API access forbidden")
                raise ProviderError("Access forbidden - check API permissions")

            elif response.status_code == 404:
                logger.error(f"Server not found: {server_id}")
                raise ProviderError(f"Server '{server_name}' not found")

            elif response.status_code == 429:
                logger.error("Kamatera API rate limit exceeded")
                raise ProviderError("Rate limit exceeded - try again later")

            else:
                logger.error(f"Kamatera API error: {response.status_code}")
                raise ProviderError(f"API error: {response.status_code}")

        except Timeout:
            logger.error("Kamatera API request timed out")
            raise ProviderError("Request timed out - Kamatera API unavailable")

        except RequestException as e:
            logger.error(f"Kamatera API request failed: {e}")
            raise ProviderError("Network error - Kamatera API unavailable")
