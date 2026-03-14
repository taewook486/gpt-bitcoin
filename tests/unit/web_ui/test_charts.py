"""
Tests for Chart Rendering Utilities (SPEC-TRADING-008).

TDD Test Suite - RED Phase
Tests define expected behavior before implementation.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from gpt_bitcoin.domain.analytics import PortfolioValueHistory, TradeDistribution
from gpt_bitcoin.web_ui import charts

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_history():
    """Sample portfolio value history."""
    return PortfolioValueHistory(
        timestamps=[
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
            datetime(2024, 1, 3),
        ],
        values_krw=[1000000.0, 1050000.0, 1020000.0],
    )


@pytest.fixture
def sample_distribution():
    """Sample trade distribution."""
    return TradeDistribution(
        by_hour={10: 5, 14: 3, 20: 2},
        by_day_of_week={0: 10, 1: 15},
        by_month={"2024-01": 25},
    )


# =============================================================================
# Chart Creation Tests
# =============================================================================


class TestCreatePortfolioValueChart:
    """Test create_portfolio_value_chart function."""

    def test_create_portfolio_value_chart(self, sample_history):
        """Test creating portfolio value chart."""
        figure = charts.create_portfolio_value_chart(sample_history)

        assert isinstance(figure, dict)
        assert "data" in figure
        assert "layout" in figure
        assert figure["layout"]["title"] == "Portfolio Value Over Time"


class TestCreatePerformanceChart:
    """Test create_performance_chart function."""

    def test_create_performance_chart(self):
        """Test creating performance chart."""
        cumulative_pl = [1000.0, 2000.0, 1500.0]
        figure = charts.create_performance_chart(cumulative_pl)

        assert isinstance(figure, dict)
        assert "data" in figure
        assert "layout" in figure
        assert figure["layout"]["title"] == "Cumulative P/L"

    def test_create_performance_chart_with_benchmark(self):
        """Test creating performance chart with benchmark."""
        cumulative_pl = [1000.0, 2000.0, 1500.0]
        benchmark = [980.0, 1950.0, 1470.0]
        figure = charts.create_performance_chart(cumulative_pl, benchmark)

        assert isinstance(figure, dict)
        assert "data" in figure


class TestCreateDistributionHeatmap:
    """Test create_distribution_heatmap function."""

    def test_create_distribution_heatmap(self, sample_distribution):
        """Test creating distribution heatmap."""
        figure = charts.create_distribution_heatmap(sample_distribution)

        assert isinstance(figure, dict)
        assert "data" in figure
        assert "layout" in figure
        assert figure["layout"]["title"] == "Trade Distribution"


# =============================================================================
# Formatting Utility Tests
# =============================================================================


class TestFormatNumber:
    """Test format_number function."""

    def test_format_number_millions(self):
        """Test formatting millions."""
        result = charts.format_number(1_500_000.0)
        assert result == "1.50M"

    def test_format_number_thousands(self):
        """Test formatting thousands."""
        result = charts.format_number(15_500.0)
        assert result == "15.50K"

    def test_format_number_small(self):
        """Test formatting small numbers."""
        result = charts.format_number(999.0)
        assert result == "999.00"

    def test_format_number_negative(self):
        """Test formatting negative numbers."""
        result = charts.format_number(-1_500_000.0)
        assert result == "-1.50M"


class TestFormatPercentage:
    """Test format_percentage function."""

    def test_format_percentage_positive(self):
        """Test formatting positive percentage."""
        result = charts.format_percentage(15.567)
        assert result == "+15.57%"

    def test_format_percentage_negative(self):
        """Test formatting negative percentage."""
        result = charts.format_percentage(-10.234)
        assert result == "-10.23%"

    def test_format_percentage_zero(self):
        """Test formatting zero percentage."""
        result = charts.format_percentage(0.0)
        assert result == "+0.00%"
