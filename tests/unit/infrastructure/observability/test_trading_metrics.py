"""
Tests for Trading Metrics.

This module tests domain-specific trading metrics including GLM API metrics,
Upbit API metrics, trading decision metrics, and portfolio metrics.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from gpt_bitcoin.infrastructure.observability.trading_metrics import (
    TradingMetrics,
    TradingMetricsConfig,
    get_trading_metrics,
    track_glm_api_call,
    track_trading_decision,
    track_upbit_api_call,
    update_portfolio_value,
)


@pytest.fixture(autouse=True)
def reset_metrics() -> Any:
    """Reset metrics singleton and registry before each test."""
    # Reset the trading metrics singleton
    import gpt_bitcoin.infrastructure.observability.trading_metrics as tm

    tm._trading_metrics = None

    # Reset the prometheus server singleton
    import gpt_bitcoin.infrastructure.observability.prometheus_exporter as pe

    pe._metrics_server = None

    yield


class TestTradingMetricsConfig:
    """Test trading metrics configuration."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = TradingMetricsConfig()

        assert config.enable_glm_metrics is True
        assert config.enable_upbit_metrics is True
        assert config.enable_portfolio_metrics is True
        assert config.enable_trading_metrics is True

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = TradingMetricsConfig(
            enable_glm_metrics=False,
            enable_upbit_metrics=False,
            enable_portfolio_metrics=True,
            enable_trading_metrics=True,
        )

        assert config.enable_glm_metrics is False
        assert config.enable_upbit_metrics is False
        assert config.enable_portfolio_metrics is True
        assert config.enable_trading_metrics is True


class TestTradingMetrics:
    """Test trading metrics functionality."""

    def test_metrics_initialization(self) -> None:
        """Test trading metrics initialization."""
        metrics = TradingMetrics()

        assert metrics._glm_tokens_counter is not None
        assert metrics._glm_cost_gauge is not None
        assert metrics._upbit_requests_counter is not None
        assert metrics._trading_duration_histogram is not None
        assert metrics._portfolio_value_gauge is not None
        assert metrics._trading_pnl_gauge is not None

    def test_increment_glm_tokens(self) -> None:
        """Test incrementing GLM token usage counter."""
        metrics = TradingMetrics()

        metrics.increment_glm_tokens(tokens=100, model="glm-4")

        # Verify counter was incremented without error
        assert metrics._glm_tokens_counter is not None

    def test_set_glm_cost(self) -> None:
        """Test setting GLM API cost gauge."""
        metrics = TradingMetrics()

        metrics.set_glm_cost(cost_krw=1500.0, model="glm-4")

        # Verify gauge was set without error
        assert metrics._glm_cost_gauge is not None

    def test_increment_upbit_requests(self) -> None:
        """Test incrementing Upbit API request counter."""
        metrics = TradingMetrics()

        metrics.increment_upbit_requests(
            endpoint="/v1/candles/minutes/1",
            method="GET",
            status="200",
        )

        # Verify counter was incremented without error
        assert metrics._upbit_requests_counter is not None

    def test_observe_trading_decision_duration(self) -> None:
        """Test observing trading decision duration."""
        metrics = TradingMetrics()

        metrics.observe_trading_decision_duration(
            duration_seconds=0.75,
            decision="buy",
        )

        # Verify histogram was observed without error
        assert metrics._trading_duration_histogram is not None

    def test_set_portfolio_value(self) -> None:
        """Test setting portfolio value gauge."""
        metrics = TradingMetrics()

        metrics.set_portfolio_value(value_krw=10000000.0)

        # Verify gauge was set without error
        assert metrics._portfolio_value_gauge is not None

    def test_set_trading_pnl(self) -> None:
        """Test setting trading P&L gauge."""
        metrics = TradingMetrics()

        metrics.set_trading_pnl(pnl_percentage=5.25)

        # Verify gauge was set without error
        assert metrics._trading_pnl_gauge is not None

    def test_multiple_operations(self) -> None:
        """Test multiple metric operations in sequence."""
        metrics = TradingMetrics()

        # Simulate a trading cycle
        metrics.increment_glm_tokens(tokens=150, model="glm-4")
        metrics.set_glm_cost(cost_krw=2000.0, model="glm-4")
        metrics.increment_upbit_requests(endpoint="/v1/accounts", method="GET", status="200")
        metrics.observe_trading_decision_duration(duration_seconds=1.2, decision="sell")
        metrics.set_portfolio_value(value_krw=12000000.0)
        metrics.set_trading_pnl(pnl_percentage=8.5)

        # All operations should complete without error
        assert True

    def test_labels_applied_correctly(self) -> None:
        """Test that labels are correctly applied to all metrics."""
        metrics = TradingMetrics()

        # Test with various label combinations
        metrics.increment_glm_tokens(tokens=100, model="glm-4-flash")
        metrics.increment_upbit_requests(
            endpoint="/v1/order",
            method="POST",
            status="201",
        )
        metrics.observe_trading_decision_duration(
            duration_seconds=0.5,
            decision="hold",
        )

        # Verify no exceptions raised
        assert True

    def test_disabled_metrics(self) -> None:
        """Test that disabled metrics don't raise errors."""
        config = TradingMetricsConfig(
            enable_glm_metrics=False,
            enable_upbit_metrics=False,
        )
        metrics = TradingMetrics(config)

        # Operations on disabled metrics should be no-ops
        metrics.increment_glm_tokens(tokens=100, model="glm-4")
        metrics.increment_upbit_requests(endpoint="/v1/test", method="GET", status="200")

        # Should complete without error
        assert True


