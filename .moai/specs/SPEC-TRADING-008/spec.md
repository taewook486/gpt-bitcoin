# SPEC-TRADING-008: Portfolio Analytics Dashboard

## Metadata

- **SPEC ID**: SPEC-TRADING-008
- **Title**: Portfolio Analytics Dashboard (포트폴리오 분석 대시보드)
- **Created**: 2026-03-05
- **Status**: Completed
- **Priority**: Medium
- **Depends On**: SPEC-TRADING-002 (TradeHistoryService), SPEC-TRADING-001 (TradingService)
- **Lifecycle Level**: spec-first

---

## Problem Analysis

### Current State

SPEC-TRADING-002에서 TradeHistoryService가 거래 내역 저장 및 FIFO P/L 계산 기능을 제공합니다. 그러나 사용자에게 포트폴리오 현황을 시각화하는 기능이 없어 다음과 같은 문제가 발생합니다:

1. **실시간 포트폴리오 가치 확인 불가**: 현재 보유 자산의 총 가치를 한눈에 볼 수 없음
2. **성과 분석 부재**: ROI, 승률, 수익/손실 추이 등 투자 성과 분석 불가
3. **과거 데이터 시각화 없음**: 시계열 차트를 통한 성과 변화 추이 파악 불가
4. **거래 내역 시각화 미지원**: 거래 패턴, 빈도 등을 그래픽으로 확인 불가

### Root Cause Analysis (Five Whys)

1. **Why?** 포트폴리오 분석 및 시각화 UI가 구현되지 않음
2. **Why?** TradeHistoryService는 데이터 제공만 담당, UI 레이어 미구현
3. **Why?** 초기 구현에서 데이터 저장에 집중, 사용자 경험 레이어 제외
4. **Why?** 분석 및 시각화 기능이 별도 SPEC으로 분리 필요
5. **Root Cause**: 데이터 시각화 및 분석 기능이 독립적인 UI 컴포넌트로 설계 필요

### Desired State

사용자가 Web UI에서 실시간 포트폴리오 가치, 성과 지표(ROI, 승률), 과거 성과 차트, 거래 내역 시각화를 확인할 수 있습니다.

---

## Environment

### Technology Stack

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Data Source | TradeHistoryService | SPEC-002 | 거래 데이터 제공 |
| Charts | Plotly | 5.18+ | 인터랙티브 차트 |
| UI | Streamlit | 1.30+ | 기존 Web UI 통합 |
| Data Processing | pandas | 2.2+ | 데이터 집계 및 분석 |
| Real-time | WebSocket/Polling | - | 실시간 가격 업데이트 |

### Integration Points

```
SPEC-TRADING-002 (TradeHistoryService)
        ↓ 거래 데이터
SPEC-TRADING-008 (PortfolioAnalytics)
        ↓ 분석 결과
    Plotly Charts
        ↓
    Web UI Dashboard Tab
        ↑
SPEC-TRADING-001 (TradingService/MockUpbitClient)
        (실시간 가격 데이터)
```

### Constraints

1. **Performance**: 대시보드 로딩 3초 이내 (최근 1년 데이터 기준)
2. **Real-time**: 가격 업데이트 30초 간격
3. **Data Volume**: 최대 10,000건 거래까지 지원
4. **Memory**: 차트 렌더링 메모리 100MB 이하

---

## Requirements (EARS Format)

### Ubiquitous Requirements

**REQ-ANALYTICS-001**: 시스템은 포트폴리오 총 가치를 실시간으로 계산해야 한다 (The system shall calculate total portfolio value in real-time).

```
The system shall calculate portfolio value:
- Sum of (quantity * current_price) for each held asset
- Include KRW cash balance
- Update on price changes (polling every 30 seconds)
```

**REQ-ANALYTICS-002**: 시스템은 성과 지표를 정확하게 계산해야 한다 (The system shall calculate performance metrics accurately).

```
The system shall calculate:
- Total ROI (%): (current_value - total_invested) / total_invested * 100
- Win Rate (%): winning_trades / total_closed_trades * 100
- Total P/L (KRW): sum of realized_profit_loss
- Average P/L per trade
```

### Event-Driven Requirements

**REQ-ANALYTICS-003**: WHEN 대시보드 탭이 열리면 THEN 시스템은 모든 분석 데이터를 로드해야 한다.

```
WHEN user navigates to "포트폴리오 (Portfolio)" tab
THEN the system shall:
    AND fetch all trade history from TradeHistoryService
    AND fetch current prices from UpbitClient
    AND calculate portfolio metrics
    AND render all charts
    AND display loading indicator during data fetch
```

