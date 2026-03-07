"""
Audit domain module for security compliance and trade logging.

This module provides:
- AuditRecord for trade attempt logging
- AuditRepository for persistence operations
- Security event tracking for regulatory compliance

@MX:NOTE: Audit module - Maintains immutable security trail
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gpt_bitcoin.config.settings import Settings


# =============================================================================
# Exceptions
# =============================================================================


class AuditError(Exception):
    """Base exception for audit-related errors."""

    pass


# =============================================================================
# Domain Models
# =============================================================================


@dataclass
class AuditRecord:
    """
    Single audit record for a trade attempt.

    Attributes:
        id: Auto-increment primary key
        ticker: Market ticker (e.g., "KRW-BTC")
        side: Trade side ("buy" or "sell")
        amount: Trade amount in KRW
        user_action: User decision ("approved", "rejected", "failed")
        two_fa_verified: Whether 2FA passed
        limit_check_passed: Whether trading limits passed
        high_value_trade: Whether trade exceeded high_value_threshold
        error_message: Error message if failed
        session_id: Session identifier for grouping
        timestamp: When the trade attempt occurred
        created_at: When record was created

    @MX:NOTE: Immutable security trail.
        Records are never updated or deleted after creation.
        @MX:REASON: Regulatory compliance requires unalterable audit log.
    """

    id: int | None = None  # Set by repository after insert
    ticker: str = ""
    side: str = ""  # "buy" or "sell"
    amount: float = 0.0
    user_action: str = ""  # "approved", "rejected", "failed"
    two_fa_verified: bool = False
    limit_check_passed: bool = False
    high_value_trade: bool = False
    error_message: str | None = None
    session_id: str = "default"
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)


# =============================================================================
# Repository Interface
# =============================================================================


class AuditRepository:
    """
    Repository for audit record persistence.

    This is a domain interface - concrete implementations are provided
    in the infrastructure layer.

    @MX:ANCHOR: AuditRepository.insert
        fan_in: 3+ (SecurityService, CLI, Web UI)
        @MX:REASON: Single entry point for all audit writes.

    @MX:WARN: Database failures must not block trade execution.
        @MX:REASON: Audit is compliance feature, not critical path.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize repository with settings for database path."""
        self.settings = settings

    async def insert(
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
        """
        Insert a new audit record.

        Returns:
            int: Record ID

        Raises:
            AuditError: If database operation fails
        """
        raise NotImplementedError("Use concrete implementation in infrastructure layer")

    async def find_with_filters(
        self,
        filters: dict,
        limit: int = 100,
    ) -> list[AuditRecord]:
        """
        Query audit records with filters.

        Args:
            filters: Dict with optional keys:
                - start_date: datetime
                - end_date: datetime
                - user_action: str
                - ticker: str
                - session_id: str
            limit: Maximum records to return

        Returns:
            list[AuditRecord]: Matching records, newest first
        """
        raise NotImplementedError("Use concrete implementation in infrastructure layer")

    async def get_daily_volume_traded(self) -> float:
        """
        Get total KRW volume traded today (successful trades only).

        Returns:
            float: Total volume in KRW
        """
        raise NotImplementedError("Use concrete implementation in infrastructure layer")

    async def get_daily_trade_count(self) -> int:
        """
        Get total number of successful trades today.

        Returns:
            int: Trade count
        """
        raise NotImplementedError("Use concrete implementation in infrastructure layer")

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
        """
        Convenience method for logging audit records.

        Returns:
            int: Record ID

        @MX:NOTE: Wraps insert() with parameter naming convenience.
            fan_in: 2+ (SecurityService.secure_request_*, secure_execute_trade)
        """
        return await self.insert(
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
