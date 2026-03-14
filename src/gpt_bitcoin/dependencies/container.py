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
from gpt_bitcoin.domain.analytics import PortfolioAnalyticsService
from gpt_bitcoin.domain.backup import BackupService
from gpt_bitcoin.domain.notification import NotificationService
from gpt_bitcoin.domain.security import SecurityService
from gpt_bitcoin.domain.testnet_config import TestnetConfig
from gpt_bitcoin.domain.trading import TradingService
from gpt_bitcoin.domain.user_profile import UserProfileService
from gpt_bitcoin.infrastructure.external.glm_client import GLMClient
from gpt_bitcoin.infrastructure.external.mock_upbit_client import MockUpbitClient
from gpt_bitcoin.infrastructure.external.upbit_client import UpbitClient
from gpt_bitcoin.infrastructure.persistence.audit_repository import (
    SQLiteAuditRepository,
)
from gpt_bitcoin.infrastructure.persistence.notification_repository import (
    NotificationRepository,
)
from gpt_bitcoin.infrastructure.persistence.profile_repository import (
    ProfileRepository,
)
from gpt_bitcoin.infrastructure.persistence.trade_repository import TradeRepository
from gpt_bitcoin.infrastructure.rate_limiting.rate_limiter import RateLimiter
from gpt_bitcoin.infrastructure.resilience.circuit_breaker import CircuitBreaker
from gpt_bitcoin.infrastructure.resilience.retry import RetryConfig


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

    # =========================================================================
    # Infrastructure - Rate Limiting & Resilience (REQ-RATE-001)
    # =========================================================================

    # Rate limiter for GLM API (60 requests/hour default)
    # @MX:ANCHOR: glm_rate_limiter
    # @MX:REASON: GLM API 호출 속도 제한의 중앙 진입점
    # fan_in: 2+ (GLMClient, tests)
    def _create_glm_rate_limiter(settings: Settings) -> RateLimiter:
        """Create rate limiter for GLM API."""
        return RateLimiter(
            default_capacity=settings.openai_requests_per_hour,  # 60/hour
            default_refill_rate=settings.openai_requests_per_hour / 3600,  # tokens/second
        )

    glm_rate_limiter: providers.Provider[RateLimiter] = providers.Singleton(
        _create_glm_rate_limiter,
        settings=settings,
    )

    # Rate limiter for Upbit API (10 requests/second, 600 requests/minute)
    # @MX:ANCHOR: upbit_rate_limiter
    # @MX:REASON: Upbit API 호출 속도 제한의 중앙 진입점
    # fan_in: 2+ (UpbitClient, MockUpbitClient, tests)
    def _create_upbit_rate_limiter(settings: Settings) -> RateLimiter:
        """Create rate limiter for Upbit API."""
        return RateLimiter(
            default_capacity=settings.upbit_requests_per_second,  # 10 tokens
            default_refill_rate=settings.upbit_requests_per_second,  # 10 tokens/second
        )

    upbit_rate_limiter: providers.Provider[RateLimiter] = providers.Singleton(
        _create_upbit_rate_limiter,
        settings=settings,
    )

    # Circuit breaker for GLM API
    # @MX:ANCHOR: glm_circuit_breaker
    # @MX:REASON: GLM API 장애 격리의 중앙 진입점
    # fan_in: 2+ (ProtectedAPIClient, tests)
    def _create_glm_circuit_breaker(settings: Settings) -> CircuitBreaker:
        """Create circuit breaker for GLM API."""
        return CircuitBreaker(
            name="glm-api",
            failure_threshold=settings.circuit_failure_threshold,  # 5 failures
            recovery_timeout=float(settings.circuit_recovery_timeout),  # 60 seconds
        )

    glm_circuit_breaker: providers.Provider[CircuitBreaker] = providers.Singleton(
        _create_glm_circuit_breaker,
        settings=settings,
    )

    # Circuit breaker for Upbit API
    # @MX:ANCHOR: upbit_circuit_breaker
    # @MX:REASON: Upbit API 장애 격리의 중앙 진입점
    # fan_in: 2+ (ProtectedAPIClient, tests)
    def _create_upbit_circuit_breaker(settings: Settings) -> CircuitBreaker:
        """Create circuit breaker for Upbit API."""
        return CircuitBreaker(
            name="upbit-api",
            failure_threshold=settings.circuit_failure_threshold,  # 5 failures
            recovery_timeout=float(settings.circuit_recovery_timeout),  # 60 seconds
        )

    upbit_circuit_breaker: providers.Provider[CircuitBreaker] = providers.Singleton(
        _create_upbit_circuit_breaker,
        settings=settings,
    )

    # Retry config for API calls
    # @MX:NOTE: Retry config는 공통 설정 사용
    def _create_api_retry_config(settings: Settings) -> RetryConfig:
        """Create retry config for API calls."""
        return RetryConfig(
            max_attempts=settings.api_max_retries,  # 3 attempts
            base_delay=settings.api_base_delay,  # 1 second
            max_delay=settings.api_max_delay,  # 60 seconds
            exponential_multiplier=2.0,
            jitter=True,
        )

    api_retry_config: providers.Provider[RetryConfig] = providers.Singleton(
        _create_api_retry_config,
        settings=settings,
    )

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

    # Profile repository - Singleton for shared database connection
    # @MX:ANCHOR: profile_repository
    # @MX:REASON: 사용자 프로필 저장소의 중앙 진입점
    # fan_in: 2+ (UserProfileService, future web UI)
    profile_repository: providers.Provider[ProfileRepository] = providers.Singleton(
        ProfileRepository,
        settings=settings,
    )

    # Notification repository - Singleton for shared database connection
    # @MX:ANCHOR: notification_repository
    # @MX:REASON: 알림 저장소의 중앙 진입점
    # fan_in: 2+ (NotificationService, InAppChannel)
    notification_repository: providers.Provider[NotificationRepository] = providers.Singleton(
        NotificationRepository,
        settings=settings,
    )

    # Trade repository - Singleton for shared database connection
    # @MX:ANCHOR: trade_repository
    # @MX:REASON: 거래 내역 저장소의 중앙 진입점
    # fan_in: 3+ (TradeHistoryService, TradingService, web_ui.py)
    trade_repository: providers.Provider[TradeRepository] = providers.Singleton(
        TradeRepository,
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
        trade_repository=trade_repository,
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

    # @MX:ANCHOR: UserProfileService
    # @MX:REASON: 사용자 프로필 관리 서비스의 중앙 진입점
    # fan_in: 2+ (future web UI, notification system)
    # @MX:NOTE: Factory를 사용하여 매 요청마다 새 인스턴스 생성
    user_profile_service: providers.Provider[UserProfileService] = providers.Factory(
        UserProfileService,
        repository=profile_repository,
        security_service=security_service,
    )

    # @MX:ANCHOR: NotificationService
    # @MX:REASON: 알림 전송 서비스의 중앙 진입점
    # fan_in: 2+ (TradingService, future web UI)
    # @MX:NOTE: Factory를 사용하여 매 요청마다 새 인스턴스 생성
    notification_service: providers.Provider[NotificationService] = providers.Factory(
        NotificationService,
        user_profile_service=user_profile_service,
        email_channel=None,  # TODO: Configure when SMTP is available
        in_app_channel=None,  # TODO: Configure InAppChannel
    )

    # @MX:ANCHOR: backup_service
    # @MX:REASON: 백업 및 복구 서비스의 중앙 진입점
    # fan_in: 2+ (web UI, scheduler)
    # @MX:NOTE: Factory를 사용하여 매 요청마다 새 인스턴스 생성
    def _create_backup_service(
        settings: Settings,
        user_profile_service: UserProfileService,
        trade_history_service: TradingService,
    ) -> BackupService:
        """Create backup service with configuration."""
        return BackupService(
            config=settings.backup,
            settings=settings,
            user_profile_service=user_profile_service,
            trade_history_service=trade_history_service,
        )

    backup_service: providers.Provider[BackupService] = providers.Factory(
        _create_backup_service,
        settings=settings,
        user_profile_service=user_profile_service,
        trade_history_service=trading_service,
    )

    # @MX:ANCHOR: portfolio_analytics_service
    # @MX:REASON: 포트폴리오 분석 서비스의 중앙 진입점 (SPEC-TRADING-008)
    # fan_in: 2+ (Portfolio Dashboard, Analytics API)
    # @MX:NOTE: Factory를 사용하여 매 요청마다 새 인스턴스 생성
    portfolio_analytics_service: providers.Provider[PortfolioAnalyticsService] = providers.Factory(
        PortfolioAnalyticsService,
        trade_history_service=trading_service,
        upbit_client=mode_aware_upbit_client,
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
