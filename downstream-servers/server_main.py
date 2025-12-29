"""
Main downstream server - handles Pokemon JSON requests on port 9001.
Routes: /legendary, /powerful, /default
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Pokemon Downstream Server (Main)")

# Get port from environment variable (Render.com sets $PORT) or default to 9001
PORT = int(os.getenv("PORT", 9001))


@app.post("/legendary")
async def legendary(request: Request):
    """Handle legendary Pokemon."""
    print(request.headers)
    data = await request.json()
    pokemon_name = data.get("name", "Unknown")
    return JSONResponse({
        "status": "accepted",
        "route": "legendary",
        "message": f"Legendary Pokemon {pokemon_name} received!",
        "pokemon": data
    })


@app.post("/powerful")
async def powerful(request: Request):
    """Handle powerful (high attack) Pokemon."""
    print(request.headers)
    data = await request.json()
    pokemon_name = data.get("name", "Unknown")
    attack = data.get("attack", 0)
    return JSONResponse({
        "status": "accepted",
        "route": "powerful",
        "message": f"Powerful Pokemon {pokemon_name} with {attack} attack received!",
        "pokemon": data
    })


@app.post("/default")
async def default(request: Request):
    """Handle all other Pokemon (catch-all)."""
    print(request.headers)
    data = await request.json()
    pokemon_name = data.get("name", "Unknown")
    return JSONResponse({
        "status": "accepted",
        "route": "default",
        "message": f"Pokemon {pokemon_name} received via default route",
        "pokemon": data
    })


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "server": "main", "port": PORT}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)

