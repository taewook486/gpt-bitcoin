# Acceptance Criteria: SPEC-TRADING-003 (CLI Integration)

## Overview

이 문서는 SPEC-TRADING-003 CLI 실거래 연동 기능의 수락 기준을 Gherkin 형식(Given-When-Then)으로 정의합니다.

---

## Feature 1: Real Trade Execution via CLI

### Scenario 1.1: Execute Buy Order in Real Mode

```gherkin
Feature: CLI 실거래 실행

  Scenario: 실거래 모드에서 매수 주문 실행
    Given 사용자가 --trade-mode real 플래그로 실행함
      And TradingService가 초기화됨
    When AI 분석 결과가 "buy"이고 percentage가 50%임
      And 사용자가 승인 프롬프트에서 'y'를 입력함
    Then TradingService.request_buy_order()가 호출됨
      And TradeApproval이 생성됨
      And 사용자 승인 후 TradingService.execute_approved_trade()가 호출됨
      And TradeResult가 반환됨
      And 결과가 화면에 표시됨
```

### Scenario 1.2: Execute Sell Order in Real Mode

```gherkin
  Scenario: 실거래 모드에서 매도 주문 실행
    Given 사용자가 --trade-mode real 플래그로 실행함
      And 보유 코인이 존재함
    When AI 분석 결과가 "sell"이고 percentage가 30%임
      And 사용자가 승인 프롬프트에서 'y'를 입력함
    Then TradingService.request_sell_order()가 호출됨
      And 승인 후 execute_approved_trade()가 호출됨
      And 매도 결과가 화면에 표시됨
```

### Scenario 1.3: Simulation Mode Does Not Call Real API

```gherkin
  Scenario: 시뮬레이션 모드는 실제 API를 호출하지 않음
    Given 사용자가 --trade-mode simulation 또는 --dry-run으로 실행함
    When AI 분석 결과가 "buy"임
    Then TradingService가 호출되지 않음
      And "[시뮬레이션] 거래가 실행됩니다" 메시지가 표시됨
      And 실제 API 호출이 발생하지 않음
```

---

## Feature 2: Interactive Approval Workflow

### Scenario 2.1: Display Approval Prompt

```gherkin
Feature: 승인 워크플로우

  Scenario: 승인 프롬프트 표시
    Given TradeApproval이 생성됨
      | field            | value          |
      | ticker           | KRW-BTC        |
      | side             | buy            |
      | amount           | 100000 KRW     |
      | estimated_price  | 50000000 KRW   |
      | estimated_qty    | 0.002 BTC      |
      | fee_estimate     | 50 KRW         |
    When interactive_approval() 호출
    Then 다음 정보가 화면에 표시됨:
      | Display          | Korean         |
      | Side             | 구분: 매수     |
      | Ticker           | 코인: KRW-BTC  |
      | Amount           | 금액: 100,000 KRW|
      | Estimated Price  | 예상 체결가    |
      | Estimated Qty    | 예상 수량      |
      | Fee              | 예상 수수료    |
      And 승인/거부 프롬프트가 표시됨
```

### Scenario 2.2: User Approves Trade

```gherkin
  Scenario: 사용자가 거래 승인
    Given 승인 프롬프트가 표시됨
    When 사용자가 'y'를 입력함
    Then approval.mark_approved()가 호출됨
      And execute_approved_trade()가 호출됨
      And True가 반환됨
```

### Scenario 2.3: User Rejects Trade

```gherkin
  Scenario: 사용자가 거래 거부
    Given 승인 프롬프트가 표시됨
    When 사용자가 'n'을 입력함
    Then trading_service.cancel_pending_request()가 호출됨
      And "거래가 취소되었습니다" 메시지가 표시됨
      And False가 반환됨
```

### Scenario 2.4: User Cancels with Escape

```gherkin
  Scenario: 사용자가 Esc로 취소
    Given 승인 프롬프트가 표시됨
    When 사용자가 'q'를 입력하거나 Esc를 누름
    Then cancel_pending_request()가 호출됨
      And False가 반환됨
```

