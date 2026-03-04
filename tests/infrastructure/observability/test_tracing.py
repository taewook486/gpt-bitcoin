# Tests for OpenTelemetry Tracing Configuration
import os
import pytest
from unittest.mock import MagicMock, patch

from gpt_bitcoin.infrastructure.observability.tracing import (
    get_tracer,
    setup_tracing,
    create_metrics,
    HealthChecker,
)


class TestGetTracer:
    """Test tracer provider initialization."""

    def test_tracer_is_singleton(self):
        """Test that get_tracer returns the same instance."""
        import gpt_bitcoin.infrastructure.observability.tracing as tracing_module
        tracing_module._tracer_provider = None

        tracer1 = get_tracer()
        tracer2 = get_tracer()
        assert tracer1 is tracer2
        assert tracer1 is not None

    def test_tracer_has_service_name(self):
        """Test service name configuration."""
        import gpt_bitcoin.infrastructure.observability.tracing as tracing_module
        tracing_module._tracer_provider = None

        tracer = get_tracer()
        assert tracer.resource.attributes.get("service.name") == "gpt-bitcoin"


class TestSetupTracing:
    """Test tracing setup function."""

    def test_default_setup(self):
        """Test default configuration."""
        import gpt_bitcoin.infrastructure.observability.tracing as tracing_module
        tracing_module._tracer_provider = None

        setup_tracing()

        tracer = get_tracer()
        assert tracer is not None

    @patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"})
    def test_otlp_endpoint_setup(self):
        """Test OTLP endpoint configuration."""
        import gpt_bitcoin.infrastructure.observability.tracing as tracing_module
        tracing_module._tracer_provider = None

        setup_tracing(
            otlp_endpoint="http://localhost:4317"
        )

        # Verify OTLP exporter is configured
        tracer = get_tracer()
        assert tracer is not None

    @patch.dict(os.environ, {"LOG_level": "DEBUG"})
    def test_log_level_setup(self):
        """Test log level configuration."""
        import gpt_bitcoin.infrastructure.observability.tracing as tracing_module
        tracing_module._tracer_provider = None

        setup_tracing(log_level="DEBUG")

        tracer = get_tracer()
        assert tracer is not None


class TestCreateMetrics:
    """Test metrics creation function."""

    def test_default_metrics(self):
        """Test default metrics creation."""
        import gpt_bitcoin.infrastructure.observability.tracing as tracing_module
        tracing_module._global_meter_provider = None

        metrics = create_metrics()

        assert "requests" in metrics
        assert "errors" in metrics
        assert "trading" in metrics
        assert "latency" in metrics

    def test_metrics_counter_has_add_method(self):
        """Test metrics counter has add method."""
        import gpt_bitcoin.infrastructure.observability.tracing as tracing_module
        tracing_module._global_meter_provider = None

        metrics = create_metrics()

        # Counters should have add method
        assert hasattr(metrics["requests"], "add")
        assert hasattr(metrics["errors"], "add")
        assert hasattr(metrics["trading"], "add")

        # Histogram should have record method
        assert hasattr(metrics["latency"], "record")


class TestHealthChecker:
    """Test health checker functionality."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test health check when all services are healthy."""
        checker = HealthChecker(
            check_external_apis=True,
            timeout_seconds=1.0,
        )

        # Mock external API check
        with patch.object(checker, "_check_external_api_connectivity", return_value=True):
            result = await checker.check_health()

            assert result["status"] == "healthy"
            assert result["checks"]["external_apis"] is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """Test health check when external APIs are unreachable."""
        checker = HealthChecker(
            check_external_apis=True,
            timeout_seconds=1.0,
        )

        # Mock external API check failure
        async def failing_check():
            raise Exception("API unreachable")

        with patch.object(checker, "_check_external_api_connectivity", side_effect=failing_check):
            result = await checker.check_health()

            assert result["status"] == "unhealthy"
            assert result["checks"]["external_apis"] is False

    @pytest.mark.asyncio
    async def test_health_check_without_external_apis(self):
        """Test health check without external API checks."""
        checker = HealthChecker(
            check_external_apis=False,
            timeout_seconds=1.0,
        )

        result = await checker.check_health()

        assert result["status"] == "healthy"
        assert "external_apis" not in result["checks"]
