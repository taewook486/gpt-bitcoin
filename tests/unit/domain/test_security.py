"""
Unit tests for SecurityService and security features.

Tests cover:
- PIN setup and verification
- PIN hash storage
- PIN change functionality
- Security lockout after failed attempts
- Trading limits enforcement
- High-value trade confirmation
- Audit logging
- Security integration with TradingService

@MX:NOTE: SecurityService 테스트 - TDD RED Phase
"""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gpt_bitcoin.domain.audit import AuditRecord
from gpt_bitcoin.domain.security import (
    LimitExceededError,
    PinAlreadySetError,
    PinNotSetError,
    SecurityError,
    SecurityLockedError,
    SecurityService,
    SecuritySettings,
)
from gpt_bitcoin.domain.trading import TradeApproval, TradeResult


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_settings():
    """Create mock settings with security configuration."""
    settings = MagicMock()
    settings.security = SecuritySettings()
    settings.security.pin_hash = None
    settings.security.pin_salt = None
    settings.security.pin_failure_count = 0
    settings.security.locked_until = None
    settings.security.max_daily_volume_krw = 10_000_000.0
    settings.security.max_daily_trades = 20
    settings.security.max_single_trade_krw = 5_000_000.0
    settings.security.high_value_threshold_krw = 100_000.0
    settings.security.max_session_volume_krw = 5_000_000.0
    settings.security.max_session_trades = 10
    return settings


@pytest.fixture
def mock_trading_service():
    """Create mock TradingService with async methods."""
    mock_service = MagicMock()
    mock_service.request_buy_order = AsyncMock()
    mock_service.request_sell_order = AsyncMock()
    mock_service.execute_approved_trade = AsyncMock()
    mock_service.upbit_client = MagicMock()
    mock_service.upbit_client.get_current_price = AsyncMock(return_value=50_000_000.0)
    return mock_service


@pytest.fixture
def mock_audit_repository():
    """Create mock AuditRepository with async methods."""
    mock_repo = MagicMock()
    mock_repo.get_daily_volume_traded = AsyncMock(return_value=0.0)
    mock_repo.get_daily_trade_count = AsyncMock(return_value=0)
    mock_repo.insert = AsyncMock(return_value=1)
    mock_repo.log_audit = AsyncMock(return_value=1)
    mock_repo.find_with_filters = AsyncMock(return_value=[])
    return mock_repo


@pytest.fixture
def security_service(mock_settings, mock_trading_service, mock_audit_repository):
    """Create SecurityService with mocked dependencies."""
    from gpt_bitcoin.domain.security import SecurityService

    return SecurityService(
        trading_service=mock_trading_service,
        settings=mock_settings,
        audit_repository=mock_audit_repository,
    )


# =============================================================================
# PIN Setup Tests
# =============================================================================


class TestPinSetup:
    """Tests for PIN setup functionality."""

    @pytest.mark.asyncio
    async def test_setup_pin_success(self, security_service: SecurityService):
        """Test successful PIN setup."""
        await security_service.setup_pin("9876")

        assert security_service.settings.security.pin_hash is not None
        assert security_service.settings.security.pin_salt is not None

    @pytest.mark.asyncio
    async def test_setup_pin_weak_pin_rejected(self, security_service: SecurityService):
        """Test weak PINs are rejected."""
        weak_pins = ["1234", "4321", "1111", "2222", "0000", "9999"]

        for pin in weak_pins:
            with pytest.raises(ValueError, match="약한 PIN"):
                await security_service.setup_pin(pin)

    @pytest.mark.asyncio
    async def test_setup_pin_invalid_format_rejected(self, security_service: SecurityService):
        """Test invalid PIN formats are rejected."""
        invalid_pins = ["abc", "12345", "123", "12ab"]

        for pin in invalid_pins:
            with pytest.raises(ValueError, match="4자리 숫자"):
                await security_service.setup_pin(pin)

    @pytest.mark.asyncio
    async def test_setup_pin_already_set_raises_error(self, security_service: SecurityService):
        """Test setting PIN twice raises error."""
        await security_service.setup_pin("9876")

        with pytest.raises(PinAlreadySetError):
            await security_service.setup_pin("5678")


