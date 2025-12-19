"""VPS Provider clients.

This module provides a unified interface for interacting with
different VPS providers (BitLaunch, Kamatera, etc.).
"""

from typing import Type

from config import config
from providers.base import ProviderClient, ProviderError
from providers.bitlaunch import BitLaunchClient
from providers.kamatera import KamateraClient

# Registry of available providers
PROVIDERS: dict[str, Type[ProviderClient]] = {
    "bitlaunch": BitLaunchClient,
    "kamatera": KamateraClient,
}


def get_provider_class(provider: str) -> Type[ProviderClient]:
    """Get the provider client class by name.

    Args:
        provider: Provider name (e.g., 'bitlaunch', 'kamatera').

    Returns:
        The provider client class.

    Raises:
        ValueError: If the provider is not supported.
    """
    if provider not in PROVIDERS:
        supported = ", ".join(PROVIDERS.keys())
        raise ValueError(f"Unknown provider: {provider}. Supported: {supported}")
    return PROVIDERS[provider]


def create_provider_client(provider: str) -> ProviderClient:
    """Create a provider client instance with credentials from config.

    Args:
        provider: Provider name (e.g., 'bitlaunch', 'kamatera').

    Returns:
        Configured provider client instance.

    Raises:
        ValueError: If provider is not supported or credentials are missing.
    """
    if provider not in PROVIDERS:
        supported = ", ".join(PROVIDERS.keys())
        raise ValueError(f"Unknown provider: {provider}. Supported: {supported}")

    credentials = config.get_provider_credentials(provider)

    if provider == "bitlaunch":
        api_key = credentials.get("api_key")
        if not api_key:
            raise ValueError("BitLaunch credentials missing 'api_key'")
        return BitLaunchClient(api_key=api_key)

    if provider == "kamatera":
        client_id = credentials.get("client_id")
        secret = credentials.get("secret")
        if not client_id or not secret:
            raise ValueError("Kamatera credentials missing 'client_id' or 'secret'")
        return KamateraClient(client_id=client_id, secret=secret)

    raise ValueError(f"No factory implementation for provider: {provider}")


__all__ = [
    "ProviderClient",
    "ProviderError",
    "BitLaunchClient",
    "KamateraClient",
    "PROVIDERS",
    "get_provider_class",
    "create_provider_client",
]
