"""
Tests for Portfolio Analytics domain module (SPEC-TRADING-008).

TDD Test Suite - RED Phase
Tests define expected behavior before implementation.

Requirements Coverage:
- REQ-ANALYTICS-001: Real-time portfolio value calculation
- REQ-ANALYTICS-002: Performance metrics accuracy (ROI, win rate, P/L)
- REQ-ANALYTICS-005: Empty state message when no trades
- REQ-ANALYTICS-006: Period filtering
- REQ-ANALYTICS-009: No division by zero
- REQ-ANALYTICS-010: Memory management (max 10,000 trades)
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from gpt_bitcoin.domain.analytics import (
    AssetHolding,
    PortfolioAnalyticsService,
    PortfolioMetrics,
    PortfolioValueHistory,
    TradeDistribution,
)
from gpt_bitcoin.domain.trade_history import TradeRecord, TradeType

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_trade_history_service():
    """Mock trade history service."""
    return MagicMock()


@pytest.fixture
def mock_upbit_client():
    """Mock Upbit client for price data."""
    client = MagicMock()
    client.get_current_price = MagicMock(return_value=50000000.0)  # 50M KRW for BTC
    return client


@pytest.fixture
def analytics_service(mock_trade_history_service, mock_upbit_client):
    """PortfolioAnalyticsService fixture."""
    return PortfolioAnalyticsService(
        trade_history_service=mock_trade_history_service,
        upbit_client=mock_upbit_client,
    )


@pytest.fixture
def sample_trades():
    """Sample trade records for testing."""
    return [
        # Buy trades
        TradeRecord(
            ticker="KRW-BTC",
            trade_type=TradeType.BUY,
            price=50000000.0,
            quantity=0.1,
            fee=500.0,
            timestamp=datetime(2024, 1, 1, 10, 0),
        ),
        TradeRecord(
            ticker="KRW-BTC",
            trade_type=TradeType.BUY,
            price=52000000.0,
            quantity=0.05,
            fee=260.0,
            timestamp=datetime(2024, 1, 2, 14, 30),
        ),
        TradeRecord(
            ticker="KRW-ETH",
            trade_type=TradeType.BUY,
            price=3000000.0,
            quantity=1.0,
            fee=300.0,
            timestamp=datetime(2024, 1, 3, 9, 15),
        ),
        # Sell trades
        TradeRecord(
            ticker="KRW-BTC",
            trade_type=TradeType.SELL,
            price=55000000.0,
            quantity=0.05,
            fee=275.0,
            timestamp=datetime(2024, 1, 5, 11, 0),
        ),
    ]


# =============================================================================
# PortfolioMetrics Tests (REQ-ANALYTICS-002)
# =============================================================================


class TestPortfolioMetrics:
    """Test PortfolioMetrics dataclass (REQ-ANALYTICS-002)."""

    def test_default_metrics_initialization(self):
        """Test default values for all metrics."""
        metrics = PortfolioMetrics()

        # Value metrics
        assert metrics.total_value_krw == 0.0
        assert metrics.cash_balance_krw == 0.0
        assert metrics.holdings_value_krw == 0.0
        assert metrics.total_invested_krw == 0.0

        # Performance metrics
        assert metrics.total_roi_percent == 0.0
        assert metrics.realized_pl_krw == 0.0
        assert metrics.unrealized_pl_krw == 0.0
        assert metrics.win_rate_percent == 0.0

        # Trade statistics
        assert metrics.total_trades == 0
        assert metrics.buy_trades == 0
        assert metrics.sell_trades == 0
        assert metrics.winning_trades == 0
        assert metrics.losing_trades == 0

        # Averages
        assert metrics.avg_profit_per_winning_trade == 0.0
        assert metrics.avg_loss_per_losing_trade == 0.0
        assert metrics.largest_win == 0.0
        assert metrics.largest_loss == 0.0

        # Timestamps
        assert isinstance(metrics.calculated_at, datetime)
        assert metrics.period_start is None
        assert metrics.period_end is None

    def test_metrics_with_period_filter(self):
        """Test metrics with time period filter (REQ-ANALYTICS-006)."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        metrics = PortfolioMetrics(
            total_trades=10,
            total_roi_percent=15.5,
            period_start=start,
            period_end=end,
        )

        assert metrics.period_start == start
        assert metrics.period_end == end