# =============================================================================
# PIN Verification Tests
# =============================================================================


class TestPinVerification:
    """Tests for PIN verification functionality."""

    @pytest.mark.asyncio
    async def test_verify_pin_success(self, security_service: SecurityService):
        """Test successful PIN verification."""
        await security_service.setup_pin("9876")

        result = await security_service.verify_pin("9876")
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_pin_incorrect_returns_false(self, security_service: SecurityService):
        """Test incorrect PIN returns False."""
        await security_service.setup_pin("9876")

        result = await security_service.verify_pin("5678")
        assert result is False
        # Verify failure count incremented
        assert security_service.settings.security.pin_failure_count == 1

    @pytest.mark.asyncio
    async def test_verify_pin_not_set_raises_error(self, security_service: SecurityService):
        """Test verifying PIN when not set raises error."""
        with pytest.raises(PinNotSetError):
            await security_service.verify_pin("9876")

    @pytest.mark.asyncio
    async def test_verify_pin_5_failures_locks_module(self, security_service: SecurityService):
        """Test 5 failed PIN attempts locks the module."""
        await security_service.setup_pin("9876")

        # Fail 5 times
        for _ in range(5):
            await security_service.verify_pin("0000")

        # Module should be locked
        assert security_service.is_locked()

        with pytest.raises(SecurityLockedError):
            await security_service.verify_pin("9876")


# =============================================================================
# PIN Change Tests
# =============================================================================


class TestPinChange:
    """Tests for PIN change functionality."""

    @pytest.mark.asyncio
    async def test_change_pin_success(self, security_service: SecurityService):
        """Test successful PIN change."""
        await security_service.setup_pin("9876")

        result = await security_service.change_pin("9876", "5678")
        assert result is True

        # Old PIN no longer works
        assert await security_service.verify_pin("9876") is False
        # New PIN works
        assert await security_service.verify_pin("5678") is True

    @pytest.mark.asyncio
    async def test_change_pin_wrong_old_pin_returns_false(self, security_service: SecurityService):
        """Test changing PIN with wrong old PIN returns False."""
        await security_service.setup_pin("9876")

        result = await security_service.change_pin("0000", "5678")
        assert result is False

        # Original PIN still works
        assert await security_service.verify_pin("9876") is True


# =============================================================================
# Trading Limits Tests
# =============================================================================


class TestTradingLimits:
    """Tests for trading limit enforcement."""

    def test_check_single_trade_limit_within_limit(self, security_service: SecurityService):
        """Test single trade within limit passes."""
        passed, error = security_service.check_single_trade_limit(1_000_000.0)
        assert passed is True
        assert error == ""

    def test_check_single_trade_limit_exceeded(self, security_service: SecurityService):
        """Test single trade exceeding limit fails."""
        passed, error = security_service.check_single_trade_limit(10_000_000.0)
        assert passed is False
        assert "한도 초과" in error

    def test_is_high_value_trade_threshold(self, security_service: SecurityService):
        """Test high-value trade detection."""
        assert not security_service.is_high_value_trade(50_000.0)
        assert security_service.is_high_value_trade(150_000.0)

    @pytest.mark.asyncio
    async def test_check_daily_limits_within_limit(self, security_service: SecurityService):
        """Test daily limits check within limit."""
        passed, error = await security_service.check_daily_limits("KRW-BTC", "buy", 1_000_000.0)
        assert passed is True

    @pytest.mark.asyncio
    async def test_check_session_limits_within_limit(self, security_service: SecurityService):
        """Test session limits check within limit."""
        passed, error = await security_service.check_session_limits("KRW-BTC", "buy", 1_000_000.0)
        assert passed is True


# =============================================================================
# Secure Trade Execution Tests
# =============================================================================


