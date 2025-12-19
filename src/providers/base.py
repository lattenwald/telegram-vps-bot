"""Abstract base class for VPS provider clients."""

from abc import ABC, abstractmethod
from typing import Optional


class ProviderError(Exception):
    """Base exception for provider API errors."""

    pass


class ProviderClient(ABC):
    """Abstract base class for VPS provider clients.

    All provider implementations must implement these methods
    to ensure consistent behavior across different providers.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name (e.g., 'bitlaunch', 'kamatera')."""
        pass

    @abstractmethod
    def find_server_by_name(self, server_name: str) -> Optional[dict]:
        """Find a server by its name.

        Args:
            server_name: Name of the server to find.

        Returns:
            dict: Server information if found, None otherwise.
                  Must include at least 'name' and 'id' fields.

        Raises:
            ProviderError: If the API request fails.
        """
        pass

    @abstractmethod
    def reboot_server(self, server_name: str) -> bool:
        """Reboot a server by name.

        Args:
            server_name: Name of the server to reboot.

        Returns:
            bool: True if reboot was initiated successfully.

        Raises:
            ProviderError: If the server is not found or API request fails.
        """
        pass
