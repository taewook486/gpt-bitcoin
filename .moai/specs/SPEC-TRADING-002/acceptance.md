# Acceptance Criteria: SPEC-TRADING-002 (Trading History)

## Overview

이 문서는 SPEC-TRADING-002 거래 내역 기능의 수락 기준을 Gherkin 형식(Given-When-Then)으로 정의합니다.

---

## Feature 1: Trade Result Persistence

### Scenario 1.1: Save Successful Trade

```gherkin
Feature: 거래 결과 저장 (Trade Result Persistence)

  Scenario: 성공한 거래 저장
    Given TradingService가 성공적으로 거래를 실행하고 TradeResult를 반환함
      And TradeResult.success = True
      And TradeResult.order_id = "uuid-1234"
    When TradeHistoryService.save_trade_result() 호출
    Then 데이터베이스에 새 레코드가 생성됨
      And 레코드의 order_uuid는 "uuid-1234"임
      And 레코드의 ticker, side, executed_price가 TradeResult와 일치함
```

### Scenario 1.2: Don't Save Failed Trade

```gherkin
  Scenario: 실패한 거래는 저장하지 않음
    Given TradingService가 거래 실행에 실패하고 TradeResult를 반환함
      And TradeResult.success = False
      And TradeResult.error_message = "잔액 부족"
    When TradeHistoryService.save_trade_result() 호출
    Then 데이터베이스에 새 레코드가 생성되지 않음
      And 반환값은 -1임
```

### Scenario 1.3: Handle Duplicate Order UUID

```gherkin
  Scenario: 중복 주문 ID 처리
    Given 데이터베이스에 order_uuid = "uuid-1234"인 레코드가 존재함
    When 동일한 order_uuid로 새 레코드 저장 시도
    Then 새 레코드가 생성되지 않음
      And 에러가 발생하지 않음
      And 로그에 경고 메시지가 기록됨
```

---

## Feature 2: Trade History Query

### Scenario 2.1: Query All Trades

```gherkin
Feature: 거래 내역 조회 (Trade History Query)

  Scenario: 모든 거래 조회
    Given 데이터베이스에 100개의 거래 레코드가 존재함
    When TradeHistoryService.get_trades()를 필터 없이 호출
    Then 최대 100개의 레코드가 반환됨
      And 레코드는 timestamp 내림차순으로 정렬됨
      And 가장 최근 거래가 첫 번째임
```

### Scenario 2.2: Query by Ticker

```gherkin
  Scenario: 코인별 조회
    Given 데이터베이스에 다양한 코인의 거래 레코드가 존재함
      And KRW-BTC 거래가 30개임
      And KRW-ETH 거래가 20개임
    When TradeHistoryService.get_trades(ticker="KRW-BTC") 호출
    Then 30개의 레코드가 반환됨
      And 모든 레코드의 ticker가 "KRW-BTC"임
```

### Scenario 2.3: Query by Date Range

```gherkin
  Scenario: 날짜 범위로 조회
    Given 데이터베이스에 2026년 1월~3월 거래가 존재함
    When TradeHistoryService.get_trades(start_date="2026-03-01", end_date="2026-03-05") 호출
    Then 2026-03-01 ~ 2026-03-05 사이의 거래만 반환됨
      And 범위 밖의 거래는 포함되지 않음
```

### Scenario 2.4: Query by Side

```gherkin
  Scenario: 매수/매도 구분 조회
    Given 데이터베이스에 매수 40개, 매도 30개가 존재함
    When TradeHistoryService.get_trades(side="buy") 호출
    Then 40개의 레코드가 반환됨
      And 모든 레코드의 side가 "buy"임
```

### Scenario 2.5: Combined Filters

```gherkin
  Scenario: 복합 필터 조회
    Given 데이터베이스에 다양한 조건의 거래가 존재함
    When TradeHistoryService.get_trades(
        ticker="KRW-BTC",
        side="sell",
        start_date="2026-03-01",
        end_date="2026-03-31"
    ) 호출
    Then 모든 필터 조건을 만족하는 거래만 반환됨
      And ticker = "KRW-BTC"
      And side = "sell"
      And timestamp가 3월 1일~31일 사이
```

### Scenario 2.6: Pagination

