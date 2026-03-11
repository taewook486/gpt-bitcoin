"""
Security domain module for trading system protection.

This module provides:
- SecurityService for 2FA authentication
- Trading limits enforcement
- High-value trade confirmation
- Audit logging integration

@MX:NOTE: Security module - Protects trading operations with authentication and limits
"""

from __future__ import annotations

import datetime
import hashlib
import secrets
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from gpt_bitcoin.config.settings import Settings
    from gpt_bitcoin.domain.audit import AuditRecord, AuditRepository
    from gpt_bitcoin.infrastructure.logging import BoundLogger
    from gpt_bitcoin.domain.trading import TradeApproval, TradeResult, TradingService
    from gpt_bitcoin.infrastructure.logging import BoundLogger


# =============================================================================
# Exceptions
# =============================================================================


class SecurityError(Exception):
    """Base exception for security-related errors."""

    pass


class PinNotSetError(SecurityError):
    """Raised when PIN is required but not configured."""

    pass


class PinAlreadySetError(SecurityError):
    """Raised when trying to set PIN when already configured."""

    pass


class SecurityLockedError(SecurityError):
    """Raised when security module is locked due to too many failures."""

    pass


class LimitExceededError(SecurityError):
    """Raised when trading limit is exceeded."""

    pass


# =============================================================================
# Domain Models
# =============================================================================


@dataclass
class SecuritySettings:
    """
    Security configuration stored in Settings.

    Attributes:
        pin_hash: SHA-256 hash of PIN + salt
        pin_salt: Random salt for PIN hashing
        pin_failure_count: Consecutive failed attempts
        locked_until: Lock expiration time
        max_daily_volume_krw: Max daily trading volume in KRW
        max_daily_trades: Max trades per day
        max_single_trade_krw: Max KRW per single trade
        high_value_threshold_krw: Extra confirmation above this threshold
        max_session_volume_krw: Max KRW per session
        max_session_trades: Max trades per session

    @MX:NOTE: Security settings are persisted in Settings JSON file.
        PIN is never stored in plain text.
    """

    pin_hash: str | None = None
    pin_salt: str | None = None
    pin_failure_count: int = 0
    locked_until: datetime.datetime | None = None

    # Trading limits
    max_daily_volume_krw: float = 10_000_000.0
    max_daily_trades: int = 20
    max_single_trade_krw: float = 5_000_000.0
    high_value_threshold_krw: float = 100_000.0

    # Session limits
    max_session_volume_krw: float = 5_000_000.0
    max_session_trades: int = 10


# Pydantic model for Settings integration
class SecuritySettingsModel(BaseModel):
    """Pydantic model for SecuritySettings validation in Settings."""

    pin_hash: str | None = Field(default=None, description="SHA-256 hash of PIN")
    pin_salt: str | None = Field(default=None, description="Salt for PIN hashing")
    pin_failure_count: int = Field(default=0, ge=0, description="Consecutive PIN failures")
    locked_until: str | None = Field(default=None, description="Lock expiration ISO datetime")
    max_daily_volume_krw: float = Field(
        default=10_000_000.0,
        ge=0,
        description="Max daily trading volume in KRW",
    )
    max_daily_trades: int = Field(default=20, ge=0, description="Max trades per day")
    max_single_trade_krw: float = Field(
        default=5_000_000.0,
        ge=0,
        description="Max KRW per single trade",
    )
    high_value_threshold_krw: float = Field(
        default=100_000.0,
        ge=0,
        description="Extra confirmation threshold",
    )
    max_session_volume_krw: float = Field(
        default=5_000_000.0,
        ge=0,
        description="Max KRW per session",
    )
    max_session_trades: int = Field(default=10, ge=0, description="Max trades per session")

    @field_validator("locked_until")
    @classmethod
    def parse_locked_until(cls, v: str | None) -> datetime.datetime | None:
        """Parse locked_until string to datetime."""
        if v is None:
            return None
        try:
            return datetime.datetime.fromisoformat(v)
        except ValueError:
            return None


# =============================================================================
# SecurityService
# =============================================================================


