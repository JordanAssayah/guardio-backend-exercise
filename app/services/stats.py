"""
Stats service - collects metrics per downstream endpoint.
"""
from __future__ import annotations

import asyncio
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict


# Maximum number of endpoints to track to prevent memory leak
MAX_ENDPOINTS = 1000


@dataclass
class EndpointStats:
    """Statistics for a single downstream endpoint."""
    request_count: int = 0
    error_count: int = 0
    incoming_bytes: int = 0
    outgoing_bytes: int = 0
    total_response_time_ms: float = 0.0
    
    @property
    def error_rate(self) -> float:
        if self.request_count == 0:
            return 0.0
        return (self.error_count / self.request_count) * 100
    
    @property
    def avg_response_time_ms(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.total_response_time_ms / self.request_count
    
    def to_dict(self) -> Dict:
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate_percent": round(self.error_rate, 2),
            "incoming_bytes": self.incoming_bytes,
            "outgoing_bytes": self.outgoing_bytes,
            "avg_response_time_ms": round(self.avg_response_time_ms, 2)
        }


class StatsCollector:
    """Async-safe statistics collector for all endpoints with LRU eviction."""
    
    def __init__(self):
        self._stats: OrderedDict[str, EndpointStats] = OrderedDict()
        self._lock = asyncio.Lock()
    
    async def record_request(
        self,
        url: str,
        incoming_bytes: int,
        outgoing_bytes: int,
        response_time_ms: float,
        is_error: bool
    ):
        """Record a request to an endpoint."""
        async with self._lock:
            if url not in self._stats:
                # Evict oldest entry if at capacity
                if len(self._stats) >= MAX_ENDPOINTS:
                    self._stats.popitem(last=False)
                self._stats[url] = EndpointStats()
            else:
                # Move to end (most recently used)
                self._stats.move_to_end(url)
            
            stats = self._stats[url]
            stats.request_count += 1
            stats.incoming_bytes += incoming_bytes
            stats.outgoing_bytes += outgoing_bytes
            stats.total_response_time_ms += response_time_ms
            if is_error:
                stats.error_count += 1
    
    async def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics for all endpoints."""
        async with self._lock:
            return {url: stats.to_dict() for url, stats in self._stats.items()}


# Singleton instance
stats_collector = StatsCollector()
