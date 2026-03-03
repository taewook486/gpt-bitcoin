"""Integration tests for Alert webhook handler."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from gpt_bitcoin.presentation.alert_handlers import (
    Alert,
    AlertAnnotation,
    AlertDeduplicator,
    AlertLabel,
    AlertManagerWebhook,
    get_deduplicator,
    router,
)


@pytest.fixture
def app():
    """Create FastAPI app with alert router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(app):
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def sample_alert_data():
    """Sample alert data for testing."""
    return {
        "status": "firing",
        "labels": {
            "alertname": "HighErrorRate",
            "severity": "critical",
            "component": "application",
        },
        "annotations": {
            "summary": "High error rate detected",
            "description": "Error rate is 10%",
            "value": "0.10",
        },
        "startsAt": "2025-01-01T00:00:00Z",
        "endsAt": "2025-01-01T00:01:00Z",
        "generatorURL": "http://prometheus:9090/graph",
        "fingerprint": "abc123",
        "receiver": "default-receiver",
    }


@pytest.fixture
def sample_webhook_data(sample_alert_data):
    """Sample webhook payload for testing."""
    return {
        "receiver": "default-receiver",
        "status": "firing",
        "alerts": [sample_alert_data],
        "groupLabels": {
            "alertname": "HighErrorRate",
        },
        "commonLabels": {
            "severity": "critical",
            "component": "application",
        },
        "commonAnnotations": {
            "summary": "High error rate detected",
        },
        "externalURL": "http://alertmanager:9093",
        "version": "4",
        "groupKey": "{}:{}",
        "truncatedAlerts": 0,
    }


class TestAlertModels:
    """Test Pydantic models for alerts."""

    def test_alert_label_model(self):
        """Test AlertLabel model validation."""
        label = AlertLabel(
            alertname="TestAlert",
            severity="warning",
            component="test",
        )
        assert label.alertname == "TestAlert"
        assert label.severity == "warning"
        assert label.component == "test"
        assert label.cost_type is None

    def test_alert_label_with_cost_type(self):
        """Test AlertLabel with cost_type."""
        label = AlertLabel(
            alertname="GLMAPICostHigh",
            severity="warning",
            component="api",
            cost_type="glm",
        )
        assert label.cost_type == "glm"

    def test_alert_annotation_model(self):
        """Test AlertAnnotation model validation."""
        annotation = AlertAnnotation(
            summary="Test summary",
            description="Test description",
            value="100",
        )
        assert annotation.summary == "Test summary"
        assert annotation.description == "Test description"
        assert annotation.value == "100"

    def test_alert_model(self, sample_alert_data):
        """Test Alert model validation."""
        alert = Alert(**sample_alert_data)
        assert alert.status == "firing"
        assert alert.labels.alertname == "HighErrorRate"
        assert alert.annotations.summary == "High error rate detected"
        assert alert.fingerprint == "abc123"

    def test_webhook_model(self, sample_webhook_data):
        """Test AlertManagerWebhook model validation."""
        webhook = AlertManagerWebhook(**sample_webhook_data)
        assert webhook.receiver == "default-receiver"
        assert webhook.status == "firing"
        assert len(webhook.alerts) == 1
        assert webhook.alerts[0].labels.alertname == "HighErrorRate"


