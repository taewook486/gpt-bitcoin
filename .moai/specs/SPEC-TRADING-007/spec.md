# SPEC-TRADING-007: Notification System

## Metadata

- **SPEC ID**: SPEC-TRADING-007
- **Title**: Notification System (알림 시스템)
- **Created**: 2026-03-05
- **Status**: Completed
- **Priority**: Medium
- **Depends On**: SPEC-TRADING-006 (User Profile Management)
- **Lifecycle Level**: spec-first

---

## Problem Analysis

### Current State

SPEC-TRADING-002(TradeHistoryService)와 SPEC-TRADING-004(SecurityService)가 구현되어 거래 내역 저장 및 보안 기능을 제공합니다. 그러나 사용자에게 실시간 알림을 보내는 기능이 없어 다음과 같은 문제가 발생합니다:

1. **가격 변동 감지 불가**: 중요한 가격 변동 시 사용자가 인지하지 못함
2. **거래 실행 알림 부재**: 거래 완료 시 즉시 알림 불가
3. **위험 상황 경고 없음**: 마진콜, 한도 초과 등 위험 상황에 대한 경고 부재
4. **수동 모니터링 필요**: 사용자가 지속적으로 시스템을 확인해야 함

### Root Cause Analysis (Five Whys)

1. **Why?** 알림 발송 메커니즘이 구현되지 않음
2. **Why?** 초기 구현에서 핵심 거래 기능에 집중하여 알림 기능 제외
3. **Why?** 알림 시스템이 별도의 인프라 구성 요소로 분리 필요
4. **Why?** 알림 채널(email, push) 설정 및 사용자 선호 관리 미설계
5. **Root Cause**: 이벤트 기반 알림 시스템이 독립적인 도메인 서비스로 설계 필요

### Desired State

사용자가 가격 알림, 거래 실행 알림, 위험 알림을 설정할 수 있으며, 이메일 및 Web UI 알림을 통해 실시간으로 정보를 받을 수 있습니다.

---

## Environment

### Technology Stack

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Event System | asyncio Events | Built-in | 비동기 이벤트 처리 |
| Email | SMTP (Gmail, etc.) | - | 이메일 알림 발송 |
| Web UI | Streamlit | 1.30+ | 인앱 알림 표시 |
| Scheduler | APScheduler | 3.10+ | 정기 알림 스케줄링 |
| Storage | SQLite | 3.45+ | 알림 기록 저장 |

### Integration Points

```
SPEC-TRADING-001 (TradingService)
        ↓ TradeResult 이벤트
SPEC-TRADING-007 (NotificationService)
        ↓ 알림 발송
    Email SMTP / Web UI Alert
        ↑
SPEC-TRADING-006 (UserProfileService)
        (알림 설정 조회)
```

### Constraints

1. **Rate Limiting**: 이메일 발송 1분당 최대 10건
2. **Queue**: 알림 발송 실패 시 재시도 큐 사용
3. **Preferences**: 사용자 알림 설정 존중 (email_enabled 등)
4. **Privacy**: 알림 내용에 민감 정보 최소화

---

## Requirements (EARS Format)

### Ubiquitous Requirements

**REQ-NOTIF-001**: 시스템은 모든 알림을 기록해야 한다 (The system shall log all notifications).

```
The system shall persist all sent notifications to SQLite database
with complete notification data including:
- notification_id, user_id, type, channel, subject, body, sent_at, status
```

**REQ-NOTIF-002**: 시스템은 사용자 알림 설정을 준수해야 한다 (The system shall respect user notification preferences).

```
The system shall check NotificationPreferences before sending:
- IF email_enabled is false, skip email channel
- IF push_enabled is false, skip push channel
- IF specific alert type disabled, skip that alert type
```

### Event-Driven Requirements

**REQ-NOTIF-003**: WHEN 거래가 실행되면 THEN 시스템은 거래 실행 알림을 발송해야 한다.

```
WHEN TradingService.execute_approved_trade() returns TradeResult with success=true
THEN NotificationService.send_trade_notification() shall be called
    AND notification shall include:
        - ticker, side, executed_price, executed_quantity
        - timestamp
    AND use channels per user preferences
```

**REQ-NOTIF-004**: WHEN 가격이 설정 임계값을 초과하면 THEN 시스템은 가격 알림을 발송해야 한다.

```
WHEN price_change_percentage >= user_configured_threshold
THEN NotificationService.send_price_alert() shall be called
    AND notification shall include:
        - ticker, current_price, change_percentage
        - threshold that was exceeded
    AND respect price_alerts preference
```

