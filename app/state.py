"""
Application state - shared state initialized at startup.
"""
from __future__ import annotations

import httpx

from app.services.proxy_rules import ProxyConfig


class AppState:
    """
    Application state container.
    Initialized at startup via lifespan, injected into routes via FastAPI dependencies.
    """
    
    def __init__(self):
        self.config: ProxyConfig | None = None
        self.secret: bytes | None = None
        self.http_client: httpx.AsyncClient | None = None


app_state = AppState()