```gherkin
  Scenario: 페이지네이션
    Given 데이터베이스에 150개의 거래가 존재함
    When TradeHistoryService.get_trades(limit=50, offset=0) 호출 (1페이지)
    Then 50개의 레코드가 반환됨
    When TradeHistoryService.get_trades(limit=50, offset=50) 호출 (2페이지)
    Then 다음 50개의 레코드가 반환됨
      And 1페이지와 중복되지 않음
```

### Scenario 2.7: Empty Result

```gherkin
  Scenario: 조회 결과 없음
    Given 데이터베이스에 KRW-XRP 거래가 없음
    When TradeHistoryService.get_trades(ticker="KRW-XRP") 호출
    Then 빈 리스트가 반환됨 []
      And 에러가 발생하지 않음
```

---

## Feature 3: Web UI Trade History Tab

### Scenario 3.1: Display Trade History Tab

```gherkin
Feature: Web UI 거래 내역 탭

  Scenario: 거래 내역 탭 표시
    Given 사용자가 Web UI에 접속함
    When "거래 내역 (Trade History)" 탭 클릭
    Then 거래 내역 테이블이 표시됨
      And 필터 컨트롤이 표시됨 (코인, 구분, 날짜)
      And 페이지네이션 컨트롤이 표시됨
```

### Scenario 3.2: Apply Filters in UI

```gherkin
  Scenario: UI에서 필터 적용
    Given 거래 내역 탭이 열려 있음
    When 사용자가 코인을 "KRW-BTC"로 선택
      And "조회" 버튼 클릭
    Then KRW-BTC 거래만 테이블에 표시됨
```

### Scenario 3.3: Empty State Display

```gherkin
  Scenario: 거래 내역 없음 표시
    Given 데이터베이스에 거래가 없음
    When 사용자가 거래 내역 탭 열람
    Then "거래 내역이 없습니다" 메시지가 표시됨
      And 빈 테이블이 표시됨
```

### Scenario 3.4: Navigate Pages

```gherkin
  Scenario: 페이지 이동
    Given 150개의 거래가 있고 페이지당 50개 표시
    When 사용자가 "다음" 버튼 클릭
    Then 2페이지 거래가 표시됨
      And "2 / 3" 페이지 정보가 표시됨
```

---

## Feature 4: CSV Export

### Scenario 4.1: Export to CSV

```gherkin
Feature: CSV 내보내기

  Scenario: 전체 거래 CSV 내보내기
    Given 데이터베이스에 50개의 거래가 존재함
    When 사용자가 "CSV 내보내기" 버튼 클릭
    Then CSV 파일이 다운로드됨
      And 파일명이 "trading_history_YYYYMMDD_HHMMSS.csv" 형식임
      And 파일에 50행의 데이터가 포함됨
      And 헤더가 한국어/영어 이중 표기됨
```

### Scenario 4.2: Export Filtered Results

```gherkin
  Scenario: 필터링된 결과 내보내기
    Given 사용자가 KRW-BTC로 필터링하여 30개 조회
    When 사용자가 "CSV 내보내기" 버튼 클릭
    Then CSV 파일에 30행의 KRW-BTC 데이터만 포함됨
```

### Scenario 4.3: CSV Format Validation

```gherkin
  Scenario: CSV 형식 검증
    Given 내보낸 CSV 파일이 존재함
    When 파일을 pandas로 읽음
    Then 다음 컬럼이 존재함:
      | Column       | Korean Header    |
      | order_uuid   | 주문ID (Order ID)|
      | ticker       | 코인 (Ticker)    |
      | side         | 구분 (Side)      |
      | executed_price| 체결가 (Price)  |
      | executed_quantity| 수량 (Qty)   |
      | fee          | 수수료 (Fee)     |
      | timestamp    | 일시 (Timestamp) |
```

---

## Feature 5: Profit/Loss Calculation

### Scenario 5.1: Calculate Realized P/L