class TestSecureTradeExecution:
    """Tests for secure trade execution flow."""

    @pytest.mark.asyncio
    async def test_secure_request_buy_requires_pin(self, security_service: SecurityService):
        """Test secure buy request requires PIN verification."""
        # Setup mock response
        mock_approval = TradeApproval(
            request_id="req-123",
            ticker="KRW-BTC",
            side="buy",
            amount=100_000.0,
            estimated_price=50_000_000.0,
        )
        security_service.trading_service.request_buy_order.return_value = mock_approval

        await security_service.setup_pin("9876")

        approval = await security_service.secure_request_buy(
            ticker="KRW-BTC",
            amount_krw=100_000.0,
            pin="9876",
            session_id="test-session",
        )

        assert approval.side == "buy"
        assert approval.ticker == "KRW-BTC"

    @pytest.mark.asyncio
    async def test_secure_request_buy_wrong_pin_rejected(
        self, security_service: SecurityService
    ):
        """Test secure buy request with wrong PIN is rejected."""
        await security_service.setup_pin("9876")

        with pytest.raises(SecurityError):  # PIN 인증 실패
            await security_service.secure_request_buy(
                ticker="KRW-BTC",
                amount_krw=100_000.0,
                pin="0000",
                session_id="test-session",
            )

    @pytest.mark.asyncio
    async def test_secure_execute_trade_logs_audit(
        self, security_service: SecurityService
    ):
        """Test secure execution logs to audit."""
        # Setup PIN first
        await security_service.setup_pin("9876")

        # Mock TradingService response
        mock_result = TradeResult(
            success=True,
            order_id="test-order-123",
            ticker="KRW-BTC",
            side="buy",
            executed_price=50_000_000.0,
            executed_amount=0.001,
            fee=25.0,
        )

        security_service.trading_service.execute_approved_trade.return_value = mock_result

        # Create mock approval
        approval = TradeApproval(
            request_id="req-123",
            ticker="KRW-BTC",
            side="buy",
            amount=100_000.0,
            estimated_price=50_000_000.0,
        )
        approval.mark_approved()

        # Execute trade
        result = await security_service.secure_execute_trade(
            approval=approval,
            high_value_confirmed=False,
            session_id="test-session",
        )

        assert result.success is True
        # Verify audit log was called
        security_service.audit_repository.log_audit.assert_called_once()


# =============================================================================
# Security Locked Tests
# =============================================================================


class TestSecurityLocked:
    """Tests for security module lockout functionality."""

    @pytest.mark.asyncio
    async def test_locked_module_rejects_trades(self, security_service: SecurityService):
        """Test locked module rejects all trade requests."""
        # Lock the module
        security_service.settings.security.locked_until = (
            datetime.datetime.now() + datetime.timedelta(minutes=5)
        )

        assert security_service.is_locked() is True

        # Should raise error when trying to trade
        with pytest.raises(SecurityLockedError):
            await security_service.verify_pin("9876")

    def test_get_lock_remaining_seconds(self, security_service: SecurityService):
        """Test getting remaining lock time."""
        # Not locked
        assert security_service.get_lock_remaining_seconds() == 0

        # Locked
        lock_time = datetime.datetime.now() + datetime.timedelta(seconds=150)
        security_service.settings.security.locked_until = lock_time
        remaining = security_service.get_lock_remaining_seconds()
        assert 140 <= remaining <= 150  # Allow for timing variance

    @pytest.mark.asyncio
    async def test_lock_expiration(self, security_service: SecurityService):
        """Test that lock expires after timeout period."""
        # Lock expired in the past
        security_service.settings.security.locked_until = (
            datetime.datetime.now() - datetime.timedelta(seconds=10)
        )

        # Should auto-unlock
        assert security_service.is_locked() is False

    @pytest.mark.asyncio
    async def test_expired_lock_resets_failure_count(self, security_service: SecurityService):
        """Test that expired lock resets failure count."""
        # Lock expired in the past with failure count
        security_service.settings.security.locked_until = (
            datetime.datetime.now() - datetime.timedelta(seconds=10)
        )
        security_service.settings.security.pin_failure_count = 3

        # is_locked should reset failure count
        security_service.is_locked()

        assert security_service.settings.security.pin_failure_count == 0