**REQ-ANALYTICS-004**: WHEN 가격이 업데이트되면 THEN 시스템은 포트폴리오 가치를 재계산해야 한다.

```
WHEN price update received (every 30 seconds)
THEN the system shall:
    AND recalculate portfolio value
    AND update "Total Value" display
    AND update "Unrealized P/L" display
    AND NOT reload entire page (partial update)
```

### State-Driven Requirements

**REQ-ANALYTICS-005**: IF 거래 내역이 없으면 THEN 시스템은 빈 상태 메시지를 표시해야 한다.

```
IF TradeHistoryService.get_trades() returns empty list
THEN the system shall display:
    AND "아직 거래 내역이 없습니다" message
    AND "거래를 시작하면 분석 데이터가 표시됩니다" guidance
    AND Disable chart sections
```

**REQ-ANALYTICS-006**: IF 특정 기간 데이터만 선택되면 THEN 시스템은 해당 기간만 분석해야 한다.

```
IF user selects date range filter
THEN the system shall:
    AND filter trades by selected period
    AND recalculate all metrics for period only
    AND update charts with filtered data
    AND display "선택 기간" indicator
```

### Optional Requirements

**REQ-ANALYTICS-007**: Where possible, 시스템은 비트코인 가격 차트를 표시해야 한다.

```
Where possible, the system shall display BTC price chart:
- Candlestick chart with 1-day intervals
- Volume overlay
- 30-day, 90-day, 1-year period options
- Interactive zoom and pan
```

**REQ-ANALYTICS-008**: Where possible, 시스템은 거래 분포 히트맵을 제공해야 한다.

```
Where possible, the system shall provide trade heatmap:
- Day of week vs. Hour of day
- Color intensity by trade count
- Click to drill down to specific trades
```

### Unwanted Behavior Requirements

**REQ-ANALYTICS-009**: 시스템은 부정확한 계산을 표시해서는 안 된다 (The system shall not display inaccurate calculations).

```
The system shall NOT display:
- Division by zero results (show "N/A" instead)
- Incomplete data calculations (show loading/error)
- Stale prices without "last updated" timestamp

AND shall validate all inputs before calculation
```

**REQ-ANALYTICS-010**: 시스템은 과도한 메모리를 사용해서는 안 된다 (The system shall not consume excessive memory).

```
The system shall NOT:
- Load more than 10,000 trades into memory at once
- Render charts with more than 1,000 data points without aggregation
- Keep stale chart data in memory after tab switch

AND shall implement data pagination and aggregation
```

---

## Specifications

### Data Model

#### PortfolioMetrics

```python
@dataclass
class PortfolioMetrics:
    """Calculated portfolio metrics."""
    # Value Metrics
    total_value_krw: float  # Total portfolio value in KRW
    cash_balance_krw: float  # Available KRW
    holdings_value_krw: float  # Value of held assets
    total_invested_krw: float  # Total KRW invested (buy orders)

    # Performance Metrics
    total_roi_percent: float  # Return on Investment (%)
    realized_pl_krw: float  # Realized profit/loss
    unrealized_pl_krw: float  # Unrealized profit/loss
    win_rate_percent: float  # Percentage of winning trades

    # Trade Statistics
    total_trades: int  # Total number of trades
    buy_trades: int  # Number of buy orders
    sell_trades: int  # Number of sell orders
    winning_trades: int  # Trades with positive P/L
    losing_trades: int  # Trades with negative P/L

    # Averages
    avg_profit_per_winning_trade: float
    avg_loss_per_losing_trade: float
    largest_win: float
    largest_loss: float

    # Timestamps
    calculated_at: datetime
    period_start: datetime | None  # For filtered views
    period_end: datetime | None

@dataclass
class AssetHolding:
    """Current holding for a single asset."""
    ticker: str
    quantity: float
    average_buy_price: float
    current_price: float
    current_value_krw: float
    unrealized_pl_krw: float
    unrealized_pl_percent: float
```

#### ChartData

```python
@dataclass
class PortfolioValueHistory:
    """Time series of portfolio value."""
    timestamps: list[datetime]
    values_krw: list[float]
    benchmark_values: list[float] | None  # e.g., BTC-only comparison

@dataclass
class TradeDistribution:
    """Trade count by time period."""
    by_hour: dict[int, int]  # 0-23 -> count
    by_day_of_week: dict[int, int]  # 0-6 (Mon-Sun) -> count
    by_month: dict[str, int]  # "YYYY-MM" -> count
```

### Component Architecture

