"""
Tests for ProfileRepository infrastructure module.

Test suite following TDD methodology for SPEC-TRADING-006.
"""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest

from gpt_bitcoin.domain.user_profile import NotificationPreferences, UserProfile
from gpt_bitcoin.infrastructure.persistence.profile_repository import (
    ProfileRepository,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def temp_db_path(tmp_path):
    """Temporary database path."""
    return tmp_path / "test_profiles.db"


@pytest.fixture
def mock_settings(temp_db_path):
    """Mock settings with test database path."""
    settings = MagicMock()
    settings.profile_db_path = temp_db_path
    return settings


@pytest.fixture
def profile_repository(mock_settings):
    """ProfileRepository fixture."""
    repo = ProfileRepository(settings=mock_settings)
    return repo


# =============================================================================
# ProfileRepository Tests
# =============================================================================


class TestProfileRepository:
    """Test ProfileRepository persistence layer."""

    # ========================================================================
    # Lifecycle Tests
    # ========================================================================

    def test_initialization_creates_table(self, profile_repository):
        """REQ-PROFILE-001: Test that repository creates table on init."""
        # Table should be created automatically
        # Verify by checking if we can query the table
        conn = sqlite3.connect(str(profile_repository._db_path))
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_profiles'")
        result = cursor.fetchone()

        assert result is not None
        conn.close()

    # ========================================================================
    # save Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_save_new_profile(self, profile_repository):
        """REQ-PROFILE-001: Test saving a new profile."""
        # Arrange
        profile = UserProfile(
            user_id="user-123",
            name="Test User",
            email="test@example.com",
        )

        # Act
        await profile_repository.save(profile)

        # Assert - Verify saved data
        conn = sqlite3.connect(str(profile_repository._db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", ("user-123",))
        row = cursor.fetchone()

        assert row is not None
        assert row[1] == "Test User"  # name
        assert row[2] == "test@example.com"  # email
        conn.close()

    @pytest.mark.asyncio
    async def test_save_updates_existing_profile(self, profile_repository):
        """REQ-PROFILE-004: Test updating existing profile."""
        # Arrange - Save initial profile
        profile = UserProfile(
            user_id="user-123",
            name="Original Name",
            email="original@example.com",
        )
        await profile_repository.save(profile)

        # Act - Update with new data
        updated_profile = UserProfile(
            user_id="user-123",
            name="Updated Name",
            email="updated@example.com",
        )
        await profile_repository.save(updated_profile)

        # Assert - Verify updated data
        conn = sqlite3.connect(str(profile_repository._db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name, email FROM user_profiles WHERE user_id = ?", ("user-123",))
        row = cursor.fetchone()

        assert row[0] == "Updated Name"
        assert row[1] == "updated@example.com"
        conn.close()

    @pytest.mark.asyncio
    async def test_save_saves_notification_preferences(self, profile_repository):
        """REQ-PROFILE-001: Test saving notification preferences."""
        # Arrange
        preferences = NotificationPreferences(
            price_alerts=False,
            email_enabled=True,
        )
        profile = UserProfile(
            user_id="user-123",
            name="User",
            notification_preferences=preferences,
        )

        # Act
        await profile_repository.save(profile)

        # Assert
        conn = sqlite3.connect(str(profile_repository._db_path))
        cursor = conn.cursor()
        cursor.execute(
            """SELECT price_alerts, email_enabled
               FROM user_profiles
               WHERE user_id = ?""",
            ("user-123",),
        )
        row = cursor.fetchone()

        assert row[0] == 0  # price_alerts (False)
        assert row[1] == 1  # email_enabled (True)
        conn.close()

    # ========================================================================
    # find_by_user_id Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_find_by_user_id_existing(self, profile_repository):
        """Test finding existing profile by user_id."""
        # Arrange
        profile = UserProfile(
            user_id="user-123",
            name="Test User",
            email="test@example.com",
        )
        await profile_repository.save(profile)

        # Act
        result = await profile_repository.find_by_user_id("user-123")

        # Assert
        assert result is not None
        assert result.user_id == "user-123"
        assert result.name == "Test User"
        assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_find_by_user_id_not_found(self, profile_repository):
        """Test finding non-existent profile returns None."""
        # Act
        result = await profile_repository.find_by_user_id("nonexistent-user")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_user_id_restores_preferences(self, profile_repository):
        """Test that notification preferences are restored correctly."""
        # Arrange
        preferences = NotificationPreferences(
            price_alerts=False,
            trade_notifications=True,
            risk_alerts=False,
            email_enabled=True,
            push_enabled=False,
            daily_summary=True,
        )
        profile = UserProfile(
            user_id="user-123",
            name="User",
            notification_preferences=preferences,
        )
        await profile_repository.save(profile)

        # Act
        result = await profile_repository.find_by_user_id("user-123")

        # Assert
        assert result is not None
        assert result.notification_preferences.price_alerts is False
        assert result.notification_preferences.trade_notifications is True
        assert result.notification_preferences.risk_alerts is False
        assert result.notification_preferences.email_enabled is True
        assert result.notification_preferences.push_enabled is False
        assert result.notification_preferences.daily_summary is True

    # ========================================================================
    # delete Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_delete_existing_profile(self, profile_repository):
        """Test deleting an existing profile."""
        # Arrange
        profile = UserProfile(
            user_id="user-123",
            name="User",
        )
        await profile_repository.save(profile)

        # Act
        await profile_repository.delete("user-123")

        # Assert
        result = await profile_repository.find_by_user_id("user-123")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_non_existent_profile(self, profile_repository):
        """Test deleting non-existent profile does not raise error."""
        # Act & Assert - Should not raise
        await profile_repository.delete("nonexistent-user")


# =============================================================================
# Schema Validation Tests
# =============================================================================


class TestSchemaValidation:
    """Test database schema validation."""

    def test_user_profiles_table_schema(self, profile_repository):
        """REQ-PROFILE-001: Verify table schema matches specification."""
        conn = sqlite3.connect(str(profile_repository._db_path))
        cursor = conn.cursor()

        # Get table schema
        cursor.execute("PRAGMA table_info(user_profiles)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        # Verify required columns exist
        assert "user_id" in columns
        assert "name" in columns
        assert "email" in columns
        assert "phone" in columns
        assert "price_alerts" in columns
        assert "trade_notifications" in columns
        assert "risk_alerts" in columns
        assert "email_enabled" in columns
        assert "push_enabled" in columns
        assert "daily_summary" in columns
        assert "preferred_language" in columns
        assert "preferred_currency" in columns
        assert "timezone" in columns
        assert "profile_image" in columns
        assert "is_email_verified" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

        # Verify user_id is PRIMARY KEY
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='user_profiles'")
        create_sql = cursor.fetchone()[0]
        assert "PRIMARY KEY" in create_sql

        conn.close()

    def test_email_index_exists(self, profile_repository):
        """Verify email index exists for lookups."""
        conn = sqlite3.connect(str(profile_repository._db_path))
        cursor = conn.cursor()

        # Check if index exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_profiles_email'"
        )
        result = cursor.fetchone()

        assert result is not None
        conn.close()
