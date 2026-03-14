# Implementation Plan: SPEC-TRADING-008 (Portfolio Analytics Dashboard)

## Overview

이 문서는 SPEC-TRADING-008 포트폴리오 분석 대시보드 기능의 구현 계획을 정의합니다.

---

## Milestones (Priority-Based)

### Phase 1: Analytics Service (Primary Goal)

**Objective**: 포트폴리오 분석 서비스 및 데이터 모델 구현

#### Tasks

1. **Data Models**
   - Priority: Critical
   - Create `PortfolioMetrics` dataclass
   - Create `AssetHolding` dataclass
   - Create `ChartData` dataclasses
   - Add validation and computed properties

2. **PortfolioAnalyticsService**
   - Priority: Critical
   - Implement `calculate_metrics()` method
   - Implement `get_current_holdings()` method
   - Implement `get_portfolio_value_history()` method
   - Implement `get_trade_distribution()` method

3. **Metrics Calculations**
   - Priority: High
   - Implement ROI calculation
   - Implement win rate calculation
   - Implement average P/L calculations
   - Handle division by zero cases

4. **Unit Tests - Core**
   - Priority: High
   - Test all metric calculations
   - Test edge cases (no trades, single trade)
   - Test filtering by period

**Deliverables**:
- Working analytics service
- All core tests passing
- Accurate calculations

---

### Phase 2: Dashboard UI (Secondary Goal)

**Objective**: Web UI 대시보드 탭 및 컴포넌트 구현

#### Tasks

1. **Dashboard Components**
   - Priority: High
   - Create `web_ui/` package structure
   - Implement overview cards component
   - Implement holdings table component
   - Implement statistics grid component

2. **Chart Components**
   - Priority: High
   - Implement cumulative P/L line chart
   - Implement portfolio value chart
   - Implement trade distribution heatmap
   - Add interactive features (zoom, hover)

3. **Real-time Updates**
   - Priority: Medium
   - Implement price polling (30s interval)
   - Implement partial UI updates
   - Add "Last Updated" timestamp

4. **Period Filtering**
   - Priority: Medium
   - Add 7D/30D/90D/1Y filter buttons
   - Implement date range picker
   - Update charts on filter change

5. **UI Tests**
   - Priority: Medium
   - Test component rendering
   - Test filter interactions
   - Test empty state handling

**Deliverables**:
- Complete dashboard tab
- All charts working
- Real-time updates functional

---

### Phase 3: Advanced Features (Final Goal)

**Objective**: 고급 차트 및 분석 기능

#### Tasks

1. **BTC Price Chart**
   - Priority: Low
   - Fetch historical price data
   - Render candlestick chart
   - Add volume overlay

2. **Benchmark Comparison**
   - Priority: Low
   - Calculate BTC buy-and-hold benchmark
   - Add comparison line to P/L chart
   - Display relative performance

3. **Performance Optimization**
   - Priority: Medium
   - Implement data aggregation for large datasets
   - Add caching for calculated metrics
   - Optimize chart rendering

4. **Integration Tests**
   - Priority: Medium
   - Test end-to-end data flow
   - Test real-time updates

**Deliverables**:
- BTC price chart
- Benchmark comparison
- Optimized performance

---

## Technical Approach

### Service Layer

```python
# domain/analytics.py

class PortfolioAnalyticsService:
    """Portfolio analytics calculation service."""

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
        """
        # Fetch trades
        trades = await self._trade_history.get_trades(
            start_date=start_date,
            end_date=end_date,
            limit=10000,  # Max supported
        )

        if not trades:
            return self._empty_metrics()

        # Calculate metrics
        buy_trades = [t for t in trades if t.side == "buy"]
        sell_trades = [t for t in trades if t.side == "sell"]

        total_invested = sum(t.total_krw for t in buy_trades)
        total_recovered = sum(t.total_krw for t in sell_trades)

        # Calculate holdings
        holdings = await self.get_current_holdings(user_id)
        holdings_value = sum(h.current_value_krw for h in holdings)

        # Calculate P/L
        pl_data = await self._trade_history.calculate_profit_loss_all()
        realized_pl = pl_data.get("total_realized_pl", 0)
        unrealized_pl = sum(h.unrealized_pl_krw for h in holdings)

        # Win rate
        winning_trades = sum(1 for t in sell_trades if self._is_winning(t))
        total_closed = len(sell_trades)
        win_rate = (winning_trades / total_closed * 100) if total_closed > 0 else 0

        # Total value (assuming cash balance tracked separately)
        total_value = holdings_value + self._get_cash_balance()

        # ROI
        roi = ((total_value - total_invested) / total_invested * 100) if total_invested > 0 else 0

        return PortfolioMetrics(
            total_value_krw=total_value,
            cash_balance_krw=self._get_cash_balance(),
            holdings_value_krw=holdings_value,
            total_invested_krw=total_invested,
            total_roi_percent=roi,
            realized_pl_krw=realized_pl,
            unrealized_pl_krw=unrealized_pl,
            win_rate_percent=win_rate,
            total_trades=len(trades),
            buy_trades=len(buy_trades),
            sell_trades=len(sell_trades),
            winning_trades=winning_trades,
            losing_trades=total_closed - winning_trades,
            calculated_at=datetime.now(),
            period_start=start_date,
            period_end=end_date,
        )

    async def get_current_holdings(
        self,
        user_id: str,
    ) -> list[AssetHolding]:
        """Get current asset holdings with live prices."""
        # Get holdings from trade history
        holdings_data = await self._trade_history.calculate_all_holdings()

        holdings = []
        for ticker, data in holdings_data.items():
            # Fetch current price
            current_price = await self._upbit_client.get_current_price(ticker)

            quantity = data["quantity"]
            avg_buy_price = data["avg_price"]
            current_value = quantity * current_price
            unrealized_pl = (current_price - avg_buy_price) * quantity
            unrealized_pl_pct = ((current_price - avg_buy_price) / avg_buy_price * 100) if avg_buy_price > 0 else 0

            holdings.append(AssetHolding(
                ticker=ticker,
                quantity=quantity,
                average_buy_price=avg_buy_price,
                current_price=current_price,
                current_value_krw=current_value,
                unrealized_pl_krw=unrealized_pl,
                unrealized_pl_percent=unrealized_pl_pct,
            ))

        return sorted(holdings, key=lambda h: h.current_value_krw, reverse=True)
```

