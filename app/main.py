"""
PokeProxy - Pokemon Streaming Proxy Service

Entry point for the FastAPI application.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from dotenv import load_dotenv

from app.logging import get_logger
from app.state import app_state
from app.routers import internal, stream
from app.services.proxy_rules import load_proxy_config
from app.services.security import get_secret
from app.config import get_config

load_dotenv()

logger = get_logger(__name__)


def _init_config() -> None:
    """Load routing configuration from file."""
    config_path = get_config().pokeproxy_config
    app_state.config = load_proxy_config(config_path)
    logger.info(f"Loaded {len(app_state.config.rules)} routing rules from {config_path}")


def _init_secret() -> None:
    """Load HMAC secret for signature validation."""
    app_state.secret = get_secret()
    logger.info("HMAC secret loaded successfully")


def _init_http_client() -> None:
    """Initialize shared HTTP client for downstream requests."""
    app_state.http_client = httpx.AsyncClient(timeout=30.0)
    logger.info("HTTP client initialized")


async def _shutdown_http_client() -> None:
    """Close the shared HTTP client."""
    if app_state.http_client:
        await app_state.http_client.aclose()
        logger.info("HTTP client closed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - handles startup and shutdown."""
    _init_config()
    _init_secret()
    _init_http_client()
    
    yield
    
    await _shutdown_http_client()
    
app = FastAPI(
    title="PokeProxy",
    description="Pokemon Streaming Proxy Service",
    lifespan=lifespan
)

app.include_router(stream.router)
app.include_router(internal.router)
