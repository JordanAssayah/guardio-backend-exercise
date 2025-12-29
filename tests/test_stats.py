"""
Tests for the stats service - metrics collection.
"""
import asyncio

import pytest

from app.services.stats import EndpointStats, StatsCollector, MAX_ENDPOINTS


class TestEndpointStats:
    """Tests for EndpointStats dataclass."""

    def test_default_values(self):
        """New EndpointStats should have zero values."""
        stats = EndpointStats()
        
        assert stats.request_count == 0
        assert stats.error_count == 0
        assert stats.incoming_bytes == 0
        assert stats.outgoing_bytes == 0
        assert stats.total_response_time_ms == 0.0

    def test_error_rate_no_requests(self):
        """Error rate should be 0 when no requests."""
        stats = EndpointStats()
        assert stats.error_rate == 0.0

    def test_error_rate_calculation(self):
        """Error rate should calculate correctly."""
        stats = EndpointStats(request_count=100, error_count=25)
        assert stats.error_rate == 25.0

    def test_error_rate_all_errors(self):
        """Error rate should be 100% when all requests fail."""
        stats = EndpointStats(request_count=10, error_count=10)
        assert stats.error_rate == 100.0

    def test_avg_response_time_no_requests(self):
        """Average response time should be 0 when no requests."""
        stats = EndpointStats()
        assert stats.avg_response_time_ms == 0.0

    def test_avg_response_time_calculation(self):
        """Average response time should calculate correctly."""
        stats = EndpointStats(request_count=10, total_response_time_ms=500.0)
        assert stats.avg_response_time_ms == 50.0

    def test_to_dict(self):
        """to_dict should return all fields with proper formatting."""
        stats = EndpointStats(
            request_count=100,
            error_count=5,
            incoming_bytes=10000,
            outgoing_bytes=5000,
            total_response_time_ms=1234.5678
        )
        
        result = stats.to_dict()
        
        assert result["request_count"] == 100
        assert result["error_count"] == 5
        assert result["error_rate_percent"] == 5.0
        assert result["incoming_bytes"] == 10000
        assert result["outgoing_bytes"] == 5000
        assert result["avg_response_time_ms"] == 12.35  # Rounded to 2 decimals


