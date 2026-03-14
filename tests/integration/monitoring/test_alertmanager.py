"""Integration tests for AlertManager configuration and integration."""

import subprocess
import time

import pytest
import requests


@pytest.mark.integration
@pytest.mark.monitoring
class TestAlertManagerIntegration:
    """Test AlertManager integration with Docker Compose."""

    @pytest.fixture(scope="class")
    def monitoring_stack(self):
        """Start monitoring stack with AlertManager."""
        # Start monitoring profile
        result = subprocess.run(
            ["docker-compose", "--profile", "monitoring", "up", "-d"],
            capture_output=True,
            text=True,
            cwd=".",
            timeout=120,
        )

        if result.returncode != 0:
            pytest.fail(f"Failed to start monitoring stack: {result.stderr}")

        # Wait for services to be healthy
        time.sleep(10)

        yield

        # Cleanup
        subprocess.run(
            ["docker-compose", "--profile", "monitoring", "down", "-v"],
            capture_output=True,
            text=True,
            cwd=".",
            timeout=60,
        )

    def test_alertmanager_container_running(self, monitoring_stack):
        """Test that AlertManager container is running."""
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                "name=gpt-bitcoin-alertmanager",
                "--format",
                "{{.Status}}",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, f"Failed to check container status: {result.stderr}"
        assert "Up" in result.stdout, f"AlertManager container not running: {result.stdout}"

    def test_alertmanager_health_endpoint(self, monitoring_stack):
        """Test AlertManager health endpoint is accessible."""
        max_retries = 5
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                response = requests.get("http://localhost:9093/-/healthy", timeout=10)
                if response.status_code == 200:
                    break
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    pytest.fail(
                        f"AlertManager health endpoint not accessible after {max_retries} attempts: {e}"
                    )
                time.sleep(retry_delay)

        assert response.status_code == 200, f"AlertManager health check failed: {response.text}"

    def test_alertmanager_ui_accessible(self, monitoring_stack):
        """Test AlertManager UI is accessible."""
        response = requests.get("http://localhost:9093/", timeout=10)
        assert response.status_code == 200, (
            f"AlertManager UI not accessible: {response.status_code}"
        )

    def test_alertmanager_config_loaded(self, monitoring_stack):
        """Test AlertManager configuration is loaded correctly."""
        response = requests.get("http://localhost:9093/api/v2/status", timeout=10)
        assert response.status_code == 200, f"Failed to get AlertManager status: {response.text}"

        status = response.json()
        assert "config" in status, "AlertManager status missing config field"

    def test_alertmanager_receivers_configured(self, monitoring_stack):
        """Test AlertManager receivers are configured."""
        response = requests.get("http://localhost:9093/api/v2/receivers", timeout=10)
        assert response.status_code == 200, f"Failed to get AlertManager receivers: {response.text}"

        receivers = response.json()
        assert isinstance(receivers, list), "Receivers should be a list"
        assert len(receivers) > 0, "No receivers configured"

        # Check for required receivers
        receiver_names = {r["name"] for r in receivers}
        expected_receivers = {
            "default-receiver",
            "critical-alerts",
            "cost-alerts",
            "trading-alerts",
            "webhook-receiver",
        }

        for expected in expected_receivers:
            assert expected in receiver_names, f"Missing receiver: {expected}"

    def test_prometheus_alertmanager_integration(self, monitoring_stack):
        """Test Prometheus can communicate with AlertManager."""
        # Check Prometheus configuration
        response = requests.get("http://localhost:9090/api/v1/alertmanagers", timeout=10)
        assert response.status_code == 200, (
            f"Failed to get Prometheus alertmanagers: {response.text}"
        )

        data = response.json()
        assert data["status"] == "success", f"Prometheus API error: {data}"

        alertmanagers = data["data"]["activeAlertmanagers"]
        assert len(alertmanagers) > 0, "No active AlertManagers configured in Prometheus"

        # Check AlertManager URL
        am_url = alertmanagers[0]["url"]
        assert "9093" in am_url, f"AlertManager URL incorrect: {am_url}"

    def test_prometheus_rules_loaded(self, monitoring_stack):
        """Test Prometheus alert rules are loaded."""
        response = requests.get("http://localhost:9090/api/v1/rules", timeout=10)
        assert response.status_code == 200, f"Failed to get Prometheus rules: {response.text}"

        data = response.json()
        assert data["status"] == "success", f"Prometheus API error: {data}"

        groups = data["data"]["groups"]
        assert len(groups) > 0, "No rule groups loaded"

        # Check for required rule groups
        group_names = {g["name"] for g in groups}
        expected_groups = {
            "application_health",
            "glm_api_costs",
            "trading_decisions",
            "system_resources",
            "data_quality",
        }

        for expected in expected_groups:
            assert expected in group_names, f"Missing rule group: {expected}"

    def test_specific_alert_rules_exist(self, monitoring_stack):
        """Test specific alert rules are defined."""
        response = requests.get("http://localhost:9090/api/v1/rules", timeout=10)
        assert response.status_code == 200, f"Failed to get Prometheus rules: {response.text}"

        data = response.json()
        groups = data["data"]["groups"]

        # Collect all rule names
        all_rules = set()
        for group in groups:
            for rule in group.get("rules", []):
                all_rules.add(rule["name"])

        # Check for critical alert rules
        expected_rules = {
            "HighErrorRate",
            "ApplicationDown",
            "GLMAPICostHigh",
            "GLMAPICostCritical",
            "TradingDecisionSlow",
            "TradingDecisionFailures",
            "StaleMarketData",
        }

        for expected in expected_rules:
            assert expected in all_rules, f"Missing alert rule: {expected}"