@dataclass
class SecurityService:
    """
    Domain service for security enforcement.

    This service wraps TradingService with security layers:
    1. 2FA verification
    2. Trading limits check
    3. High-value confirmation
    4. Audit logging

    @MX:NOTE: SecurityService is the secure entry point for all trades.
        TradingService should not be called directly after this is implemented.

    @MX:ANCHOR: SecurityService.verify_pin
        fan_in: 3+ (secure_request_buy, secure_request_sell, CLI)
        @MX:REASON: Centralized 2FA verification for all trading operations

    @MX:ANCHOR: SecurityService.secure_execute_trade
        fan_in: 2+ (secure_request_buy, secure_request_sell)
        @MX:REASON: Single entry point for secure trade execution with audit
    """

    MAX_PIN_FAILURES: ClassVar[int] = 5
    LOCK_DURATION_SECONDS: ClassVar[int] = 300  # 5 minutes
    WEAK_PINS: ClassVar[set[str]] = {
        "1234", "4321", "1111", "2222", "3333", "4444",
        "5555", "6666", "7777", "8888", "9999", "0000"
    }

    trading_service: TradingService
    settings: Settings
    audit_repository: AuditRepository

    # Session counters (reset per session)
    _session_volume_traded: float = field(default=0.0)
    _session_trade_count: int = field(default=0)

    def __init__(
        self,
        trading_service: TradingService,
        settings: Settings,
        audit_repository: AuditRepository,
    ) -> None:
        """Initialize SecurityService with dependencies."""
        self.trading_service = trading_service
        self.settings = settings
        self.audit_repository = audit_repository

    # =========================================================================
    # 2FA Methods
    # =========================================================================

    async def verify_pin(self, pin: str) -> bool:
        """
        Verify 4-digit PIN against stored hash.

        Returns:
            bool: True if PIN is correct

        Raises:
            SecurityLockedError: If module is locked due to too many failures
            PinNotSetError: If PIN has not been configured

        @MX:WARN: Increments failure count on incorrect PIN.
            Locks module after 5 consecutive failures.
            @MX:REASON: Brute force protection for PIN-based authentication.
        """
        # Cache security settings locally for efficiency
        security = self.settings.security

        # Check if locked
        if self.is_locked():
            raise SecurityLockedError(
                f"보안 모듈이 잠겼습니다. {self.get_lock_remaining_seconds() // 60}분 후 다시 시도하세요"
            )

        # Check if PIN is set
        if security.pin_hash is None:
            raise PinNotSetError("PIN이 설정되지 않았습니다. 먼저 PIN을 설정해주세요.")

        # Verify PIN
        pin_hash = self._hash_pin(pin, security.pin_salt)
        if pin_hash == security.pin_hash:
            # Correct PIN - reset failure count
            security.pin_failure_count = 0
            return True
        else:
            # Incorrect PIN - increment failure count
            security.pin_failure_count += 1

            # Check if should lock
            if security.pin_failure_count >= self.MAX_PIN_FAILURES:
                security.locked_until = (
                    datetime.datetime.now()
                    + datetime.timedelta(seconds=self.LOCK_DURATION_SECONDS)
                )

            return False

    async def setup_pin(self, new_pin: str) -> None:
        """
        Set up PIN for the first time.

        Requirements:
        - Must be exactly 4 digits
        - Cannot be sequential (1234, 4321)
        - Cannot be repetitive (1111, 2222)

        Raises:
            ValueError: If PIN does not meet requirements
            PinAlreadySetError: If PIN is already configured
        """
        # Check if already set
        if self.settings.security.pin_hash is not None:
            raise PinAlreadySetError("PIN이 이미 설정되어 있습니다. 변경하려면 change_pin을 사용하세요.")

        # Validate PIN strength
        self._validate_pin_strength(new_pin)

        # Generate salt and hash
        salt = secrets.token_hex(16)
        pin_hash = self._hash_pin(new_pin, salt)

        # Store in settings
        self.settings.security.pin_hash = pin_hash
        self.settings.security.pin_salt = salt
        self.settings.security.pin_failure_count = 0

    async def change_pin(self, old_pin: str, new_pin: str) -> bool:
        """
        Change existing PIN after verifying old PIN.

        Returns:
            bool: True if PIN changed successfully
        """
        # Verify old PIN
        if not await self.verify_pin(old_pin):
            return False

        # Validate new PIN strength
        self._validate_pin_strength(new_pin)

        # Generate new salt and hash
        salt = secrets.token_hex(16)
        pin_hash = self._hash_pin(new_pin, salt)

        # Store new PIN
        self.settings.security.pin_hash = pin_hash
        self.settings.security.pin_salt = salt

        return True

    def is_pin_set(self) -> bool:
        """Check if PIN has been set up."""
        return self.settings.security.pin_hash is not None and self.settings.security.pin_hash != ""

    def is_locked(self) -> bool:
        """Check if security module is currently locked."""
        if self.settings.security.locked_until is None:
            return False

        # Check if lock has expired
        if datetime.datetime.now() >= self.settings.security.locked_until:
            self.settings.security.locked_until = None
            self.settings.security.pin_failure_count = 0
            return False

        return True

    def get_lock_remaining_seconds(self) -> int:
        """Get remaining lock time in seconds (0 if not locked)."""
        if self.settings.security.locked_until is None:
            return 0

        remaining = self.settings.security.locked_until - datetime.datetime.now()
        return max(0, int(remaining.total_seconds()))

    def _hash_pin(self, pin: str, salt: str) -> str:
        """Hash PIN with salt using SHA-256."""
        combined = f"{pin}{salt}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def _validate_pin_strength(self, pin: str) -> None:
        """
        Validate PIN strength requirements.

        Requirements:
        - Must be exactly 4 digits
        - Cannot be in weak PINs list

        Raises:
            ValueError: If PIN does not meet requirements
        """
        if not pin.isdigit() or len(pin) != 4:
            raise ValueError("PIN은 4자리 숫자여야 합니다.")

        if pin in self.WEAK_PINS:
            raise ValueError(f"약한 PIN입니다: {pin}. 연속되거나 반복되는 숫자는 사용할 수 없습니다.")

    # =========================================================================
    # Limits Methods
    # =========================================================================

    async def check_daily_limits(
        self,
        _ticker: str,
        _side: str,
        amount_krw: float,
    ) -> tuple[bool, str]:
        """
        Check if trade would exceed daily limits.

        Returns:
            tuple[bool, str]: (passed, error_message_if_failed)
        """
        # Check volume limit
        daily_volume = await self.audit_repository.get_daily_volume_traded()
        if daily_volume + amount_krw > self.settings.security.max_daily_volume_krw:
            return (
                False,
                f"일일 거래 한도 초과 ({self.settings.security.max_daily_volume_krw:,.0f} KRW)",
            )

        # Check trade count limit
        daily_count = await self.audit_repository.get_daily_trade_count()
        if daily_count >= self.settings.security.max_daily_trades:
            return (
                False,
                f"일일 거래 횟수 한도 초과 ({self.settings.security.max_daily_trades}회)",
            )

        return True, ""

    async def check_session_limits(
        self,
        _ticker: str,
        _side: str,
        amount_krw: float,
    ) -> tuple[bool, str]:
        """
        Check if trade would exceed session limits.

        Returns:
            tuple[bool, str]: (passed, error_message_if_failed)
        """
        # Check volume limit
        if self._session_volume_traded + amount_krw > self.settings.security.max_session_volume_krw:
            return (
                False,
                f"세션 거래 한도 초과 ({self.settings.security.max_session_volume_krw:,.0f} KRW)",
            )

        # Check trade count limit
        if self._session_trade_count >= self.settings.security.max_session_trades:
            return (
                False,
                f"세션 거래 횟수 한도 초과 ({self.settings.security.max_session_trades}회)",
            )

        return True, ""

    def check_single_trade_limit(self, amount_krw: float) -> tuple[bool, str]:
        """
        Check if single trade exceeds limit.

        Returns:
            tuple[bool, str]: (passed, error_message_if_failed)
        """
        if amount_krw > self.settings.security.max_single_trade_krw:
            return (
                False,
                f"단일 거래 한도 초과 ({self.settings.security.max_single_trade_krw:,.0f} KRW)",
            )

        return True, ""

    def is_high_value_trade(self, amount_krw: float) -> bool:
        """Check if trade requires extra confirmation."""
        return amount_krw > self.settings.security.high_value_threshold_krw

    # =========================================================================
    # Secure Trade Execution
    # =========================================================================

    async def secure_request_buy(
        self,
        ticker: str,
        amount_krw: float,
        pin: str,
        session_id: str,
    ) -> TradeApproval:
        """
        Request buy order with security checks.

        Flow:
        1. Verify PIN
        2. Check single trade limit
        3. Check daily/session limits
        4. Request via TradingService

        Returns:
            TradeApproval: Approval request from TradingService

        Raises:
            SecurityLockedError: Module locked
            PinNotSetError: PIN not configured
            LimitExceededError: Trading limit exceeded
        """
        # Verify PIN
        if not await self.verify_pin(pin):
            raise SecurityError("PIN 인증 실패")

        # Check single trade limit
        passed, error = self.check_single_trade_limit(amount_krw)
        if not passed:
            raise LimitExceededError(error)

        # Check daily limits
        passed, error = await self.check_daily_limits(ticker, "buy", amount_krw)
        if not passed:
            raise LimitExceededError(error)

        # Check session limits
        passed, error = await self.check_session_limits(ticker, "buy", amount_krw)
        if not passed:
            raise LimitExceededError(error)

        # Log audit attempt
        await self.audit_repository.log_audit(
            ticker=ticker,
            side="buy",
            amount=amount_krw,
            user_action="approved",
            two_fa_verified=True,
            limit_check_passed=True,
            high_value_trade=self.is_high_value_trade(amount_krw),
            error_message=None,
            session_id=session_id,
        )

        # Request via TradingService
        approval = await self.trading_service.request_buy_order(ticker, amount_krw)

        return approval

    async def secure_request_sell(
        self,
        ticker: str,
        quantity: float,
        pin: str,
        session_id: str,
    ) -> TradeApproval:
        """
        Request sell order with security checks (same flow as buy).
        """
        # Verify PIN
        if not await self.verify_pin(pin):
            raise SecurityError("PIN 인증 실패")

        # Get estimated value for limit checks
        price = await self.trading_service.upbit_client.get_current_price(ticker)
        amount_krw = price * quantity

        # Check single trade limit
        passed, error = self.check_single_trade_limit(amount_krw)
        if not passed:
            raise LimitExceededError(error)

        # Check daily limits
        passed, error = await self.check_daily_limits(ticker, "sell", amount_krw)
        if not passed:
            raise LimitExceededError(error)

        # Check session limits
        passed, error = await self.check_session_limits(ticker, "sell", amount_krw)
        if not passed:
            raise LimitExceededError(error)

        # Log audit attempt
        await self.audit_repository.log_audit(
            ticker=ticker,
            side="sell",
            amount=amount_krw,
            user_action="approved",
            two_fa_verified=True,
            limit_check_passed=True,
            high_value_trade=self.is_high_value_trade(amount_krw),
            error_message=None,
            session_id=session_id,
        )

        # Request via TradingService
        approval = await self.trading_service.request_sell_order(ticker, quantity)

        return approval

    async def secure_execute_trade(
        self,
        approval: TradeApproval,
        high_value_confirmed: bool,
        session_id: str,
    ) -> TradeResult:
        """
        Execute trade with security validation.

        Flow:
        1. Check high-value confirmation if needed
        2. Execute via TradingService
        3. Log to audit (success or failure)
        4. Update session counters

        @MX:WARN: Executes REAL trades with REAL money.
            All security checks must pass before execution.
            @MX:REASON: Direct API call to Upbit exchange.
        """
        # Check high-value confirmation
        if self.is_high_value_trade(approval.amount) and not high_value_confirmed:
            raise SecurityError("고액 거래 확인이 필요합니다.")

        # Execute via TradingService
        result = await self.trading_service.execute_approved_trade(approval)

        # Log audit based on result
        user_action = "approved" if result.success else "failed"

        await self.audit_repository.log_audit(
            ticker=approval.ticker,
            side=approval.side,
            amount=approval.amount,
            user_action=user_action,
            two_fa_verified=True,
            limit_check_passed=True,
            high_value_trade=self.is_high_value_trade(approval.amount),
            error_message=result.error_message if not result.success else None,
            session_id=session_id,
        )

        # Update session counters
        if result.success:
            self._session_volume_traded += approval.amount
            self._session_trade_count += 1

        return result

    # =========================================================================
    # Audit Methods
    # =========================================================================

    async def log_audit(
        self,
        ticker: str,
        side: str,
        amount: float,
        user_action: str,
        two_fa_verified: bool,
        limit_check_passed: bool,
        high_value_trade: bool,
        error_message: str | None = None,
        session_id: str = "default",
    ) -> int:
        """Log trade attempt to audit table."""
        record_id = await self.audit_repository.insert(
            ticker=ticker,
            side=side,
            amount=amount,
            user_action=user_action,
            two_fa_verified=two_fa_verified,
            limit_check_passed=limit_check_passed,
            high_value_trade=high_value_trade,
            error_message=error_message,
            session_id=session_id,
        )
        return record_id

    async def get_audit_history(
        self,
        start_date: datetime.datetime | None = None,
        end_date: datetime.datetime | None = None,
        user_action: str | None = None,
        limit: int = 100,
    ) -> list[AuditRecord]:
        """Query audit log history."""
        return await self.audit_repository.find_with_filters(
            filters={
                "start_date": start_date,
                "end_date": end_date,
                "user_action": user_action,
            },
            limit=limit,
        )
