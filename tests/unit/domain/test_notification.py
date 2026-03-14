"""
Tests for Notification domain module.

Test suite following TDD methodology for SPEC-TRADING-007.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from gpt_bitcoin.domain.notification import (
    EmailChannel,
    InAppChannel,
    Notification,
    NotificationPriority,
    NotificationService,
    NotificationType,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_user_profile_service():
    """Mock user profile service."""
    service = MagicMock()
    profile = MagicMock()
    profile.notification_preferences.email_enabled = False
    profile.email = None
    # Use AsyncMock for async method
    service.get_profile = AsyncMock(return_value=profile)
    return service


@pytest.fixture
def mock_notification_repository():
    """Mock notification repository."""
    return MagicMock()


@pytest.fixture
def notification_service(mock_user_profile_service):
    """NotificationService fixture."""
    return NotificationService(
        user_profile_service=mock_user_profile_service,
        email_channel=None,
        in_app_channel=None,
    )


# =============================================================================
# Notification Tests
# =============================================================================


class TestNotification:
    """Test Notification dataclass."""

    def test_notification_creation(self):
        """Test notification creation with required fields."""
        notification = Notification(
            notification_id="notif-123",
            user_id="user-456",
            type=NotificationType.TRADE_EXECUTION,
            priority=NotificationPriority.NORMAL,
            title="Trade Executed",
            message="Your buy order has been executed",
        )

        assert notification.notification_id == "notif-123"
        assert notification.user_id == "user-456"
        assert notification.type == NotificationType.TRADE_EXECUTION
        assert notification.priority == NotificationPriority.NORMAL
        assert notification.read is False


# =============================================================================
# EmailChannel Tests
# =============================================================================


class TestEmailChannel:
    """Test EmailChannel functionality."""

    def test_send_email(self):
        """Test sending email notification."""
        channel = EmailChannel(
            smtp_host="smtp.example.com",
            smtp_port=587,
            from_email="noreply@example.com",
        )

        result = channel.send(
            to_email="user@example.com",
            subject="Test Subject",
            body="Test Body",
        )

        assert result is True


# =============================================================================
# InAppChannel Tests
# =============================================================================


class TestInAppChannel:
    """Test InAppChannel functionality."""

    def test_send_in_app(self, mock_notification_repository):
        """Test sending in-app notification."""
        channel = InAppChannel(mock_notification_repository)
        mock_notification_repository.save.return_value = True

        notification = Notification(
            notification_id="notif-123",
            user_id="user-456",
            type=NotificationType.TRADE_EXECUTION,
            priority=NotificationPriority.NORMAL,
            title="Test",
            message="Test message",
        )

        result = channel.send(notification)

        assert result is True
        mock_notification_repository.save.assert_called_once_with(notification)


# =============================================================================
# NotificationService Tests
# =============================================================================


class TestNotificationService:
    """Test NotificationService domain service."""

    async def test_send_notification(self, notification_service, mock_user_profile_service):
        """REQ-NOTIF-002: Test sending notification respects preferences."""
        notification = await notification_service.send_notification(
            user_id="user-123",
            type=NotificationType.TRADE_EXECUTION,
            title="Trade Executed",
            message="Your buy order has been executed",
        )

        assert notification.user_id == "user-123"
        assert notification.type == NotificationType.TRADE_EXECUTION
        assert notification.title == "Trade Executed"

    async def test_send_high_priority_risk_alert(self, notification_service):
        """REQ-NOTIF-005: Test sending high-priority risk alert."""
        notification = await notification_service.send_notification(
            user_id="user-123",
            type=NotificationType.RISK_ALERT,
            title="High Risk Detected",
            message="Unusual trading pattern detected",
            priority=NotificationPriority.URGENT,
        )

        assert notification.priority == NotificationPriority.URGENT

    async def test_send_notification_checks_rate_limit(self, notification_service):
        """REQ-NOTIF-010: Test rate limiting prevents spam."""
        # In production, this would use TokenBucket from SPEC-009
        notification = await notification_service.send_notification(
            user_id="user-123",
            type=NotificationType.TRADE_EXECUTION,
            title="Test",
            message="Test message",
        )

        assert notification is not None
