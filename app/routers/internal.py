"""
Internal router - health checks and metrics.
"""
from typing import Dict

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.stats import stats_collector

router = APIRouter(tags=["internal"])


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(example="healthy")


class EndpointStatsResponse(BaseModel):
    """Statistics for a single downstream endpoint."""
    request_count: int = Field(example=100, description="Total number of requests")
    error_count: int = Field(example=5, description="Number of failed requests")
    error_rate_percent: float = Field(example=5.0, description="Percentage of failed requests")
    incoming_bytes: int = Field(example=10240, description="Total bytes received")
    outgoing_bytes: int = Field(example=20480, description="Total bytes sent to downstream")
    avg_response_time_ms: float = Field(example=45.23, description="Average response time in milliseconds")


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy")


@router.get(
    "/stats",
    response_model=Dict[str, EndpointStatsResponse],
    responses={
        200: {
            "description": "Statistics per downstream endpoint",
            "content": {
                "application/json": {
                    "example": {
                        "http://downstream.com/endpoint": {
                            "request_count": 100,
                            "error_count": 5,
                            "error_rate_percent": 5.0,
                            "incoming_bytes": 10240,
                            "outgoing_bytes": 20480,
                            "avg_response_time_ms": 45.23
                        }
                    }
                }
            }
        }
    }
)
async def stats() -> Dict[str, EndpointStatsResponse]:
    """
    Get statistics for all matched endpoints since server start.
    
    Returns a dictionary where keys are downstream URLs and values contain:
    - **request_count**: Total number of requests
    - **error_count**: Number of failed requests  
    - **error_rate_percent**: Percentage of failed requests
    - **incoming_bytes**: Total bytes received
    - **outgoing_bytes**: Total bytes sent to downstream
    - **avg_response_time_ms**: Average response time in milliseconds
    """
    return await stats_collector.get_all_stats()

