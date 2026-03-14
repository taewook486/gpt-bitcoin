# SPEC-TRADING-006: User Profile Management

## Metadata

- **SPEC ID**: SPEC-TRADING-006
- **Title**: User Profile Management (사용자 프로필 관리)
- **Created**: 2026-03-05
- **Status**: Completed
- **Priority**: Medium
- **Depends On**: SPEC-TRADING-004 (SecurityService)
- **Lifecycle Level**: spec-first

---

## Problem Analysis

### Current State

SPEC-TRADING-004에서 SecurityService가 구현되어 PIN 기반 2FA, 거래 한도 설정, 감사 로그 기능을 제공합니다. 그러나 사용자 프로필 정보(이름, 이메일, 알림 설정 등)가 저장되지 않아 다음과 같은 문제가 발생합니다:

1. **개인화 불가**: 사용자별 맞춤 설정 불가능
2. **알림 대상 정보 부재**: 이메일 알림 발송을 위한 연락처 정보 없음
3. **사용자 식별 제한**: 감사 로그에서 사용자 식별이 PIN으로만 제한됨
4. **환경 설정 미저장**: 언어, 통화 표시 형식 등 사용자 선호 설정 미보관

### Root Cause Analysis (Five Whys)

1. **Why?** 사용자 프로필 데이터가 저장소에 저장되지 않음
2. **Why?** 초기 구현에서 보안 기능에 집중하여 사용자 정보 관리 기능 제외
3. **Why?** SecurityService가 인증 및 권한 관리에만 집중
4. **Why?** 프로필 관리 요구사항이 별도 기능으로 분리 필요
5. **Root Cause**: 사용자 프로필 관리가 독립적인 도메인 서비스로 설계 필요

### Desired State

사용자가 자신의 프로필 정보를 등록, 수정, 조회할 수 있으며, 이 정보가 SecurityService와 통합되어 감사 로그 및 알림 시스템에서 활용됩니다.

---

## Environment

### Technology Stack

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Database | SQLite | 3.45+ | 기존 trades.db와 통합 또는 별도 profiles.db |
| Validation | Pydantic | 2.9+ | 프로필 데이터 검증 |
| Integration | SecurityService | SPEC-004 | 기존 보안 서비스와 연동 |
| UI | Streamlit | 1.30+ | Web UI 프로필 탭 추가 |

### Integration Points

```
SPEC-TRADING-004 (SecurityService)
        ↓ 인증 사용자 정보
SPEC-TRADING-006 (UserProfileService)
        ↓ 프로필 데이터
    SQLite DB (profiles 테이블)
        ↓ 조회
    Web UI / 알림 시스템 (SPEC-007)
```

### Constraints

1. **Privacy**: 사용자 개인정보는 로컬에만 저장
2. **Validation**: 이메일 형식 검증 필수
3. **Integration**: SecurityService와 긴밀한 연동 필요
4. **Optional Fields**: 대부분의 프로필 필드는 선택사항

---

## Requirements (EARS Format)

### Ubiquitous Requirements

**REQ-PROFILE-001**: 시스템은 사용자 프로필 데이터를 영구 저장해야 한다 (The system shall persist user profile data).

```
The system shall persist user profile data to SQLite database
with complete profile information including:
- user_id, name, email, notification_preferences, created_at, updated_at
```

**REQ-PROFILE-002**: 시스템은 프로필 데이터에 대한 유효성 검사를 수행해야 한다 (The system shall validate profile data).

```
The system shall validate:
- Email format (RFC 5322 compliant)
- Name length (1-100 characters)
- Phone number format (optional, E.164 if provided)
```

### Event-Driven Requirements

**REQ-PROFILE-003**: WHEN 사용자가 처음으로 프로필을 생성하면 THEN 시스템은 기본 알림 설정으로 초기화해야 한다.

```
WHEN user creates profile for the first time
THEN UserProfileService.create_profile() shall initialize:
    AND notification_preferences shall default to:
        - price_alerts: true
        - trade_notifications: true
        - risk_alerts: true
        - email_enabled: false (requires email verification)
```

**REQ-PROFILE-004**: WHEN 프로필이 업데이트되면 THEN 시스템은 updated_at 타임스탬프를 갱신해야 한다.

```
WHEN UserProfileService.update_profile() is called
THEN the system shall:
    AND update the updated_at timestamp to current time
    AND preserve created_at unchanged
    AND log the update action via AuditLog
```

### State-Driven Requirements

**REQ-PROFILE-005**: IF 이메일이 제공되지 않으면 THEN 이메일 알림 기능을 비활성화해야 한다.