```
src/gpt_bitcoin/
├── domain/
│   ├── analytics.py (NEW)
│   │   ├── PortfolioMetrics (dataclass)
│   │   ├── AssetHolding (dataclass)
│   │   ├── ChartData (dataclass)
│   │   └── PortfolioAnalyticsService
│   ├── trade_history.py (existing - SPEC-002)
│   └── trading.py (existing - SPEC-001)
├── web_ui/
│   ├── __init__.py (NEW)
│   ├── dashboard.py (NEW)
│   │   ├── render_portfolio_overview()
│   │   ├── render_performance_charts()
│   │   └── render_trade_analysis()
│   └── charts.py (NEW)
└── web_ui.py (MODIFY - add Portfolio tab)
```

### Class Design

#### PortfolioAnalyticsService

```python
class PortfolioAnalyticsService:
    """
    Domain service for portfolio analytics calculation.

    Responsibilities:
    - Calculate portfolio metrics from trade history
    - Generate chart data for visualization
    - Track holdings and current values
    - Support time-period filtering

    @MX:NOTE: Depends on TradeHistoryService for data.
        Does NOT modify any data, only calculates.
    """

    def __init__(
        self,
        trade_history_service: TradeHistoryService,
        upbit_client: UpbitClient | MockUpbitClient,
    ):
        self._trade_history = trade_history_service
        self._upbit_client = upbit_client

    async def calculate_metrics(
        self,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> PortfolioMetrics:
        """
        Calculate all portfolio metrics.

        @MX:ANCHOR: Primary analytics calculation entry point.
            fan_in: 2+ (Web UI dashboard, API endpoint)
            @MX:REASON: Centralizes all portfolio calculations.
        """
        pass

    async def get_current_holdings(
        self,
        user_id: str,
    ) -> list[AssetHolding]:
        """
        Get current asset holdings with live prices.

        Returns holdings sorted by value (descending).
        """
        pass

    async def get_portfolio_value_history(
        self,
        user_id: str,
        period: Literal["7d", "30d", "90d", "1y"],
    ) -> PortfolioValueHistory:
        """
        Get portfolio value over time.

        Uses trade history to reconstruct past values.
        """
        pass

    async def get_trade_distribution(
        self,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> TradeDistribution:
        """
        Analyze trade timing patterns.
        """
        pass

    async def get_performance_chart_data(
        self,
        user_id: str,
        period: Literal["7d", "30d", "90d", "1y"],
    ) -> dict:
        """
        Generate data for performance charts.

        Returns dict with:
        - cumulative_pl: Cumulative P/L over time
        - trade_markers: Points where trades occurred
        - benchmark: BTC buy-and-hold comparison
        """
        pass
```

### UI Design (Web UI)

#### Portfolio Dashboard Tab Structure

```
+-----------------------------------------------------------------+
| [Portfolio Analytics]                    [Last Updated: 12:34]   |
+-----------------------------------------------------------------+
| Overview Cards:                                                  |
| +-----------------+ +-----------------+ +-----------------+      |
| | Total Value     | | Total P/L       | | ROI             |      |
| | 5,000,000 KRW   | | +500,000 KRW    | | +11.1%          |      |
| | [Unrealized]    | | [Realized]      | | [All Time]      |      |
| +-----------------+ +-----------------+ +-----------------+      |
+-----------------------------------------------------------------+
| Current Holdings:                                                |
| +--------------------------------------------------------+      |
| | Ticker | Quantity | Avg Price | Current | P/L      | %   |      |
| | BTC    | 0.05     | 50,000K   | 55,000K | +250,000 | +10%|      |
| | ETH    | 0.5      | 3,000K    | 3,200K  | +100,000 | +6% |      |
| +--------------------------------------------------------+      |
+-----------------------------------------------------------------+
| Performance Chart: [7D] [30D] [90D] [1Y]                        |
| +--------------------------------------------------------+      |
| | [Cumulative P/L Line Chart]                            |      |
| |   ^                                                    |      |
| | P/L      ____                                          |      |
| |   |    _/    \___                                      |      |
| |   |____________\___________________                    |      |
| |   +-------------------------------------> Time         |      |
| +--------------------------------------------------------+      |
+-----------------------------------------------------------------+
| Trade Statistics:                                                |
| +-----------------+ +-----------------+ +-----------------+      |
| | Win Rate        | | Avg Win         | | Avg Loss        |      |
| | 65%             | | +50,000 KRW     | | -30,000 KRW     |      |
| +-----------------+ +-----------------+ +-----------------+      |
+-----------------------------------------------------------------+
| Trade Distribution (Heatmap):                                    |
| +--------------------------------------------------------+      |
| | [Day of Week vs Hour of Day Heatmap]                   |      |
| +--------------------------------------------------------+      |
+-----------------------------------------------------------------+
```

