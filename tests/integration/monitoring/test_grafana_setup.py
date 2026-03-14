"""
Integration tests for Grafana monitoring setup.

Tests verify:
- Grafana service starts correctly
- Prometheus datasource is configured
- Dashboard is provisioned
- Health endpoints are accessible
"""

import asyncio

import aiohttp
import pytest

# Test configuration
GRAFANA_HOST = "localhost"
GRAFANA_PORT = 3000
GRAFANA_BASE_URL = f"http://{GRAFANA_HOST}:{GRAFANA_PORT}"
GRAFANA_ADMIN_USER = "admin"
GRAFANA_ADMIN_PASSWORD = "admin"

PROMETHEUS_HOST = "localhost"
PROMETHEUS_PORT = 9090
PROMETHEUS_BASE_URL = f"http://{PROMETHEUS_HOST}:{PROMETHEUS_PORT}"


@pytest.fixture
async def http_session() -> aiohttp.ClientSession:
    """Create HTTP session for API requests."""
    async with aiohttp.ClientSession() as session:
        yield session


@pytest.fixture
def grafana_auth() -> aiohttp.BasicAuth:
    """Create Basic Auth for Grafana API."""
    return aiohttp.BasicAuth(GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD)


class TestGrafanaService:
    """Tests for Grafana service availability."""

    @pytest.mark.asyncio
    async def test_grafana_health_endpoint(self, http_session: aiohttp.ClientSession) -> None:
        """Test that Grafana health endpoint is accessible."""
        max_retries = 30
        retry_interval = 2

        for attempt in range(max_retries):
            try:
                async with http_session.get(f"{GRAFANA_BASE_URL}/api/health") as response:
                    assert response.status == 200, f"Expected 200, got {response.status}"
                    data = await response.json()
                    assert data.get("database") == "ok", "Database health check failed"
                    return
            except aiohttp.ClientError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_interval)
                else:
                    pytest.fail(
                        f"Grafana health endpoint not accessible after {max_retries} retries"
                    )

    @pytest.mark.asyncio
    async def test_grafana_api_ready(
        self, http_session: aiohttp.ClientSession, grafana_auth: aiohttp.BasicAuth
    ) -> None:
        """Test that Grafana API is ready to accept requests."""
        async with http_session.get(
            f"{GRAFANA_BASE_URL}/api/frontend/settings", auth=grafana_auth
        ) as response:
            assert response.status == 200, f"Expected 200, got {response.status}"
            data = await response.json()
            assert "defaults" in data, "API response missing expected structure"


class TestPrometheusDatasource:
    """Tests for Prometheus datasource configuration."""

    @pytest.mark.asyncio
    async def test_prometheus_datasource_exists(
        self, http_session: aiohttp.ClientSession, grafana_auth: aiohttp.BasicAuth
    ) -> None:
        """Test that Prometheus datasource is configured."""
        async with http_session.get(
            f"{GRAFANA_BASE_URL}/api/datasources", auth=grafana_auth
        ) as response:
            assert response.status == 200, f"Expected 200, got {response.status}"
            datasources = await response.json()

            prometheus_found = False
            for ds in datasources:
                if ds.get("type") == "prometheus":
                    prometheus_found = True
                    assert ds.get("name") == "Prometheus", "Datasource name mismatch"
                    assert ds.get("isDefault") is True, "Prometheus should be default datasource"
                    break

            assert prometheus_found, "Prometheus datasource not found"

    @pytest.mark.asyncio
    async def test_prometheus_datasource_health(
        self, http_session: aiohttp.ClientSession, grafana_auth: aiohttp.BasicAuth
    ) -> None:
        """Test that Prometheus datasource can connect to Prometheus."""
        # Get datasource ID
        async with http_session.get(
            f"{GRAFANA_BASE_URL}/api/datasources/name/Prometheus", auth=grafana_auth
        ) as response:
            if response.status == 404:
                pytest.skip("Prometheus datasource not found")
            assert response.status == 200, f"Expected 200, got {response.status}"
            ds = await response.json()
            ds_id = ds.get("id")

        # Test datasource health
        async with http_session.post(
            f"{GRAFANA_BASE_URL}/api/datasources/{ds_id}/health",
            auth=grafana_auth,
        ) as response:
            assert response.status == 200, f"Expected 200, got {response.status}"
            data = await response.json()
            assert data.get("status") == "OK", f"Datasource health check failed: {data}"

    @pytest.mark.asyncio
    async def test_prometheus_query_via_grafana(
        self, http_session: aiohttp.ClientSession, grafana_auth: aiohttp.BasicAuth
    ) -> None:
        """Test that Grafana can query Prometheus metrics."""
        query = {
            "queries": [
                {
                    "refId": "A",
                    "datasource": {"type": "prometheus", "uid": "prometheus"},
                    "expr": "up",
                }
            ]
        }

        async with http_session.post(
            f"{GRAFANA_BASE_URL}/api/ds/query",
            auth=grafana_auth,
            json=query,
        ) as response:
            assert response.status == 200, f"Expected 200, got {response.status}"
            data = await response.json()
            assert "results" in data, "Query response missing results"
            assert "A" in data["results"], "Query result missing refId A"


