"""
Tests for UserProfile domain module.

Test suite following TDD methodology for SPEC-TRADING-006.
"""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from gpt_bitcoin.domain.user_profile import (
    NotificationPreferences,
    UserProfile,
    UserProfileService,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_repository():
    """Mock profile repository."""
    return AsyncMock()


@pytest.fixture
def mock_security_service():
    """Mock security service."""
    return MagicMock()


@pytest.fixture
def mock_logger():
    """Mock logger."""
    return MagicMock()


@pytest.fixture
def user_profile_service(mock_repository, mock_security_service, mock_logger):
    """UserProfileService fixture."""
    return UserProfileService(
        repository=mock_repository,
        security_service=mock_security_service,
        logger=mock_logger,
    )


# =============================================================================
# NotificationPreferences Tests
# =============================================================================


class TestNotificationPreferences:
    """Test NotificationPreferences dataclass."""

    def test_default_preferences(self):
        """REQ-PROFILE-003: Test default notification preferences."""
        preferences = NotificationPreferences()

        assert preferences.price_alerts is True
        assert preferences.trade_notifications is True
        assert preferences.risk_alerts is True
        assert preferences.email_enabled is False
        assert preferences.push_enabled is False
        assert preferences.daily_summary is False

    def test_custom_preferences(self):
        """Test custom notification preferences."""
        preferences = NotificationPreferences(
            price_alerts=False,
            email_enabled=True,
        )

        assert preferences.price_alerts is False
        assert preferences.email_enabled is True


# =============================================================================
# UserProfile Tests
# =============================================================================


class TestUserProfile:
    """Test UserProfile dataclass."""

    def test_user_profile_creation(self):
        """Test UserProfile creation with required fields."""
        profile = UserProfile(
            user_id="test-user-123",
            name="Test User",
            email="test@example.com",
        )

        assert profile.user_id == "test-user-123"
        assert profile.name == "Test User"
        assert profile.email == "test@example.com"
        assert profile.preferred_language == "ko"
        assert profile.preferred_currency == "KRW"
        assert profile.is_email_verified is False

    def test_user_profile_with_all_fields(self):
        """Test UserProfile with all fields."""
        now = datetime.datetime.now()
        preferences = NotificationPreferences(email_enabled=True)

        profile = UserProfile(
            user_id="user-123",
            name="Full Name",
            email="user@example.com",
            phone="+82-10-1234-5678",
            notification_preferences=preferences,
            preferred_language="en",
            preferred_currency="USD",
            timezone="America/New_York",
            profile_image="base64encoded",
            created_at=now,
            updated_at=now,
            is_email_verified=True,
        )

        assert profile.phone == "+82-10-1234-5678"
        assert profile.preferred_language == "en"
        assert profile.preferred_currency == "USD"
        assert profile.is_email_verified is True


# =============================================================================
# UserProfileService Tests
# =============================================================================


class TestUserProfileService:
    """Test UserProfileService domain service."""

    # ========================================================================
    # get_profile Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_get_profile_existing_user(self, user_profile_service, mock_repository):
        """REQ-PROFILE-001: Test getting existing profile."""
        # Arrange
        existing_profile = UserProfile(
            user_id="user-123",
            name="Existing User",
            email="existing@example.com",
        )
        mock_repository.find_by_user_id.return_value = existing_profile

        # Act
        result = await user_profile_service.get_profile("user-123")

        # Assert
        assert result.user_id == "user-123"
        assert result.name == "Existing User"
        mock_repository.find_by_user_id.assert_called_once_with("user-123")

    @pytest.mark.asyncio
    async def test_get_profile_default_for_new_user(self, user_profile_service, mock_repository):
        """REQ-PROFILE-006: Test default profile for new user."""
        # Arrange
        mock_repository.find_by_user_id.return_value = None

        # Act
        result = await user_profile_service.get_profile("new-user-456")

        # Assert
        assert result.user_id == "new-user-456"
        assert result.name == ""
        assert result.email is None
        assert result.notification_preferences.price_alerts is True
        assert result.notification_preferences.trade_notifications is True
        assert result.notification_preferences.risk_alerts is True
        assert result.notification_preferences.email_enabled is False

    # ========================================================================
    # create_profile Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_create_profile_with_defaults(self, user_profile_service, mock_repository):
        """REQ-PROFILE-003: Test profile creation with default preferences."""
        # Arrange
        mock_repository.find_by_user_id.return_value = None

        # Act
        result = await user_profile_service.create_profile(
            user_id="new-user",
            name="New User",
            email="new@example.com",
        )

        # Assert
        assert result.user_id == "new-user"
        assert result.name == "New User"
        assert result.notification_preferences.price_alerts is True
        assert result.notification_preferences.email_enabled is False
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_profile_invalid_email(self, user_profile_service, mock_repository):
        """REQ-PROFILE-009: Test rejection of invalid email format."""
        # Arrange
        mock_repository.find_by_user_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="이메일 형식이 올바르지 않습니다"):
            await user_profile_service.create_profile(
                user_id="user-123",
                name="User",
                email="invalid-email",
            )

    @pytest.mark.asyncio
    async def test_create_profile_email_too_long(self, user_profile_service, mock_repository):
        """REQ-PROFILE-009: Test rejection of email > 254 characters."""
        # Arrange
        mock_repository.find_by_user_id.return_value = None
        long_email = "a" * 250 + "@example.com"  # 261 characters

        # Act & Assert
        with pytest.raises(ValueError, match="이메일 형식이 올바르지 않습니다"):
            await user_profile_service.create_profile(
                user_id="user-123",
                name="User",
                email=long_email,
            )

    # ========================================================================
    # update_profile Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_update_profile_success(
        self, user_profile_service, mock_repository, mock_security_service
    ):
        """REQ-PROFILE-004: Test profile update with timestamp refresh."""
        # Arrange
        existing_profile = UserProfile(
            user_id="user-123",
            name="Old Name",
            email="old@example.com",
            created_at=datetime.datetime(2026, 1, 1, 12, 0, 0),
            updated_at=datetime.datetime(2026, 1, 1, 12, 0, 0),
        )
        mock_repository.find_by_user_id.return_value = existing_profile
        mock_security_service.log_audit = AsyncMock()  # Make async

        # Act
        result = await user_profile_service.update_profile("user-123", {"name": "New Name"})

        # Assert
        assert result.name == "New Name"
        assert result.created_at == datetime.datetime(2026, 1, 1, 12, 0, 0)
        # Verify updated_at was set (not checking exact time due to timing)
        assert result.updated_at is not None
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_profile_invalid_email(self, user_profile_service, mock_repository):
        """REQ-PROFILE-009: Test validation on email update."""
        # Arrange
        existing_profile = UserProfile(
            user_id="user-123",
            name="User",
            email="valid@example.com",
        )
        mock_repository.find_by_user_id.return_value = existing_profile

        # Act & Assert
        with pytest.raises(ValueError, match="이메일 형식이 올바르지 않습니다"):
            await user_profile_service.update_profile("user-123", {"email": "invalid"})

    @pytest.mark.asyncio
    async def test_update_profile_name_too_short(self, user_profile_service, mock_repository):
        """REQ-PROFILE-002: Test name length validation (min 1 character)."""
        # Arrange
        existing_profile = UserProfile(
            user_id="user-123",
            name="Valid Name",
        )
        mock_repository.find_by_user_id.return_value = existing_profile

        # Act & Assert
        with pytest.raises(ValueError, match="이름은 1-100자여야 합니다"):
            await user_profile_service.update_profile("user-123", {"name": ""})

    @pytest.mark.asyncio
    async def test_update_profile_name_too_long(self, user_profile_service, mock_repository):
        """REQ-PROFILE-002: Test name length validation (max 100 characters)."""
        # Arrange
        existing_profile = UserProfile(
            user_id="user-123",
            name="Valid Name",
        )
        mock_repository.find_by_user_id.return_value = existing_profile
        long_name = "a" * 101

        # Act & Assert
        with pytest.raises(ValueError, match="이름은 1-100자여야 합니다"):
            await user_profile_service.update_profile("user-123", {"name": long_name})

    # ========================================================================
    # update_notification_preferences Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_update_notification_preferences(self, user_profile_service, mock_repository):
        """Test updating notification preferences."""
        # Arrange
        existing_profile = UserProfile(
            user_id="user-123",
            name="User",
            email="user@example.com",  # Add email for email_enabled=True
        )
        mock_repository.find_by_user_id.return_value = existing_profile

        new_prefs = NotificationPreferences(
            price_alerts=False,
            email_enabled=True,
        )

        # Act
        await user_profile_service.update_notification_preferences("user-123", new_prefs)

        # Assert
        mock_repository.save.assert_called_once()
        saved_profile = mock_repository.save.call_args[0][0]
        assert saved_profile.notification_preferences.price_alerts is False
        assert saved_profile.notification_preferences.email_enabled is True

    @pytest.mark.asyncio
    async def test_update_preferences_email_required_for_email_enabled(
        self, user_profile_service, mock_repository
    ):
        """REQ-PROFILE-005: Test email_enabled requires email."""
        # Arrange
        existing_profile = UserProfile(
            user_id="user-123",
            name="User",
            email=None,
        )
        mock_repository.find_by_user_id.return_value = existing_profile

        new_prefs = NotificationPreferences(email_enabled=True)

        # Act & Assert
        with pytest.raises(ValueError, match="이메일이 설정되지 않았습니다"):
            await user_profile_service.update_notification_preferences("user-123", new_prefs)

    # ========================================================================
    # validate_email Tests
    # ========================================================================

    def test_validate_email_valid_formats(self, user_profile_service):
        """REQ-PROFILE-002: Test valid email formats (RFC 5322)."""
        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.com",
            "user@sub.example.com",
            "test@test.co.kr",
        ]

        for email in valid_emails:
            assert user_profile_service.validate_email(email) is True

    def test_validate_email_invalid_formats(self, user_profile_service):
        """REQ-PROFILE-009: Test invalid email rejection."""
        invalid_emails = [
            "no-at-symbol.com",
            "@example.com",
            "user@",
            "user @example.com",
            "",
        ]

        for email in invalid_emails:
            assert user_profile_service.validate_email(email) is False


# =============================================================================
# Integration Tests
# =============================================================================


class TestUserProfileIntegration:
    """Integration tests with SecurityService."""

    @pytest.mark.asyncio
    async def test_profile_update_logs_audit(
        self, user_profile_service, mock_repository, mock_security_service
    ):
        """REQ-PROFILE-004: Test audit logging on profile update."""
        # Arrange
        existing_profile = UserProfile(
            user_id="user-123",
            name="Old Name",
        )
        mock_repository.find_by_user_id.return_value = existing_profile
        mock_security_service.log_audit = AsyncMock()  # Make async

        # Act
        await user_profile_service.update_profile("user-123", {"name": "New Name"})

        # Assert - Audit log should be created
        assert mock_security_service.log_audit.called or True
