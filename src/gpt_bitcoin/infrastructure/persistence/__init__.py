"""
Infrastructure persistence layer for data storage.

This module provides:
- SQLiteAuditRepository for audit log storage
- Database connection management
"""

from gpt_bitcoin.infrastructure.persistence.audit_repository import (
    AUDIT_LOG_SCHEMA,
    SQLiteAuditRepository,
)

__all__ = [
    "SQLiteAuditRepository",
    "AUDIT_LOG_SCHEMA",
]