class TestAlertDeduplicator:
    """Test AlertDeduplicator class."""

    def test_deduplicator_initialization(self):
        """Test deduplicator initialization without Redis."""
        deduplicator = AlertDeduplicator()
        assert deduplicator.redis_client is None
        assert isinstance(deduplicator.local_cache, dict)
        assert deduplicator.dedup_window_seconds == 300

    def test_dedup_key_generation(self, sample_alert_data):
        """Test deduplication key generation."""
        deduplicator = AlertDeduplicator()
        alert = Alert(**sample_alert_data)

        key1 = deduplicator._get_dedup_key(alert)
        key2 = deduplicator._get_dedup_key(alert)

        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex digest length

    def test_local_cache_deduplication(self, sample_alert_data):
        """Test local cache deduplication."""
        deduplicator = AlertDeduplicator()
        alert = Alert(**sample_alert_data)

        # First check should not be duplicate
        assert not deduplicator.is_duplicate(alert)

        # Second check should be duplicate
        assert deduplicator.is_duplicate(alert)

    def test_different_alerts_not_duplicates(self, sample_alert_data):
        """Test that different alerts are not duplicates."""
        deduplicator = AlertDeduplicator()

        alert1 = Alert(**sample_alert_data)
        alert2_data = sample_alert_data.copy()
        alert2_data["fingerprint"] = "def456"
        alert2 = Alert(**alert2_data)

        assert not deduplicator.is_duplicate(alert1)
        assert not deduplicator.is_duplicate(alert2)

    def test_status_change_not_duplicate(self, sample_alert_data):
        """Test that status change is not duplicate."""
        deduplicator = AlertDeduplicator()

        firing_alert = Alert(**sample_alert_data)
        resolved_data = sample_alert_data.copy()
        resolved_data["status"] = "resolved"
        resolved_alert = Alert(**resolved_data)

        assert not deduplicator.is_duplicate(firing_alert)
        assert not deduplicator.is_duplicate(resolved_alert)

    def test_cache_cleanup(self, sample_alert_data):
        """Test cache cleanup removes expired entries."""
        deduplicator = AlertDeduplicator()
        deduplicator.dedup_window_seconds = 1  # 1 second for testing

        alert = Alert(**sample_alert_data)
        deduplicator.is_duplicate(alert)

        assert len(deduplicator.local_cache) == 1

        # Wait for expiration
        import time

        time.sleep(2)

        deduplicator.cleanup_cache()

        assert len(deduplicator.local_cache) == 0

    @pytest.mark.asyncio
    async def test_redis_deduplication(self, sample_alert_data):
        """Test Redis-based deduplication."""
        # Mock Redis client (sync interface)
        redis_mock = MagicMock()
        redis_mock.get = MagicMock(return_value=None)
        redis_mock.setex = MagicMock(return_value=True)

        deduplicator = AlertDeduplicator(redis_client=redis_mock)
        alert = Alert(**sample_alert_data)

        # First check - not duplicate
        assert not deduplicator.is_duplicate(alert)
        redis_mock.get.assert_called_once()
        redis_mock.setex.assert_called_once()

        # Second check - duplicate
        redis_mock.get = MagicMock(return_value="2025-01-01T00:00:00+00:00")
        assert deduplicator.is_duplicate(alert)

    @pytest.mark.asyncio
    async def test_redis_fallback_to_local(self, sample_alert_data):
        """Test fallback to local cache when Redis fails."""
        redis_mock = MagicMock()
        redis_mock.get = MagicMock(side_effect=Exception("Redis connection error"))

        deduplicator = AlertDeduplicator(redis_client=redis_mock)
        alert = Alert(**sample_alert_data)

        # Should fall back to local cache
        assert not deduplicator.is_duplicate(alert)
        assert len(deduplicator.local_cache) == 1


