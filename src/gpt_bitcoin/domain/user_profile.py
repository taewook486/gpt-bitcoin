"""
User Profile domain module for profile management.

This module provides:
- UserProfile: Domain model for user profile information
- NotificationPreferences: User notification settings
- UserProfileService: Domain service for profile management

@MX:NOTE: User profile module - Manages user information and preferences
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    # BoundLogger is from structlog.stdlib
    from structlog.stdlib import BoundLogger

    from gpt_bitcoin.domain.security import SecurityService
    from gpt_bitcoin.infrastructure.persistence.profile_repository import (
        ProfileRepository,
    )


# =============================================================================
# Domain Models
# =============================================================================


@dataclass
class NotificationPreferences:
    """
    User notification settings.

    Attributes:
        price_alerts: Price change notifications enabled
        trade_notifications: Trade execution notifications enabled
        risk_alerts: Risk warning notifications enabled
        email_enabled: Email delivery enabled
        push_enabled: Browser push notifications enabled
        daily_summary: Daily portfolio summary enabled

    @MX:NOTE: email_enabled defaults to False until email is verified
    """

    price_alerts: bool = True
    trade_notifications: bool = True
    risk_alerts: bool = True
    email_enabled: bool = False
    push_enabled: bool = False
    daily_summary: bool = False


@dataclass
class UserProfile:
    """
    User profile information.

    Attributes:
        user_id: Unique identifier (from SecurityService)
        name: Display name (1-100 characters)
        email: Email address (validated format)
        phone: Phone number (optional, E.164 format)
        notification_preferences: User notification settings
        preferred_language: UI language (ko, en, ja)
        preferred_currency: Currency display (KRW, USD)
        timezone: IANA timezone (e.g., "Asia/Seoul")
        profile_image: Base64 encoded or file path
        created_at: Profile creation timestamp
        updated_at: Last update timestamp
        is_email_verified: Email verification status

    @MX:NOTE: Most fields are optional to support gradual profile completion
    """

    user_id: str
    name: str = ""
    email: str | None = None
    phone: str | None = None
    notification_preferences: NotificationPreferences = field(
        default_factory=NotificationPreferences
    )
    preferred_language: Literal["ko", "en", "ja"] = "ko"
    preferred_currency: Literal["KRW", "USD"] = "KRW"
    timezone: str = "Asia/Seoul"
    profile_image: str | None = None
    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now())
    updated_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now())
    is_email_verified: bool = False


# =============================================================================
# Exceptions
# =============================================================================


class ValidationError(Exception):
    """Raised when profile data validation fails."""

    pass


# =============================================================================
# UserProfileService
# =============================================================================


class UserProfileService:
    """
    Domain service for user profile management.

    Responsibilities:
    - Create, read, update user profiles
    - Manage notification preferences
    - Validate profile data (email, name length)
    - Integrate with SecurityService for audit logging

    @MX:NOTE: Single user assumption for MVP.
        Multi-user support in future versions.

    @MX:ANCHOR: UserProfileService.get_profile
        fan_in: 3+ (Web UI, NotificationService, AuditLog)
        @MX:REASON: Centralizes all profile reads.
    """

    # Email validation regex (RFC 5322 compliant simplified)
    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    # Name length constraints
    NAME_MIN_LENGTH = 1
    NAME_MAX_LENGTH = 100

    # Email max length (RFC 5321)
    EMAIL_MAX_LENGTH = 254

    def __init__(
        self,
        repository: ProfileRepository,
        security_service: SecurityService,
        logger: BoundLogger | None = None,
    ) -> None:
        """
        Initialize UserProfileService with dependencies.

        Args:
            repository: Profile repository for persistence
            security_service: Security service for audit logging
            logger: Optional logger for logging
        """
        self._repository = repository
        self._security_service = security_service
        self._logger = logger

    # =========================================================================
    # Profile Management
    # =========================================================================

    async def get_profile(self, user_id: str) -> UserProfile:
        """
        Get user profile or create default.

        REQ-PROFILE-006: Returns default profile for new users.

        Args:
            user_id: User identifier

        Returns:
            UserProfile: Existing profile or default profile
        """
        profile = await self._repository.find_by_user_id(user_id)

        if profile is None:
            # Return default profile for new user
            return UserProfile(
                user_id=user_id,
                name="",
                email=None,
                notification_preferences=NotificationPreferences(),
            )

        return profile

    async def create_profile(
        self,
        user_id: str,
        name: str,
        email: str | None = None,
        **kwargs,
    ) -> UserProfile:
        """
        Create a new user profile.

        REQ-PROFILE-003: Initializes with default notification preferences.

        Args:
            user_id: User identifier
            name: Display name
            email: Email address (optional, validated if provided)
            **kwargs: Additional profile fields

        Returns:
            UserProfile: Created profile

        Raises:
            ValueError: If email format is invalid
        """
        # Validate email if provided
        if email is not None:
            if not self.validate_email(email):
                raise ValueError("이메일 형식이 올바르지 않습니다")

        # Create profile with default preferences
        profile = UserProfile(
            user_id=user_id,
            name=name,
            email=email,
            notification_preferences=NotificationPreferences(),
            **kwargs,
        )

        # Save to repository
        await self._repository.save(profile)

        return profile

    async def update_profile(
        self,
        user_id: str,
        updates: dict,
    ) -> UserProfile:
        """
        Update user profile with validation.

        REQ-PROFILE-004: Refreshes updated_at timestamp.
        REQ-PROFILE-004: Logs update action via AuditLog.

        Args:
            user_id: User identifier
            updates: Dictionary of fields to update

        Returns:
            UserProfile: Updated profile

        Raises:
            ValueError: If validation fails
        """
        # Get existing profile
        profile = await self._repository.find_by_user_id(user_id)
        if profile is None:
            raise ValueError(f"프로필을 찾을 수 없습니다: {user_id}")

        # Validate email if being updated
        if "email" in updates and updates["email"] is not None:
            if not self.validate_email(updates["email"]):
                raise ValueError("이메일 형식이 올바르지 않습니다")

        # Validate name if being updated
        if "name" in updates:
            name = updates["name"]
            if not (self.NAME_MIN_LENGTH <= len(name) <= self.NAME_MAX_LENGTH):
                raise ValueError(
                    f"이름은 {self.NAME_MIN_LENGTH}-{self.NAME_MAX_LENGTH}자여야 합니다"
                )

        # Apply updates
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        # Update timestamp
        profile.updated_at = datetime.datetime.now()

        # Save updated profile
        await self._repository.save(profile)

        # Log audit (via SecurityService)
        if self._security_service:
            await self._security_service.log_audit(
                ticker="N/A",
                side="profile_update",
                amount=0,
                user_action="profile_updated",
                two_fa_verified=False,
                limit_check_passed=True,
                high_value_trade=False,
                error_message=None,
                session_id=user_id,
            )

        # Return the updated profile (already has fresh state from memory)
        return profile

    async def update_notification_preferences(
        self,
        user_id: str,
        preferences: NotificationPreferences,
    ) -> None:
        """
        Update notification settings.

        REQ-PROFILE-005: Forces email_enabled=False if email not set.

        Args:
            user_id: User identifier
            preferences: New notification preferences

        Raises:
            ValueError: If email_enabled=True but email not set
        """
        # Get existing profile
        profile = await self._repository.find_by_user_id(user_id)
        if profile is None:
            raise ValueError(f"프로필을 찾을 수 없습니다: {user_id}")

        # REQ-PROFILE-005: Check email requirement
        if preferences.email_enabled and not profile.email:
            raise ValueError(
                "이메일이 설정되지 않았습니다. "
                "이메일 알림을 활성화하려면 먼저 이메일을 등록해주세요."
            )

        # Update preferences
        profile.notification_preferences = preferences
        profile.updated_at = datetime.datetime.now()

        # Save
        await self._repository.save(profile)

    # =========================================================================
    # Validation Methods
    # =========================================================================

    def validate_email(self, email: str) -> bool:
        """
        Validate email format (RFC 5322 compliant).

        REQ-PROFILE-002: Validates email format

        Args:
            email: Email address to validate

        Returns:
            bool: True if valid format
        """
        # Check length
        if len(email) > self.EMAIL_MAX_LENGTH:
            return False

        # Check format
        return bool(self.EMAIL_REGEX.match(email))


__all__ = [
    "NotificationPreferences",
    "UserProfile",
    "UserProfileService",
    "ValidationError",
]
