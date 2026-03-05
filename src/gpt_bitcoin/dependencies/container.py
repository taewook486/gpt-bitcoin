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

from dependency_injector import containers, providers

from gpt_bitcoin.config.settings import Settings, get_settings
from gpt_bitcoin.domain.testnet_config import TestnetConfig
from gpt_bitcoin.domain.trading import TradingService
from gpt_bitcoin.domain.security import SecurityService
from gpt_bitcoin.infrastructure.external.glm_client import GLMClient
from gpt_bitcoin.infrastructure.external.mock_upbit_client import MockUpbitClient
from gpt_bitcoin.infrastructure.external.upbit_client import UpbitClient
from gpt_bitcoin.infrastructure.persistence.audit_repository import (
    SQLiteAuditRepository,
)


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
    # Always uses global endpoint: https://api.z.ai/api/paas/v4/
    glm_client: providers.Provider[GLMClient] = providers.Singleton(
        GLMClient,
        settings=settings,
    )

    # Upbit client - Factory for async context manager support
    upbit_client: providers.Provider[UpbitClient] = providers.Factory(
        UpbitClient,
        settings=settings,
    )

    # MockUpbitClient for testnet simulation
    mock_upbit_client: providers.Provider[MockUpbitClient] = providers.Factory(
        MockUpbitClient,
        config=providers.Singleton(TestnetConfig),
    )

    # @MX:ANCHOR: mode_aware_upbit_client
    # @MX:REASON: TestnetMode에 따라 적절한 클라이언트를 선택하는 중앙 진입점
    # fan_in: 3+ (trading_service, tests, main.py)
    def _get_mode_aware_client(settings: Settings) -> UpbitClient | MockUpbitClient:
        """
        Get the appropriate upbit client based on testnet mode.

        @MX:NOTE: testnet_mode가 True이면 MockUpbitClient, 아니면 UpbitClient 반환

        Args:
            settings: Application settings

        Returns:
            MockUpbitClient if testnet_mode is True, otherwise UpbitClient
        """
        if settings.testnet_mode:
            return MockUpbitClient()
        return UpbitClient(settings)

    mode_aware_upbit_client: providers.Provider[UpbitClient | MockUpbitClient] = providers.Factory(
        _get_mode_aware_client,
        settings=settings,
    )

    # =========================================================================
    # Infrastructure - Persistence
    # =========================================================================

    # Audit repository - Singleton for shared database connection
    # @MX:ANCHOR: audit_repository
    # @MX:REASON: 감사 로그 저장소의 중앙 진입점
    # fan_in: 3+ (SecurityService, main.py, web_ui.py)
    audit_repository: providers.Provider[SQLiteAuditRepository] = providers.Singleton(
        SQLiteAuditRepository,
        settings=settings,
    )

    # =========================================================================
    # Domain Services
    # =========================================================================

    # @MX:NOTE: TradingService is stateful, so Factory is used instead of Singleton.
    # Each call gets a fresh instance with clean state.
    trading_service: providers.Provider[TradingService] = providers.Factory(
        TradingService,
        upbit_client=upbit_client,
        settings=settings,
    )

    # @MX:ANCHOR: SecurityService
    # @MX:REASON: 2FA 및 거래 한도를 적용하는 보안 래퍼
    # fan_in: 2+ (main.py, web_ui.py)
    # @MX:NOTE: Factory를 사용하여 매 요청마다 새 인스턴스 생성 (세션 상태 관리)
    security_service: providers.Provider[SecurityService] = providers.Factory(
        SecurityService,
        trading_service=trading_service,
        settings=settings,
        audit_repository=audit_repository,
    )


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