class TestWebhookEndpoints:
    """Test webhook HTTP endpoints."""

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/alerts/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "alert-handlers"
        assert "timestamp" in data

    def test_stats_endpoint(self, client):
        """Test stats endpoint."""
        # Reset global deduplicator to ensure consistent state
        from gpt_bitcoin.presentation.alert_handlers import _deduplicator
        import gpt_bitcoin.presentation.alert_handlers as handler_module
        handler_module._deduplicator = None

        response = client.get("/alerts/stats")

        assert response.status_code == 200
        data = response.json()
        assert "deduplication" in data
        assert data["deduplication"]["backend"] in ["local_cache", "redis"]
        assert "cache_size" in data["deduplication"]
        assert "timestamp" in data

    def test_webhook_receive_single_alert(self, client, sample_webhook_data):
        """Test receiving single alert via webhook."""
        with patch("gpt_bitcoin.presentation.alert_handlers.get_deduplicator") as mock_dedup:
            mock_dedup.return_value = AlertDeduplicator()

            response = client.post("/alerts/webhook", json=sample_webhook_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["processed_alerts"] == 1
            assert data["deduplicated_alerts"] == 0

    def test_webhook_receive_multiple_alerts(self, client, sample_alert_data):
        """Test receiving multiple alerts via webhook."""
        webhook_data = {
            "receiver": "default-receiver",
            "status": "firing",
            "alerts": [sample_alert_data, sample_alert_data.copy()],
            "groupLabels": {},
            "commonLabels": {},
            "commonAnnotations": {},
            "externalURL": "http://alertmanager:9093",
            "version": "4",
            "groupKey": "{}:{}",
        }

        with patch("gpt_bitcoin.presentation.alert_handlers.get_deduplicator") as mock_dedup:
            deduplicator = AlertDeduplicator()
            mock_dedup.return_value = deduplicator

            response = client.post("/alerts/webhook", json=webhook_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["processed_alerts"] == 1  # Second is deduplicated
            assert data["deduplicated_alerts"] == 1

    def test_webhook_deduplication(self, client, sample_alert_data):
        """Test alert deduplication in webhook."""
        webhook_data = {
            "receiver": "default-receiver",
            "status": "firing",
            "alerts": [sample_alert_data],
            "groupLabels": {},
            "commonLabels": {},
            "commonAnnotations": {},
            "externalURL": "http://alertmanager:9093",
            "version": "4",
            "groupKey": "{}:{}",
        }

        with patch("gpt_bitcoin.presentation.alert_handlers.get_deduplicator") as mock_dedup:
            deduplicator = AlertDeduplicator()
            mock_dedup.return_value = deduplicator

            # First request - alert processed
            response1 = client.post("/alerts/webhook", json=webhook_data)
            assert response1.json()["processed_alerts"] == 1
            assert response1.json()["deduplicated_alerts"] == 0

            # Second request - alert deduplicated
            response2 = client.post("/alerts/webhook", json=webhook_data)
            assert response2.json()["processed_alerts"] == 0
            assert response2.json()["deduplicated_alerts"] == 1

    def test_webhook_resolved_alert(self, client, sample_alert_data):
        """Test receiving resolved alert."""
        resolved_data = sample_alert_data.copy()
        resolved_data["status"] = "resolved"

        webhook_data = {
            "receiver": "default-receiver",
            "status": "resolved",
            "alerts": [resolved_data],
            "groupLabels": {},
            "commonLabels": {},
            "commonAnnotations": {},
            "externalURL": "http://alertmanager:9093",
            "version": "4",
            "groupKey": "{}:{}",
        }

        with patch("gpt_bitcoin.presentation.alert_handlers.get_deduplicator") as mock_dedup:
            mock_dedup.return_value = AlertDeduplicator()

            response = client.post("/alerts/webhook", json=webhook_data)

            assert response.status_code == 200
            assert response.json()["status"] == "success"

    def test_webhook_invalid_payload(self, client):
        """Test webhook with invalid payload."""
        invalid_data = {
            "receiver": "test",
            # Missing required fields
        }

        response = client.post("/alerts/webhook", json=invalid_data)

        assert response.status_code == 422  # Validation error

    def test_webhook_critical_alert_logging(self, client, sample_alert_data):
        """Test critical alert is logged at error level."""
        critical_data = sample_alert_data.copy()
        critical_data["labels"]["severity"] = "critical"

        webhook_data = {
            "receiver": "critical-alerts",
            "status": "firing",
            "alerts": [critical_data],
            "groupLabels": {},
            "commonLabels": {},
            "commonAnnotations": {},
            "externalURL": "http://alertmanager:9093",
            "version": "4",
            "groupKey": "{}:{}",
        }

        with patch("gpt_bitcoin.presentation.alert_handlers.get_deduplicator") as mock_dedup:
            with patch("gpt_bitcoin.presentation.alert_handlers.logger") as mock_logger:
                mock_dedup.return_value = AlertDeduplicator()

                response = client.post("/alerts/webhook", json=webhook_data)

                assert response.status_code == 200
                # Verify error level logging was called
                mock_logger.error.assert_called_once()

    def test_webhook_cost_alert(self, client):
        """Test cost alert handling."""
        cost_alert = {
            "status": "firing",
            "labels": {
                "alertname": "GLMAPICostHigh",
                "severity": "warning",
                "component": "api",
                "cost_type": "glm",
            },
            "annotations": {
                "summary": "High GLM API cost",
                "description": "Cost exceeds threshold",
                "value": "15000",
            },
            "startsAt": "2025-01-01T00:00:00Z",
            "endsAt": "2025-01-01T00:01:00Z",
            "generatorURL": "http://prometheus:9090/graph",
            "fingerprint": "cost123",
            "receiver": "cost-alerts",
        }

        webhook_data = {
            "receiver": "cost-alerts",
            "status": "firing",
            "alerts": [cost_alert],
            "groupLabels": {"alertname": "GLMAPICostHigh"},
            "commonLabels": {"component": "api", "cost_type": "glm"},
            "commonAnnotations": {"summary": "High GLM API cost"},
            "externalURL": "http://alertmanager:9093",
            "version": "4",
            "groupKey": "{}:{}",
        }

        with patch("gpt_bitcoin.presentation.alert_handlers.get_deduplicator") as mock_dedup:
            mock_dedup.return_value = AlertDeduplicator()

            response = client.post("/alerts/webhook", json=webhook_data)

            assert response.status_code == 200
            assert response.json()["status"] == "success"


@pytest.mark.asyncio
class TestAsyncWebhookEndpoints:
    """Test async webhook endpoints."""

    async def test_async_webhook_receive(self, async_client, sample_webhook_data):
        """Test async webhook reception."""
        with patch("gpt_bitcoin.presentation.alert_handlers.get_deduplicator") as mock_dedup:
            mock_dedup.return_value = AlertDeduplicator()

            response = await async_client.post("/alerts/webhook", json=sample_webhook_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    async def test_concurrent_webhook_requests(self, async_client, sample_alert_data):
        """Test concurrent webhook requests."""
        import asyncio

        webhook_data = {
            "receiver": "default-receiver",
            "status": "firing",
            "alerts": [sample_alert_data],
            "groupLabels": {},
            "commonLabels": {},
            "commonAnnotations": {},
            "externalURL": "http://alertmanager:9093",
            "version": "4",
            "groupKey": "{}:{}",
        }

        # Create different fingerprints for each request
        async def send_request(index):
            data = webhook_data.copy()
            data["alerts"][0]["fingerprint"] = f"test{index}"
            return await async_client.post("/alerts/webhook", json=data)

        with patch("gpt_bitcoin.presentation.alert_handlers.get_deduplicator") as mock_dedup:
            mock_dedup.return_value = AlertDeduplicator()

            # Send 10 concurrent requests
            tasks = [send_request(i) for i in range(10)]
            responses = await asyncio.gather(*tasks)

            # All should succeed
            for response in responses:
                assert response.status_code == 200
                assert response.json()["status"] == "success"
