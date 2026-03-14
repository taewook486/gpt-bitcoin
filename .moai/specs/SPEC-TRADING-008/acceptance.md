# Acceptance Criteria: SPEC-TRADING-008 (Portfolio Analytics Dashboard)

## Overview

이 문서는 SPEC-TRADING-008 포트폴리오 분석 대시보드 기능의 수락 기준을 Gherkin 형식(Given-When-Then)으로 정의합니다.

---

## Feature 1: Portfolio Metrics Calculation

### Scenario 1.1: Calculate Total Value

```gherkin
Feature: 포트폴리오 지표 계산 (Portfolio Metrics Calculation)

  Scenario: 총 포트폴리오 가치 계산
    Given 사용자가 다음 자산을 보유함:
      | Ticker | Quantity | Current Price |
      | BTC    | 0.1      | 50,000,000    |
      | ETH    | 1.0      | 3,000,000     |
      And KRW 잔액이 1,000,000임
    When PortfolioAnalyticsService.calculate_metrics() 호출
    Then total_value_krw는 9,000,000임 (0.1*50M + 1.0*3M + 1M)
```

### Scenario 1.2: Calculate ROI

```gherkin
  Scenario: ROI 계산
    Given 총 투자금(total_invested)이 8,000,000 KRW임
      And 현재 포트폴리오 가치가 9,000,000 KRW임
    When ROI 계산
    Then total_roi_percent는 +12.5%임
      And 계산식: ((9M - 8M) / 8M) * 100
```

### Scenario 1.3: Calculate Win Rate

```gherkin
  Scenario: 승률 계산
    Given 매도 거래가 10건 있음
      And 그 중 6건이 수익, 4건이 손실임
    When 승률 계산
    Then win_rate_percent는 60%임
      And winning_trades는 6임
      And losing_trades는 4임
```

### Scenario 1.4: Handle No Trades

```gherkin
  Scenario: 거래 없음 처리
    Given 사용자의 거래 내역이 없음
    When calculate_metrics() 호출
    Then 다음 기본값이 반환됨:
      | Metric            | Value |
      | total_trades      | 0     |
      | total_value_krw   | 0     |
      | total_roi_percent | 0     |
      | win_rate_percent  | 0     |
```

### Scenario 1.5: Division by Zero Protection

```gherkin
  Scenario: 0으로 나누기 방지
    Given total_invested가 0임 (매수만 있고 매도가 없음)
    When ROI 계산
    Then total_roi_percent는 0 또는 N/A로 표시됨
      And ZeroDivisionError가 발생하지 않음
```

---

## Feature 2: Current Holdings

### Scenario 2.1: Get Holdings with Live Prices

```gherkin
Feature: 현재 보유 자산 (Current Holdings)

  Scenario: 실시간 가격으로 보유 자산 조회
    Given 사용자가 KRW-BTC 0.05를 평균 50,000,000 KRW에 매수함
      And 현재 BTC 가격이 55,000,000 KRW임
    When get_current_holdings() 호출
    Then 다음 AssetHolding이 반환됨:
      | Field               | Value           |
      | ticker              | KRW-BTC         |
      | quantity            | 0.05            |
      | average_buy_price   | 50,000,000      |
      | current_price       | 55,000,000      |
      | current_value_krw   | 2,750,000       |
      | unrealized_pl_krw   | +250,000        |
      | unrealized_pl_percent| +5%            |
```

### Scenario 2.2: Sort Holdings by Value

```gherkin
  Scenario: 가치 순 정렬
    Given 사용자가 다음 자산을 보유함:
      | Ticker | Value      |
      | ETH    | 3,000,000  |
      | BTC    | 5,000,000  |
      | XRP    | 500,000    |
    When get_current_holdings() 호출
    Then 반환 순서가 다음과 같음:
      | Order | Ticker |
      | 1     | BTC    |
      | 2     | ETH    |
      | 3     | XRP    |
```

---

## Feature 3: Dashboard Display

### Scenario 3.1: Display Overview Cards

```gherkin
Feature: 대시보드 표시 (Dashboard Display)

  Scenario: 개요 카드 표시
    Given 사용자가 포트폴리오 탭을 열음
    Then 다음 카드가 표시됨:
      | Card         | Content              |
      | Total Value  | 9,000,000 KRW (+12%) |
      | Realized P/L | +500,000 KRW         |
      | Unrealized P/L| +400,000 KRW        |
```

### Scenario 3.2: Display Holdings Table

```gherkin
  Scenario: 보유 자산 테이블 표시
    Given 사용자가 포트폴리오 탭을 열음
    Then 보유 자산 테이블이 표시됨
      And 컬럼: Ticker, Quantity, Avg Price, Current, P/L, %
      And 각 자산의 정보가 행으로 표시됨
```

### Scenario 3.3: Empty State

```gherkin
  Scenario: 빈 상태 표시
    Given 사용자의 거래 내역이 없음
    When 포트폴리오 탭 열람
    Then "아직 거래 내역이 없습니다" 메시지 표시
      And "거래를 시작하면 분석 데이터가 표시됩니다" 안내 표시
      And 차트 영역이 비활성화됨
```

---

## Feature 4: Performance Charts

### Scenario 4.1: Cumulative P/L Chart

```gherkin
Feature: 성과 차트 (Performance Charts)

  Scenario: 누적 손익 차트
    Given 사용자가 지난 30일간 거래함
    When "30D" 기간 선택
    Then 누적 P/L 라인 차트가 표시됨
      And X축은 날짜
      And Y축은 포트폴리오 가치 (KRW)
      And 거래 발생 지점이 마커로 표시됨
```