class TestStatsCollector:
    """Tests for StatsCollector class."""

    @pytest.fixture
    def collector(self):
        """Fresh StatsCollector for each test."""
        return StatsCollector()

    async def test_record_single_request(self, collector):
        """Should record a single request correctly."""
        await collector.record_request(
            url="http://test.com",
            incoming_bytes=100,
            outgoing_bytes=50,
            response_time_ms=25.5,
            is_error=False
        )
        
        stats = await collector.get_all_stats()
        
        assert "http://test.com" in stats
        assert stats["http://test.com"]["request_count"] == 1
        assert stats["http://test.com"]["incoming_bytes"] == 100
        assert stats["http://test.com"]["outgoing_bytes"] == 50
        assert stats["http://test.com"]["avg_response_time_ms"] == 25.5
        assert stats["http://test.com"]["error_count"] == 0

    async def test_record_multiple_requests_same_endpoint(self, collector):
        """Should accumulate stats for same endpoint."""
        for i in range(5):
            await collector.record_request(
                url="http://test.com",
                incoming_bytes=100,
                outgoing_bytes=50,
                response_time_ms=10.0,
                is_error=i == 2  # One error
            )
        
        stats = await collector.get_all_stats()
        
        assert stats["http://test.com"]["request_count"] == 5
        assert stats["http://test.com"]["incoming_bytes"] == 500
        assert stats["http://test.com"]["outgoing_bytes"] == 250
        assert stats["http://test.com"]["error_count"] == 1
        assert stats["http://test.com"]["error_rate_percent"] == 20.0

    async def test_record_multiple_endpoints(self, collector):
        """Should track stats separately per endpoint."""
        await collector.record_request(
            url="http://endpoint1.com",
            incoming_bytes=100,
            outgoing_bytes=50,
            response_time_ms=10.0,
            is_error=False
        )
        await collector.record_request(
            url="http://endpoint2.com",
            incoming_bytes=200,
            outgoing_bytes=100,
            response_time_ms=20.0,
            is_error=True
        )
        
        stats = await collector.get_all_stats()
        
        assert len(stats) == 2
        assert stats["http://endpoint1.com"]["request_count"] == 1
        assert stats["http://endpoint1.com"]["error_count"] == 0
        assert stats["http://endpoint2.com"]["request_count"] == 1
        assert stats["http://endpoint2.com"]["error_count"] == 1

    async def test_error_tracking(self, collector):
        """Should correctly track errors."""
        await collector.record_request(
            url="http://test.com",
            incoming_bytes=100,
            outgoing_bytes=50,
            response_time_ms=100.0,
            is_error=True
        )
        
        stats = await collector.get_all_stats()
        
        assert stats["http://test.com"]["error_count"] == 1
        assert stats["http://test.com"]["error_rate_percent"] == 100.0

    async def test_empty_stats(self, collector):
        """Should return empty dict when no requests recorded."""
        stats = await collector.get_all_stats()
        assert stats == {}

    async def test_lru_eviction(self, collector):
        """Should evict oldest endpoint when at capacity."""
        # Add MAX_ENDPOINTS entries
        for i in range(MAX_ENDPOINTS):
            await collector.record_request(
                url=f"http://endpoint{i}.com",
                incoming_bytes=100,
                outgoing_bytes=50,
                response_time_ms=10.0,
                is_error=False
            )
        
        stats = await collector.get_all_stats()
        assert len(stats) == MAX_ENDPOINTS
        assert "http://endpoint0.com" in stats  # First entry still there
        
        # Add one more - should evict the oldest
        await collector.record_request(
            url="http://new-endpoint.com",
            incoming_bytes=100,
            outgoing_bytes=50,
            response_time_ms=10.0,
            is_error=False
        )
        
        stats = await collector.get_all_stats()
        assert len(stats) == MAX_ENDPOINTS
        assert "http://endpoint0.com" not in stats  # First entry evicted
        assert "http://new-endpoint.com" in stats

    async def test_access_refreshes_lru_position(self, collector):
        """Accessing an endpoint should move it to end (most recent)."""
        # Add 3 endpoints
        await collector.record_request(url="http://first.com", incoming_bytes=1, outgoing_bytes=1, response_time_ms=1, is_error=False)
        await collector.record_request(url="http://second.com", incoming_bytes=1, outgoing_bytes=1, response_time_ms=1, is_error=False)
        await collector.record_request(url="http://third.com", incoming_bytes=1, outgoing_bytes=1, response_time_ms=1, is_error=False)
        
        # Access first one again
        await collector.record_request(url="http://first.com", incoming_bytes=1, outgoing_bytes=1, response_time_ms=1, is_error=False)
        
        # Now second.com is the oldest
        stats = await collector.get_all_stats()
        keys = list(stats.keys())
        
        # Order should be: second, third, first (first moved to end)
        assert keys == ["http://second.com", "http://third.com", "http://first.com"]

    async def test_concurrent_access(self, collector):
        """Should handle concurrent requests safely."""
        async def record_requests(endpoint: str, count: int):
            for _ in range(count):
                await collector.record_request(
                    url=endpoint,
                    incoming_bytes=100,
                    outgoing_bytes=50,
                    response_time_ms=10.0,
                    is_error=False
                )
        
        # Run concurrent tasks
        await asyncio.gather(
            record_requests("http://endpoint1.com", 100),
            record_requests("http://endpoint2.com", 100),
            record_requests("http://endpoint3.com", 100),
        )
        
        stats = await collector.get_all_stats()
        
        assert stats["http://endpoint1.com"]["request_count"] == 100
        assert stats["http://endpoint2.com"]["request_count"] == 100
        assert stats["http://endpoint3.com"]["request_count"] == 100

