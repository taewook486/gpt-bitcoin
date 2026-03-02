"""
Dependency injection container using dependency-injector.

This module provides centralized dependency management with:
- Singleton lifecycle for shared resources (HTTP clients)
- Factory lifecycle for per-request instances (services)
- Easy mock injection for testing
- Configuration-driven wiring

Example:
    ```python
    # Production usage
    container = get_container()
    glm_client = container.glm_client()
    upbit_client = container.upbit_client()

    # Testing with mocks
    container = get_container()
    container.glm_client.override(mock_glm_client)
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dependency_injector import containers, providers

from gpt_bitcoin.config.settings import Settings, get_settings
from gpt_bitcoin.infrastructure.external.glm_client import GLMClient
from gpt_bitcoin.infrastructure.external.upbit_client import UpbitClient

if TYPE_CHECKING:
    pass


class Container(containers.DeclarativeContainer):
    """
    Main DI container for the trading system.

    Configuration providers are defined first, followed by infrastructure
    providers, then domain service providers.

    Wiring:
        The container auto-wires the application on import.
        Use `container.wire(modules=[__name__])` in entry points.
    """

    # =========================================================================
    # Configuration
    # =========================================================================

    config = providers.Configuration()

    settings: providers.Provider[Settings] = providers.Singleton(
        get_settings,
    )

    # =========================================================================
    # Infrastructure - External API Clients
    # =========================================================================

    # GLM client - Singleton to reuse rate limiter state
    glm_client: providers.Provider[GLMClient] = providers.Singleton(
        GLMClient,
        settings=settings,
    )

    # Upbit client - Factory for async context manager support
    upbit_client: providers.Provider[UpbitClient] = providers.Factory(
        UpbitClient,
        settings=settings,
    )

    # =========================================================================
    # Domain Services (Future)
    # =========================================================================

    # These will be added as domain services are implemented:
    # - MarketDataService
    # - NewsService
    # - TradingService
    # - DecisionService


# =============================================================================
# Container Management
# =============================================================================

_container: Container | None = None


def get_container() -> Container:
    """
    Get the global DI container.

    Creates container on first call and returns cached instance
    on subsequent calls.

    Returns:
        Container instance
    """
    global _container
    if _container is None:
        _container = Container()
    return _container


def reset_container() -> None:
    """
    Reset the global container.

    Useful for testing or when configuration changes.
    """
    global _container
    if _container is not None:
        _container.unwire()
    _container = None


def override_for_testing(
    glm_client: GLMClient | None = None,
    upbit_client: UpbitClient | None = None,
) -> Container:
    """
    Create a container with mocked dependencies for testing.

    Args:
        glm_client: Mock GLM client (optional)
        upbit_client: Mock Upbit client (optional)

    Returns:
        Container with overridden dependencies

    Example:
        ```python
        mock_glm = MockGLMClient()
        container = override_for_testing(glm_client=mock_glm)
        # Now container.glm_client() returns mock_glm
        ```
    """
    container = get_container()

    if glm_client is not None:
        container.glm_client.override(providers.Object(glm_client))

    if upbit_client is not None:
        container.upbit_client.override(providers.Object(upbit_client))

    return container


def clear_overrides() -> None:
    """Clear all dependency overrides."""
    container = get_container()
    container.glm_client.reset_override()
    container.upbit_client.reset_override()
