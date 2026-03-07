"""
Audit repository implementation for SQLite persistence.

This module provides:
- SQLiteAuditRepository for audit record storage
- Database connection management
- CRUD operations for audit records

@MX:NOTE: Uses SQLite for local audit log storage.
"""

from __future__ import annotations

import aiosqlite
import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from gpt_bitcoin.domain.audit import AuditRecord, AuditRepository

if TYPE_CHECKING:
    from gpt_bitcoin.config.settings import Settings


# =============================================================================
# Database Schema
# =============================================================================


# SQL schema for audit_log table
AUDIT_LOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    side TEXT NOT NULL CHECK(side IN ('buy', 'sell')),
    amount REAL NOT NULL,
    user_action TEXT NOT NULL,
    two_fa_verified BOOLEAN NOT NULL DEFAULT 0,
    limit_check_passed BOOLEAN NOT NULL DEFAULT 0,
    high_value_trade BOOLEAN NOT NULL DEFAULT 0,
    error_message TEXT,
    session_id TEXT NOT NULL DEFAULT 'default',
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_log_ticker ON audit_log(ticker);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_session ON audit_log(session_id);
"""


# =============================================================================
# SQLiteAuditRepository
# =============================================================================


class SQLiteAuditRepository(AuditRepository):
    """
    SQLite implementation of AuditRepository.

    @MX:ANCHOR: SQLiteAuditRepository.insert
        fan_in: 3+ (SecurityService, CLI, Web UI)
        @MX:REASON: Single entry point for all audit writes.

    @MX:WARN: Database failures are logged but do not block trade execution.
        @MX:REASON: Audit is compliance feature, not critical path.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize repository with settings."""
        super().__init__(settings)
        # Use same db as settings, with audit_log table
        self.db_path = Path(settings.db_path)

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get database connection and ensure schema exists."""
        conn = await aiosqlite.connect(self.db_path)
        await conn.execute(AUDIT_LOG_SCHEMA)
        return conn

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
        """Insert a new audit record."""
        try:
            async with await self._get_connection() as conn:
                cursor = await conn.execute(
                    """INSERT INTO audit_log
                    (ticker, side, amount, user_action, two_fa_verified,
                     limit_check_passed, high_value_trade, error_message, session_id, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        ticker,
                        side,
                        amount,
                        user_action,
                        two_fa_verified,
                        limit_check_passed,
                        high_value_trade,
                        error_message,
                        session_id,
                        datetime.datetime.now().isoformat(),
                    ),
                )
                await conn.commit()
                return cursor.lastrowid
        except Exception as e:
            # Log error but don't raise - audit is not critical path
            print(f"[AUDIT] Failed to insert audit record: {e}")
            return -1

    async def find_with_filters(
        self,
        filters: dict,
        limit: int = 100,
    ) -> list[AuditRecord]:
        """Query audit records with filters."""
        try:
            async with await self._get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                query = "SELECT * FROM audit_log WHERE 1=1"
                params = []

                # Build dynamic query
                if start_date := filters.get("start_date"):
                    query += " AND timestamp >= ?"
                    params.append(start_date.isoformat())

                if end_date := filters.get("end_date"):
                    query += " AND timestamp <= ?"
                    params.append(end_date.isoformat())

                if user_action := filters.get("user_action"):
                    query += " AND user_action = ?"
                    params.append(user_action)

                if ticker := filters.get("ticker"):
                    query += " AND ticker = ?"
                    params.append(ticker)

                if session_id := filters.get("session_id"):
                    query += " AND session_id = ?"
                    params.append(session_id)

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                async with conn.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    return [
                        AuditRecord(
                            id=row["id"],
                            ticker=row["ticker"],
                            side=row["side"],
                            amount=row["amount"],
                            user_action=row["user_action"],
                            two_fa_verified=bool(row["two_fa_verified"]),
                            limit_check_passed=bool(row["limit_check_passed"]),
                            high_value_trade=bool(row["high_value_trade"]),
                            error_message=row["error_message"],
                            session_id=row["session_id"],
                            timestamp=datetime.datetime.fromisoformat(row["timestamp"]),
                            created_at=datetime.datetime.fromisoformat(row["created_at"]),
                        )
                        for row in rows
                    ]
        except Exception as e:
            print(f"[AUDIT] Failed to query audit records: {e}")
            return []

    async def get_daily_volume_traded(self) -> float:
        """Get total KRW volume traded today (successful trades only)."""
        try:
            async with await self._get_connection() as conn:
                today = datetime.datetime.now().date().isoformat()

                async with conn.execute(
                    """SELECT COALESCE(SUM(amount), 0) as total
                    FROM audit_log
                    WHERE DATE(timestamp) = ?
                    AND user_action = 'approved'
                    AND side IN ('buy', 'sell')""",
                    (today,),
                ) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else 0.0
        except Exception:
            return 0.0

    async def get_daily_trade_count(self) -> int:
        """Get total number of successful trades today."""
        try:
            async with await self._get_connection() as conn:
                today = datetime.datetime.now().date().isoformat()

                async with conn.execute(
                    """SELECT COUNT(*) as count
                    FROM audit_log
                    WHERE DATE(timestamp) = ?
                    AND user_action = 'approved'
                    AND side IN ('buy', 'sell')""",
                    (today,),
                ) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else 0
        except Exception:
            return 0