class TestDashboardProvisioning:
    """Tests for dashboard auto-provisioning."""

    @pytest.mark.asyncio
    async def test_trading_dashboard_exists(
        self, http_session: aiohttp.ClientSession, grafana_auth: aiohttp.BasicAuth
    ) -> None:
        """Test that Trading Overview dashboard is provisioned."""
        # Search for dashboard by UID
        async with http_session.get(
            f"{GRAFANA_BASE_URL}/api/dashboards/uid/trading-overview",
            auth=grafana_auth,
        ) as response:
            assert response.status == 200, f"Expected 200, got {response.status}"
            data = await response.json()
            dashboard = data.get("dashboard", {})
            assert dashboard.get("title") == "Trading Overview", "Dashboard title mismatch"
            assert dashboard.get("uid") == "trading-overview", "Dashboard UID mismatch"

    @pytest.mark.asyncio
    async def test_dashboard_panels_exist(
        self, http_session: aiohttp.ClientSession, grafana_auth: aiohttp.BasicAuth
    ) -> None:
        """Test that dashboard contains expected panels."""
        async with http_session.get(
            f"{GRAFANA_BASE_URL}/api/dashboards/uid/trading-overview",
            auth=grafana_auth,
        ) as response:
            assert response.status == 200, f"Expected 200, got {response.status}"
            data = await response.json()
            panels = data.get("dashboard", {}).get("panels", [])

            # Check for expected row panels
            row_titles = [p.get("title") for p in panels if p.get("type") == "row"]
            expected_rows = [
                "Trading Performance",
                "API Metrics",
                "Cost Monitoring",
                "System Health",
            ]

            for expected_row in expected_rows:
                assert expected_row in row_titles, f"Missing row panel: {expected_row}"

    @pytest.mark.asyncio
    async def test_dashboard_prometheus_queries(
        self, http_session: aiohttp.ClientSession, grafana_auth: aiohttp.BasicAuth
    ) -> None:
        """Test that dashboard panels use Prometheus datasource."""
        async with http_session.get(
            f"{GRAFANA_BASE_URL}/api/dashboards/uid/trading-overview",
            auth=grafana_auth,
        ) as response:
            assert response.status == 200, f"Expected 200, got {response.status}"
            data = await response.json()
            panels = data.get("dashboard", {}).get("panels", [])

            # Collect all panel targets
            all_targets = []
            for panel in panels:
                targets = panel.get("targets", [])
                all_targets.extend(targets)

            # Verify Prometheus datasource usage
            for target in all_targets:
                ds_type = target.get("datasource", {}).get("type")
                assert ds_type == "prometheus", f"Panel uses non-Prometheus datasource: {ds_type}"