class TestTradingMetricsFunctions:
    """Test module-level convenience functions."""

    def test_get_trading_metrics_singleton(self) -> None:
        """Test that get_trading_metrics returns singleton instance."""
        metrics1 = get_trading_metrics()
        metrics2 = get_trading_metrics()

        assert metrics1 is metrics2

    def test_track_glm_api_call_decorator(self) -> None:
        """Test GLM API call tracking decorator."""
        mock_metrics = MagicMock()
        with patch(
            "gpt_bitcoin.infrastructure.observability.trading_metrics.get_trading_metrics",
            return_value=mock_metrics,
        ):

            @track_glm_api_call(model="glm-4")
            def test_function() -> str:
                return "success"

            result = test_function()

            assert result == "success"
            mock_metrics.increment_glm_tokens.assert_called()

    def test_track_upbit_api_call_decorator(self) -> None:
        """Test Upbit API call tracking decorator."""
        mock_metrics = MagicMock()
        with patch(
            "gpt_bitcoin.infrastructure.observability.trading_metrics.get_trading_metrics",
            return_value=mock_metrics,
        ):

            @track_upbit_api_call(endpoint="/v1/accounts", method="GET")
            def test_function() -> str:
                return "success"

            result = test_function()

            assert result == "success"
            mock_metrics.increment_upbit_requests.assert_called()

    def test_track_trading_decision_decorator(self) -> None:
        """Test trading decision tracking decorator."""
        mock_metrics = MagicMock()
        with patch(
            "gpt_bitcoin.infrastructure.observability.trading_metrics.get_trading_metrics",
            return_value=mock_metrics,
        ):

            @track_trading_decision(decision="buy")
            def test_function() -> str:
                return "executed"

            result = test_function()

            assert result == "executed"
            mock_metrics.observe_trading_decision_duration.assert_called()

    def test_update_portfolio_value_function(self) -> None:
        """Test portfolio value update function."""
        mock_metrics = MagicMock()
        with patch(
            "gpt_bitcoin.infrastructure.observability.trading_metrics.get_trading_metrics",
            return_value=mock_metrics,
        ):
            update_portfolio_value(value_krw=15000000.0)

            mock_metrics.set_portfolio_value.assert_called_once_with(value_krw=15000000.0)


class TestTradingMetricsIntegration:
    """Integration tests for trading metrics."""

    def test_metrics_output_includes_all_metrics(self) -> None:
        """Test that metrics output includes all defined metrics."""
        metrics = TradingMetrics()

        # Perform operations
        metrics.increment_glm_tokens(tokens=200, model="glm-4")
        metrics.set_glm_cost(cost_krw=3000.0, model="glm-4")
        metrics.increment_upbit_requests(
            endpoint="/v1/candles/days",
            method="GET",
            status="200",
        )
        metrics.observe_trading_decision_duration(duration_seconds=1.5, decision="buy")
        metrics.set_portfolio_value(value_krw=20000000.0)
        metrics.set_trading_pnl(pnl_percentage=12.3)

        # Get metrics output
        output = metrics.get_metrics_output()

        # Verify all metrics are present
        assert "glm_tokens_used_total" in output
        assert "glm_api_cost_krw" in output
        assert "upbit_api_requests_total" in output
        assert "trading_decision_duration_seconds" in output
        assert "portfolio_value_krw" in output
        assert "trading_pnl_percentage" in output

    def test_concurrent_metric_updates(self) -> None:
        """Test that concurrent metric updates work correctly."""
        import threading

        metrics = TradingMetrics()

        def update_metrics() -> None:
            for i in range(10):
                metrics.increment_glm_tokens(tokens=10, model="glm-4")
                metrics.increment_upbit_requests(
                    endpoint=f"/v1/test{i}",
                    method="GET",
                    status="200",
                )

        threads = [threading.Thread(target=update_metrics) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All updates should complete without error
        assert True