### Chart Components

```python
# web_ui/charts.py

import plotly.graph_objects as go
import plotly.express as px

def create_cumulative_pl_chart(
    history: PortfolioValueHistory,
    trade_markers: list[datetime],
) -> go.Figure:
    """
    Create cumulative P/L line chart.

    @MX:NOTE: Uses Plotly for interactive charts.
    """
    fig = go.Figure()

    # P/L line
    fig.add_trace(go.Scatter(
        x=history.timestamps,
        y=history.values_krw,
        mode='lines',
        name='Portfolio Value',
        line=dict(color='#1f77b4', width=2),
    ))

    # Trade markers
    if trade_markers:
        fig.add_trace(go.Scatter(
            x=trade_markers,
            y=[history.values_krw[i] for i, t in enumerate(history.timestamps) if t in trade_markers],
            mode='markers',
            name='Trades',
            marker=dict(color='red', size=8),
        ))

    fig.update_layout(
        title='Cumulative P/L',
        xaxis_title='Date',
        yaxis_title='Value (KRW)',
        hovermode='x unified',
    )

    return fig

def create_holdings_pie_chart(holdings: list[AssetHolding]) -> go.Figure:
    """Create holdings distribution pie chart."""
    fig = go.Figure(data=[go.Pie(
        labels=[h.ticker for h in holdings],
        values=[h.current_value_krw for h in holdings],
        hole=0.3,
    )])

    fig.update_layout(
        title='Holdings Distribution',
    )

    return fig

def create_trade_heatmap(distribution: TradeDistribution) -> go.Figure:
    """Create trade timing heatmap."""
    # Create 2D array for day x hour
    import numpy as np

    z = np.zeros((7, 24))
    for day, count in distribution.by_day_of_week.items():
        # Simplified: use average hourly count for the day
        avg_hourly = count / 24
        z[day, :] = avg_hourly

    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=list(range(24)),
        y=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        colorscale='Blues',
    ))

    fig.update_layout(
        title='Trade Distribution Heatmap',
        xaxis_title='Hour of Day',
        yaxis_title='Day of Week',
    )

    return fig
```

### Dashboard Component

```python
# web_ui/dashboard.py

import streamlit as st
from gpt_bitcoin.domain.analytics import PortfolioAnalyticsService

def render_portfolio_dashboard(
    analytics_service: PortfolioAnalyticsService,
    user_id: str,
):
    """Render complete portfolio dashboard."""

    # Period selector
    period = st.radio(
        "Period",
        ["7D", "30D", "90D", "1Y"],
        horizontal=True,
    )

    # Calculate metrics
    with st.spinner("Calculating..."):
        metrics = asyncio.run(
            analytics_service.calculate_metrics(user_id, period)
        )

    # Overview cards
    render_overview_cards(metrics)

    # Holdings table
    render_holdings_table(analytics_service, user_id)

    # Performance chart
    render_performance_chart(analytics_service, user_id, period)

    # Statistics
    render_statistics_grid(metrics)

    # Trade distribution
    render_trade_distribution(analytics_service, user_id)

def render_overview_cards(metrics: PortfolioMetrics):
    """Render top overview cards."""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Total Value",
            f"{metrics.total_value_krw:,.0f} KRW",
            f"{metrics.total_roi_percent:+.1f}%",
        )

    with col2:
        st.metric(
            "Realized P/L",
            f"{metrics.realized_pl_krw:+,.0f} KRW",
        )

    with col3:
        st.metric(
            "Unrealized P/L",
            f"{metrics.unrealized_pl_krw:+,.0f} KRW",
        )
```