# =============================================================================
# AssetHolding Tests
# =============================================================================


class TestAssetHolding:
    """Test AssetHolding dataclass."""

    def test_asset_holding_creation(self):
        """Test asset holding with all fields."""
        holding = AssetHolding(
            ticker="KRW-BTC",
            quantity=0.1,
            average_buy_price=50000000.0,
            current_price=55000000.0,
            current_value_krw=5500000.0,
            unrealized_pl_krw=500000.0,
            unrealized_pl_percent=10.0,
        )

        assert holding.ticker == "KRW-BTC"
        assert holding.quantity == 0.1
        assert holding.average_buy_price == 50000000.0
        assert holding.current_price == 55000000.0
        assert holding.unrealized_pl_krw == 500000.0
        assert holding.unrealized_pl_percent == 10.0


# =============================================================================
# PortfolioValueHistory Tests (REQ-ANALYTICS-001)
# =============================================================================


class TestPortfolioValueHistory:
    """Test PortfolioValueHistory dataclass (REQ-ANALYTICS-001)."""

    def test_value_history_creation(self):
        """Test value history with timestamps and values."""
        timestamps = [
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
            datetime(2024, 1, 3),
        ]
        values = [1000000.0, 1050000.0, 1020000.0]

        history = PortfolioValueHistory(
            timestamps=timestamps,
            values_krw=values,
        )

        assert len(history.timestamps) == 3
        assert history.values_krw == values
        assert history.benchmark_values is None

    def test_value_history_with_benchmark(self):
        """Test value history with benchmark comparison."""
        timestamps = [datetime(2024, 1, 1)]
        values = [1000000.0]
        benchmark = [980000.0]

        history = PortfolioValueHistory(
            timestamps=timestamps,
            values_krw=values,
            benchmark_values=benchmark,
        )

        assert history.benchmark_values == benchmark


# =============================================================================
# TradeDistribution Tests (REQ-ANALYTICS-008)
# =============================================================================


class TestTradeDistribution:
    """Test TradeDistribution dataclass (REQ-ANALYTICS-008)."""

    def test_empty_distribution(self):
        """Test empty distribution."""
        dist = TradeDistribution()

        assert len(dist.by_hour) == 0
        assert len(dist.by_day_of_week) == 0
        assert len(dist.by_month) == 0

    def test_distribution_with_data(self):
        """Test distribution with trade counts."""
        dist = TradeDistribution(
            by_hour={10: 5, 14: 3},
            by_day_of_week={0: 10, 1: 15},
            by_month={"2024-01": 25},
        )

        assert dist.by_hour[10] == 5
        assert dist.by_day_of_week[1] == 15
        assert dist.by_month["2024-01"] == 25


# =============================================================================
# PortfolioAnalyticsService.calculate_metrics Tests (REQ-ANALYTICS-002)
# =============================================================================


