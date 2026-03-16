# Acceptance Criteria: SPEC-TRADING-009 (API Rate Limiting)

## Overview

이 문서는 SPEC-TRADING-009 API 속도 제한 기능의 수락 기준을 Gherkin 형식(Given-When-Then)으로 정의합니다.

---

## Feature 1: Token Bucket Rate Limiting

### Scenario 1.1: Consume Available Tokens

```gherkin
Feature: 토큰 버킷 속도 제한 (Token Bucket Rate Limiting)

  Scenario: 가용 토큰 소비
    Given 토큰 버킷 용량이 10이고 리필 속도가 1.0/초임
      And 현재 토큰이 10개 있음
    When 5개의 토큰 소비
    Then 소비가 성공함
      And 남은 토큰이 5개임
```

### Scenario 1.2: Reject When Insufficient Tokens

```gherkin
  Scenario: 토큰 부족 시 거부
    Given 토큰 버킷 용량이 10이고 리필 속도가 1.0/초임
      And 현재 토큰이 3개 있음
    When 5개의 토큰 소비 시도
    Then 소비가 실패함
      And 토큰이 여전히 3개임
```

### Scenario 1.3: Token Refill

```gherkin
  Scenario: 토큰 리필
    Given 토큰 버킷 용량이 10이고 리필 속도가 2.0/초임
      And 현재 토큰이 0개임
    When 1초 대기
    Then 토큰이 2개 리필됨
```

### Scenario 1.4: No Overfill

```gherkin
  Scenario: 최대 용량 초과 방지
    Given 토큰 버킷 용량이 10이고 리필 속도가 10.0/초임
      And 현재 토큰이 10개임
    When 1초 대기
    Then 토큰이 여전히 10개임 (용량 초과하지 않음)
```

---

## Feature 2: Rate Limiter

### Scenario 2.1: Allow Under Limit

```gherkin
Feature: 속도 제한기 (Rate Limiter)

  Scenario: 제한 미만 허용
    Given 분당 60회 제한 설정됨
      And 현재 요청이 30회임
    When RateLimiter.acquire() 호출
    Then 요청이 허용됨
      And 통계의 total_requests가 증가함
```

### Scenario 2.2: Reject Over Limit

```gherkin
  Scenario: 제한 초과 거부
    Given 분당 60회 제한 설정됨
      And 현재 요청이 60회임
    When RateLimiter.acquire(wait=False) 호출
    Then RateLimitError가 발생함
      And rejected_requests가 증가함
```

### Scenario 2.3: Wait for Token

```gherkin
  Scenario: 토큰 대기
    Given 분당 60회 제한 설정됨
      And 현재 토큰이 없음
    When RateLimiter.acquire(wait=True) 호출
    Then 토큰이 생길 때까지 대기함
      And 토큰 획득 후 요청이 진행됨
```

---

## Feature 3: Exponential Backoff Retry

### Scenario 3.1: Retry on Transient Failure

```gherkin
Feature: 지수 백오프 재시도 (Exponential Backoff Retry)

  Scenario: 일시적 실패 시 재시도
    Given RetryHandler가 최대 3회 재시도로 설정됨
      And 함수가 처음 2회 실패 후 3회째 성공함
    When RetryHandler.execute() 호출
    Then 3회 시도 후 성공함
      And 첫 번째 재시도 전 1초 대기
      And 두 번째 재시도 전 2초 대기
```

### Scenario 3.2: Max Retry Exceeded

```gherkin
  Scenario: 최대 재시도 초과
    Given RetryHandler가 최대 3회 재시도로 설정됨
      And 함수가 항상 실패함
    When RetryHandler.execute() 호출
    Then 4회 시도 후 (초기 + 3 재시도) 마지막 에러 발생
      And 더 이상 재시도하지 않음
```

### Scenario 3.3: No Retry on Client Error

```gherkin
  Scenario: 클라이언트 에러는 재시도 안 함
    Given 함수가 400 Bad Request 에러 발생함
    When RetryHandler.execute() 호출
    Then 재시도 없이 즉시 에러 발생
```

### Scenario 3.4: Jitter Applied

```gherkin
  Scenario: 지터 적용
    Given RetryHandler가 지터 활성화로 설정됨
      And base_delay가 1초임
    When 여러 번 재시도 실행
    Then 대기 시간이 매번 다름 (0.5~1.5초 범위)
```

---

## Feature 4: Circuit Breaker

### Scenario 4.1: Normal Operation (Closed State)

```gherkin
Feature: 서킷 브레이커 (Circuit Breaker)

  Scenario: 정상 동작 (Closed 상태)
    Given CircuitBreaker가 CLOSED 상태임
    When 함수 호출
    Then 함수가 정상 실행됨
      And consecutive_failures가 0임
```

### Scenario 4.2: Open After Failures

```gherkin
  Scenario: 실패 후 Open
    Given CircuitBreaker 실패 임계값이 5임
    When 5회 연속 실패
    Then 서킷 상태가 OPEN으로 변경됨
      And 로그에 "Circuit open" 기록됨
```

### Scenario 4.3: Reject When Open