**REQ-NOTIF-005**: WHEN 위험 조건이 감지되면 THEN 시스템은 위험 알림을 발송해야 한다.

```
WHEN risk condition detected:
    - Daily loss limit approached (90%)
    - Position size limit exceeded
    - Margin call threshold reached
THEN NotificationService.send_risk_alert() shall be called immediately
    AND notification shall have HIGH priority
    AND bypass quiet hours (if applicable)
```

### State-Driven Requirements

**REQ-NOTIF-006**: IF 사용자의 email_enabled가 false이면 THEN 이메일 채널을 사용하지 않아야 한다.

```
IF user_profile.notification_preferences.email_enabled is false
THEN the system shall NOT send via email channel
    AND log reason as "email_disabled_by_user"
    AND attempt alternative channels (push, in-app)
```

**REQ-NOTIF-007**: IF 알림 발송이 실패하면 THEN 시스템은 재시도 큐에 추가해야 한다.

```
IF notification send fails (network error, SMTP error)
THEN the system shall:
    AND add to retry queue with exponential backoff
    AND max 3 retry attempts
    AND log failure with ERROR level
    AND mark notification status as "failed" after max retries
```

### Optional Requirements

**REQ-NOTIF-008**: Where possible, 시스템은 브라우저 푸시 알림을 지원해야 한다.

```
Where possible, the system shall support browser push notifications:
- Request notification permission on first visit
- Display desktop notifications for critical alerts
- Support notification click actions (navigate to relevant page)
```

**REQ-NOTIF-009**: Where possible, 시스템은 조용한 시간(quiet hours)을 지원해야 한다.

```
Where possible, the system shall support quiet hours:
- User-configured time range (e.g., 23:00-07:00)
- Suppress non-critical notifications during quiet hours
- Risk alerts bypass quiet hours
```

### Unwanted Behavior Requirements

**REQ-NOTIF-010**: 시스템은 알림 스팸을 방지해야 한다 (The system shall not spam notifications).

```
The system shall NOT send:
- More than 1 price alert per ticker per hour (configurable)
- More than 5 notifications per user per hour (non-critical)
- Duplicate notifications within 5 minutes

AND shall implement rate limiting per user, per type
```

**REQ-NOTIF-011**: 시스템은 민감한 정보를 알림에 포함해서는 안 된다 (The system shall not include sensitive data in notifications).

```
The system shall NOT include in notifications:
- Full account balance
- PIN codes or authentication tokens
- Private keys or API secrets

AND shall use generic terms like "거래 완료" without specific amounts in email subjects
```

---

## Specifications

### Data Model

#### Notification Schema

```python
@dataclass
class Notification:
    """Stored notification record."""
    notification_id: str  # UUID
    user_id: str  # Target user
    type: Literal[
        "trade_executed",
        "price_alert",
        "risk_alert",
        "daily_summary",
        "system"
    ]
    channel: Literal["email", "push", "in_app"]
    priority: Literal["low", "normal", "high", "critical"]
    subject: str  # Notification title
    body: str  # Notification content (plain text)
    html_body: str | None  # HTML content for email
    data: dict  # Additional structured data
    sent_at: datetime
    status: Literal["pending", "sent", "failed", "cancelled"]
    retry_count: int
    error_message: str | None

@dataclass
class PriceAlertConfig:
    """User-configured price alert."""
    alert_id: str  # UUID
    user_id: str
    ticker: str
    threshold_type: Literal["percentage_change", "absolute_price"]
    threshold_value: float  # e.g., 5.0 for 5% change
    direction: Literal["above", "below", "both"]
    is_active: bool
    created_at: datetime
    last_triggered_at: datetime | None
```

#### SQLite Schema

```sql
CREATE TABLE IF NOT EXISTS notifications (
    notification_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL,
    channel TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'normal',
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    html_body TEXT,
    data TEXT,  -- JSON
    sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'pending',
    retry_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_type ON notifications(type);

CREATE TABLE IF NOT EXISTS price_alert_configs (
    alert_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    threshold_type TEXT NOT NULL,
    threshold_value REAL NOT NULL,
    direction TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_triggered_at TEXT
);

CREATE INDEX idx_price_alerts_user ON price_alert_configs(user_id);
CREATE INDEX idx_price_alerts_ticker ON price_alert_configs(ticker);
```

### Component Architecture

