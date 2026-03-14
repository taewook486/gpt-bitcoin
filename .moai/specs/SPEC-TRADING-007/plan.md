# Implementation Plan: SPEC-TRADING-007 (Notification System)

## Overview

이 문서는 SPEC-TRADING-007 알림 시스템 기능의 구현 계획을 정의합니다.

---

## Milestones (Priority-Based)

### Phase 1: Foundation (Primary Goal)

**Objective**: 알림 데이터 모델 및 기본 발송 기능 구현

#### Tasks

1. **Data Models**
   - Priority: Critical
   - Create `Notification` dataclass
   - Create `PriceAlertConfig` dataclass
   - Create database schema

2. **NotificationRepository**
   - Priority: Critical
   - Implement CRUD operations
   - Implement retry queue queries
   - Implement notification history queries

3. **NotificationChannel Abstraction**
   - Priority: Critical
   - Create abstract `NotificationChannel` class
   - Define `send()` and `is_available()` interface
   - Enable channel extensibility

4. **InAppChannel**
   - Priority: High
   - Implement in-app notification storage
   - Implement read/unread status
   - Support notification dismissal

5. **NotificationService Core**
   - Priority: High
   - Implement `send_notification()` base method
   - Implement preference checking
   - Implement rate limiting

6. **Unit Tests - Core**
   - Priority: High
   - Test Notification creation
   - Test Repository operations
   - Test preference checking

**Deliverables**:
- Working notification persistence
- In-app channel functional
- All core tests passing

---

### Phase 2: Email Channel (Secondary Goal)

**Objective**: 이메일 알림 채널 구현

#### Tasks

1. **EmailChannel Implementation**
   - Priority: High
   - Configure SMTP client
   - Implement email sending
   - Handle SMTP errors

2. **Email Templates**
   - Priority: Medium
   - Create HTML email templates
   - Create plain text fallback
   - Support bilingual content (Korean/English)

3. **Email Rate Limiting**
   - Priority: Medium
   - Implement per-minute rate limit
   - Implement per-hour rate limit
   - Queue excess emails

4. **Unit Tests - Email**
   - Priority: Medium
   - Test email composition
   - Test rate limiting
   - Test error handling

**Deliverables**:
- Email channel functional
- Rate limiting working
- Tests passing

---

### Phase 3: Alert Types (Final Goal)

**Objective**: 각 알림 유형 구현

#### Tasks

1. **Trade Notification**
   - Priority: High
   - Hook into TradingService events
   - Format trade notification content
   - Support buy/sell templates

2. **Price Alert**
   - Priority: High
   - Implement PriceAlertConfig CRUD
   - Implement price monitoring scheduler
   - Calculate percentage change
   - Trigger alerts on threshold

3. **Risk Alert**
   - Priority: High
   - Define risk conditions (daily loss, margin, etc.)
   - Implement HIGH priority bypass
   - Integrate with SecurityService limits

4. **Rate Limiter**
   - Priority: High
   - Implement token bucket algorithm
   - Per-user, per-type limits
   - Cooldown periods

5. **Retry Queue**
   - Priority: Medium
   - Implement retry logic
   - Exponential backoff
   - Max retry limit

6. **Integration Tests**
   - Priority: Medium
   - Test end-to-end notification flow
   - Test TradingService integration

**Deliverables**:
- All alert types functional
- Rate limiting working
- Retry queue operational

---

## Technical Approach

### Channel Architecture

```python
# domain/notification.py

from abc import ABC, abstractmethod

class NotificationChannel(ABC):
    """Abstract base for notification channels."""

    @property
    @abstractmethod
    def channel_type(self) -> str:
        """Return channel identifier."""
        pass

    @abstractmethod
    async def send(
        self,
        notification: Notification,
        user_profile: UserProfile,
    ) -> bool:
        """Send notification. Returns True if successful."""
        pass

    @abstractmethod
    async def is_available(self, user_profile: UserProfile) -> bool:
        """Check if channel is available for user."""
        pass
```

### Service Layer

