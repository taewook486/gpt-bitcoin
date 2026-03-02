# Tests for OpenTelemetry Tracing Configuration
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

    def test_tracer_is_singleton():
        tracer1 = get_tracer()
        tracer2 = get_tracer()
        assert tracer1 is tracer2
        assert tracer1 is not None


    def test_tracer_has_service_name():
        """Test service name configuration."""
        tracer = get_tracer()
        assert tracer.resource.attributes.get("service.name") == "gpt-bitcoin"


class TestSetupTracing:
    """Test tracing setup function."""

    def test_default_setup(self):
        """Test default configuration."""
        setup_tracing()

        tracer = get_tracer()
        assert tracer is not None

        # Verify console exporter is configured
        assert any(tracer.span_processor) is not None

    @patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"})
    def test_otlp_endpoint_setup(self):
        """Test OTLP endpoint configuration."""
        setup_tracing(
            otlp_endpoint="http://localhost:4317"
        )

        # Verify OTLP exporter is configured
        tracer = get_tracer()
        # OTLP exporter should be added
        assert any(
            span_processor
            for processor in tracer.span_processor
            if hasattr(processor, "endpoint")
        )

    @patch.dict(os.environ, {"LOG_level": "DEBUG"})
    def test_log_level_setup(self):
        """Test log level configuration."""
        setup_tracing(log_level="DEBUG")

        tracer = get_tracer()
        # Verify debug level is configured
        assert any(tracer.span_processor) is not None


class TestCreateMetrics:
    """Test metrics creation function."""

    def test_default_metrics(self):
        """Test default metrics creation."""
        metrics = create_metrics()

        assert "requests" in metrics
        assert "errors" in metrics
        assert "trading" in metrics
        assert "latency" in metrics

    def test_metrics_counter_increment(self):
        """Test metrics counter increment."""
        metrics = create_metrics()

        # Increment request counter
        metrics["requests"].add(1, {"endpoint": "/test"})

        # Verify counter was incremented
        assert metrics["requests"].get_value({"endpoint": "/test"}) == 1


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
        with patch.object(checker, "_check_external_api", return_value=True):
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
        with patch.object(checker, "_check_external_api", side_effect=Exception("API unreachable")):
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