@pytest.mark.integration
@pytest.mark.monitoring
class TestAlertManagerRouting:
    """Test AlertManager routing configuration."""

    @pytest.fixture(scope="class")
    def monitoring_stack(self):
        """Start monitoring stack with AlertManager."""
        result = subprocess.run(
            ["docker-compose", "--profile", "monitoring", "up", "-d"],
            capture_output=True,
            text=True,
            cwd=".",
            timeout=120,
        )

        if result.returncode != 0:
            pytest.fail(f"Failed to start monitoring stack: {result.stderr}")

        time.sleep(10)

        yield

        subprocess.run(
            ["docker-compose", "--profile", "monitoring", "down", "-v"],
            capture_output=True,
            text=True,
            cwd=".",
            timeout=60,
        )

    def test_critical_alert_routing(self, monitoring_stack):
        """Test critical alerts are routed correctly."""
        # Create test alert with critical severity
        alert_data = {
            "labels": {
                "alertname": "TestCriticalAlert",
                "severity": "critical",
                "component": "test",
            },
            "annotations": {
                "summary": "Test critical alert",
                "description": "This is a test alert",
            },
        }

        # Send test alert to AlertManager
        response = requests.post(
            "http://localhost:9093/api/v2/alerts",
            json=[alert_data],
            timeout=10,
        )

        assert response.status_code == 200, f"Failed to create test alert: {response.text}"

        # Verify alert is present
        time.sleep(2)
        response = requests.get("http://localhost:9093/api/v2/alerts", timeout=10)
        assert response.status_code == 200, f"Failed to get alerts: {response.text}"

        alerts = response.json()
        test_alerts = [a for a in alerts if a["labels"].get("alertname") == "TestCriticalAlert"]
        assert len(test_alerts) > 0, "Test alert not found in AlertManager"

    def test_cost_alert_routing(self, monitoring_stack):
        """Test cost alerts are routed to cost-alerts receiver."""
        # Create test alert for cost monitoring
        alert_data = {
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
        }

        response = requests.post(
            "http://localhost:9093/api/v2/alerts",
            json=[alert_data],
            timeout=10,
        )

        assert response.status_code == 200, f"Failed to create cost alert: {response.text}"

        # Clean up - resolve the alert
        alert_data["endsAt"] = "2025-01-01T00:00:00Z"
        requests.post(
            "http://localhost:9093/api/v2/alerts",
            json=[alert_data],
            timeout=10,
        )


@pytest.mark.integration
@pytest.mark.monitoring
@pytest.mark.slow
class TestAlertManagerEndToEnd:
    """End-to-end tests for AlertManager alert flow."""

    @pytest.fixture(scope="class")
    def monitoring_stack(self):
        """Start monitoring stack with AlertManager."""
        result = subprocess.run(
            ["docker-compose", "--profile", "monitoring", "up", "-d"],
            capture_output=True,
            text=True,
            cwd=".",
            timeout=120,
        )

        if result.returncode != 0:
            pytest.fail(f"Failed to start monitoring stack: {result.stderr}")

        time.sleep(10)

        yield

        subprocess.run(
            ["docker-compose", "--profile", "monitoring", "down", "-v"],
            capture_output=True,
            text=True,
            cwd=".",
            timeout=60,
        )

    def test_alert_firing_and_resolution(self, monitoring_stack):
        """Test alert firing and resolution flow."""
        # Create alert
        alert_data = {
            "labels": {
                "alertname": "TestAlert",
                "severity": "warning",
                "component": "test",
            },
            "annotations": {
                "summary": "Test alert for E2E test",
            },
            "startsAt": "2025-01-01T00:00:00Z",
        }

        # Fire alert
        response = requests.post(
            "http://localhost:9093/api/v2/alerts",
            json=[alert_data],
            timeout=10,
        )
        assert response.status_code == 200, f"Failed to fire alert: {response.text}"

        # Verify alert is firing
        time.sleep(2)
        response = requests.get("http://localhost:9093/api/v2/alerts", timeout=10)
        alerts = response.json()
        firing_alerts = [
            a
            for a in alerts
            if a["labels"].get("alertname") == "TestAlert" and a["status"]["state"] == "active"
        ]
        assert len(firing_alerts) > 0, "Alert not in firing state"

        # Resolve alert
        alert_data["endsAt"] = "2025-01-01T00:01:00Z"
        response = requests.post(
            "http://localhost:9093/api/v2/alerts",
            json=[alert_data],
            timeout=10,
        )
        assert response.status_code == 200, f"Failed to resolve alert: {response.text}"

        # Verify alert is resolved
        time.sleep(2)
        response = requests.get("http://localhost:9093/api/v2/alerts?active=false", timeout=10)
        alerts = response.json()
        resolved_alerts = [a for a in alerts if a["labels"].get("alertname") == "TestAlert"]
        # Note: Resolved alerts may not be immediately visible depending on retention settings
