# Acceptance Criteria: SPEC-TRADING-006 (User Profile Management)

## Overview

이 문서는 SPEC-TRADING-006 사용자 프로필 관리 기능의 수락 기준을 Gherkin 형식(Given-When-Then)으로 정의합니다.

---

## Feature 1: Profile Data Persistence

### Scenario 1.1: Create Default Profile

```gherkin
Feature: 프로필 데이터 저장 (Profile Data Persistence)

  Scenario: 새 사용자 기본 프로필 생성
    Given 사용자 ID가 "user123"인 프로필이 존재하지 않음
    When UserProfileService.get_profile("user123") 호출
    Then 기본값으로 새 프로필이 생성됨
      And name이 빈 문자열임
      And email이 None임
      And notification_preferences.price_alerts가 True임
      And notification_preferences.email_enabled가 False임
```

### Scenario 1.2: Update Profile

```gherkin
  Scenario: 프로필 업데이트
    Given 사용자 ID가 "user123"인 프로필이 존재함
    When UserProfileService.update_profile("user123", {"name": "홍길동", "email": "hong@example.com"}) 호출
    Then 프로필의 name이 "홍길동"으로 변경됨
      And 프로필의 email이 "hong@example.com"으로 변경됨
      And updated_at이 현재 시간으로 갱신됨
      And created_at은 변경되지 않음
```

### Scenario 1.3: Invalid Email Rejection

```gherkin
  Scenario: 잘못된 이메일 형식 거부
    Given 사용자 ID가 "user123"인 프로필이 존재함
    When UserProfileService.update_profile("user123", {"email": "invalid-email"}) 호출
    Then ValidationError가 발생함
      And 에러 메시지에 "Invalid email format"이 포함됨
      And 기존 프로필 데이터는 변경되지 않음
```

---

## Feature 2: Email Validation

### Scenario 2.1: Valid Email Formats

```gherkin
Feature: 이메일 유효성 검사 (Email Validation)

  Scenario Outline: 유효한 이메일 형식
    Given 이메일 검증 기능이 활성화됨
    When "<email>" 주소 검증
    Then 검증 결과는 <valid>임

    Examples:
      | email                      | valid  |
      | user@example.com           | true   |
      | user+tag@example.com       | true   |
      | user.name@example.co.uk    | true   |
      | user@subdomain.example.com | true   |
      | user@xn--domain.com        | true   |
```

### Scenario 2.2: Invalid Email Formats

```gherkin
  Scenario Outline: 잘못된 이메일 형식
    Given 이메일 검증 기능이 활성화됨
    When "<email>" 주소 검증
    Then 검증 결과는 false임

    Examples:
      | email              |
      | invalid            |
      | @example.com       |
      | user@              |
      | user@.com          |
      | user@example       |
      | user@@example.com  |
```

---

## Feature 3: Notification Preferences

### Scenario 3.1: Update Notification Preferences

```gherkin
Feature: 알림 설정 (Notification Preferences)

  Scenario: 알림 설정 업데이트
    Given 사용자 프로필이 존재함
    When UserProfileService.update_notification_preferences() 호출:
      | preference          | value  |
      | price_alerts        | true   |
      | trade_notifications | true   |
      | risk_alerts         | true   |
      | email_enabled       | false  |
    Then 모든 설정이 업데이트됨
      And 감사 로그에 변경 내역이 기록됨
```

### Scenario 3.2: Email Disabled Without Email Address

```gherkin
  Scenario: 이메일 없이 이메일 알림 활성화 시도
    Given 사용자 프로필의 email이 None임
    When email_enabled를 true로 설정 시도
    Then 시스템이 자동으로 email_enabled를 false로 설정함
      And 경고 메시지가 표시됨
```

---

## Feature 4: Web UI Profile Tab

### Scenario 4.1: Display Profile Tab