```gherkin
  Scenario: Open 상태에서 거부
    Given CircuitBreaker가 OPEN 상태임
    When 함수 호출 시도
    Then CircuitOpenError가 즉시 발생함
      And 실제 함수가 호출되지 않음
```

### Scenario 4.4: Half-Open After Timeout

```gherkin
  Scenario: 타임아웃 후 Half-Open
    Given CircuitBreaker가 OPEN 상태임
      And 복구 타임아웃이 60초임
    When 60초 대기
    Then 서킷 상태가 HALF_OPEN으로 변경됨
```

### Scenario 4.5: Close on Success in Half-Open

```gherkin
  Scenario: Half-Open에서 성공 시 Close
    Given CircuitBreaker가 HALF_OPEN 상태임
    When 함수 호출 성공
    Then 서킷 상태가 CLOSED로 변경됨
      And consecutive_failures가 0으로 리셋됨
```

### Scenario 4.6: Reopen on Failure in Half-Open

```gherkin
  Scenario: Half-Open에서 실패 시 Reopen
    Given CircuitBreaker가 HALF_OPEN 상태임
    When 함수 호출 실패
    Then 서킷 상태가 OPEN으로 변경됨
```

---

## Feature 5: Protected API Client

### Scenario 5.1: Full Protection Stack

```gherkin
Feature: 보호된 API 클라이언트 (Protected API Client)

  Scenario: 전체 보호 스택
    Given ProtectedAPIClient가 구성됨
    When API 호출
    Then 다음 순서로 실행됨:
      1. Circuit breaker 확인 (OPEN이면 거부)
      2. Rate limiter 토큰 획득
      3. Retry handler로 실행
      4. 결과 반환 또는 에러 발생
```

### Scenario 5.2: Rate Limited

```gherkin
  Scenario: 속도 제한 적용
    Given API 속도 제한에 도달함
    When ProtectedAPIClient.call() 호출
    Then 요청이 대기하거나 거부됨
      And 실제 API 호출이 지연됨
```

### Scenario 5.3: Circuit Open

```gherkin
  Scenario: 서킷 오픈 상태
    Given CircuitBreaker가 OPEN 상태임
    When ProtectedAPIClient.call() 호출
    Then CircuitOpenError가 즉시 발생함
      And Rate limiter 체크하지 않음
      And 실제 API 호출하지 않음
```

---

## Feature 6: Statistics and Monitoring

### Scenario 6.1: Rate Limit Stats

```gherkin
Feature: 통계 및 모니터링 (Statistics and Monitoring)

  Scenario: 속도 제한 통계
    Given RateLimiter가 활성화됨
      And 100회 요청 중 10회가 거부됨
    When RateLimiter.get_stats() 호출
    Then 다음 통계가 반환됨:
      | total_requests     | 100 |
      | rejected_requests  | 10  |
      | current_tokens     | >0  |
```

### Scenario 6.2: Circuit Breaker Stats

```gherkin
  Scenario: 서킷 브레이커 통계
    Given CircuitBreaker가 활성화됨
      And 3회 연속 실패 발생
    When 상태 확인
    Then consecutive_failures = 3
      And state = CLOSED (임계값 미달)
```

---

## Feature 7: Integration with API Clients

### Scenario 7.1: OpenAI Client Protection

```gherkin
Feature: API 클라이언트 통합 (API Client Integration)

  Scenario: OpenAI 클라이언트 보호
    Given GLMClient가 ProtectedAPIClient로 래핑됨
    When chat completion 요청
    Then 속도 제한이 적용됨
      And 재시도 로직이 활성화됨
      And 서킷 브레이커가 보호함
```

### Scenario 7.2: Upbit Client Protection

```gherkin
  Scenario: Upbit 클라이언트 보호
    Given UpbitClient가 ProtectedAPIClient로 래핑됨
    When 시세 조회 요청
    Then 초당 10회, 분당 600회 제한 적용됨
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
      And TokenBucket 커버리지 = 100%
      And CircuitBreaker 커버리지 >= 95%
      And RetryHandler 커버리지 >= 95%
```

### Performance

```gherkin
Feature: 성능 기준

  Scenario: 속도 제한 확인 성능
    Given RateLimiter가 활성화됨
    When acquire() 호출
    Then 응답 시간 < 1ms
```

### Thread Safety

```gherkin
Feature: 스레드 안전성

  Scenario: 동시 접근
    Given 10개의 동시 요청
    When 모든 요청이 동시에 acquire() 호출
    Then 경쟁 조건 없이 올바르게 처리됨
      And 토큰이 음수가 되지 않음
```

---

## Definition of Done

- [ ] 모든 Gherkin 시나리오에 대한 테스트 구현
- [ ] 테스트 커버리지 85% 이상 달성
- [ ] TokenBucket 구현 완료
- [ ] RateLimiter 구현 완료
- [ ] CircuitBreaker 구현 완료
- [ ] RetryHandler 구현 완료
- [ ] ProtectedAPIClient 구현 완료
- [ ] GLMClient 통합 완료
- [ ] UpbitClient 통합 완료
- [ ] Lint 에러 0개
- [ ] Type checking 에러 0개
- [ ] 문서화 완료 (docstrings)

---

Version: 1.0.0
Last Updated: 2026-03-05
Author: MoAI SPEC Builder
