# Implementation Plan: SPEC-TRADING-006 (User Profile Management)

## Overview

이 문서는 SPEC-TRADING-006 사용자 프로필 관리 기능의 구현 계획을 정의합니다.

---

## Milestones (Priority-Based)

### Phase 1: Foundation (Primary Goal)

**Objective**: 프로필 데이터 모델 및 기본 CRUD 기능 구현

#### Tasks

1. **Data Models**
   - Priority: Critical
   - Create `UserProfile` dataclass with all fields
   - Create `NotificationPreferences` dataclass
   - Add Pydantic validation

2. **ProfileRepository**
   - Priority: Critical
   - Implement database schema (user_profiles table)
   - Implement CRUD operations (Create, Read, Update)
   - No Delete operation (soft delete pattern)

3. **UserProfileService**
   - Priority: High
   - Implement `get_profile()` with default creation
   - Implement `update_profile()` with validation
   - Implement `update_notification_preferences()`

4. **Email Validation**
   - Priority: High
   - Implement RFC 5322 compliant email validation
   - Handle edge cases (international domains, plus addressing)

5. **Unit Tests - Core**
   - Priority: High
   - Test UserProfile creation and validation
   - Test ProfileRepository operations
   - Test UserProfileService methods

**Deliverables**:
- Working profile persistence layer
- All core tests passing
- Email validation working

---

### Phase 2: Security Integration (Secondary Goal)

**Objective**: SecurityService와 연동하여 감사 로그 기능 구현

#### Tasks

1. **Audit Log Integration**
   - Priority: High
   - Log profile creation events
   - Log profile update events (with field masking)
   - Log preference changes

2. **Sensitive Data Handling**
   - Priority: Medium
   - Mask email in logs (u***@example.com)
   - Mask phone in logs (***-****-1234)
   - Implement secure logging utilities

3. **Integration Tests**
   - Priority: Medium
   - Test SecurityService integration
   - Test audit log entries

**Deliverables**:
- Audit logging for profile changes
- Sensitive data properly masked
- Integration tests passing

---

### Phase 3: Web UI Integration (Final Goal)

**Objective**: Web UI에 프로필 설정 탭 추가

#### Tasks

1. **Profile Settings Tab**
   - Priority: High
   - Create new tab in Streamlit UI
   - Build profile form with all fields
   - Add validation feedback

2. **Notification Preferences UI**
   - Priority: Medium
   - Add checkbox controls for all preferences
   - Add enable/disable logic based on email availability
   - Show warning when email notifications disabled

3. **Save and Reset**
   - Priority: Medium
   - Implement save functionality
   - Implement reset to defaults
   - Add success/error notifications

4. **UI Tests**
   - Priority: Medium
   - Test form rendering
   - Test save functionality
   - Test validation feedback

**Deliverables**:
- Complete Profile Settings tab
- All UI interactions working
- User-friendly feedback

---

## Technical Approach

### Repository Pattern

```python
# infrastructure/persistence/profile_repository.py

class ProfileRepository:
    """Repository for user profile persistence."""

    def __init__(self, db: Database):
        self._db = db

    async def find_by_user_id(self, user_id: str) -> UserProfile | None:
        """Find profile by user ID."""
        pass

    async def save(self, profile: UserProfile) -> None:
        """
        Save or update profile.

        @MX:NOTE: Uses INSERT OR REPLACE for upsert semantics.
        """
        pass
```

### Service Layer

```python
# domain/user_profile.py

class UserProfileService:
    """User profile management service."""

    async def get_profile(self, user_id: str) -> UserProfile:
        """
        Get profile or create default.

        @MX:ANCHOR: Primary profile access point.
        """
        profile = await self._repository.find_by_user_id(user_id)
        if profile is None:
            profile = self._create_default_profile(user_id)
            await self._repository.save(profile)
        return profile

    async def update_profile(
        self,
        user_id: str,
        updates: dict,
    ) -> UserProfile:
        """Update profile with validation."""
        profile = await self.get_profile(user_id)

        # Validate email if provided
        if "email" in updates and updates["email"]:
            if not self.validate_email(updates["email"]):
                raise ValidationError("Invalid email format")

        # Apply updates
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        profile.updated_at = datetime.now()

        # Audit log
        await self._security_service.log_action(
            action="profile_update",
            details=self._mask_sensitive_data(updates),
        )

        await self._repository.save(profile)
        return profile
```