```gherkin
Feature: Web UI 프로필 탭

  Scenario: 프로필 탭 표시
    Given 사용자가 Web UI에 접속함
    When "프로필 설정 (Profile Settings)" 탭 클릭
    Then 프로필 폼이 표시됨
      And 이름 입력 필드가 표시됨
      And 이메일 입력 필드가 표시됨
      And 알림 설정 체크박스가 표시됨
```

### Scenario 4.2: Save Profile Changes

```gherkin
  Scenario: 프로필 변경 저장
    Given 프로필 탭이 열려 있음
    When 사용자가 이름을 "홍길동"으로 입력
      And "저장 (Save)" 버튼 클릭
    Then "저장되었습니다" 성공 메시지가 표시됨
      And 프로필이 데이터베이스에 저장됨
```

### Scenario 4.3: Reset to Defaults

```gherkin
  Scenario: 기본값으로 초기화
    Given 프로필 탭이 열려 있고 변경사항이 있음
    When "기본값 복원 (Reset to Defaults)" 버튼 클릭
    Then 확인 대화상자가 표시됨
    When 사용자가 확인 클릭
    Then 모든 필드가 기본값으로 복원됨
```

### Scenario 4.4: Email Validation Feedback

```gherkin
  Scenario: 이메일 유효성 피드백
    Given 프로필 탭이 열려 있음
    When 사용자가 이메일 필드에 "invalid" 입력
      And 포커스가 이메일 필드를 벗어남
    Then "올바른 이메일 형식이 아닙니다" 에러 메시지가 표시됨
```

---

## Feature 5: Audit Logging

### Scenario 5.1: Log Profile Creation

```gherkin
Feature: 감사 로그 (Audit Logging)

  Scenario: 프로필 생성 로그
    Given 새 사용자가 첫 프로필을 생성함
    When UserProfileService.get_profile()가 기본 프로필 생성
    Then 감사 로그에 다음 항목이 기록됨:
      | action   | profile_create |
      | user_id  | user123        |
      | timestamp| 현재 시간      |
```

### Scenario 5.2: Log Profile Update with Masking

```gherkin
  Scenario: 프로필 업데이트 로그 (마스킹 적용)
    Given 사용자가 이메일을 "sensitive@example.com"으로 변경함
    When UserProfileService.update_profile() 호출
    Then 감사 로그의 details 필드에 이메일이 마스킹됨:
      | email    | s***@example.com |
      And 전체 이메일이 로그에 평문으로 기록되지 않음
```

---

## Feature 6: Language Preferences

### Scenario 6.1: Set Language Preference

```gherkin
Feature: 언어 설정 (Language Preferences)

  Scenario: 언어 설정 변경
    Given 사용자 프로필이 존재함
    When preferred_language를 "en"으로 설정
    Then 프로필의 preferred_language가 "en"으로 저장됨
      And 이후 알림이 영어로 발송됨 (SPEC-007 구현 시)
```

---

## Quality Gates

### Test Coverage

```gherkin
Feature: 테스트 커버리지

  Scenario: 최소 커버리지 달성
    Given 모든 테스트가 작성됨
    When pytest --cov 실행
    Then 전체 커버리지 >= 85%
      And UserProfileService 커버리지 >= 90%
      And ProfileRepository 커버리지 >= 95%
```

### Code Quality

```gherkin
Feature: 코드 품질

  Scenario: 린터 통과
    Given 모든 코드가 작성됨
    When ruff check 실행
    Then 에러 0개
      And 경고 < 5개
```

---

## Definition of Done

- [ ] 모든 Gherkin 시나리오에 대한 테스트 구현
- [ ] 테스트 커버리지 85% 이상 달성
- [ ] Web UI에 프로필 설정 탭 추가 완료
- [ ] 이메일 유효성 검사 작동
- [ ] SecurityService 감사 로그 연동 완료
- [ ] 민감 정보 로그 마스킹 적용
- [ ] Lint 에러 0개
- [ ] Type checking 에러 0개
- [ ] 문서화 완료 (docstrings)

---

Version: 1.0.0
Last Updated: 2026-03-05
Author: MoAI SPEC Builder