class TestGrafanaPrometheusIntegration:
    """Tests for Grafana-Prometheus integration."""

    @pytest.mark.asyncio
    async def test_prometheus_self_monitoring(self, http_session: aiohttp.ClientSession) -> None:
        """Test that Prometheus is collecting metrics from itself."""
        async with http_session.get(
            f"{PROMETHEUS_BASE_URL}/api/v1/query",
            params={"query": "up{job='prometheus'}"},
        ) as response:
            assert response.status == 200, f"Expected 200, got {response.status}"
            data = await response.json()
            assert data.get("status") == "success", "Prometheus query failed"
            result = data.get("data", {}).get("result", [])
            assert len(result) > 0, "No metrics found for prometheus job"

    @pytest.mark.asyncio
    async def test_grafana_query_prometheus_metrics(
        self, http_session: aiohttp.ClientSession, grafana_auth: aiohttp.BasicAuth
    ) -> None:
        """Test that Grafana can query Prometheus metrics through dashboard."""
        # Query a simple metric through Grafana's datasource proxy
        query = {
            "queries": [
                {
                    "refId": "A",
                    "datasource": {"type": "prometheus", "uid": "prometheus"},
                    "expr": "prometheus_build_info",
                }
            ]
        }

        async with http_session.post(
            f"{GRAFANA_BASE_URL}/api/ds/query",
            auth=grafana_auth,
            json=query,
        ) as response:
            assert response.status == 200, f"Expected 200, got {response.status}"
            data = await response.json()
            assert "results" in data, "Query response missing results"


class TestGrafanaConfiguration:
    """Tests for Grafana configuration."""

    @pytest.mark.asyncio
    async def test_grafana_settings(
        self, http_session: aiohttp.ClientSession, grafana_auth: aiohttp.BasicAuth
    ) -> None:
        """Test Grafana settings are correctly configured."""
        async with http_session.get(
            f"{GRAFANA_BASE_URL}/api/frontend/settings",
            auth=grafana_auth,
        ) as response:
            assert response.status == 200, f"Expected 200, got {response.status}"
            data = await response.json()
            defaults = data.get("defaults", {})

            # Verify basic settings
            assert "datasources" in defaults, "Missing datasources configuration"

    @pytest.mark.asyncio
    async def test_anonymous_access_disabled(self, http_session: aiohttp.ClientSession) -> None:
        """Test that anonymous access is disabled."""
        async with http_session.get(f"{GRAFANA_BASE_URL}/api/search") as response:
            # Should return 401 without authentication
            assert response.status == 401, f"Expected 401, got {response.status}"


# Smoke tests for quick verification
class TestSmokeTests:
    """Quick smoke tests for basic functionality."""

    @pytest.mark.asyncio
    async def test_grafana_ui_accessible(self, http_session: aiohttp.ClientSession) -> None:
        """Test that Grafana UI is accessible."""
        async with http_session.get(f"{GRAFANA_BASE_URL}/") as response:
            assert response.status == 200, f"Expected 200, got {response.status}"

    @pytest.mark.asyncio
    async def test_prometheus_ui_accessible(self, http_session: aiohttp.ClientSession) -> None:
        """Test that Prometheus UI is accessible."""
        async with http_session.get(f"{PROMETHEUS_BASE_URL}/") as response:
            assert response.status == 200, f"Expected 200, got {response.status}"

    @pytest.mark.asyncio
    async def test_grafana_login(
        self, http_session: aiohttp.ClientSession, grafana_auth: aiohttp.BasicAuth
    ) -> None:
        """Test that Grafana login works with default credentials."""
        async with http_session.get(f"{GRAFANA_BASE_URL}/api/user", auth=grafana_auth) as response:
            assert response.status == 200, f"Expected 200, got {response.status}"
            data = await response.json()
            assert data.get("login") == GRAFANA_ADMIN_USER, "Login user mismatch"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
