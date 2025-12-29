"""
Internal router - health checks and metrics.
"""
from fastapi import APIRouter

from app.services.stats import stats_collector

router = APIRouter(tags=["internal"])


@router.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/stats")
async def stats() -> dict:
    """
    Get statistics for all matched endpoints since server start.
    
    Returns per endpoint:
        - request_count: Total number of requests
        - error_count: Number of failed requests
        - error_rate_percent: Percentage of failed requests
        - incoming_bytes: Total bytes received
        - outgoing_bytes: Total bytes sent to downstream
        - avg_response_time_ms: Average response time in milliseconds
    """
    return await stats_collector.get_all_stats()

