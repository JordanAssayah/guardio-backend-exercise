"""
Tests for the internal router - health check and stats endpoints.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import internal
from app.services.stats import StatsCollector, stats_collector


@pytest.fixture
def app():
    """Create a test FastAPI app."""
    test_app = FastAPI()
    test_app.include_router(internal.router)
    return test_app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_200(self, client):
        """Health endpoint should return 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_status_healthy(self, client):
        """Health endpoint should return healthy status."""
        response = client.get("/health")
        assert response.json() == {"status": "healthy"}


class TestStatsEndpoint:
    """Tests for the /stats endpoint."""

    @pytest.fixture(autouse=True)
    def reset_stats(self):
        """Reset stats collector before and after each test."""
        # Clear internal state
        stats_collector._stats.clear()
        yield
        stats_collector._stats.clear()

    def test_stats_returns_200(self, client):
        """Stats endpoint should return 200."""
        response = client.get("/stats")
        assert response.status_code == 200

    def test_stats_empty_initially(self, client):
        """Stats should be empty when no requests recorded."""
        response = client.get("/stats")
        assert response.json() == {}

    async def test_stats_returns_recorded_data(self, client):
        """Stats should return data for recorded requests."""
        # Record some requests
        await stats_collector.record_request(
            url="http://endpoint1.com",
            incoming_bytes=100,
            outgoing_bytes=50,
            response_time_ms=25.0,
            is_error=False
        )
        await stats_collector.record_request(
            url="http://endpoint2.com",
            incoming_bytes=200,
            outgoing_bytes=100,
            response_time_ms=50.0,
            is_error=True
        )
        
        response = client.get("/stats")
        data = response.json()
        
        assert "http://endpoint1.com" in data
        assert "http://endpoint2.com" in data
        
        assert data["http://endpoint1.com"]["request_count"] == 1
        assert data["http://endpoint1.com"]["error_count"] == 0
        
        assert data["http://endpoint2.com"]["request_count"] == 1
        assert data["http://endpoint2.com"]["error_count"] == 1

    async def test_stats_structure(self, client):
        """Stats should have the expected structure."""
        await stats_collector.record_request(
            url="http://test.com",
            incoming_bytes=1000,
            outgoing_bytes=500,
            response_time_ms=100.0,
            is_error=False
        )
        
        response = client.get("/stats")
        endpoint_stats = response.json()["http://test.com"]
        
        # Verify all expected fields are present
        assert "request_count" in endpoint_stats
        assert "error_count" in endpoint_stats
        assert "error_rate_percent" in endpoint_stats
        assert "incoming_bytes" in endpoint_stats
        assert "outgoing_bytes" in endpoint_stats
        assert "avg_response_time_ms" in endpoint_stats
        
        # Verify values
        assert endpoint_stats["request_count"] == 1
        assert endpoint_stats["incoming_bytes"] == 1000
        assert endpoint_stats["outgoing_bytes"] == 500
        assert endpoint_stats["avg_response_time_ms"] == 100.0

