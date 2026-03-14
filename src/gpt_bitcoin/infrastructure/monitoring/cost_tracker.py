"""
GLM API Cost Tracker.

This module provides cost tracking functionality for GLM API usage,
including token usage logging, daily/monthly cost calculation,
threshold alerts, and cost trend analysis.

Features:
- SQLite-based usage logging
- Daily and monthly cost reports
- Configurable cost thresholds with alerts
- 7-day cost trend analysis
- Integration with TradingMetrics
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import aiosqlite
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models
# =============================================================================


class GLMUsageLog(BaseModel):
    """GLM API usage log entry."""

    timestamp: datetime = Field(default_factory=datetime.now, description="Log timestamp")
    model: str = Field(..., description="GLM model name (glm-4, glm-5)")
    prompt_tokens: int = Field(..., ge=0, description="Number of prompt tokens")
    completion_tokens: int = Field(..., ge=0, description="Number of completion tokens")
    total_tokens: int = Field(..., ge=0, description="Total tokens used")
    cost_krw: float = Field(..., ge=0, description="Cost in KRW")
    request_id: str | None = Field(default=None, description="Optional request ID")
    metadata: dict[str, str] = Field(default_factory=dict, description="Additional metadata")


class DailyCostReport(BaseModel):
    """Daily cost report."""

    date: str = Field(..., description="Report date (YYYY-MM-DD)")
    total_cost_krw: float = Field(..., ge=0, description="Total cost in KRW")
    total_tokens: int = Field(..., ge=0, description="Total tokens used")
    request_count: int = Field(..., ge=0, description="Number of API requests")
    model_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description="Cost breakdown by model",
    )


class MonthlyCostReport(BaseModel):
    """Monthly cost report."""

    month: str = Field(..., description="Report month (YYYY-MM)")
    total_cost_krw: float = Field(..., ge=0, description="Total cost in KRW")
    total_tokens: int = Field(..., ge=0, description="Total tokens used")
    request_count: int = Field(..., ge=0, description="Number of API requests")
    daily_average_cost: float = Field(..., ge=0, description="Daily average cost")
    model_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description="Cost breakdown by model",
    )


class CostTrend(BaseModel):
    """7-day cost trend analysis."""

    period_start: str = Field(..., description="Trend period start date")
    period_end: str = Field(..., description="Trend period end date")
    daily_costs: list[float] = Field(default_factory=list, description="Daily costs")
    average_cost: float = Field(..., ge=0, description="Average daily cost")
    trend_direction: str = Field(..., description="increasing, decreasing, stable")
    change_percentage: float = Field(
        ...,
        description="Percentage change from previous period",
    )


class CostAlert(BaseModel):
    """Cost threshold alert."""

    alert_type: str = Field(..., description="Alert type (daily, monthly, trend)")
    threshold_krw: float = Field(..., ge=0, description="Threshold in KRW")
    current_value_krw: float = Field(..., ge=0, description="Current value in KRW")
    message: str = Field(..., description="Alert message")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Alert timestamp",
    )


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class CostTrackerConfig:
    """Configuration for cost tracker.

    Attributes:
        database_path: Path to SQLite database file
        daily_threshold_krw: Daily cost threshold for alerts
        monthly_threshold_krw: Monthly cost threshold for alerts
        glm_4_price_per_1k: GLM-4 price per 1K tokens in KRW
        glm_5_price_per_1k: GLM-5 price per 1K tokens in KRW
        enable_alerts: Enable cost threshold alerts
    """

    database_path: str = "data/glm_usage.db"
    daily_threshold_krw: float = 10000.0  # 10,000 KRW
    monthly_threshold_krw: float = 200000.0  # 200,000 KRW
    glm_4_price_per_1k: float = 0.0005  # 0.0005 KRW per 1K tokens
    glm_5_price_per_1k: float = 0.001  # 0.001 KRW per 1K tokens
    enable_alerts: bool = True


# =============================================================================
# Cost Tracker
# =============================================================================


class CostTracker:
    """
    GLM API cost tracker with SQLite persistence.

    Provides comprehensive cost tracking including:
    - Token usage logging
    - Daily and monthly cost reports
    - Threshold alerts
    - Cost trend analysis

    Example:
        ```python
        tracker = CostTracker(config)
        await tracker.initialize()

        # Log usage
        await tracker.log_usage(
            model="glm-4",
            prompt_tokens=100,
            completion_tokens=50,
        )

        # Get daily report
        report = await tracker.get_daily_report()
        print(f"Today's cost: {report.total_cost_krw} KRW")
        ```
    """

    def __init__(self, config: CostTrackerConfig | None = None) -> None:
        """Initialize cost tracker.

        Args:
            config: Optional cost tracker configuration
        """
        self._config = config or CostTrackerConfig()
        self._db: aiosqlite.Connection | None = None
        self._alert_callbacks: list = []

        logger.info(
            "Cost tracker initialized",
            database_path=self._config.database_path,
            daily_threshold=self._config.daily_threshold_krw,
        )

    async def initialize(self) -> None:
        """Initialize database connection and create tables."""
        # Ensure data directory exists
        db_path = Path(self._config.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect to database
        self._db = await aiosqlite.connect(self._config.database_path)

        # Create table if not exists
        await self._create_table()

        logger.info("Cost tracker database initialized")

    async def _create_table(self) -> None:
        """Create glm_usage_log table if not exists."""
        if not self._db:
            raise RuntimeError("Database not initialized")

        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS glm_usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                cost_krw REAL NOT NULL,
                request_id TEXT,
                metadata TEXT
            )
        """)

        # Create indexes for efficient querying
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON glm_usage_log(timestamp)
        """)

        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_model
            ON glm_usage_log(model)
        """)

        await self._db.commit()

    async def log_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        request_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> GLMUsageLog:
        """
        Log GLM API usage.

        Args:
            model: GLM model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            request_id: Optional request ID
            metadata: Optional metadata

        Returns:
            Created usage log entry
        """
        if not self._db:
            raise RuntimeError("Database not initialized")

        # Calculate total tokens
        total_tokens = prompt_tokens + completion_tokens

        # Calculate cost based on model
        cost_krw = self._calculate_cost(model, total_tokens)

        # Create log entry
        log_entry = GLMUsageLog(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_krw=cost_krw,
            request_id=request_id,
            metadata=metadata or {},
        )

        # Insert into database
        await self._db.execute(
            """
            INSERT INTO glm_usage_log
            (timestamp, model, prompt_tokens, completion_tokens, total_tokens, cost_krw, request_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_entry.timestamp.isoformat(),
                log_entry.model,
                log_entry.prompt_tokens,
                log_entry.completion_tokens,
                log_entry.total_tokens,
                log_entry.cost_krw,
                log_entry.request_id,
                str(log_entry.metadata) if log_entry.metadata else None,
            ),
        )

        await self._db.commit()

        logger.info(
            "GLM usage logged",
            model=model,
            total_tokens=total_tokens,
            cost_krw=cost_krw,
        )

        # Check thresholds and trigger alerts
        if self._config.enable_alerts:
            await self._check_thresholds()

        return log_entry

    def _calculate_cost(self, model: str, total_tokens: int) -> float:
        """Calculate cost in KRW based on model and tokens.

        Args:
            model: GLM model name
            total_tokens: Total tokens used

        Returns:
            Cost in KRW
        """
        # Select price based on model
        if "glm-5" in model.lower():
            price_per_1k = self._config.glm_5_price_per_1k
        else:
            price_per_1k = self._config.glm_4_price_per_1k

        # Calculate cost
        cost = (total_tokens / 1000) * price_per_1k
        return cost

    async def _check_thresholds(self) -> list[CostAlert]:
        """Check cost thresholds and generate alerts.

        Returns:
            List of triggered alerts
        """
        alerts = []

        # Check daily threshold
        daily_report = await self.get_daily_report()
        if daily_report.total_cost_krw >= self._config.daily_threshold_krw:
            alert = CostAlert(
                alert_type="daily",
                threshold_krw=self._config.daily_threshold_krw,
                current_value_krw=daily_report.total_cost_krw,
                message=(
                    f"Daily cost {daily_report.total_cost_krw:.2f} KRW "
                    f"exceeds threshold {self._config.daily_threshold_krw:.2f} KRW"
                ),
            )
            alerts.append(alert)
            logger.warning(alert.message)

        # Check monthly threshold
        monthly_report = await self.get_monthly_report()
        if monthly_report.total_cost_krw >= self._config.monthly_threshold_krw:
            alert = CostAlert(
                alert_type="monthly",
                threshold_krw=self._config.monthly_threshold_krw,
                current_value_krw=monthly_report.total_cost_krw,
                message=(
                    f"Monthly cost {monthly_report.total_cost_krw:.2f} KRW "
                    f"exceeds threshold {self._config.monthly_threshold_krw:.2f} KRW"
                ),
            )
            alerts.append(alert)
            logger.warning(alert.message)

        # Trigger alert callbacks
        for alert in alerts:
            await self._trigger_alert_callbacks(alert)

        return alerts

    def add_alert_callback(self, callback) -> None:
        """Add callback for cost alerts.

        Args:
            callback: Async function to call on alert
        """
        self._alert_callbacks.append(callback)

    async def _trigger_alert_callbacks(self, alert: CostAlert) -> None:
        """Trigger all registered alert callbacks.

        Args:
            alert: Cost alert to process
        """
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

    async def get_daily_report(self, date: datetime | None = None) -> DailyCostReport:
        """
        Generate daily cost report.

        Args:
            date: Target date (defaults to today)

        Returns:
            Daily cost report
        """
        if not self._db:
            raise RuntimeError("Database not initialized")

        target_date = date or datetime.now()
        date_str = target_date.strftime("%Y-%m-%d")

        # Query daily usage
        cursor = await self._db.execute(
            """
            SELECT
                model,
                SUM(total_tokens) as total_tokens,
                SUM(cost_krw) as total_cost,
                COUNT(*) as request_count
            FROM glm_usage_log
            WHERE DATE(timestamp) = DATE(?)
            GROUP BY model
            """,
            (target_date.isoformat(),),
        )

        rows = await cursor.fetchall()

        # Aggregate results
        total_cost = 0.0
        total_tokens = 0
        request_count = 0
        model_breakdown = {}

        for row in rows:
            model, tokens, cost, count = row
            total_cost += cost or 0
            total_tokens += tokens or 0
            request_count += count or 0
            model_breakdown[model] = cost or 0

        return DailyCostReport(
            date=date_str,
            total_cost_krw=total_cost,
            total_tokens=total_tokens,
            request_count=request_count,
            model_breakdown=model_breakdown,
        )

    async def get_monthly_report(
        self,
        year: int | None = None,
        month: int | None = None,
    ) -> MonthlyCostReport:
        """
        Generate monthly cost report.

        Args:
            year: Target year (defaults to current year)
            month: Target month (defaults to current month)

        Returns:
            Monthly cost report
        """
        if not self._db:
            raise RuntimeError("Database not initialized")

        target_year = year or datetime.now().year
        target_month = month or datetime.now().month
        month_str = f"{target_year:04d}-{target_month:02d}"

        # Query monthly usage
        cursor = await self._db.execute(
            """
            SELECT
                model,
                SUM(total_tokens) as total_tokens,
                SUM(cost_krw) as total_cost,
                COUNT(*) as request_count,
                COUNT(DISTINCT DATE(timestamp)) as day_count
            FROM glm_usage_log
            WHERE strftime('%Y-%m', timestamp) = ?
            GROUP BY model
            """,
            (month_str,),
        )

        rows = await cursor.fetchall()

        # Aggregate results
        total_cost = 0.0
        total_tokens = 0
        request_count = 0
        day_count = 0
        model_breakdown = {}

        for row in rows:
            model, tokens, cost, count, days = row
            total_cost += cost or 0
            total_tokens += tokens or 0
            request_count += count or 0
            day_count = max(day_count, days or 0)
            model_breakdown[model] = cost or 0

        # Calculate daily average
        daily_average = total_cost / day_count if day_count > 0 else 0

        return MonthlyCostReport(
            month=month_str,
            total_cost_krw=total_cost,
            total_tokens=total_tokens,
            request_count=request_count,
            daily_average_cost=daily_average,
            model_breakdown=model_breakdown,
        )

    async def get_cost_trend(self, days: int = 7) -> CostTrend:
        """
        Analyze cost trend over the specified period.

        Args:
            days: Number of days to analyze (default: 7)

        Returns:
            Cost trend analysis
        """
        if not self._db:
            raise RuntimeError("Database not initialized")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Query daily costs
        cursor = await self._db.execute(
            """
            SELECT
                DATE(timestamp) as date,
                SUM(cost_krw) as daily_cost
            FROM glm_usage_log
            WHERE DATE(timestamp) >= DATE(?)
            AND DATE(timestamp) <= DATE(?)
            GROUP BY DATE(timestamp)
            ORDER BY date
            """,
            (start_date.isoformat(), end_date.isoformat()),
        )

        rows = await cursor.fetchall()

        # Extract daily costs
        daily_costs = [row[1] or 0 for row in rows]

        # Calculate average
        average_cost = sum(daily_costs) / len(daily_costs) if daily_costs else 0

        # Determine trend direction
        if len(daily_costs) >= 2:
            recent_avg = sum(daily_costs[-3:]) / 3 if len(daily_costs) >= 3 else daily_costs[-1]
            earlier_avg = sum(daily_costs[:3]) / 3 if len(daily_costs) >= 3 else daily_costs[0]

            if earlier_avg > 0:
                change_pct = ((recent_avg - earlier_avg) / earlier_avg) * 100
            else:
                change_pct = 0

            if change_pct > 10:
                trend_direction = "increasing"
            elif change_pct < -10:
                trend_direction = "decreasing"
            else:
                trend_direction = "stable"
        else:
            change_pct = 0
            trend_direction = "stable"

        return CostTrend(
            period_start=start_date.strftime("%Y-%m-%d"),
            period_end=end_date.strftime("%Y-%m-%d"),
            daily_costs=daily_costs,
            average_cost=average_cost,
            trend_direction=trend_direction,
            change_percentage=change_pct,
        )

    async def close(self) -> None:
        """Close database connection."""
        if self._db:
            await self._db.close()
            self._db = None
            logger.info("Cost tracker database closed")


# =============================================================================
# Global Instance
# =============================================================================

_cost_tracker: CostTracker | None = None


def get_cost_tracker(config: CostTrackerConfig | None = None) -> CostTracker:
    """Get or create the global cost tracker instance.

    Args:
        config: Optional cost tracker configuration

    Returns:
        Global CostTracker instance
    """
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker(config)
    return _cost_tracker


__all__ = [
    "CostAlert",
    "CostTracker",
    "CostTrackerConfig",
    "CostTrend",
    "DailyCostReport",
    "GLMUsageLog",
    "MonthlyCostReport",
    "get_cost_tracker",
]
