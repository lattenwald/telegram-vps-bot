"""BitLaunch API client for managing VPS instances.

Provides methods to interact with the BitLaunch.io API.
"""

import logging
from typing import Dict, List, Optional

import requests
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)


class BitLaunchError(Exception):
    """Base exception for BitLaunch API errors."""

    pass


class BitLaunchClient:
    """Client for interacting with the BitLaunch API."""

    def __init__(self, api_key: str, base_url: str = "https://app.bitlaunch.io/api"):
        """Initialize BitLaunch API client.

        Args:
            api_key: BitLaunch API key for authentication.
            base_url: Base URL for the BitLaunch API.
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = 30  # 30 second timeout

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests.

        Returns:
            dict: HTTP headers including authentication.
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def get_servers(self) -> List[Dict]:
        """Retrieve list of all servers.

        Returns:
            list: List of server dictionaries.

        Raises:
            BitLaunchError: If the API request fails.
        """
        url = f"{self.base_url}/servers"

        try:
            logger.info("Fetching server list from BitLaunch API")
            response = requests.get(
                url, headers=self._get_headers(), timeout=self.timeout
            )

            if response.status_code == 200:
                servers = response.json()
                logger.info(f"Successfully retrieved {len(servers)} servers")
                return servers

            elif response.status_code == 401:
                logger.error("BitLaunch API authentication failed")
                raise BitLaunchError("Authentication failed - check API key")

            elif response.status_code == 429:
                logger.error("BitLaunch API rate limit exceeded")
                raise BitLaunchError("Rate limit exceeded - try again later")

            else:
                logger.error(f"BitLaunch API error: {response.status_code}")
                raise BitLaunchError(f"API error: {response.status_code}")

        except Timeout:
            logger.error("BitLaunch API request timed out")
            raise BitLaunchError("Request timed out - BitLaunch API unavailable")

        except RequestException as e:
            logger.error(f"BitLaunch API request failed: {e}")
            raise BitLaunchError("Network error - BitLaunch API unavailable")

    def find_server_by_name(self, server_name: str) -> Optional[Dict]:
        """Find a server by its name.

        Args:
            server_name: Name of the server to find.

        Returns:
            dict: Server information if found, None otherwise.

        Raises:
            BitLaunchError: If the API request fails.
        """
        servers = self.get_servers()

        for server in servers:
            if server.get("name") == server_name:
                logger.info(f"Found server: {server_name} (ID: {server.get('id')})")
                return server

        logger.warning(f"Server not found: {server_name}")
        return None

    def reboot_server(self, server_name: str) -> bool:
        """Reboot a server by name.

        Args:
            server_name: Name of the server to reboot.

        Returns:
            bool: True if reboot was successful, False otherwise.

        Raises:
            BitLaunchError: If the API request fails or server is not found.
        """
        server = self.find_server_by_name(server_name)

        if not server:
            raise BitLaunchError(f"Server '{server_name}' not found")

        server_id = server.get("id")
        url = f"{self.base_url}/servers/{server_id}/restart"

        try:
            logger.info(f"Rebooting server: {server_name} (ID: {server_id})")
            response = requests.post(
                url, headers=self._get_headers(), timeout=self.timeout
            )

            if response.status_code == 200:
                logger.info(f"Successfully initiated reboot for server: {server_name}")
                return True

            elif response.status_code == 401:
                logger.error("BitLaunch API authentication failed")
                raise BitLaunchError("Authentication failed - check API key")

            elif response.status_code == 404:
                logger.error(f"Server not found: {server_id}")
                raise BitLaunchError(f"Server '{server_name}' not found")

            elif response.status_code == 429:
                logger.error("BitLaunch API rate limit exceeded")
                raise BitLaunchError("Rate limit exceeded - try again later")

            else:
                logger.error(f"BitLaunch API error: {response.status_code}")
                raise BitLaunchError(f"API error: {response.status_code}")

        except Timeout:
            logger.error("BitLaunch API request timed out")
            raise BitLaunchError("Request timed out - BitLaunch API unavailable")

        except RequestException as e:
            logger.error(f"BitLaunch API request failed: {e}")
            raise BitLaunchError("Network error - BitLaunch API unavailable")