```python
# domain/notification.py

class NotificationService:
    """Notification management service."""

    def __init__(
        self,
        repository: NotificationRepository,
        user_profile_service: UserProfileService,
        channels: list[NotificationChannel],
        rate_limiter: RateLimiter,
    ):
        self._repository = repository
        self._user_profile_service = user_profile_service
        self._channels = {c.channel_type: c for c in channels}
        self._rate_limiter = rate_limiter

    async def _send_via_channels(
        self,
        notification: Notification,
        user_profile: UserProfile,
    ) -> bool:
        """
        Send notification via all enabled channels.

        @MX:NOTE: Iterates through channels, respects availability.
        """
        success = False
        for channel in self._channels.values():
            if await channel.is_available(user_profile):
                try:
                    if await channel.send(notification, user_profile):
                        success = True
                except NotificationError as e:
                    logger.error(f"Channel {channel.channel_type} failed: {e}")
        return success

    async def send_trade_notification(
        self,
        user_id: str,
        trade_result: TradeResult,
    ) -> Notification:
        """
        Send trade execution notification.

        @MX:ANCHOR: Primary entry for trade notifications.
        """
        # Check preferences
        profile = await self._user_profile_service.get_profile(user_id)
        if not profile.notification_preferences.trade_notifications:
            return None  # Skip silently

        # Check rate limit
        if not await self._rate_limiter.allow(user_id, "trade"):
            logger.warning(f"Rate limit exceeded for {user_id} trade notifications")
            return None

        # Create notification
        notification = Notification(
            notification_id=str(uuid4()),
            user_id=user_id,
            type="trade_executed",
            channel="multi",
            priority="normal",
            subject=self._format_trade_subject(trade_result),
            body=self._format_trade_body(trade_result),
            data={"trade_result": asdict(trade_result)},
            sent_at=datetime.now(),
            status="pending",
            retry_count=0,
        )

        # Send via channels
        if await self._send_via_channels(notification, profile):
            notification.status = "sent"
        else:
            notification.status = "failed"

        await self._repository.save(notification)
        return notification
```

### Rate Limiter

```python
# infrastructure/notification/rate_limiter.py

class RateLimiter:
    """
    Token bucket rate limiter for notifications.

    @MX:NOTE: Per-user, per-type rate limiting.
    """

    def __init__(
        self,
        max_per_hour: int = 5,
        max_per_day: int = 50,
    ):
        self._max_per_hour = max_per_hour
        self._max_per_day = max_per_day
        self._buckets: dict[str, TokenBucket] = {}

    async def allow(self, user_id: str, notification_type: str) -> bool:
        """Check if notification is allowed."""
        key = f"{user_id}:{notification_type}"
        if key not in self._buckets:
            self._buckets[key] = TokenBucket(
                capacity=self._max_per_hour,
                refill_rate=self._max_per_hour / 3600,
            )
        return self._buckets[key].consume()
```

---

## Architecture Design

### Package Structure

```
src/gpt_bitcoin/
├── domain/
│   ├── notification.py          # [NEW] NotificationService, channels
│   └── trading.py               # [MODIFY] Add notification hooks
│
├── infrastructure/
│   ├── notification/            # [NEW PACKAGE]
│   │   ├── __init__.py
│   │   ├── rate_limiter.py
│   │   └── email_sender.py
│   └── persistence/
│       └── notification_repository.py  # [NEW]
│
├── dependencies/
│   └── container.py             # [MODIFY] Register services
│
├── config/
│   └── settings.py              # [MODIFY] Add SMTP settings
│
└── web_ui.py                    # [MODIFY] Add Notifications panel
```

### Data Flow

```
+------------------+
| TradingService   |
| (TradeResult)    |
+--------+---------+
         | Event
         v
+------------------+
| Notification     |
| Service          |
+--------+---------+
         |
         +-----> Check Preferences (UserProfileService)
         |
         +-----> Check Rate Limit
         |
         v
+------------------+         +------------------+
| InAppChannel     |         | EmailChannel     |
| (always)         |         | (if enabled)     |
+--------+---------+         +--------+---------+
         |                            |
         v                            v
+------------------+         +------------------+
| Notification DB  |         | SMTP Server      |
+------------------+         +------------------+
```

---

## Configuration Changes

### Settings Additions

