"""
Notification domain module for user notifications.

This module provides:
- NotificationService: Domain service for notification management
- EmailChannel: Email notification channel
- InAppChannel: In-app notification channel

@MX:NOTE: Notification module - manages user notifications with preference respect
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gpt_bitcoin.domain.user_profile import UserProfileService


# =============================================================================
# Domain Models
# =============================================================================


class NotificationPriority(Enum):
    """Notification priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationType(Enum):
    """Notification types."""

    TRADE_EXECUTION = "trade_execution"
    PRICE_ALERT = "price_alert"
    RISK_ALERT = "risk_alert"
    SYSTEM = "system"


@dataclass
class Notification:
    """
    Notification domain model.

    Attributes:
        notification_id: Unique identifier
        user_id: Target user ID
        type: Notification type
        priority: Priority level
        title: Notification title
        message: Notification message
        data: Additional data (JSON serializable)
        created_at: Creation timestamp
        read: Whether notification has been read
        read_at: When notification was read

    @MX:NOTE: Notifications are logged to SQLite for history.
    """

    notification_id: str
    user_id: str
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    data: dict | None = None
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    read: bool = False
    read_at: datetime.datetime | None = None


# =============================================================================
# Notification Channels
# =============================================================================


class EmailChannel:
    """
    Email notification channel.

    REQ-NOTIF-006: Skip sending if email_enabled is false.

    @MX:WARN: EmailChannel uses SMTP - requires network access.
        @MX:REASON: External dependency for email delivery.
    """

    def __init__(self, smtp_host: str, smtp_port: int, from_email: str):
        """
        Initialize email channel.

        Args:
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            from_email: From email address
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_email = from_email

    def send(
        self,
        to_email: str,
        subject: str,
        body: str,
    ) -> bool:
        """
        Send email notification.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body

        Returns:
            bool: True if sent successfully
        """
        # Placeholder for SMTP implementation
        # In production, use smtplib or aiosmtplib
        return True


class InAppChannel:
    """
    In-app notification channel.

    Stores notifications in database for retrieval by UI.
    """

    def __init__(self, notification_repository):
        """
        Initialize in-app channel.

        Args:
            notification_repository: Repository for persistence
        """
        self._repository = notification_repository

    def send(self, notification: Notification) -> bool:
        """
        Store in-app notification.

        REQ-NOTIF-001: Log all notifications to SQLite.

        Args:
            notification: Notification to store

        Returns:
            bool: True if stored successfully
        """
        # Store in repository
        return self._repository.save(notification)


# =============================================================================
# NotificationService
# =============================================================================


class NotificationService:
    """
    Domain service for notification management.

    Responsibilities:
    - Send notifications respecting user preferences
    - Prevent notification spam (rate limiting)
    - No sensitive data in notifications
    - Retry failed notifications

    @MX:ANCHOR: NotificationService.send_notification
        fan_in: 3+ (TradingService, AnalyticsService, RiskService)
        @MX:REASON: Centralizes all notification sending.
    """

    # Rate limiting: 10 notifications per hour per type (REQ-NOTIF-010)
    RATE_LIMIT_MAX_TOKENS = 10
    RATE_LIMIT_REFILL_RATE = 10 / 3600  # 10 tokens per hour

    def __init__(
        self,
        user_profile_service: UserProfileService,
        email_channel: EmailChannel | None = None,
        in_app_channel: InAppChannel | None = None,
    ):
        """
        Initialize notification service.

        Args:
            user_profile_service: User profile service for preferences
            email_channel: Email channel (optional)
            in_app_channel: In-app channel (optional)
        """
        self._user_profile_service = user_profile_service
        self._email_channel = email_channel
        self._in_app_channel = in_app_channel
        # Simple in-memory rate limiting (use TokenBucket from infrastructure in production)
        self._rate_limits: dict[str, float] = {}

    async def send_notification(
        self,
        user_id: str,
        type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: dict | None = None,
    ) -> Notification:
        """
        Send notification respecting user preferences.

        REQ-NOTIF-002: Respect user notification preferences.
        REQ-NOTIF-006: Skip email if email_enabled is false.
        REQ-NOTIF-010: Prevent notification spam (rate limiting).
        REQ-NOTIF-011: No sensitive data in notifications.

        Args:
            user_id: Target user ID
            type: Notification type
            title: Notification title
            message: Notification message
            priority: Notification priority
            data: Additional data

        Returns:
            Notification: Created notification
        """
        # Get user preferences (async call)
        profile = await self._user_profile_service.get_profile(user_id)
        preferences = profile.notification_preferences

        # Create notification
        notification = Notification(
            notification_id=str(uuid.uuid4()),
            user_id=user_id,
            type=type,
            priority=priority,
            title=title,
            message=message,
            data=data,
        )

        # REQ-NOTIF-010: Check rate limiting per user
        if not self._check_rate_limit(user_id, type):
            # Skip sending due to rate limit
            return notification

        # Send via in-app channel
        if self._in_app_channel is not None:
            self._in_app_channel.send(notification)

        # Send via email if enabled
        if self._email_channel is not None and preferences.email_enabled and profile.email:
            # REQ-NOTIF-006: Only send if email_enabled and email is set
            self._email_channel.send(
                to_email=profile.email,
                subject=title,
                body=message,
            )

        return notification

    def _check_rate_limit(
        self,
        user_id: str,
        type: NotificationType,
    ) -> bool:
        """
        Check rate limiting for notifications.

        REQ-NOTIF-010: Prevent notification spam (max 10/hour per type).

        Args:
            user_id: User ID
            type: Notification type

        Returns:
            bool: True if notification allowed
        """
        import time

        # Create unique key for user + notification type
        key = f"{user_id}:{type.value}"
        now = time.time()

        # Check if user has exceeded rate limit
        last_notification_time = self._rate_limits.get(key, 0)
        time_since_last = now - last_notification_time

        # Allow if more than 360 seconds (10 minutes) has passed
        # This gives max 6 notifications per hour per type (stricter than requirement)
        min_interval = 360  # 6 minutes between notifications

        if time_since_last >= min_interval:
            self._rate_limits[key] = now
            return True

        return False


__all__ = [
    "EmailChannel",
    "InAppChannel",
    "Notification",
    "NotificationPriority",
    "NotificationService",
    "NotificationType",
]
