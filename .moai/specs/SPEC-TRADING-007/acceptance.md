# Acceptance Criteria: SPEC-TRADING-007 (Notification System)

## Overview

이 문서는 SPEC-TRADING-007 알림 시스템 기능의 수락 기준을 Gherkin 형식(Given-When-Then)으로 정의합니다.

---

## Feature 1: Trade Notifications

### Scenario 1.1: Successful Trade Notification

```gherkin
Feature: 거래 알림 (Trade Notifications)

  Scenario: 성공한 거래 알림 발송
    Given 사용자가 KRW-BTC 0.001을 50,000,000 KRW에 매수함
      And 사용자의 trade_notifications 설정이 true임
    When 거래가 성공적으로 실행됨
    Then 알림이 생성됨
      And 알림 유형이 "trade_executed"임
      And 알림 내용에 ticker, side, 가격, 수량이 포함됨
      And in_app 채널로 알림이 발송됨
```

### Scenario 1.2: Skip Notification When Disabled

```gherkin
  Scenario: 알림 비활성화 시 건너뜀
    Given 사용자의 trade_notifications 설정이 false임
    When 거래가 성공적으로 실행됨
    Then 거래 알림이 발송되지 않음
      And 로그에 "trade_notifications disabled" 기록됨
```

---

## Feature 2: Price Alerts

### Scenario 2.1: Price Alert Trigger

```gherkin
Feature: 가격 알림 (Price Alerts)

  Scenario: 가격 상승 알림 트리거
    Given 사용자가 KRW-BTC에 대해 5% 상승 알림을 설정함
      And 현재 가격이 50,000,000 KRW임
    When 가격이 52,500,000 KRW (5% 상승)로 변경됨
    Then 가격 알림이 발송됨
      And 알림 내용에 "5% 상승"이 포함됨
      And 알림 내용에 현재 가격이 포함됨
```

### Scenario 2.2: Price Alert Cooldown

```gherkin
  Scenario: 가격 알림 쿨다운
    Given 사용자가 KRW-BTC 알림을 받은 지 30분이 지나지 않음
    When 가격이 다시 5% 상승함
    Then 새 알림이 발송되지 않음 (쿨다운)
```

### Scenario 2.3: Price Alert Below Threshold

```gherkin
  Scenario: 가격 하락 알림 트리거
    Given 사용자가 KRW-BTC에 대해 5% 하락 알림을 설정함
      And 현재 가격이 50,000,000 KRW임
    When 가격이 47,500,000 KRW (5% 하락)로 변경됨
    Then 가격 알림이 발송됨
      And 알림 내용에 "5% 하락"이 포함됨
```

---

## Feature 3: Risk Alerts

### Scenario 3.1: Daily Loss Limit Alert

```gherkin
Feature: 위험 알림 (Risk Alerts)

  Scenario: 일일 손실 한도 경고
    Given 사용자의 일일 손실 한도가 1,000,000 KRW임
      And 현재 일일 손실이 900,000 KRW (90%)임
    When 위험 감지 시스템이 실행됨
    Then HIGH 우선순위 위험 알림이 발송됨
      And 알림 내용에 "90% 도달"이 포함됨
      And 알림이 rate limit을 무시함
```

### Scenario 3.2: Risk Alert Bypasses Quiet Hours

```gherkin
  Scenario: 위험 알림은 조용한 시간 무시
    Given 현재 시간이 02:00 (조용한 시간)임
      And 위험 조건이 감지됨
    When 위험 알림 발송
    Then 알림이 정상적으로 발송됨
      And 조용한 시간 설정이 무시됨
```

---

## Feature 4: Rate Limiting

### Scenario 4.1: Hourly Rate Limit

```gherkin
Feature: 속도 제한 (Rate Limiting)

  Scenario: 시간당 알림 제한
    Given 사용자가 지난 1시간 동안 5개의 알림을 받음
    When 6번째 일반 알림 발송 시도
    Then 알림이 발송되지 않음
      And 로그에 rate limit 초과 기록됨
```

### Scenario 4.2: Rate Limit Does Not Affect Risk Alerts

```gherkin
  Scenario: 위험 알림은 속도 제한 제외
    Given 사용자가 rate limit에 도달함
    When 위험 알림 발송
    Then 위험 알림이 정상적으로 발송됨
```

---

## Feature 5: Email Channel

### Scenario 5.1: Email Notification

```gherkin
Feature: 이메일 채널 (Email Channel)

  Scenario: 이메일 알림 발송
    Given 사용자의 email_enabled 설정이 true임
      And 이메일이 "user@example.com"으로 설정됨
    When 거래 알림이 생성됨
    Then 이메일이 "user@example.com"으로 발송됨
      And 이메일 제목에 민감한 정보가 없음
```

### Scenario 5.2: Email Disabled

```gherkin
  Scenario: 이메일 비활성화 시 스킵
    Given 사용자의 email_enabled 설정이 false임
    When 알림 발송
    Then 이메일 채널이 스킵됨
      And in_app 채널만 사용됨
```

