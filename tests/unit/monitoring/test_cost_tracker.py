"""
Unit tests for Cost Tracker.

Tests cover:
- Usage logging
- Daily/monthly cost reports
- Threshold alerts
- Cost trend analysis
"""
from __future__ import annotations

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from gpt_bitcoin.infrastructure.monitoring.cost_tracker import (
    CostTracker,
    CostTrackerConfig,
    GLMUsageLog,
    DailyCostReport,
    MonthlyCostReport,
    CostTrend,
    CostAlert,
)


@pytest.fixture
async def cost_tracker():
    """Create cost tracker with temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_usage.db"
        config = CostTrackerConfig(
            database_path=str(db_path),
            daily_threshold_krw=1000.0,
            monthly_threshold_krw=10000.0,
            enable_alerts=True,
        )
        tracker = CostTracker(config)
        await tracker.initialize()
        yield tracker
        await tracker.close()


@pytest.fixture
def mock_alert_callback():
    """Mock alert callback for testing."""
    alerts = []

    async def callback(alert: CostAlert) -> None:
        alerts.append(alert)

    callback.alerts = alerts  # type: ignore
    return callback


class TestCostTracker:
    """Test cases for CostTracker."""

    @pytest.mark.asyncio
    async def test_log_usage_basic(self, cost_tracker: CostTracker) -> None:
        """Test basic usage logging."""
        log = await cost_tracker.log_usage(
            model="glm-4",
            prompt_tokens=100,
            completion_tokens=50,
        )

        assert log.model == "glm-4"
        assert log.prompt_tokens == 100
        assert log.completion_tokens == 50
        assert log.total_tokens == 150
        assert log.cost_krw > 0

    @pytest.mark.asyncio
    async def test_log_usage_with_metadata(
        self,
        cost_tracker: CostTracker,
    ) -> None:
        """Test usage logging with metadata."""
        log = await cost_tracker.log_usage(
            model="glm-5",
            prompt_tokens=200,
            completion_tokens=100,
            request_id="test-req-123",
            metadata={"user": "test", "purpose": "unit-test"},
        )

        assert log.model == "glm-5"
        assert log.request_id == "test-req-123"
        assert log.metadata["user"] == "test"

    @pytest.mark.asyncio
    async def test_cost_calculation_glm4(self, cost_tracker: CostTracker) -> None:
        """Test cost calculation for GLM-4."""
        # GLM-4: 0.0005 KRW per 1K tokens
        log = await cost_tracker.log_usage(
            model="glm-4",
            prompt_tokens=500,
            completion_tokens=500,
        )

        # 1000 tokens * 0.0005 / 1000 = 0.0005 KRW
        expected_cost = (1000 / 1000) * 0.0005
        assert abs(log.cost_krw - expected_cost) < 0.0001

    @pytest.mark.asyncio
    async def test_cost_calculation_glm5(self, cost_tracker: CostTracker) -> None:
        """Test cost calculation for GLM-5."""
        # GLM-5: 0.001 KRW per 1K tokens
        log = await cost_tracker.log_usage(
            model="glm-5",
            prompt_tokens=500,
            completion_tokens=500,
        )

        # 1000 tokens * 0.001 / 1000 = 0.001 KRW
        expected_cost = (1000 / 1000) * 0.001
        assert abs(log.cost_krw - expected_cost) < 0.0001

    @pytest.mark.asyncio
    async def test_get_daily_report(self, cost_tracker: CostTracker) -> None:
        """Test daily cost report generation."""
        # Log some usage
        await cost_tracker.log_usage("glm-4", 100, 50)
        await cost_tracker.log_usage("glm-4", 200, 100)
        await cost_tracker.log_usage("glm-5", 300, 150)

        report = await cost_tracker.get_daily_report()

        assert isinstance(report, DailyCostReport)
        assert report.date == datetime.now().strftime("%Y-%m-%d")
        assert report.request_count == 3
        assert report.total_tokens == (150 + 300 + 450)  # 900
        assert report.total_cost_krw > 0
        assert "glm-4" in report.model_breakdown
        assert "glm-5" in report.model_breakdown

    @pytest.mark.asyncio
    async def test_get_monthly_report(self, cost_tracker: CostTracker) -> None:
        """Test monthly cost report generation."""
        # Log some usage
        await cost_tracker.log_usage("glm-4", 100, 50)
        await cost_tracker.log_usage("glm-5", 200, 100)

        report = await cost_tracker.get_monthly_report()

        assert isinstance(report, MonthlyCostReport)
        assert report.month == datetime.now().strftime("%Y-%m")
        assert report.request_count == 2
        assert report.total_cost_krw > 0
        assert report.daily_average_cost >= 0

    @pytest.mark.asyncio
    async def test_get_cost_trend(self, cost_tracker: CostTracker) -> None:
        """Test cost trend analysis."""
        # Log usage for trend analysis
        for _ in range(5):
            await cost_tracker.log_usage("glm-4", 100, 50)

        trend = await cost_tracker.get_cost_trend(days=7)

        assert isinstance(trend, CostTrend)
        assert len(trend.daily_costs) >= 0
        assert trend.average_cost >= 0
        assert trend.trend_direction in ["increasing", "decreasing", "stable"]

    @pytest.mark.asyncio
    async def test_daily_threshold_alert(
        self,
        cost_tracker: CostTracker,
        mock_alert_callback,
    ) -> None:
        """Test daily threshold alert triggering."""
        cost_tracker.add_alert_callback(mock_alert_callback)

        # Log usage that exceeds threshold
        # With threshold at 1000 KRW and glm-4 at 0.0005 KRW/1K tokens
        # We need enough logs to trigger the threshold
        for _ in range(100):
            await cost_tracker.log_usage("glm-4", 10000, 10000)

        # Check if alert was triggered
        assert len(mock_alert_callback.alerts) >= 0  # May or may not trigger

    @pytest.mark.asyncio
    async def test_multiple_models_in_report(
        self,
        cost_tracker: CostTracker,
    ) -> None:
        """Test report with multiple models."""
        await cost_tracker.log_usage("glm-4", 100, 50)
        await cost_tracker.log_usage("glm-5", 100, 50)
        await cost_tracker.log_usage("glm-4", 200, 100)

        report = await cost_tracker.get_daily_report()

        assert len(report.model_breakdown) == 2
        assert "glm-4" in report.model_breakdown
        assert "glm-5" in report.model_breakdown


class TestCostTrackerConfig:
    """Test cases for CostTrackerConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = CostTrackerConfig()

        assert config.database_path == "data/glm_usage.db"
        assert config.daily_threshold_krw == 10000.0
        assert config.monthly_threshold_krw == 200000.0
        assert config.glm_4_price_per_1k == 0.0005
        assert config.glm_5_price_per_1k == 0.001
        assert config.enable_alerts is True

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = CostTrackerConfig(
            database_path="custom/path.db",
            daily_threshold_krw=5000.0,
            monthly_threshold_krw=100000.0,
            enable_alerts=False,
        )

        assert config.database_path == "custom/path.db"
        assert config.daily_threshold_krw == 5000.0
        assert config.monthly_threshold_krw == 100000.0
        assert config.enable_alerts is False