```gherkin
Feature: 수익/손실 계산

  Scenario: 실현 수익 계산
    Given 다음 거래가 존재함:
      | Side | Quantity | Price  | Fee  |
      | buy  | 0.001    | 50,000 | 0.025|
      | sell | 0.001    | 55,000 | 0.027|
    When TradeHistoryService.calculate_profit_loss("KRW-BTC") 호출
    Then 다음 결과가 반환됨:
      | total_buy_krw  | 50,000    |
      | total_sell_krw | 55,000    |
      | total_fees     | 0.052     |
      | realized_pl    | 4,999.948 |
      | unrealized_qty | 0         |
```

### Scenario 5.2: FIFO Matching

```gherkin
  Scenario: FIFO 매칭
    Given 다음 거래가 존재함:
      | Order | Side | Quantity | Price  |
      | 1     | buy  | 0.002    | 50,000 |
      | 2     | buy  | 0.001    | 52,000 |
      | 3     | sell | 0.002    | 55,000 |
    When P/L 계산 실행
    Then 매도 0.002는 매수 1의 0.002와 매칭됨 (FIFO)
      And realized_pl = (55,000 - 50,000) * 0.002 - fees
```

### Scenario 5.3: Partial Sell

```gherkin
  Scenario: 부분 매도 처리
    Given 다음 거래가 존재함:
      | Side | Quantity | Price  |
      | buy  | 0.003    | 50,000 |
      | sell | 0.001    | 55,000 |
    When P/L 계산 실행
    Then unrealized_quantity = 0.002
      And realized_pl는 0.001에 대해서만 계산됨
```

### Scenario 5.4: No Sells (Unrealized Only)

```gherkin
  Scenario: 매도 없음 (미실현만)
    Given 매수만 존재함:
      | Side | Quantity | Price  |
      | buy  | 0.001    | 50,000 |
    When P/L 계산 실행
    Then realized_pl = 0
      And unrealized_quantity = 0.001
```

---

## Feature 6: Error Handling

### Scenario 6.1: Database Connection Failure

```gherkin
Feature: 에러 처리

  Scenario: 데이터베이스 연결 실패
    Given trades.db 파일이 손상됨
    When 거래 내역 조회 시도
    Then 에러가 로그에 기록됨
      And 사용자에게 "데이터베이스 오류" 메시지 표시
      And 앱이 크래시되지 않음
```

### Scenario 6.2: Graceful Degradation on Save Failure

```gherkin
  Scenario: 저장 실패 시 정상 동작
    Given 데이터베이스에 쓰기 권한이 없음
    When TradeHistoryService.save_trade_result() 호출
    Then 에러가 로그에 기록됨
      And TradingService는 정상적으로 거래를 완료함
      And 사용자에게 저장 실패 알림 표시
```

---

## Feature 7: Immutability

### Scenario 7.1: No Update Allowed

```gherkin
Feature: 기록 불변성

  Scenario: 수정 불가
    Given 데이터베이스에 거래 레코드가 존재함
    When 직접 UPDATE SQL 실행 시도
    Then TradeRepository는 UPDATE 메서드를 제공하지 않음
      And 데이터베이스 제약조건으로 수정 차단
```

### Scenario 7.2: No Delete Allowed

```gherkin
  Scenario: 삭제 불가
    Given 데이터베이스에 거래 레코드가 존재함
    When TradeRepository를 통한 삭제 시도
    Then TradeRepository는 DELETE 메서드를 제공하지 않음
      And 에러가 발생하거나 무시됨
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
      And TradeHistoryService 커버리지 >= 90%
      And TradeRepository 커버리지 >= 95%
```

### Performance

```gherkin
Feature: 성능 기준

  Scenario: 조회 성능
    Given 데이터베이스에 1,000개의 레코드가 존재함
    When get_trades(limit=100) 호출
    Then 응답 시간 < 1초

  Scenario: 저장 성능
    Given 데이터베이스가 정상 작동함
    When save_trade_result() 호출
    Then 응답 시간 < 100ms
```

### Linting

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
- [ ] Web UI에 거래 내역 탭 추가 완료
- [ ] CSV 내보내기 기능 작동
- [ ] P/L 계산 기능 작동
- [ ] 모든 에러 시나리오에 대한 graceful handling
- [ ] Lint 에러 0개
- [ ] Type checking 에러 0개 (mypy/pyright)
- [ ] 문서화 완료 (docstrings, README 업데이트)

---

Version: 1.0.0
Last Updated: 2026-03-04
Author: MoAI SPEC Builder