### Scenario 5.3: Email Send Failure

```gherkin
  Scenario: 이메일 발송 실패
    Given SMTP 서버가 응답하지 않음
    When 이메일 알림 발송 시도
    Then 알림 상태가 "failed"로 저장됨
      And retry_queue에 추가됨
      And ERROR 레벨 로그 기록됨
```

---

## Feature 6: Retry Queue

### Scenario 6.1: Retry on Failure

```gherkin
Feature: 재시도 큐 (Retry Queue)

  Scenario: 실패 시 재시도
    Given 알림 발송이 실패함
    When retry_queue 프로세서 실행
    Then 알림이 재시도됨
      And retry_count가 1 증가함
```

### Scenario 6.2: Max Retry Exceeded

```gherkin
  Scenario: 최대 재시도 초과
    Given 알림의 retry_count가 3임
    When 재시도 시도
    Then 알림 상태가 "failed"로 최종 설정됨
      And 더 이상 재시도하지 않음
```

### Scenario 6.3: Exponential Backoff

```gherkin
  Scenario: 지수 백오프
    Given 첫 번째 재시도가 실패함
    When 두 번째 재시도 예약
    Then 대기 시간이 지수적으로 증가함
      | Retry | Wait Time |
      | 1     | 1 minute  |
      | 2     | 2 minutes |
      | 3     | 4 minutes |
```

---

## Feature 7: In-App Notifications

### Scenario 7.1: Display Notifications

```gherkin
Feature: 인앱 알림 (In-App Notifications)

  Scenario: 알림 표시
    Given 사용자가 Web UI에 로그인함
      And 읽지 않은 알림이 3개 있음
    When 알림 패널 열람
    Then 3개의 알림이 목록으로 표시됨
      And 각 알림에 시간, 제목, 내용이 표시됨
```

### Scenario 7.2: Mark as Read

```gherkin
  Scenario: 알림 읽음 표시
    Given 읽지 않은 알림이 있음
    When 사용자가 알림 클릭 또는 "읽음" 버튼 클릭
    Then 알림이 "읽음" 상태로 변경됨
      And 알림 배지 카운트가 감소함
```

### Scenario 7.3: Dismiss Notification

```gherkin
  Scenario: 알림 삭제
    Given 알림이 표시됨
    When 사용자가 "삭제" 버튼 클릭
    Then 알림이 목록에서 제거됨
      And 데이터베이스에서 삭제되지 않음 (보관)
```

---

## Feature 8: Notification Preferences

### Scenario 8.1: Update Preferences

```gherkin
Feature: 알림 설정 (Notification Preferences)

  Scenario: 알림 설정 변경
    Given 사용자가 프로필 설정 페이지에 있음
    When 다음 설정을 변경함:
      | price_alerts        | false |
      | trade_notifications | true  |
      | email_enabled       | false |
    Then 설정이 저장됨
      And 이후 알림이 새 설정에 따라 발송됨
```

### Scenario 8.2: Email Required for Email Notifications

```gherkin
  Scenario: 이메일 없이 이메일 알림 활성화 불가
    Given 사용자 프로필에 이메일이 없음
    When email_enabled를 true로 설정 시도
    Then 시스템이 자동으로 false로 유지함
      And 경고 메시지가 표시됨
```

---

## Feature 9: Notification Content

### Scenario 9.1: No Sensitive Data in Subjects

```gherkin
Feature: 알림 내용 (Notification Content)

  Scenario: 제목에 민감 정보 없음
    Given 거래 알림이 생성됨
    When 이메일 발송
    Then 이메일 제목에 다음이 포함되지 않음:
      | 항목          | 이유              |
      | 구체적 금액   | 보안              |
      | 계좌 잔액     | 프라이버시        |
      | PIN/토큰      | 보안              |
      And 제목은 "거래 완료 알림"과 같이 일반적임
```

### Scenario 9.2: Bilingual Support

```gherkin
  Scenario: 이중 언어 지원
    Given 사용자의 preferred_language가 "en"임
    When 알림 생성
    Then 알림 내용이 영어로 작성됨
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
      And NotificationService 커버리지 >= 90%
      And RateLimiter 커버리지 >= 100%
```

### Performance

```gherkin
Feature: 성능 기준

  Scenario: 알림 발송 성능
    Given 알림이 생성됨
    When 알림 발송
    Then in_app 발송 < 50ms
      And email 발송 < 3초
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
- [ ] Web UI에 알림 패널 추가 완료
- [ ] 이메일 발송 기능 작동
- [ ] 가격 알림 스케줄러 작동
- [ ] 위험 알림 rate limit 무시 작동
- [ ] Retry queue 작동
- [ ] Lint 에러 0개
- [ ] Type checking 에러 0개
- [ ] 문서화 완료 (docstrings)

---

Version: 1.0.0
Last Updated: 2026-03-05
Author: MoAI SPEC Builder