```
src/gpt_bitcoin/
├── domain/
│   ├── notification.py (NEW)
│   │   ├── Notification (dataclass)
│   │   ├── PriceAlertConfig (dataclass)
│   │   ├── NotificationService
│   │   ├── EmailChannel
│   │   └── InAppChannel
│   └── trading.py (existing - SPEC-001)
├── infrastructure/
│   └── persistence/
│       └── notification_repository.py (NEW)
└── web_ui.py (MODIFY - add Notifications panel)
```

### Class Design

#### NotificationService

```python
class NotificationService:
    """
    Domain service for notification management.

    Responsibilities:
    - Send notifications via multiple channels
    - Manage price alert configurations
    - Handle retry logic and rate limiting
    - Respect user preferences

    @MX:NOTE: Uses channel abstraction for extensibility.
        New channels can be added without modifying core logic.
    """

    def __init__(
        self,
        repository: NotificationRepository,
        user_profile_service: UserProfileService,
        channels: list[NotificationChannel],
        rate_limiter: RateLimiter,
    ):
        """Initialize with dependencies."""
        pass

    async def send_trade_notification(
        self,
        user_id: str,
        trade_result: TradeResult,
    ) -> Notification:
        """
        Send trade execution notification.

        @MX:ANCHOR: Primary entry for trade notifications.
            fan_in: 1 (TradingService)
            @MX:REASON: Centralizes all trade notification logic.
        """
        pass

    async def send_price_alert(
        self,
        user_id: str,
        ticker: str,
        current_price: float,
        change_percentage: float,
        config: PriceAlertConfig,
    ) -> Notification:
        """Send price change alert."""
        pass

    async def send_risk_alert(
        self,
        user_id: str,
        risk_type: str,
        details: dict,
    ) -> Notification:
        """
        Send high-priority risk alert.

        @MX:WARN: Risk alerts bypass rate limiting and quiet hours.
            @MX:REASON: Critical alerts must reach user immediately.
        """
        pass

    async def check_price_alerts(
        self,
        ticker: str,
        current_price: float,
        previous_price: float,
    ) -> list[Notification]:
        """
        Check and trigger price alerts for all configured users.

        Called by price monitoring scheduler.
        """
        pass

    async def process_retry_queue(self) -> int:
        """Process pending retry queue. Returns count of processed."""
        pass
```

#### NotificationChannel (Abstract)

```python
class NotificationChannel(ABC):
    """Abstract base for notification channels."""

    @property
    @abstractmethod
    def channel_type(self) -> str:
        """Return channel identifier (email, push, in_app)."""
        pass

    @abstractmethod
    async def send(
        self,
        notification: Notification,
        user_profile: UserProfile,
    ) -> bool:
        """
        Send notification via this channel.

        Returns:
            bool: True if successful, False otherwise

        Raises:
            NotificationError: If send fails critically
        """
        pass

    @abstractmethod
    async def is_available(self, user_profile: UserProfile) -> bool:
        """Check if channel is available for user."""
        pass
```

#### EmailChannel

```python
class EmailChannel(NotificationChannel):
    """Email notification channel."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_address: str,
    ):
        """Initialize SMTP configuration."""
        pass

    @property
    def channel_type(self) -> str:
        return "email"

    async def send(
        self,
        notification: Notification,
        user_profile: UserProfile,
    ) -> bool:
        """Send email notification."""
        pass

    async def is_available(self, user_profile: UserProfile) -> bool:
        """Check if email is enabled and configured."""
        return (
            user_profile.notification_preferences.email_enabled
            and user_profile.email is not None
        )
```

#### InAppChannel

```python
class InAppChannel(NotificationChannel):
    """In-app notification channel (Web UI)."""

    @property
    def channel_type(self) -> str:
        return "in_app"

    async def send(
        self,
        notification: Notification,
        user_profile: UserProfile,
    ) -> bool:
        """Store notification for in-app display."""
        # Store in database, will be fetched by Web UI polling
        pass

    async def is_available(self, user_profile: UserProfile) -> bool:
        """Always available for logged-in users."""
        return True
```

### UI Design (Web UI)

#### Notifications Panel

```
+-----------------------------------------------------------------+
| [Notifications]                                    [Mark All Read]|
+-----------------------------------------------------------------+
| Price Alerts:                                                    |
| [+ New Alert]                                                    |
| +-------------------------------------------------------------+ |
| | Ticker: [KRW-BTC v]  Threshold: [5] % [v]  Direction: [Both v]|
| | [Active x]                              [Delete] [Edit]       |
| +-------------------------------------------------------------+ |
+-----------------------------------------------------------------+
| Recent Notifications:                                            |
| +-------------------------------------------------------------+ |
| | [!] HIGH: Risk Alert - Daily loss limit at 90%              | |
| |     2026-03-05 14:30                              [Dismiss] | |
| +-------------------------------------------------------------+ |
| | [i] Trade Executed - KRW-BTC BUY 0.001 @ 50,000,000 KRW     | |
| |     2026-03-05 14:15                              [Dismiss] | |
| +-------------------------------------------------------------+ |
+-----------------------------------------------------------------+
```