### Scenario 2.5: Ctrl-C Handling

```gherkin
  Scenario: Ctrl-C로 인터럽트
    Given 승인 프롬프트가 대기 중임
    When 사용자가 Ctrl-C를 누름
    Then KeyboardInterrupt가 catch됨
      And cancel_pending_request()가 호출됨
      And "사용자가 취소했습니다" 메시지가 표시됨
      And False가 반환됨
      And 프로그램이 안전하게 종료됨
```

### Scenario 2.6: Approval Timeout

```gherkin
  Scenario: 승인 타임아웃
    Given 승인 프롬프트가 표시됨
      And timeout이 30초로 설정됨
    When 사용자가 30초 동안 입력하지 않음
    Then "승인 시간이 만료되었습니다" 메시지가 표시됨
      And cancel_pending_request()가 호출됨
      And False가 반환됨
```

### Scenario 2.7: Expired Approval Auto-Reject

```gherkin
  Scenario: 만료된 승인 요청 자동 거부
    Given TradeApproval.expires_at이 과거 시간임
    When interactive_approval() 호출
    Then "승인 요청이 이미 만료되었습니다" 메시지가 표시됨
      And False가 반환됨
      And 사용자 입력을 기다리지 않음
```

---

## Feature 3: Manual Trading Commands

### Scenario 3.1: Manual Buy Command

```gherkin
Feature: 수동 거래 명령

  Scenario: 수동 매수 명령
    Given 사용자가 다음 인자로 실행함:
      | Argument  | Value     |
      | --buy     | KRW-BTC   |
      | --amount  | 50000     |
    When run_trading_session() 실행
    Then AI 분석을 건너뜀
      And request_buy_order("KRW-BTC", 50000)가 호출됨
      And 승인 프롬프트가 표시됨
```

### Scenario 3.2: Manual Sell Command

```gherkin
  Scenario: 수동 매도 명령
    Given 사용자가 다음 인자로 실행함:
      | Argument   | Value     |
      | --sell    | KRW-BTC   |
      | --quantity| 0.001     |
    When run_trading_session() 실행
    Then AI 분석을 건너뜀
      And request_sell_order("KRW-BTC", 0.001)가 호출됨
      And 승인 프롬프트가 표시됨
```

### Scenario 3.3: Manual Buy Missing Amount

```gherkin
  Scenario: 매수 명령에 금액 누락
    Given 사용자가 --buy KRW-BTC만 입력함 (--amount 누락)
    When run_trading_session() 실행
    Then "오류: --amount가 필요합니다" 메시지가 표시됨
      And 거래가 실행되지 않음
```

### Scenario 3.4: Manual Sell Missing Quantity

```gherkin
  Scenario: 매도 명령에 수량 누락
    Given 사용자가 --sell KRW-BTC만 입력함 (--quantity 누락)
    When run_trading_session() 실행
    Then "오류: --quantity가 필요합니다" 메시지가 표시됨
      And 거래가 실행되지 않음
```

---

## Feature 4: Auto-Approve Mode

### Scenario 4.1: Auto-Approve Bypasses Prompt

```gherkin
Feature: 자동 승인 모드

  Scenario: 자동 승인으로 프롬프트 건너뜀
    Given 사용자가 --auto-approve 플래그를 사용함
    When 거래 요청이 생성됨
    Then 승인 프롬프트가 표시되지 않음
      And "⚠️ 자동 승인 모드" 경고가 표시됨
      And 즉시 execute_approved_trade()가 호출됨
```

### Scenario 4.2: Auto-Approve Warning Display

```gherkin
  Scenario: 자동 승인 모드 경고
    Given --auto-approve 플래그가 설정됨
    When 거래 실행 시작
    Then 눈에 띄는 경고 메시지가 표시됨:
      "⚠️ 자동 승인 모드 - 사용자 확인 없이 실행"
```

---

## Feature 5: Result Display

### Scenario 5.1: Display Success Result

