"""
Tests for Prometheus Exporter.

This module tests the Prometheus metrics export functionality including
metrics server startup, custom metrics registration, and endpoint exposure.
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from prometheus_client import Counter, Gauge, Histogram

from gpt_bitcoin.infrastructure.observability.prometheus_exporter import (
    PrometheusMetricsServer,
    PrometheusConfig,
    start_prometheus_server,
    get_metrics_server,
)


@pytest.fixture(autouse=True)
def reset_singletons() -> Any:
    """Reset singleton instances before each test."""
    # Reset the prometheus server singleton
    import gpt_bitcoin.infrastructure.observability.prometheus_exporter as pe
    pe._metrics_server = None

    # Reset the trading metrics singleton
    import gpt_bitcoin.infrastructure.observability.trading_metrics as tm
    tm._trading_metrics = None

    yield


class TestPrometheusConfig:
    """Test Prometheus configuration."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = PrometheusConfig()

        assert config.port == 9090
        assert config.host == "0.0.0.0"
        assert config.prefix == "gpt_bitcoin"
        assert config.enable_default_metrics is True

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = PrometheusConfig(
            port=8080,
            host="127.0.0.1",
            prefix="custom_prefix",
            enable_default_metrics=False,
        )

        assert config.port == 8080
        assert config.host == "127.0.0.1"
        assert config.prefix == "custom_prefix"
        assert config.enable_default_metrics is False


class TestPrometheusMetricsServer:
    """Test Prometheus metrics server functionality."""

    def test_server_initialization(self) -> None:
        """Test metrics server initialization."""
        config = PrometheusConfig(port=9091)
        server = PrometheusMetricsServer(config)

        assert server.config.port == 9091
        assert server._registry is not None
        assert server._server is None

    def test_register_counter(self) -> None:
        """Test counter metric registration."""
        server = PrometheusMetricsServer()

        counter = server.register_counter(
            name="test_counter",
            description="Test counter description",
            labelnames=["status"],
        )

        assert isinstance(counter, Counter)
        assert counter._name == "gpt_bitcoin_test_counter"

    def test_register_gauge(self) -> None:
        """Test gauge metric registration."""
        server = PrometheusMetricsServer()

        gauge = server.register_gauge(
            name="test_gauge",
            description="Test gauge description",
            labelnames=["type"],
        )

        assert isinstance(gauge, Gauge)
        assert gauge._name == "gpt_bitcoin_test_gauge"

    def test_register_histogram(self) -> None:
        """Test histogram metric registration."""
        server = PrometheusMetricsServer()

        histogram = server.register_histogram(
            name="test_histogram",
            description="Test histogram description",
            labelnames=["endpoint"],
            buckets=[0.1, 0.5, 1.0, 5.0],
        )

        assert isinstance(histogram, Histogram)
        assert histogram._name == "gpt_bitcoin_test_histogram"

    def test_metric_prefix_applied(self) -> None:
        """Test that metric prefix is correctly applied."""
        config = PrometheusConfig(prefix="my_app")
        server = PrometheusMetricsServer(config)

        counter = server.register_counter(
            name="requests",
            description="Request counter",
        )

        assert counter._name == "my_app_requests"

    @pytest.mark.asyncio
    async def test_start_server(self) -> None:
        """Test starting the Prometheus metrics server."""
        server = PrometheusMetricsServer()

        with patch("asyncio.start_server") as mock_start_server:
            mock_server = AsyncMock()
            mock_start_server.return_value = mock_server

            await server.start()

            mock_start_server.assert_called_once()
            assert server._server is not None

    @pytest.mark.asyncio
    async def test_stop_server(self) -> None:
        """Test stopping the Prometheus metrics server."""
        server = PrometheusMetricsServer()

        with patch("asyncio.start_server") as mock_start_server:
            mock_server = AsyncMock()
            mock_server.wait_closed = AsyncMock()
            mock_start_server.return_value = mock_server

            await server.start()
            await server.stop()

            mock_server.close.assert_called_once()
            mock_server.wait_closed.assert_called_once()

    def test_get_metric_value(self) -> None:
        """Test retrieving metric value."""
        server = PrometheusMetricsServer()

        counter = server.register_counter(
            name="test_counter",
            description="Test counter",
        )
        counter.inc()

        # Metric should exist in registry
        assert server._registry is not None

    def test_labels_applied_correctly(self) -> None:
        """Test that labels are correctly applied to metrics."""
        server = PrometheusMetricsServer()

        counter = server.register_counter(
            name="test_labeled_counter",
            description="Test labeled counter",
            labelnames=["method", "status"],
        )

        # Increment with labels
        counter.labels(method="GET", status="200").inc()
        counter.labels(method="POST", status="201").inc()

        # Verify no exceptions raised
        assert counter is not None