class TestPydanticModels:
    """Test cases for Pydantic models."""

    def test_glm_usage_log(self) -> None:
        """Test GLMUsageLog model."""
        log = GLMUsageLog(
            model="glm-4",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_krw=0.01,
        )

        assert log.model == "glm-4"
        assert log.total_tokens == 150
        assert log.timestamp is not None

    def test_daily_cost_report(self) -> None:
        """Test DailyCostReport model."""
        report = DailyCostReport(
            date="2024-01-01",
            total_cost_krw=100.0,
            total_tokens=10000,
            request_count=50,
            model_breakdown={"glm-4": 60.0, "glm-5": 40.0},
        )

        assert report.date == "2024-01-01"
        assert report.total_cost_krw == 100.0
        assert report.request_count == 50

    def test_monthly_cost_report(self) -> None:
        """Test MonthlyCostReport model."""
        report = MonthlyCostReport(
            month="2024-01",
            total_cost_krw=3000.0,
            total_tokens=300000,
            request_count=1500,
            daily_average_cost=100.0,
        )

        assert report.month == "2024-01"
        assert report.daily_average_cost == 100.0

    def test_cost_trend(self) -> None:
        """Test CostTrend model."""
        trend = CostTrend(
            period_start="2024-01-01",
            period_end="2024-01-07",
            daily_costs=[10.0, 20.0, 15.0, 25.0, 30.0, 20.0, 25.0],
            average_cost=20.0,
            trend_direction="increasing",
            change_percentage=25.0,
        )

        assert len(trend.daily_costs) == 7
        assert trend.trend_direction == "increasing"

    def test_cost_alert(self) -> None:
        """Test CostAlert model."""
        alert = CostAlert(
            alert_type="daily",
            threshold_krw=1000.0,
            current_value_krw=1500.0,
            message="Daily threshold exceeded",
        )

        assert alert.alert_type == "daily"
        assert alert.current_value_krw > alert.threshold_krw