### Scenario 4.2: Period Filter

```gherkin
  Scenario: 기간 필터
    Given 대시보드가 표시됨
    When "7D" 버튼 클릭
    Then 지난 7일 데이터만 표시됨
      And 모든 차트가 업데이트됨
      And 지표가 해당 기간으로 재계산됨
```

### Scenario 4.3: Chart Interactivity

```gherkin
  Scenario: 차트 인터랙션
    Given 누적 P/L 차트가 표시됨
    When 마우스를 차트 위에 올림
    Then 해당 지점의 날짜와 값이 툴팁으로 표시됨
    When 차트 영역을 드래그
    Then 해당 영역이 확대됨
```

---

## Feature 5: Real-time Updates

### Scenario 5.1: Price Update Refresh

```gherkin
Feature: 실시간 업데이트 (Real-time Updates)

  Scenario: 가격 업데이트 시 새로고침
    Given 대시보드가 표시됨
      And "Last Updated: 12:00" 표시됨
    When 30초 후 가격 업데이트 발생
    Then 포트폴리오 가치가 재계산됨
      And "Last Updated: 12:00:30"으로 갱신됨
      And 페이지 전체 새로고침 없음 (부분 업데이트)
```

### Scenario 5.2: Price Change Indicator

```gherkin
  Scenario: 가격 변동 표시
    Given BTC 보유 중이고 가격이 50,000,000 KRW임
    When 가격이 51,000,000 KRW로 상승
    Then Total Value 카드에 상승 표시 (+녹색)
      And Unrealized P/L이 증가함
```

---

## Feature 6: Trade Statistics

### Scenario 6.1: Statistics Grid

```gherkin
Feature: 거래 통계 (Trade Statistics)

  Scenario: 통계 그리드 표시
    Given 대시보드가 표시됨
    Then 다음 통계가 표시됨:
      | Statistic    | Value         |
      | Win Rate     | 65%           |
      | Avg Win      | +50,000 KRW   |
      | Avg Loss     | -30,000 KRW   |
      | Largest Win  | +200,000 KRW  |
      | Largest Loss | -100,000 KRW  |
```

### Scenario 6.2: Trade Count

```gherkin
  Scenario: 거래 횟수 표시
    Given 총 50건 거래 (30 매수, 20 매도)
    When 대시보드 표시
    Then total_trades = 50
      And buy_trades = 30
      And sell_trades = 20
```

---

## Feature 7: Trade Distribution

### Scenario 7.1: Heatmap Display

```gherkin
Feature: 거래 분포 (Trade Distribution)

  Scenario: 히트맵 표시
    Given 사용자가 다양한 시간에 거래함
    When 대시보드 열람
    Then 거래 분포 히트맵이 표시됨
      And X축은 시간 (0-23)
      And Y축은 요일 (Mon-Sun)
      And 색상 강도는 거래 횟수
```

### Scenario 7.2: Distribution Summary

```gherkin
  Scenario: 분포 요약
    Given 거래가 다음과 같이 분포됨:
      | Day   | Hour | Count |
      | Mon   | 9    | 10    |
      | Wed   | 14   | 8     |
    When 분포 분석
    Then by_day_of_week[0] = 10 (Monday)
      And by_hour[9] = 10 (9 AM)
```

---

## Feature 8: Performance

### Scenario 8.1: Dashboard Load Time

```gherkin
Feature: 성능 (Performance)

  Scenario: 대시보드 로딩 시간
    Given 1,000건의 거래 내역이 있음
    When 포트폴리오 탭 열람
    Then 로딩이 3초 이내에 완료됨
      And 로딩 스피너가 표시됨
```

### Scenario 8.2: Large Dataset Handling

```gherkin
  Scenario: 대용량 데이터 처리
    Given 10,000건의 거래 내역이 있음
    When calculate_metrics() 호출
    Then 처리가 5초 이내에 완료됨
      And 메모리 사용량이 100MB 이하임
```

### Scenario 8.3: Chart Aggregation

```gherkin
  Scenario: 차트 데이터 집계
    Given 1년치 거래 데이터 (365일 x 10건 = 3,650건)
    When 1년 차트 렌더링
    Then 데이터가 일별로 집계됨
      And 차트 포인트가 365개 이하임
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
      And PortfolioAnalyticsService 커버리지 >= 90%
      And 데이터 모델 커버리지 = 100%
```

### Accuracy

```gherkin
Feature: 계산 정확성

  Scenario: 수익률 계산 검증
    Given 수동 계산 결과:
      | 투자금    | 1,000,000 KRW |
      | 현재 가치 | 1,100,000 KRW |
      | 예상 ROI  | 10%           |
    When 시스템 계산
    Then 결과가 수동 계산과 일치함 (소수점 2자리까지)
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
- [ ] Web UI에 포트폴리오 탭 추가 완료
- [ ] 모든 차트가 정상 렌더링됨
- [ ] 실시간 가격 업데이트 작동
- [ ] 계산 정확성 검증 완료
- [ ] 대시보드 로딩 3초 이내
- [ ] Lint 에러 0개
- [ ] Type checking 에러 0개
- [ ] 문서화 완료 (docstrings)

---

Version: 1.0.0
Last Updated: 2026-03-05
Author: MoAI SPEC Builder