class TestPrometheusServerFunctions:
    """Test module-level functions."""

    def test_get_metrics_server_singleton(self) -> None:
        """Test that get_metrics_server returns singleton instance."""
        server1 = get_metrics_server()
        server2 = get_metrics_server()

        assert server1 is server2

    @pytest.mark.asyncio
    async def test_start_prometheus_server(self) -> None:
        """Test convenience function to start Prometheus server."""
        with patch("asyncio.start_server") as mock_start_server:
            mock_server = AsyncMock()
            mock_start_server.return_value = mock_server

            server = await start_prometheus_server(port=9090)

            assert server is not None
            mock_start_server.assert_called_once()


class TestPrometheusIntegration:
    """Integration tests for Prometheus exporter."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_handler(self) -> None:
        """Test that metrics endpoint handler returns valid response."""
        server = PrometheusMetricsServer()

        # Register a metric
        counter = server.register_counter(
            name="test_requests",
            description="Test request counter",
        )
        counter.inc()

        # Get metrics output
        metrics_output = server.get_metrics_output()

        assert "gpt_bitcoin_test_requests" in metrics_output
        assert "Test request counter" in metrics_output

    def test_multiple_metric_types_coexist(self) -> None:
        """Test that multiple metric types can coexist."""
        server = PrometheusMetricsServer()

        counter = server.register_counter("counter1", "Counter 1")
        gauge = server.register_gauge("gauge1", "Gauge 1")
        histogram = server.register_histogram("histogram1", "Histogram 1")

        # Use all metrics
        counter.inc()
        gauge.set(42.0)
        histogram.observe(0.5)

        metrics_output = server.get_metrics_output()

        assert "gpt_bitcoin_counter1" in metrics_output
        assert "gpt_bitcoin_gauge1" in metrics_output
        assert "gpt_bitcoin_histogram1" in metrics_output

    @pytest.mark.asyncio
    async def test_handle_request_success(self) -> None:
        """Test _handle_request processes HTTP request successfully."""
        server = PrometheusMetricsServer()

        # Register a metric
        counter = server.register_counter("test_counter", "Test counter")
        counter.inc()

        # Create mock reader and writer
        reader = AsyncMock()
        reader.read = AsyncMock(return_value=b"GET /metrics HTTP/1.1")
        writer = AsyncMock()
        writer.write = MagicMock()
        writer.drain = AsyncMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()

        # Handle request
        await server._handle_request(reader, writer)

        # Verify response was written
        writer.write.assert_called_once()
        writer.drain.assert_called_once()
        writer.close.assert_called_once()
        writer.wait_closed.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_request_with_error(self) -> None:
        """Test _handle_request handles errors gracefully."""
        server = PrometheusMetricsServer()

        # Create mock reader that raises error
        reader = AsyncMock()
        reader.read = AsyncMock(side_effect=Exception("Connection error"))
        writer = AsyncMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()

        # Handle request - should not raise
        await server._handle_request(reader, writer)

        # Writer should still be closed
        writer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_server_failure(self) -> None:
        """Test start handles server startup failures."""
        server = PrometheusMetricsServer()

        with patch("asyncio.start_server") as mock_start_server:
            mock_start_server.side_effect = OSError("Address already in use")

            with pytest.raises(OSError, match="Address already in use"):
                await server.start()
