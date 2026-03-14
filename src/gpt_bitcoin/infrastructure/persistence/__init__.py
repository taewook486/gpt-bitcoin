"""
Infrastructure persistence layer for data storage.

This module provides:
- SQLiteAuditRepository for audit log storage
- TradeRepository for trade history storage
- Database connection management
"""

from gpt_bitcoin.infrastructure.persistence.audit_repository import (
    AUDIT_LOG_SCHEMA,
    SQLiteAuditRepository,
)
from gpt_bitcoin.infrastructure.persistence.trade_repository import TradeRepository

__all__ = [
    "AUDIT_LOG_SCHEMA",
    "SQLiteAuditRepository",
    "TradeRepository",
]