class TestSecurityAuditMethods:
    """Tests for SecurityService audit logging methods."""

    @pytest.mark.asyncio
    async def test_log_audit_convenience(self, security_service: SecurityService):
        """Test log_audit convenience method."""
        record_id = await security_service.log_audit(
            ticker="KRW-BTC",
            side="buy",
            amount=10000.0,
            user_action="approved",
            two_fa_verified=True,
            limit_check_passed=True,
            high_value_trade=False,
            session_id="test-session",
        )

        assert record_id == 1
        security_service.audit_repository.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_audit_history(self, security_service: SecurityService):
        """Test getting audit history."""
        # Mock return value
        mock_record = AuditRecord(
            id=1,
            ticker="KRW-BTC",
            side="buy",
            amount=10000.0,
            user_action="approved",
            two_fa_verified=True,
            limit_check_passed=True,
            high_value_trade=False,
        )
        security_service.audit_repository.find_with_filters = AsyncMock(
            return_value=[mock_record]
        )

        history = await security_service.get_audit_history(limit=10)

        assert len(history) == 1
        assert history[0].ticker == "KRW-BTC"
        security_service.audit_repository.find_with_filters.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_audit_history_with_filters(self, security_service: SecurityService):
        """Test getting audit history with date filters."""
        start_date = datetime.datetime(2026, 3, 1)
        end_date = datetime.datetime(2026, 3, 31)

        await security_service.get_audit_history(
            start_date=start_date,
            end_date=end_date,
            user_action="approved",
            limit=50,
        )

        # Verify filters were passed correctly
        security_service.audit_repository.find_with_filters.assert_called_once()
        call_args = security_service.audit_repository.find_with_filters.call_args
        assert call_args[1]["limit"] == 50
        assert call_args[1]["filters"]["start_date"] == start_date


class TestSecuritySessionCounters:
    """Tests for session counter management."""

    def test_initial_session_counters(self, security_service: SecurityService):
        """Test that session counters start at zero."""
        assert security_service._session_volume_traded == 0.0
        assert security_service._session_trade_count == 0

    @pytest.mark.asyncio
    async def test_session_counters_increment_on_success(
        self, security_service: SecurityService, mock_trading_service, mock_settings
    ):
        """Test that successful trades increment session counters."""
        # Setup PIN first (use strong PIN)
        await security_service.setup_pin("5928")

        # Mock successful trade execution
        mock_approval = TradeApproval(
            request_id="test-id",
            ticker="KRW-BTC",
            side="buy",
            amount=10000.0,
            approved=True,
        )
        mock_result = TradeResult(
            success=True,
            order_id="test-order",
            ticker="KRW-BTC",
            side="buy",
            executed_price=50000000.0,
            executed_amount=0.0002,
        )
        mock_trading_service.execute_approved_trade = AsyncMock(return_value=mock_result)

        # Execute trade
        result = await security_service.secure_execute_trade(
            approval=mock_approval,
            high_value_confirmed=False,
            session_id="test",
        )

        # Verify counters incremented
        assert security_service._session_volume_traded == 10000.0
        assert security_service._session_trade_count == 1

    @pytest.mark.asyncio
    async def test_session_counters_not_increment_on_failure(
        self, security_service: SecurityService, mock_trading_service, mock_settings
    ):
        """Test that failed trades don't increment session counters."""
        # Setup PIN first (use strong PIN)
        await security_service.setup_pin("5928")

        # Mock failed trade execution
        mock_approval = TradeApproval(
            request_id="test-id",
            ticker="KRW-BTC",
            side="buy",
            amount=10000.0,
            approved=True,
        )
        mock_result = TradeResult(
            success=False,
            ticker="KRW-BTC",
            side="buy",
            error_message="Test error",
        )
        mock_trading_service.execute_approved_trade = AsyncMock(return_value=mock_result)

        # Execute trade
        result = await security_service.secure_execute_trade(
            approval=mock_approval,
            high_value_confirmed=False,
            session_id="test",
        )

        # Verify counters NOT incremented
        assert security_service._session_volume_traded == 0.0
        assert security_service._session_trade_count == 0
