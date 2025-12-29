#!/usr/bin/env python3
"""
Mock downstream server for testing the Pokemon proxy.

This server simulates the downstream services defined in config.json:
- /legendary - receives legendary Pokemon
- /powerful - receives high attack Pokemon  
- /default - receives all other Pokemon

Run with: python scripts/mock_downstream.py
Listens on: http://localhost:9001
"""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Mock Downstream Server", description="Test server for Pokemon proxy")


def log_request(endpoint: str, data: dict, headers: dict):
    """Log incoming Pokemon data."""
    reason = headers.get("x-grd-reason", "unknown")
    timestamp = datetime.now().strftime("%H:%M:%S")
    name = data.get("name", "Unknown")
    number = data.get("number", "?")
    
    print(f"[{timestamp}] {endpoint.upper()} | Pokemon: {name} (#{number}) | Reason: {reason}")


@app.post("/legendary")
async def legendary(request: Request):
    """Endpoint for legendary Pokemon."""
    data = await request.json()
    log_request("legendary", data, dict(request.headers))
    
    return JSONResponse({
        "status": "caught",
        "message": f"Legendary {data.get('name', 'Pokemon')} has been captured!",
        "endpoint": "legendary",
        "pokemon": data
    })


@app.post("/powerful")
async def powerful(request: Request):
    """Endpoint for powerful Pokemon."""
    data = await request.json()
    log_request("powerful", data, dict(request.headers))
    
    return JSONResponse({
        "status": "stored",
        "message": f"Powerful {data.get('name', 'Pokemon')} stored in special containment!",
        "endpoint": "powerful",
        "pokemon": data
    })


@app.post("/default")
async def default(request: Request):
    """Default catch-all endpoint."""
    data = await request.json()
    log_request("default", data, dict(request.headers))
    
    return JSONResponse({
        "status": "ok",
        "message": f"{data.get('name', 'Pokemon')} added to Pokedex!",
        "endpoint": "default",
        "pokemon": data
    })


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "server": "mock-downstream"}


if __name__ == "__main__":
    print("\n🎮 Mock Downstream Server")
    print("=" * 50)
    print("Listening on http://localhost:9001")
    print("Endpoints:")
    print("  POST /legendary - Legendary Pokemon")
    print("  POST /powerful  - High attack Pokemon")
    print("  POST /default   - Default catch-all")
    print("=" * 50 + "\n")
    
    uvicorn.run(app, host="127.0.0.1", port=9001, log_level="warning")