```python
# config/settings.py additions

class Settings(BaseSettings):
    # ... existing settings ...

    # Notification Settings
    notification_rate_limit_hour: int = Field(
        default=5,
        description="Max notifications per user per hour",
    )
    notification_rate_limit_day: int = Field(
        default=50,
        description="Max notifications per user per day",
    )
    notification_retry_max: int = Field(
        default=3,
        description="Max retry attempts for failed notifications",
    )

    # Email Settings
    smtp_host: str = Field(
        default="",
        description="SMTP server hostname",
    )
    smtp_port: int = Field(
        default=587,
        description="SMTP server port",
    )
    smtp_user: str = Field(
        default="",
        description="SMTP username",
    )
    smtp_password: str = Field(
        default="",
        description="SMTP password (use env var)",
    )
    email_from_address: str = Field(
        default="noreply@example.com",
        description="Sender email address",
    )
```

### Container Registration

```python
# dependencies/container.py additions

from gpt_bitcoin.domain.notification import NotificationService, InAppChannel, EmailChannel
from gpt_bitcoin.infrastructure.persistence.notification_repository import NotificationRepository
from gpt_bitcoin.infrastructure.notification.rate_limiter import RateLimiter

class Container(containers.DeclarativeContainer):
    # ... existing providers ...

    notification_repository: providers.Provider[NotificationRepository] = providers.Factory(
        NotificationRepository,
        db=database,
    )

    rate_limiter: providers.Provider[RateLimiter] = providers.Singleton(
        RateLimiter,
        max_per_hour=settings.provided.notification_rate_limit_hour,
        max_per_day=settings.provided.notification_rate_limit_day,
    )

    in_app_channel: providers.Provider[InAppChannel] = providers.Factory(
        InAppChannel,
        repository=notification_repository,
    )

    email_channel: providers.Provider[EmailChannel] = providers.Factory(
        EmailChannel,
        smtp_host=settings.provided.smtp_host,
        smtp_port=settings.provided.smtp_port,
        smtp_user=settings.provided.smtp_user,
        smtp_password=settings.provided.smtp_password,
        from_address=settings.provided.email_from_address,
    )

    notification_service: providers.Provider[NotificationService] = providers.Factory(
        NotificationService,
        repository=notification_repository,
        user_profile_service=user_profile_service,
        channels=[in_app_channel, email_channel],
        rate_limiter=rate_limiter,
    )
```

---

## Testing Strategy

### Test Coverage Goals

| Component | Target Coverage | Priority |
|-----------|-----------------|----------|
| NotificationService | 90% | Critical |
| NotificationChannel | 95% | Critical |
| RateLimiter | 100% | High |
| NotificationRepository | 95% | High |
| Email Templates | 80% | Medium |

### Key Test Cases

```python
# tests/unit/domain/test_notification.py

class TestNotificationService:
    """Test NotificationService."""

    @pytest.mark.asyncio
    async def test_trade_notification_respects_preferences(self, service, mock_profile):
        """Test that trade notifications respect user preferences."""
        mock_profile.notification_preferences.trade_notifications = False

        notification = await service.send_trade_notification("user1", mock_trade_result)

        assert notification is None  # Should skip silently

    @pytest.mark.asyncio
    async def test_rate_limiting(self, service, rate_limiter):
        """Test rate limiting."""
        # Send 5 notifications (limit)
        for _ in range(5):
            await service.send_trade_notification("user1", mock_trade_result)

        # 6th should be blocked
        notification = await service.send_trade_notification("user1", mock_trade_result)
        assert notification is None

    @pytest.mark.asyncio
    async def test_risk_alert_bypasses_rate_limit(self, service, rate_limiter):
        """Test that risk alerts bypass rate limiting."""
        # Exhaust rate limit
        for _ in range(5):
            await service.send_trade_notification("user1", mock_trade_result)

        # Risk alert should still go through
        notification = await service.send_risk_alert("user1", "daily_loss", {})
        assert notification is not None
        assert notification.status == "sent"
```

---

## Dependencies

### New Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| aiosmtplib | >=3.0.0 | Async SMTP client |
| jinja2 | >=3.1.0 | Email templates |

### Existing Dependencies Used

| Package | Usage |
|---------|-------|
| pydantic | Notification validation |
| pytest + pytest-asyncio | Testing |
| streamlit | UI |

---

## Security Considerations

### Email Security

1. **SMTP Credentials**: Store in environment variables, never in code
2. **TLS**: Always use TLS for SMTP connections
3. **Content Sanitization**: No sensitive data in email subjects

### Rate Limiting

- Prevents notification abuse
- Protects SMTP reputation
- Ensures user experience

---

Version: 1.0.0
Last Updated: 2026-03-05
Author: MoAI SPEC Builder