```
IF profile.email is None or empty string
THEN notification_preferences.email_enabled shall be forced to false
    AND the system shall display warning about disabled email notifications
```

**REQ-PROFILE-006**: IF 프로필이 존재하지 않으면 THEN 시스템은 기본값으로 빈 프로필을 반환해야 한다.

```
IF UserProfileService.get_profile() finds no existing profile
THEN the system shall return a default profile with:
    AND name = ""
    AND email = ""
    AND all notification_preferences set to defaults
    AND is_new_profile flag set to true
```

### Optional Requirements

**REQ-PROFILE-007**: Where possible, 시스템은 프로필 이미지를 지원해야 한다.

```
Where possible, the system shall support profile image:
- Accept PNG, JPG formats (max 2MB)
- Store as base64 or file path
- Display in Web UI header
- Default avatar for users without image
```

**REQ-PROFILE-008**: Where possible, 시스템은 다국어 설정을 지원해야 한다.

```
Where possible, the system shall support language preferences:
- Korean (ko), English (en), Japanese (ja)
- Affect Web UI display language
- Affect notification language
- Store in profile.preferred_language
```

### Unwanted Behavior Requirements

**REQ-PROFILE-009**: 시스템은 잘못된 형식의 이메일을 저장해서는 안 된다 (The system shall not store invalid email formats).

```
The system shall NOT allow:
- Email without @ symbol
- Email with invalid domain format
- Email longer than 254 characters

AND shall raise ValidationError with descriptive message
```

**REQ-PROFILE-010**: 시스템은 민감한 프로필 정보를 로그에 평문으로 기록해서는 안 된다 (The system shall not log sensitive profile data in plain text).

```
The system shall NOT log:
- Email address in plain text (mask as u***@example.com)
- Phone number in plain text (mask as ***-****-1234)
- Full profile data in DEBUG logs

Exception: Audit logs with appropriate access controls
```

---

## Specifications

### Data Model

#### UserProfile Schema

```python
@dataclass
class UserProfile:
    """User profile information."""
    user_id: str  # Unique identifier (from SecurityService)
    name: str  # Display name (1-100 characters)
    email: str | None  # Email address (validated format)
    phone: str | None  # Phone number (optional, E.164 format)
    notification_preferences: NotificationPreferences
    preferred_language: Literal["ko", "en", "ja"]
    preferred_currency: Literal["KRW", "USD"]
    timezone: str  # IANA timezone (e.g., "Asia/Seoul")
    profile_image: str | None  # Base64 encoded or file path
    created_at: datetime
    updated_at: datetime
    is_email_verified: bool

@dataclass
class NotificationPreferences:
    """User notification settings."""
    price_alerts: bool  # Price change notifications
    trade_notifications: bool  # Trade execution notifications
    risk_alerts: bool  # Risk warning notifications
    email_enabled: bool  # Email delivery enabled
    push_enabled: bool  # Browser push notifications
    daily_summary: bool  # Daily portfolio summary
```

#### SQLite Schema

```sql
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
);

CREATE INDEX idx_profiles_email ON user_profiles(email);
```

### Component Architecture

```
src/gpt_bitcoin/
├── domain/
│   ├── user_profile.py (NEW)
│   │   ├── UserProfile (dataclass)
│   │   ├── NotificationPreferences (dataclass)
│   │   └── UserProfileService
│   └── security.py (existing - SPEC-004)
├── infrastructure/
│   └── persistence/
│       └── profile_repository.py (NEW)
└── web_ui.py (MODIFY - add Profile tab)
```

### Class Design

#### UserProfileService

```python
class UserProfileService:
    """
    Domain service for user profile management.

    Responsibilities:
    - Create, read, update user profiles
    - Manage notification preferences
    - Validate profile data
    - Integrate with SecurityService for audit logging

    @MX:NOTE: Single user assumption for MVP.
        Multi-user support in future versions.
    """

    def __init__(
        self,
        repository: ProfileRepository,
        security_service: SecurityService,
    ):
        """Initialize with repository and security service."""
        pass

    async def get_profile(self, user_id: str) -> UserProfile:
        """
        Get user profile or create default.

        @MX:ANCHOR: Primary entry point for profile access.
            fan_in: 3+ (Web UI, NotificationService, AuditLog)
            @MX:REASON: Centralizes all profile reads.
        """
        pass

    async def update_profile(
        self,
        user_id: str,
        updates: dict,
    ) -> UserProfile:
        """
        Update user profile with validation.

        Raises:
            ValidationError: If email format invalid
        """
        pass

    async def update_notification_preferences(
        self,
        user_id: str,
        preferences: NotificationPreferences,
    ) -> None:
        """Update notification settings."""
        pass

    def validate_email(self, email: str) -> bool:
        """Validate email format (RFC 5322)."""
        pass
```