class TestCalculateMetrics:
    """Test calculate_metrics method (REQ-ANALYTICS-002, REQ-ANALYTICS-009)."""

    def test_calculate_metrics_empty_trades(self, analytics_service, mock_trade_history_service):
        """
        REQ-ANALYTICS-005: Empty state when no trades.

        시스템은 거래 내역이 없을 때 빈 상태 메시지를 표시해야 한다.
        """
        mock_trade_history_service.get_trades.return_value = []

        metrics = analytics_service.calculate_metrics(user_id="test_user")

        assert metrics.total_trades == 0
        assert metrics.total_invested_krw == 0.0
        assert metrics.win_rate_percent == 0.0
        assert metrics.total_roi_percent == 0.0

    def test_calculate_metrics_with_trades(
        self, analytics_service, mock_trade_history_service, sample_trades
    ):
        """
        REQ-ANALYTICS-002: Calculate performance metrics accurately.

        시스템은 성과 지표를 정확하게 계산해야 한다:
        - Total ROI (%): (current_value - total_invested) / total_invested * 100
        - Win Rate (%): winning_trades / total_closed_trades * 100
        - Total P/L (KRW): sum of realized_profit_loss
        """
        mock_trade_history_service.get_trades.return_value = sample_trades

        metrics = analytics_service.calculate_metrics(user_id="test_user")

        # Verify structure
        assert isinstance(metrics, PortfolioMetrics)
        assert metrics.total_trades == len(sample_trades)
        assert metrics.buy_trades == 3  # 3 buy trades
        assert metrics.sell_trades == 1  # 1 sell trade

    def test_calculate_metrics_no_division_by_zero(
        self, analytics_service, mock_trade_history_service
    ):
        """
        REQ-ANALYTICS-009: No division by zero.

        시스템은 부정확한 계산을 표시해서는 안 된다:
        - Division by zero results (show "N/A" instead)
        - Validate all inputs before calculation
        """
        mock_trade_history_service.get_trades.return_value = []

        metrics = analytics_service.calculate_metrics(user_id="test_user")

        # All calculations should handle zero division gracefully
        assert metrics.total_invested_krw == 0.0
        assert metrics.total_roi_percent == 0.0  # Not NaN or inf
        assert metrics.win_rate_percent == 0.0
        assert metrics.avg_profit_per_winning_trade == 0.0
        assert metrics.avg_loss_per_losing_trade == 0.0

    def test_calculate_metrics_with_period_filter(
        self, analytics_service, mock_trade_history_service
    ):
        """
        REQ-ANALYTICS-006: Filter by selected time period.

        시스템은 선택된 기간의 데이터만 분석해야 한다.
        """
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        mock_trade_history_service.get_trades.return_value = []

        metrics = analytics_service.calculate_metrics(
            user_id="test_user",
            start_date=start_date,
            end_date=end_date,
        )

        assert metrics.period_start == start_date
        assert metrics.period_end == end_date
        mock_trade_history_service.get_trades.assert_called_once_with(
            ticker=None,
            start_date=start_date,
            end_date=end_date,
        )


# =============================================================================
# PortfolioAnalyticsService.get_current_holdings Tests (REQ-ANALYTICS-001)
# =============================================================================


class TestGetCurrentHoldings:
    """Test get_current_holdings method (REQ-ANALYTICS-001)."""

    def test_get_holdings_empty(self, analytics_service, mock_trade_history_service):
        """Test getting holdings when no trades."""
        mock_trade_history_service.get_trades.return_value = []

        holdings = analytics_service.get_current_holdings(user_id="test_user")

        assert holdings == []

    def test_get_holdings_with_positions(
        self, analytics_service, mock_trade_history_service, sample_trades
    ):
        """
        REQ-ANALYTICS-001: Real-time portfolio value calculation.

        시스템은 포트폴리오 총 가치를 실시간으로 계산해야 한다:
        - Sum of (quantity * current_price) for each held asset
        - Include KRW cash balance
        - Update on price changes
        """
        mock_trade_history_service.get_trades.return_value = sample_trades

        holdings = analytics_service.get_current_holdings(user_id="test_user")

        # Should have holdings for BTC (after sell, 0.05 + 0.05 = 0.1 BTC remaining)
        # And ETH (1.0 ETH)
        assert len(holdings) > 0

        # Each holding should have required fields
        for holding in holdings:
            assert isinstance(holding, AssetHolding)
            assert holding.ticker in ["KRW-BTC", "KRW-ETH"]
            assert holding.quantity >= 0
            assert holding.current_price > 0
            assert holding.current_value_krw >= 0


# =============================================================================
# PortfolioAnalyticsService.get_portfolio_value_history Tests
# =============================================================================


