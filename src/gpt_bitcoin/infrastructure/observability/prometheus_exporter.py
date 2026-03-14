"""
Prometheus Metrics Exporter.

This module provides Prometheus metrics export functionality including
a metrics server, metric registration, and endpoint exposure for scraping.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)

# Global metrics server instance
_metrics_server: PrometheusMetricsServer | None = None


@dataclass
class PrometheusConfig:
    """Configuration for Prometheus metrics server.

    Attributes:
        port: Port number for metrics server (default: 9090)
        host: Host address to bind (default: 0.0.0.0)
        prefix: Prefix for all metrics (default: gpt_bitcoin)
        enable_default_metrics: Enable default process metrics (default: True)
    """

    port: int = 9090
    host: str = "0.0.0.0"
    prefix: str = "gpt_bitcoin"
    enable_default_metrics: bool = True


class PrometheusMetricsServer:
    """Prometheus metrics server for exposing metrics endpoint.

    This class provides a Prometheus-compatible metrics server that exposes
    metrics on an HTTP endpoint for scraping by Prometheus servers.

    Attributes:
        config: Prometheus configuration
        _registry: Prometheus collector registry
        _server: asyncio server instance
    """

    def __init__(self, config: PrometheusConfig | None = None) -> None:
        """Initialize Prometheus metrics server.

        Args:
            config: Optional Prometheus configuration
        """
        self.config = config or PrometheusConfig()
        self._registry = CollectorRegistry()
        self._server: asyncio.Server | None = None

        if self.config.enable_default_metrics:
            # Import and enable default process metrics
            try:
                from prometheus_client import GC_COLLECTOR, PLATFORM_COLLECTOR, PROCESS_COLLECTOR

                if PROCESS_COLLECTOR:
                    self._registry.register(PROCESS_COLLECTOR)
                if PLATFORM_COLLECTOR:
                    self._registry.register(PLATFORM_COLLECTOR)
                if GC_COLLECTOR:
                    self._registry.register(GC_COLLECTOR)
            except Exception as e:
                logger.warning(f"Failed to register default collectors: {e}")

        logger.info(
            f"Prometheus metrics server initialized on {self.config.host}:{self.config.port}"
        )

    def register_counter(
        self,
        name: str,
        description: str,
        labelnames: Sequence[str] | None = None,
    ) -> Counter:
        """Register a counter metric.

        Args:
            name: Metric name (prefix will be added automatically)
            description: Metric description
            labelnames: Optional sequence of label names

        Returns:
            Registered Counter instance
        """
        full_name = f"{self.config.prefix}_{name}"
        counter = Counter(
            full_name,
            description,
            labelnames=labelnames or (),
            registry=self._registry,
        )
        logger.debug(f"Registered counter: {full_name}")
        return counter

    def register_gauge(
        self,
        name: str,
        description: str,
        labelnames: Sequence[str] | None = None,
    ) -> Gauge:
        """Register a gauge metric.

        Args:
            name: Metric name (prefix will be added automatically)
            description: Metric description
            labelnames: Optional sequence of label names

        Returns:
            Registered Gauge instance
        """
        full_name = f"{self.config.prefix}_{name}"
        gauge = Gauge(
            full_name,
            description,
            labelnames=labelnames or (),
            registry=self._registry,
        )
        logger.debug(f"Registered gauge: {full_name}")
        return gauge

    def register_histogram(
        self,
        name: str,
        description: str,
        labelnames: Sequence[str] | None = None,
        buckets: Sequence[float] | None = None,
    ) -> Histogram:
        """Register a histogram metric.

        Args:
            name: Metric name (prefix will be added automatically)
            description: Metric description
            labelnames: Optional sequence of label names
            buckets: Optional histogram buckets

        Returns:
            Registered Histogram instance
        """
        full_name = f"{self.config.prefix}_{name}"
        # Default buckets if not provided
        if buckets is None:
            buckets = (
                0.005,
                0.01,
                0.025,
                0.05,
                0.075,
                0.1,
                0.25,
                0.5,
                0.75,
                1.0,
                2.5,
                5.0,
                7.5,
                10.0,
                float("inf"),
            )
        histogram = Histogram(
            full_name,
            description,
            labelnames=labelnames or (),
            buckets=buckets,
            registry=self._registry,
        )
        logger.debug(f"Registered histogram: {full_name}")
        return histogram

    def get_metrics_output(self) -> str:
        """Get metrics output in Prometheus text format.

        Returns:
            Metrics output as string
        """
        return generate_latest(self._registry).decode("utf-8")

    async def _handle_request(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle HTTP request for metrics endpoint.

        Args:
            reader: Stream reader for incoming data
            writer: Stream writer for outgoing data
        """
        try:
            # Read HTTP request (we don't need to parse it fully)
            await reader.read(1024)

            # Generate metrics output
            metrics_output = self.get_metrics_output()

            # Send HTTP response
            response = (
                f"HTTP/1.1 200 OK\r\n"
                f"Content-Type: {CONTENT_TYPE_LATEST}\r\n"
                f"Content-Length: {len(metrics_output)}\r\n"
                f"\r\n"
                f"{metrics_output}"
            )

            writer.write(response.encode("utf-8"))
            await writer.drain()

        except Exception as e:
            logger.error(f"Error handling metrics request: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def start(self) -> None:
        """Start the Prometheus metrics server."""
        try:
            self._server = await asyncio.start_server(
                self._handle_request,
                self.config.host,
                self.config.port,
            )

            addr = self._server.sockets[0].getsockname()
            logger.info(f"Prometheus metrics server started on {addr[0]}:{addr[1]}")

        except Exception as e:
            logger.error(f"Failed to start Prometheus metrics server: {e}")
            raise

    async def stop(self) -> None:
        """Stop the Prometheus metrics server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("Prometheus metrics server stopped")


def get_metrics_server(config: PrometheusConfig | None = None) -> PrometheusMetricsServer:
    """Get or create the global metrics server instance.

    Args:
        config: Optional Prometheus configuration

    Returns:
        Global PrometheusMetricsServer instance
    """
    global _metrics_server
    if _metrics_server is None:
        _metrics_server = PrometheusMetricsServer(config)
    return _metrics_server


async def start_prometheus_server(
    port: int = 9090,
    host: str = "0.0.0.0",
    prefix: str = "gpt_bitcoin",
) -> PrometheusMetricsServer:
    """Convenience function to start Prometheus server.

    Args:
        port: Port number for metrics server
        host: Host address to bind
        prefix: Prefix for all metrics

    Returns:
        Started PrometheusMetricsServer instance
    """
    config = PrometheusConfig(port=port, host=host, prefix=prefix)
    server = get_metrics_server(config)
    await server.start()
    return server


__all__ = [
    "PrometheusConfig",
    "PrometheusMetricsServer",
    "get_metrics_server",
    "start_prometheus_server",
]