### UI Design (Web UI)

#### Profile Settings Tab Structure

```
+-----------------------------------------------------------------+
| [User Profile]                                                   |
+-----------------------------------------------------------------+
| Basic Information:                                               |
| [Name: _____________] [Email: _____________] [Phone: ________] |
+-----------------------------------------------------------------+
| Notification Settings:                                           |
| [x] Price Alerts    [x] Trade Notifications  [x] Risk Alerts    |
| [ ] Email Enabled   [ ] Push Notifications   [ ] Daily Summary  |
+-----------------------------------------------------------------+
| Preferences:                                                     |
| [Language: Korean v] [Currency: KRW v] [Timezone: Asia/Seoul v] |
+-----------------------------------------------------------------+
| [Save Changes]                              [Reset to Defaults] |
+-----------------------------------------------------------------+
```

---

## MX Tag Targets

### High Fan-In Functions (>= 3 callers)

| Function | Expected Fan-In | MX Tag Type | Location |
|----------|-----------------|-------------|----------|
| `UserProfileService.get_profile()` | 3+ | @MX:ANCHOR | domain/user_profile.py |
| `ProfileRepository.find_by_user_id()` | 2+ | @MX:NOTE | infrastructure/persistence/profile_repository.py |

### Danger Zones (Complexity >= 15 or Critical Operations)

| Function | Risk | MX Tag Type | Reason |
|----------|------|-------------|--------|
| `validate_email()` | Edge cases | @MX:WARN | RFC 5322 compliance, regex complexity |
| Profile update | Data integrity | @MX:NOTE | Must preserve audit trail |

---

## Files to Modify

### New Files

| File Path | Purpose | Lines (Est.) |
|-----------|---------|--------------|
| `src/gpt_bitcoin/domain/user_profile.py` | UserProfileService, data models | ~180 |
| `src/gpt_bitcoin/infrastructure/persistence/profile_repository.py` | Profile persistence | ~100 |
| `tests/unit/domain/test_user_profile.py` | Unit tests | ~300 |
| `tests/unit/infrastructure/test_profile_repository.py` | Repository tests | ~150 |

### Modified Files

| File Path | Changes | Lines Changed (Est.) |
|-----------|---------|---------------------|
| `src/gpt_bitcoin/web_ui.py` | Add Profile Settings tab | +100 |
| `src/gpt_bitcoin/dependencies/container.py` | Register UserProfileService | +10 |
| `src/gpt_bitcoin/infrastructure/persistence/database.py` | Add profiles table schema | +20 |

---

## Risks and Mitigations

### Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Email validation edge cases | Medium | Low | Use proven email-validator library |
| Profile data loss | Low | Medium | Regular backups, soft delete pattern |
| Privacy concerns | Medium | Medium | Local-only storage, no external transmission |
| Integration complexity with SecurityService | Low | Medium | Clear interface contracts |

---

## Traceability Matrix

| Requirement | Component | Test Case |
|-------------|-----------|-----------|
| REQ-PROFILE-001 | ProfileRepository.save() | test_persist_profile() |
| REQ-PROFILE-002 | UserProfileService.validate_email() | test_email_validation() |
| REQ-PROFILE-003 | UserProfileService.create_profile() | test_default_preferences() |
| REQ-PROFILE-004 | UserProfileService.update_profile() | test_updated_at_refresh() |
| REQ-PROFILE-005 | NotificationPreferences validation | test_email_required_for_email_notifications() |
| REQ-PROFILE-006 | UserProfileService.get_profile() | test_default_profile_for_new_user() |
| REQ-PROFILE-007 | Profile image support | test_profile_image_upload() |
| REQ-PROFILE-008 | Language preferences | test_language_preference() |
| REQ-PROFILE-009 | Email validation | test_invalid_email_rejection() |
| REQ-PROFILE-010 | Sensitive data logging | test_no_plain_text_email_in_logs() |

---

## Success Criteria

1. **Functional**: All 10 requirements implemented and passing tests
2. **Coverage**: Minimum 85% test coverage
3. **Integration**: SecurityService audit logging works with profile updates
4. **Validation**: All edge cases for email validation handled
5. **UI**: Profile settings tab displays and saves correctly

---

## Related SPECs

- **SPEC-TRADING-004**: SecurityService (authentication integration)
- **SPEC-TRADING-007**: Notification System (uses profile preferences)

---

Version: 1.0.0
Last Updated: 2026-03-05
Author: MoAI SPEC Builder