---

## MX Tag Targets

### High Fan-In Functions (>= 3 callers)

| Function | Expected Fan-In | MX Tag Type | Location |
|----------|-----------------|-------------|----------|
| `NotificationService.send_trade_notification()` | 1 | @MX:ANCHOR | domain/notification.py |
| `NotificationRepository.save()` | 3+ | @MX:NOTE | infrastructure/persistence/notification_repository.py |

### Danger Zones (Complexity >= 15 or Critical Operations)

| Function | Risk | MX Tag Type | Reason |
|----------|------|-------------|--------|
| `send_risk_alert()` | Bypasses rate limit | @MX:WARN | Critical alerts must reach user |
| Rate limiter | Spam prevention | @MX:NOTE | Essential for user experience |
| Retry queue | Data loss risk | @MX:NOTE | Failed notifications must be tracked |

---

## Files to Modify

### New Files

| File Path | Purpose | Lines (Est.) |
|-----------|---------|--------------|
| `src/gpt_bitcoin/domain/notification.py` | NotificationService, channels | ~350 |
| `src/gpt_bitcoin/infrastructure/persistence/notification_repository.py` | Persistence | ~120 |
| `src/gpt_bitcoin/infrastructure/notification/rate_limiter.py` | Rate limiting | ~80 |
| `tests/unit/domain/test_notification.py` | Unit tests | ~450 |
| `tests/unit/infrastructure/test_notification_repository.py` | Repository tests | ~200 |

### Modified Files

| File Path | Changes | Lines Changed (Est.) |
|-----------|---------|---------------------|
| `src/gpt_bitcoin/web_ui.py` | Add Notifications panel | +150 |
| `src/gpt_bitcoin/dependencies/container.py` | Register NotificationService | +15 |
| `src/gpt_bitcoin/config/settings.py` | Add SMTP settings | +20 |

---

## Risks and Mitigations

### Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Email delivery failures | Medium | Medium | Retry queue with exponential backoff |
| Rate limiter too strict | Low | Low | Configurable thresholds |
| Spam filter blocking | Medium | Medium | Use reputable SMTP, proper headers |
| Alert spam during high volatility | Medium | Medium | Aggregation, cooldown periods |

---

## Traceability Matrix

| Requirement | Component | Test Case |
|-------------|-----------|-----------|
| REQ-NOTIF-001 | NotificationRepository.save() | test_log_notification() |
| REQ-NOTIF-002 | NotificationService._check_preferences() | test_respect_user_preferences() |
| REQ-NOTIF-003 | NotificationService.send_trade_notification() | test_trade_notification() |
| REQ-NOTIF-004 | NotificationService.send_price_alert() | test_price_alert() |
| REQ-NOTIF-005 | NotificationService.send_risk_alert() | test_risk_alert_bypasses_rate_limit() |
| REQ-NOTIF-006 | EmailChannel.is_available() | test_email_disabled_skips_email() |
| REQ-NOTIF-007 | NotificationService.process_retry_queue() | test_retry_queue() |
| REQ-NOTIF-008 | PushChannel (optional) | test_push_notification() |
| REQ-NOTIF-009 | QuietHoursFilter (optional) | test_quiet_hours() |
| REQ-NOTIF-010 | RateLimiter | test_rate_limiting() |
| REQ-NOTIF-011 | Notification content sanitization | test_no_sensitive_data_in_notifications() |

---

## Success Criteria

1. **Functional**: All 11 requirements implemented and passing tests
2. **Coverage**: Minimum 85% test coverage
3. **Integration**: TradingService events trigger notifications
4. **Rate Limiting**: No user receives more than 5 notifications/hour (non-critical)
5. **Retry**: Failed notifications retry up to 3 times
6. **UI**: Notifications panel displays correctly

---

## Related SPECs

- **SPEC-TRADING-001**: TradingService (trade events source)
- **SPEC-TRADING-006**: UserProfileService (notification preferences)
- **SPEC-TRADING-009**: API Rate Limiting (similar rate limiting patterns)

---

Version: 1.0.0
Last Updated: 2026-03-05
Author: MoAI SPEC Builder