```gherkin
Feature: 결과 표시

  Scenario: 성공 결과 표시
    Given TradeResult.success = True
      | field            | value        |
      | order_id         | uuid-1234    |
      | ticker           | KRW-BTC      |
      | side             | buy          |
      | executed_price   | 50000000     |
      | executed_amount  | 0.001        |
      | fee              | 25           |
    When _display_result() 호출
    Then 녹색 테두리의 성공 패널이 표시됨
      And "주문 완료" 제목이 표시됨
      And 모든 필드가 포맷팅되어 표시됨
```

### Scenario 5.2: Display Failure Result

```gherkin
  Scenario: 실패 결과 표시
    Given TradeResult.success = False
      | field          | value       |
      | ticker         | KRW-BTC     |
      | side           | buy         |
      | error_message  | 잔액 부족   |
    When _display_result() 호출
    Then 빨간색 테두리의 실패 패널이 표시됨
      And "주문 실패" 제목이 표시됨
      And 오류 메시지가 포함됨
```

---

## Feature 6: Error Handling

### Scenario 6.1: TradingService Exception

```gherkin
Feature: 에러 처리

  Scenario: TradingService 예외 처리
    Given TradingService가 ValueError를 발생시킴
      And 에러 메시지가 "잔액 부족"임
    When 거래 실행 시도
    Then 에러가 catch됨
      And "거래 요청 실패: 잔액 부족" 메시지가 표시됨
      And 프로그램이 종료되지 않음
```

### Scenario 6.2: Upbit API Error

```gherkin
  Scenario: Upbit API 에러 처리
    Given UpbitClient가 UpbitAPIError를 발생시킴
    When execute_approved_trade() 호출
    Then TradeResult.success = False로 반환됨
      And error_message에 에러 내용이 포함됨
      And 실패 결과가 표시됨
```

### Scenario 6.3: Concurrent Trade Prevention

```gherkin
  Scenario: 동시 거래 방지
    Given TradingService.state = PENDING_APPROVAL
    When 새로운 거래 요청 시도
    Then "이미 진행 중인 거래가 있습니다" 경고가 표시됨
      And 새 거래 요청이 거부됨
```

---

## Feature 7: Backward Compatibility

### Scenario 7.1: --dry-run Alias

```gherkin
Feature: 하위 호환성

  Scenario: --dry-run 플래그 호환
    Given 사용자가 --dry-run 플래그를 사용함
    When run_trading_session() 실행
    Then --trade-mode simulation으로 처리됨
      And 시뮬레이션 모드로 동작함
```

### Scenario 7.2: Default to Simulation

```gherkin
  Scenario: 기본값은 시뮬레이션
    Given --trade-mode 플래그가 지정되지 않음
    When run_trading_session() 실행
    Then simulation 모드로 동작함
      And 실제 거래가 실행되지 않음
```

---

## Quality Gates

### Test Coverage

```gherkin
Feature: 테스트 커버리지

  Scenario: 최소 커버리지 달성
    Given 모든 테스트가 작성됨
    When pytest --cov 실행
    Then 새로운 코드 커버리지 >= 85%
      And approval workflow 커버리지 >= 90%
```

### Performance

```gherkin
Feature: 성능 기준

  Scenario: 승인 프롬프트 응답
    Given 승인 프롬프트가 표시됨
    When 사용자가 입력함
    Then 응답 시간 < 100ms
```

### Linting

```gherkin
Feature: 코드 품질

  Scenario: 린터 통과
    Given 모든 코드가 작성됨
    When ruff check 실행
    Then 에러 0개
```

---

## Definition of Done

- [ ] 모든 Gherkin 시나리오에 대한 테스트 구현
- [ ] 테스트 커버리지 85% 이상 달성
- [ ] AI 기반 거래 실행 with 승인 워크플로우
- [ ] 수동 매수/매도 명령 작동
- [ ] 시뮬레이션/실거래 모드 전환
- [ ] Ctrl-C 안전 처리
- [ ] Lint 에러 0개
- [ ] Type checking 에러 0개
- [ ] 하위 호환성 유지 (--dry-run)

---

Version: 1.0.0
Last Updated: 2026-03-04
Author: MoAI SPEC Builder
