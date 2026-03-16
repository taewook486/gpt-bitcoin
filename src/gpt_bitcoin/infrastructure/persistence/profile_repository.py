"""
Profile repository for user profile persistence.

This module provides:
- ProfileRepository: SQLite-based profile persistence
- Schema management for user_profiles table

@MX:NOTE: Profile repository - Manages user profile data persistence
"""

from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gpt_bitcoin.config.settings import Settings
    from gpt_bitcoin.domain.user_profile import UserProfile


# =============================================================================
# ProfileRepository
# =============================================================================


class ProfileRepository:
    """
    SQLite repository for user profile persistence.

    Handles storage and retrieval of user profiles with notification preferences.

    @MX:NOTE: Thread-safe - uses connection-per-call pattern.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize profile repository.

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
        if hasattr(self._settings, "profile_db_path"):
            return Path(self._settings.profile_db_path)

        # Default to data directory
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        return data_dir / "profiles.db"

    def _initialize_schema(self) -> None:
        """Create database schema if not exists."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()

        # Create user_profiles table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                email TEXT,
                phone TEXT,
                price_alerts INTEGER NOT NULL DEFAULT 1,
                trade_notifications INTEGER NOT NULL DEFAULT 1,
                risk_alerts INTEGER NOT NULL DEFAULT 1,
                email_enabled INTEGER NOT NULL DEFAULT 0,
                push_enabled INTEGER NOT NULL DEFAULT 0,
                daily_summary INTEGER NOT NULL DEFAULT 0,
                preferred_language TEXT NOT NULL DEFAULT 'ko',
                preferred_currency TEXT NOT NULL DEFAULT 'KRW',
                timezone TEXT NOT NULL DEFAULT 'Asia/Seoul',
                profile_image TEXT,
                is_email_verified INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create email index
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_profiles_email
            ON user_profiles(email)
        """
        )

        conn.commit()
        conn.close()

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    async def save(self, profile: UserProfile) -> None:
        """
        Save or update user profile.

        REQ-PROFILE-001: Persists profile data to SQLite.

        Args:
            profile: UserProfile to save
        """
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()

        # Convert notification preferences to integer (0/1)
        prefs = profile.notification_preferences

        cursor.execute(
            """
            INSERT OR REPLACE INTO user_profiles
            (user_id, name, email, phone,
             price_alerts, trade_notifications, risk_alerts,
             email_enabled, push_enabled, daily_summary,
             preferred_language, preferred_currency, timezone,
             profile_image, is_email_verified, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                profile.user_id,
                profile.name,
                profile.email,
                profile.phone,
                1 if prefs.price_alerts else 0,
                1 if prefs.trade_notifications else 0,
                1 if prefs.risk_alerts else 0,
                1 if prefs.email_enabled else 0,
                1 if prefs.push_enabled else 0,
                1 if prefs.daily_summary else 0,
                profile.preferred_language,
                profile.preferred_currency,
                profile.timezone,
                profile.profile_image,
                1 if profile.is_email_verified else 0,
                profile.created_at.isoformat(),
                profile.updated_at.isoformat(),
            ),
        )

        conn.commit()
        conn.close()

    async def find_by_user_id(self, user_id: str) -> UserProfile | None:
        """
        Find profile by user ID.

        Args:
            user_id: User identifier

        Returns:
            UserProfile if found, None otherwise
        """
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM user_profiles WHERE user_id = ?
        """,
            (user_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        # Parse row into UserProfile
        from gpt_bitcoin.domain.user_profile import (
            NotificationPreferences,
            UserProfile,
        )

        # Row indices:
        # 0: user_id, 1: name, 2: email, 3: phone,
        # 4-9: notification preferences
        # 10-13: language, currency, timezone, image
        # 14: verified, 15: created, 16: updated
        return UserProfile(
            user_id=row[0],
            name=row[1],
            email=row[2],
            phone=row[3],
            notification_preferences=NotificationPreferences(
                price_alerts=bool(row[4]),
                trade_notifications=bool(row[5]),
                risk_alerts=bool(row[6]),
                email_enabled=bool(row[7]),
                push_enabled=bool(row[8]),
                daily_summary=bool(row[9]),
            ),
            preferred_language=row[10],
            preferred_currency=row[11],
            timezone=row[12],
            profile_image=row[13],
            is_email_verified=bool(row[14]),
            created_at=datetime.datetime.fromisoformat(row[15]),
            updated_at=datetime.datetime.fromisoformat(row[16]),
        )

    async def delete(self, user_id: str) -> None:
        """
        Delete profile by user ID.

        Args:
            user_id: User identifier to delete
        """
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM user_profiles WHERE user_id = ?
        """,
            (user_id,),
        )

        conn.commit()
        conn.close()


__all__ = ["ProfileRepository"]
