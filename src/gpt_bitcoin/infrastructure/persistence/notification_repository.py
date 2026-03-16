"""
Notification repository for notification persistence.

This module provides:
- NotificationRepository: SQLite-based notification persistence

@MX:NOTE: Notification repository - manages notification data persistence
"""

from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gpt_bitcoin.config.settings import Settings
    from gpt_bitcoin.domain.notification import Notification


# =============================================================================
# NotificationRepository
# =============================================================================


class NotificationRepository:
    """
    SQLite repository for notification persistence.

    Handles storage and retrieval of notifications with read status tracking.

    @MX:NOTE: Thread-safe - uses connection-per-call pattern.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize notification repository.

        Args:
            settings: Application settings containing database path
        """
        self._settings = settings
        self._db_path = self._get_db_path()

        # Initialize database schema
        self._initialize_schema()

    def _get_db_path(self) -> Path:
        """Get database path from settings."""
        # Try to get from settings, fallback to default
        if hasattr(self._settings, "notification_db_path"):
            return Path(self._settings.notification_db_path)

        # Default to data directory
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        return data_dir / "notifications.db"

    def _initialize_schema(self) -> None:
        """Create database schema if not exists."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()

        # Create notifications table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                priority TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                data TEXT,
                created_at TEXT NOT NULL,
                read INTEGER NOT NULL DEFAULT 0,
                read_at TEXT
            )
        """
        )

        # Create indexes
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_notifications_user_id
            ON notifications(user_id, created_at DESC)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_notifications_read
            ON notifications(user_id, read)
        """
        )

        conn.commit()
        conn.close()

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def save(self, notification: Notification) -> bool:
        """
        Save or update notification.

        REQ-NOTIF-001: Log all notifications to SQLite.

        Args:
            notification: Notification to save

        Returns:
            bool: True if saved successfully
        """
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()

        try:
            # Convert data to JSON string
            import json

            data_json = json.dumps(notification.data) if notification.data else None

            cursor.execute(
                """
                INSERT OR REPLACE INTO notifications
                (notification_id, user_id, type, priority, title, message, data,
                 created_at, read, read_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    notification.notification_id,
                    notification.user_id,
                    notification.type.value,
                    notification.priority.value,
                    notification.title,
                    notification.message,
                    data_json,
                    notification.created_at.isoformat(),
                    1 if notification.read else 0,
                    notification.read_at.isoformat() if notification.read_at else None,
                ),
            )

            conn.commit()
            return True

        except Exception:
            return False
        finally:
            conn.close()

    def find_by_user_id(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 100,
    ) -> list[Notification]:
        """
        Find notifications by user ID.

        Args:
            user_id: User identifier
            unread_only: Only return unread notifications
            limit: Maximum number of notifications to return

        Returns:
            List of notifications
        """
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()

        query = "SELECT * FROM notifications WHERE user_id = ?"
        params = [user_id]

        if unread_only:
            query += " AND read = 0"

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_notification(row) for row in rows]

    def mark_as_read(self, notification_id: str) -> bool:
        """
        Mark notification as read.

        Args:
            notification_id: Notification identifier

        Returns:
            bool: True if marked successfully
        """
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE notifications
                SET read = 1, read_at = ?
                WHERE notification_id = ?
            """,
                (datetime.datetime.now().isoformat(), notification_id),
            )

            conn.commit()
            return True

        except Exception:
            return False
        finally:
            conn.close()

    def _row_to_notification(self, row) -> Notification:
        """Convert database row to Notification object."""
        import json

        from gpt_bitcoin.domain.notification import (
            Notification,
            NotificationPriority,
            NotificationType,
        )

        return Notification(
            notification_id=row[0],
            user_id=row[1],
            type=NotificationType(row[2]),
            priority=NotificationPriority(row[3]),
            title=row[4],
            message=row[5],
            data=json.loads(row[6]) if row[6] else None,
            created_at=datetime.datetime.fromisoformat(row[7]),
            read=bool(row[8]),
            read_at=datetime.datetime.fromisoformat(row[9]) if row[9] else None,
        )


__all__ = ["NotificationRepository"]