---

## MX Tag Targets

### High Fan-In Functions (>= 3 callers)

| Function | Expected Fan-In | MX Tag Type | Location |
|----------|-----------------|-------------|----------|
| `PortfolioAnalyticsService.calculate_metrics()` | 2+ | @MX:ANCHOR | domain/analytics.py |
| `get_current_prices()` | 3+ | @MX:ANCHOR | upbit_client |

### Danger Zones (Complexity >= 15 or Critical Operations)

| Function | Risk | MX Tag Type | Reason |
|----------|------|-------------|--------|
| `calculate_metrics()` | Division by zero | @MX:WARN | Multiple division operations, zero handling |
| `get_portfolio_value_history()` | Data reconstruction | @MX:WARN | Complex time series reconstruction |
| Chart rendering | Memory | @MX:NOTE | Large datasets may cause memory issues |

---

## Files to Modify

### New Files

| File Path | Purpose | Lines (Est.) |
|-----------|---------|--------------|
| `src/gpt_bitcoin/domain/analytics.py` | PortfolioAnalyticsService, data models | ~250 |
| `src/gpt_bitcoin/web_ui/__init__.py` | Package init | ~10 |
| `src/gpt_bitcoin/web_ui/dashboard.py` | Dashboard components | ~300 |
| `src/gpt_bitcoin/web_ui/charts.py` | Chart rendering utilities | ~200 |
| `tests/unit/domain/test_analytics.py` | Unit tests | ~400 |
| `tests/unit/web_ui/test_dashboard.py` | Dashboard tests | ~200 |

### Modified Files

| File Path | Changes | Lines Changed (Est.) |
|-----------|---------|---------------------|
| `src/gpt_bitcoin/web_ui.py` | Add Portfolio Analytics tab | +50 |
| `src/gpt_bitcoin/dependencies/container.py` | Register PortfolioAnalyticsService | +10 |

---

## Risks and Mitigations

### Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Slow dashboard loading | Medium | Medium | Pagination, aggregation, caching |
| Inaccurate calculations | Low | High | Comprehensive unit tests, validation |
| Memory issues with large datasets | Medium | Medium | Data aggregation, lazy loading |
| Stale price data | Medium | Low | Clear "last updated" timestamp |

### Technical Debt Considerations

1. **Initial Implementation**: Simple synchronous calculations
2. **Future Enhancement**: Background calculation with caching
3. **Future Enhancement**: WebSocket for real-time price updates

---

## Traceability Matrix

| Requirement | Component | Test Case |
|-------------|-----------|-----------|
| REQ-ANALYTICS-001 | PortfolioAnalyticsService.calculate_metrics() | test_portfolio_value_calculation() |
| REQ-ANALYTICS-002 | PortfolioMetrics dataclass | test_performance_metrics_accuracy() |
| REQ-ANALYTICS-003 | web_ui/dashboard.py | test_dashboard_loads_all_data() |
| REQ-ANALYTICS-004 | PortfolioAnalyticsService (real-time) | test_price_update_refreshes_value() |
| REQ-ANALYTICS-005 | dashboard.py (empty state) | test_empty_state_display() |
| REQ-ANALYTICS-006 | calculate_metrics() with filters | test_period_filtering() |
| REQ-ANALYTICS-007 | charts.py (price chart) | test_btc_price_chart() |
| REQ-ANALYTICS-008 | charts.py (heatmap) | test_trade_heatmap() |
| REQ-ANALYTICS-009 | Calculation validation | test_no_division_by_zero() |
| REQ-ANALYTICS-010 | Memory management | test_large_dataset_aggregation() |

---

## Success Criteria

1. **Functional**: All 10 requirements implemented and passing tests
2. **Performance**: Dashboard loads within 3 seconds
3. **Coverage**: Minimum 85% test coverage
4. **Accuracy**: Calculations match manual verification
5. **UI**: All charts render correctly with interactions
6. **Real-time**: Value updates on price changes

---

## Related SPECs

- **SPEC-TRADING-001**: TradingService (trade execution, price data)
- **SPEC-TRADING-002**: TradeHistoryService (trade history data source)
- **SPEC-TRADING-006**: UserProfileService (preference for currency display)

---

Version: 1.0.0
Last Updated: 2026-03-05
Author: MoAI SPEC Builder