---

## Architecture Design

### Package Structure

```
src/gpt_bitcoin/
├── domain/
│   ├── analytics.py          # [NEW] PortfolioAnalyticsService
│   ├── trade_history.py      # [EXISTING] Data source
│   └── trading.py            # [EXISTING] Price data
│
├── web_ui/
│   ├── __init__.py           # [NEW]
│   ├── dashboard.py          # [NEW] Dashboard components
│   └── charts.py             # [NEW] Chart utilities
│
├── dependencies/
│   └── container.py          # [MODIFY] Register services
│
└── web_ui.py                 # [MODIFY] Add Portfolio tab
```

### Data Flow

```
+------------------+
| TradeHistory     |
| Service          |
+--------+---------+
         | Trade records
         v
+------------------+
| Portfolio        |
| AnalyticsService |
+--------+---------+
         | Metrics, Chart Data
         v
+------------------+         +------------------+
| Dashboard        |         | UpbitClient      |
| Components       |<--------| (current prices) |
+--------+---------+         +------------------+
         |
         v
+------------------+
| Plotly Charts    |
+------------------+
```

---

## Configuration Changes

### Settings Additions

```python
# config/settings.py additions

class Settings(BaseSettings):
    # ... existing settings ...

    # Analytics Settings
    analytics_max_trades: int = Field(
        default=10000,
        description="Maximum trades to analyze",
    )
    analytics_cache_ttl_seconds: int = Field(
        default=60,
        description="Cache TTL for calculated metrics",
    )
    price_update_interval_seconds: int = Field(
        default=30,
        description="Price update polling interval",
    )
```

---

## Testing Strategy

### Test Coverage Goals

| Component | Target Coverage | Priority |
|-----------|-----------------|----------|
| PortfolioMetrics | 100% | Critical |
| AssetHolding | 100% | Critical |
| PortfolioAnalyticsService | 90% | High |
| Dashboard Components | 70% | Medium |
| Chart Functions | 60% | Medium |

### Key Test Cases

```python
# tests/unit/domain/test_analytics.py

class TestPortfolioAnalyticsService:
    """Test PortfolioAnalyticsService."""

    @pytest.mark.asyncio
    async def test_calculate_metrics_empty(self, service):
        """Test metrics with no trades."""
        metrics = await service.calculate_metrics("user_with_no_trades")

        assert metrics.total_trades == 0
        assert metrics.total_value_krw == 0
        assert metrics.total_roi_percent == 0

    @pytest.mark.asyncio
    async def test_calculate_metrics_with_trades(self, service, sample_trades):
        """Test metrics calculation with trades."""
        metrics = await service.calculate_metrics("user1")

        assert metrics.total_trades > 0
        assert metrics.total_invested_krw > 0
        # ROI should be calculated correctly

    @pytest.mark.asyncio
    async def test_win_rate_calculation(self, service):
        """Test win rate calculation."""
        # Setup: 6 wins, 4 losses
        metrics = await service.calculate_metrics("user_with_10_sells")

        assert metrics.win_rate_percent == 60.0
        assert metrics.winning_trades == 6
        assert metrics.losing_trades == 4

    def test_roi_calculation(self):
        """Test ROI formula."""
        # Invested: 1,000,000 KRW
        # Current value: 1,100,000 KRW
        # Expected ROI: 10%

        roi = ((1_100_000 - 1_000_000) / 1_000_000) * 100
        assert roi == 10.0

    def test_no_division_by_zero(self):
        """Test division by zero handling."""
        # When total_invested is 0, ROI should be 0 or N/A
        with pytest.raises(ZeroDivisionError):
            _ = 100 / 0

        # Our implementation should handle this
        roi = 0 if 0 == 0 else ((100 - 0) / 0) * 100
        assert roi == 0
```

---

## Dependencies

### New Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| plotly | >=5.18.0 | Interactive charts |
| kaleido | >=0.2.0 | Chart image export (optional) |

### Existing Dependencies Used

| Package | Usage |
|---------|-------|
| pandas | Data processing |
| streamlit | UI |
| pytest + pytest-asyncio | Testing |

---

## Performance Considerations

### Data Volume

- Expected: 10-50 trades per day
- Annual: ~5,000 trades
- Dashboard should handle 10,000 trades

### Optimization Strategies

1. **Aggregation**: Aggregate data for charts (daily/weekly points)
2. **Caching**: Cache calculated metrics for 60 seconds
3. **Lazy Loading**: Load chart data only when tab is active
4. **Pagination**: Limit trade list display to 100 rows

---

Version: 1.0.0
Last Updated: 2026-03-05
Author: MoAI SPEC Builder