class TestGetPortfolioValueHistory:
    """Test get_portfolio_value_history method."""

    def test_value_history_empty(self, analytics_service, mock_trade_history_service):
        """Test value history when no trades."""
        mock_trade_history_service.get_trades.return_value = []

        history = analytics_service.get_portfolio_value_history(
            user_id="test_user",
            period="30d",
        )

        assert isinstance(history, PortfolioValueHistory)
        assert len(history.timestamps) == 0
        assert len(history.values_krw) == 0

    def test_value_history_with_data(
        self, analytics_service, mock_trade_history_service, sample_trades
    ):
        """Test value history reconstruction from trades."""
        mock_trade_history_service.get_trades.return_value = sample_trades

        history = analytics_service.get_portfolio_value_history(
            user_id="test_user",
            period="30d",
        )

        assert isinstance(history, PortfolioValueHistory)
        assert len(history.timestamps) == len(history.values_krw)


# =============================================================================
# PortfolioAnalyticsService.get_trade_distribution Tests (REQ-ANALYTICS-008)
# =============================================================================


class TestGetTradeDistribution:
    """Test get_trade_distribution method (REQ-ANALYTICS-008)."""

    def test_trade_distribution_empty(self, analytics_service, mock_trade_history_service):
        """Test distribution when no trades."""
        mock_trade_history_service.get_trades.return_value = []

        distribution = analytics_service.get_trade_distribution(user_id="test_user")

        assert isinstance(distribution, TradeDistribution)
        assert len(distribution.by_hour) == 0
        assert len(distribution.by_day_of_week) == 0

    def test_trade_distribution_by_hour(self, analytics_service, mock_trade_history_service):
        """
        REQ-ANALYTICS-008: Trade heatmap by hour and day.

        시스템은 거래 분포 히트맵을 제공해야 한다:
        - Day of week vs. Hour of day
        - Color intensity by trade count
        """
        # Create trades at different hours
        trades = [
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=50000000.0,
                quantity=0.1,
                fee=500.0,
                timestamp=datetime(2024, 1, 1, 10, 0),  # 10 AM
            ),
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=50000000.0,
                quantity=0.1,
                fee=500.0,
                timestamp=datetime(2024, 1, 1, 14, 30),  # 2:30 PM
            ),
        ]

        mock_trade_history_service.get_trades.return_value = trades

        distribution = analytics_service.get_trade_distribution(user_id="test_user")

        assert isinstance(distribution, TradeDistribution)
        # Should have distribution by hour
        assert distribution.by_hour.get(10) == 1
        assert distribution.by_hour.get(14) == 1


# =============================================================================
# PortfolioAnalyticsService.get_performance_chart_data Tests
# =============================================================================


class TestGetPerformanceChartData:
    """Test get_performance_chart_data method."""

    def test_performance_chart_data_empty(self, analytics_service, mock_trade_history_service):
        """Test chart data when no trades."""
        mock_trade_history_service.get_trades.return_value = []

        data = analytics_service.get_performance_chart_data(
            user_id="test_user",
            period="30d",
        )

        assert "cumulative_pl" in data
        assert "trade_markers" in data
        assert "benchmark" in data

        assert len(data["cumulative_pl"]["timestamps"]) == 0
        assert len(data["trade_markers"]) == 0


# =============================================================================
# Memory Management Tests (REQ-ANALYTICS-010)
# =============================================================================


class TestMemoryManagement:
    """Test memory management (REQ-ANALYTICS-010)."""

    def test_max_trades_limit(self):
        """
        REQ-ANALYTICS-010: System should not consume excessive memory.

        시스템은 과도한 메모리를 사용해서는 안 된다:
        - Load more than 10,000 trades into memory at once
        """
        assert hasattr(PortfolioAnalyticsService, "MAX_TRADES_TO_LOAD")
        assert PortfolioAnalyticsService.MAX_TRADES_TO_LOAD == 10000