---

## Architecture Design

### Package Structure

```
src/gpt_bitcoin/
├── domain/
│   ├── security.py              # [EXISTING] SecurityService
│   └── user_profile.py          # [NEW] UserProfileService
│
├── infrastructure/
│   └── persistence/
│       ├── database.py          # [MODIFY] Add profiles schema
│       └── profile_repository.py # [NEW]
│
├── dependencies/
│   └── container.py             # [MODIFY] Register services
│
└── web_ui.py                    # [MODIFY] Add Profile tab
```

### Data Flow

```
+------------------+
| Web UI           |
| (Profile Tab)    |
+--------+---------+
         | Profile Update
         v
+------------------+
| UserProfile      |
| Service          |
+--------+---------+
         | Audit Event
         v
+------------------+         +------------------+
| SecurityService  |<------->| Profile          |
|                  |         | Repository       |
+------------------+         +--------+---------+
                                      |
                                      v
                             +------------------+
                             | SQLite DB        |
                             | (profiles table) |
                             +------------------+
```

---

## Configuration Changes

### Settings Additions

```python
# config/settings.py additions

class Settings(BaseSettings):
    # ... existing settings ...

    # Profile Settings
    default_language: str = Field(
        default="ko",
        description="Default language for new users",
    )
    default_currency: str = Field(
        default="KRW",
        description="Default currency display",
    )
    default_timezone: str = Field(
        default="Asia/Seoul",
        description="Default timezone",
    )
```

### Container Registration

```python
# dependencies/container.py additions

from gpt_bitcoin.domain.user_profile import UserProfileService
from gpt_bitcoin.infrastructure.persistence.profile_repository import ProfileRepository

class Container(containers.DeclarativeContainer):
    # ... existing providers ...

    profile_repository: providers.Provider[ProfileRepository] = providers.Factory(
        ProfileRepository,
        db=database,
    )

    user_profile_service: providers.Provider[UserProfileService] = providers.Factory(
        UserProfileService,
        repository=profile_repository,
        security_service=security_service,
    )
```

---

## Testing Strategy

### Test Coverage Goals

| Component | Target Coverage | Priority |
|-----------|-----------------|----------|
| UserProfile | 100% | Critical |
| NotificationPreferences | 100% | Critical |
| ProfileRepository | 95% | High |
| UserProfileService | 90% | High |
| Web UI Integration | 70% | Medium |

### Key Test Cases

```python
# tests/unit/domain/test_user_profile.py

class TestUserProfileService:
    """Test UserProfileService."""

    @pytest.mark.asyncio
    async def test_get_profile_creates_default(self, service):
        """Test default profile creation for new users."""
        profile = await service.get_profile("new_user")

        assert profile.name == ""
        assert profile.email is None
        assert profile.notification_preferences.price_alerts is True
        assert profile.is_email_verified is False

    @pytest.mark.asyncio
    async def test_update_profile_validates_email(self, service):
        """Test email validation during update."""
        with pytest.raises(ValidationError):
            await service.update_profile(
                "user1",
                {"email": "invalid-email"},
            )

    def test_validate_email_rfc5322(self, service):
        """Test RFC 5322 email validation."""
        # Valid emails
        assert service.validate_email("user@example.com") is True
        assert service.validate_email("user+tag@example.co.uk") is True
        assert service.validate_email("user@xn--domain.com") is True  # IDN

        # Invalid emails
        assert service.validate_email("invalid") is False
        assert service.validate_email("@example.com") is False
        assert service.validate_email("user@") is False
```

---

## Dependencies

### New Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| email-validator | >=2.1.0 | RFC 5322 email validation |

### Existing Dependencies Used

| Package | Usage |
|---------|-------|
| pydantic | Profile validation |
| pytest + pytest-asyncio | Testing |
| streamlit | UI |

---

## Security Considerations

### Data Protection

1. **Local Storage Only**: Profile data never transmitted externally
2. **Log Masking**: Sensitive fields masked in all logs
3. **Email Verification**: Required before enabling email notifications (future)

### Privacy

- No PII collection beyond necessary fields
- User can delete profile data (future: data export/deletion)
- Clear indication of what data is stored

---

Version: 1.0.0
Last Updated: 2026-03-05
Author: MoAI SPEC Builder
