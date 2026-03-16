"""
Tests for Web UI Dashboard Components (SPEC-TRADING-008).

TDD Test Suite - RED Phase
Tests define expected behavior before implementation.
"""

from __future__ import annotations

import pytest

from gpt_bitcoin.domain.analytics import (
    AssetHolding,
    PortfolioMetrics,
    TradeDistribution,
)
from gpt_bitcoin.web_ui import dashboard

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_metrics():
    """Sample portfolio metrics."""
    return PortfolioMetrics(
        total_value_krw=1000000.0,
        total_invested_krw=500000.0,
        total_roi_percent=15.5,
        win_rate_percent=60.0,
        total_trades=10,
        buy_trades=5,
        sell_trades=5,
    )


@pytest.fixture
def sample_holdings():
    """Sample asset holdings."""
    return [
        AssetHolding(
            ticker="KRW-BTC",
            quantity=0.1,
            average_buy_price=50000000.0,
            current_price=55000000.0,
            current_value_krw=5500000.0,
            unrealized_pl_krw=500000.0,
            unrealized_pl_percent=10.0,
        ),
        AssetHolding(
            ticker="KRW-ETH",
            quantity=1.0,
            average_buy_price=3000000.0,
            current_price=3200000.0,
            current_value_krw=3200000.0,
            unrealized_pl_krw=200000.0,
            unrealized_pl_percent=6.67,
        ),
    ]


@pytest.fixture
def sample_distribution():
    """Sample trade distribution."""
    return TradeDistribution(
        by_hour={10: 5, 14: 3, 20: 2},
        by_day_of_week={0: 10, 1: 15},
        by_month={"2024-01": 25},
    )


# =============================================================================
# Dashboard Component Tests
# =============================================================================


class TestRenderPortfolioOverview:
    """Test render_portfolio_overview function."""

    def test_render_portfolio_overview(self, sample_metrics):
        """Test rendering portfolio overview cards."""
        # Should not raise any errors
        dashboard.render_portfolio_overview(sample_metrics)


class TestRenderPerformanceCharts:
    """Test render_performance_charts function."""

    def test_render_performance_charts(self, sample_metrics):
        """Test rendering performance charts."""
        # Should not raise any errors
        dashboard.render_performance_charts(sample_metrics)


class TestRenderTradeAnalysis:
    """Test render_trade_analysis function."""

    def test_render_trade_analysis(self, sample_distribution):
        """Test rendering trade analysis heatmap."""
        # Should not raise any errors
        dashboard.render_trade_analysis(sample_distribution)


class TestRenderHoldingsTable:
    """Test render_holdings_table function."""

    def test_render_holdings_table(self, sample_holdings):
        """Test rendering holdings table."""
        # Should not raise any errors
        dashboard.render_holdings_table(sample_holdings)

    def test_render_holdings_table_empty(self):
        """Test rendering empty holdings table."""
        dashboard.render_holdings_table([])
