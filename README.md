# PokeProxy - Pokemon Streaming Proxy Service

A reverse-proxy service that consumes Pokemon protobuf streams from Guardio's API, validates HMAC signatures, matches routing rules, and forwards JSON payloads to downstream services.

## Quick Start

```bash
# Install dependencies
uv sync

# Generate protobuf code (if not already generated)
uv run python -m grpc_tools.protoc --python_out=app/proto --proto_path=app/proto app/proto/pokemon.proto

# Copy the example .env file and configure it
cp .env.example .env

# Generate a secret for HMAC signature validation
openssl rand -base64 32
# Copy the output and paste it as POKEPROXY_SECRET in your .env file

# Run the server
uv run fastapi dev app/main.py
```

## Configuration

### Environment Variables

| Variable                  | Description                                         | Required | Default |
| ------------------------- | --------------------------------------------------- | -------- | ------- |
| `POKEPROXY_CONFIG`        | Path to the JSON config file with routing rules     | Yes      | -       |
| `POKEPROXY_SECRET`        | Base64-encoded HMAC secret for signature validation | Yes      | -       |
| `POKEPROXY_MAX_BODY_SIZE` | Maximum request body size in bytes                  | No       | 4096    |

### Config File Format

```json
{
  "rules": [
    {
      "url": "http://downstream-service.com/endpoint",
      "reason": "Human-readable reason for this route",
      "match": [
        "hit_points==20",
        "type_two!=word",
        "special_defense > 10",
        "generation< 20"
      ]
    }
  ]
}
```

**Match operators:** `==`, `!=`, `>`, `<`

Rules are evaluated in order. First matching rule wins. All conditions in a rule must match (AND logic).

## API Endpoints

### POST /stream

Receives Pokemon protobuf data, validates, matches rules, and proxies to downstream.

**Headers:**

- `X-Grd-Signature` (required): HMAC-SHA256 signature of the request body

**Response:** Proxied response from downstream service, or error.

### GET /stats

Returns metrics per matched endpoint since server start:

```json
{
  "http://downstream.com/endpoint": {
    "request_count": 100,
    "error_count": 5,
    "error_rate_percent": 5.0,
    "incoming_bytes": 10240,
    "outgoing_bytes": 20480,
    "avg_response_time_ms": 45.23
  }
}
```

### GET /health

Health check endpoint.

## Connecting to Guardio Stream API

```bash
# Start your server with ngrok
ngrok http 8000

# Issue stream-start request to Guardio
curl -X POST https://hiring.external.guardio.dev/be/stream_start \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://<your-ngrok-url>/stream",
    "email": "test@guard.io",
    "enc_secret": "<your-base64-encoded-secret>"
  }'
```

---

## Testing

### Run Unit Tests

```bash
# Install test dependencies
uv pip install -e ".[test]"

# Run all tests
POKEPROXY_SECRET="your-base64-secret" POKEPROXY_CONFIG="./config.json" pytest tests/ -v

# Run with coverage report
POKEPROXY_SECRET="your-base64-secret" POKEPROXY_CONFIG="./config.json" pytest tests/ --cov=app --cov-report=term-missing
```

### Manual Testing with Mock Downstream

Start all three components to test the full flow:

```bash
# Terminal 1: Start mock downstream server (simulates your config.json endpoints)
python scripts/mock_downstream.py

# Terminal 2: Start the proxy server
fastapi dev app/main.py

# Terminal 3: Send test Pokemon (inline secret)
POKEPROXY_SECRET="your-base64-secret" python scripts/send_pokemon.py              # Pikachu → /default
POKEPROXY_SECRET="your-base64-secret" python scripts/send_pokemon.py --legendary  # Mewtwo → /legendary
POKEPROXY_SECRET="your-base64-secret" python scripts/send_pokemon.py --powerful   # Dragonite → /powerful
```

Or source your `.env` file first:

```bash
export $(grep -v '^#' .env | xargs)
python scripts/send_pokemon.py --legendary
```

---

## Checkpoint Answers

### 1. The URL must be accessible from the internet. What are your options?

**Development/Testing:**

- **Tunneling services** like Ngrok, Cloudflare Tunnel, or Localtunnel
  - Pros: Zero deployment, instant HTTPS, real-time debugging
  - Cons: Transient URLs, not for production

**Production:**

- **Cloud PaaS** like Render, Railway, Fly.io, Heroku, AWS AppRunner, or Google Cloud Run
  - Pros: Static URLs, managed SSL, high availability
  - Cons: Slower iteration (push-to-deploy)

**Legacy approach:**

- Port forwarding on router (not recommended: security risk, requires static IP)

**Decision:** Ngrok for development, Cloud PaaS for production deployment.

### 2. What would a minimal service that prints the Pokemon names to screen look like?

```python
from fastapi import FastAPI, Request
from app.proto import pokemon_pb2

app = FastAPI()

@app.post("/stream")
async def stream(request: Request):
    pokemon = pokemon_pb2.Pokemon()
    pokemon.ParseFromString(await request.body())
    print(f"Received: {pokemon.name}")
    return {"status": "ok"}
```

### 3. What order of implementation would make for the best "MVP" at any point?

1. **Ingestion** - Accept POST requests, read raw bytes
2. **Deserialization** - Parse protobuf into Python objects (can now see data)
3. **Security** - HMAC signature validation (service is now secure)
4. **Rules Engine** - Config loading and condition matching (service has logic)
5. **Proxy** - Forward to downstream services (service is complete)
6. **Stats** - Observability endpoint (bonus)

This order follows the data flow and ensures each phase is independently testable.

---

## Project Structure

```
├── app/
│   ├── main.py              # FastAPI app entry point with lifespan
│   ├── state.py             # Shared app state (config, secrets)
│   ├── routers/             # Route handlers (controllers)
│   │   ├── stream.py        # POST /stream - main proxy endpoint
│   │   └── internal.py      # GET /health, /stats
│   ├── services/            # Business logic
│   │   ├── config.py        # Config loading and rules matching
│   │   ├── security.py      # HMAC signature validation
│   │   ├── proxy.py         # HTTP forwarding to downstream
│   │   └── stats.py         # Per-endpoint metrics collection
│   └── proto/
│       ├── pokemon.proto
│       └── pokemon_pb2.py   # Generated protobuf code
├── config.json              # Example routing config
├── pyproject.toml           # Dependencies
└── README.md
```

**Architecture notes:**

- `routers/` - Similar to controllers in NestJS, handle HTTP requests
- `services/` - Business logic, reusable across routes
- `state.py` - Shared state injected via FastAPI's dependency system
- `main.py` - App factory with modern `lifespan` context manager (not deprecated `on_event`)

## Performance Considerations

- **Async HTTP client** (httpx) for non-blocking downstream requests
- **Config loaded once** at startup, not per-request
- **Async-safe stats** collection with `asyncio.Lock` (doesn't block event loop)
- **LRU eviction** in stats collector prevents memory leaks (max 1000 endpoints)
- **Single JSON encoding** - body encoded once, used for both forwarding and stats
- **Timing-safe HMAC comparison** to prevent timing attacks

### Max Body Size Calculation

The default `POKEPROXY_MAX_BODY_SIZE` is **4096 bytes (4KB)**, derived from analyzing the Pokemon protobuf schema:

```
message Pokemon {
    uint64 number          // varint: 1-2 bytes (Pokemon #1-898)
    string name            // ~20 bytes max ("Crabominable")
    string type_one        // ~10 bytes max ("Electric")
    string type_two        // ~10 bytes max
    uint64 total           // varint: 2 bytes
    uint64 hit_points      // varint: 1-2 bytes (max 255)
    uint64 attack          // varint: 1-2 bytes
    uint64 defense         // varint: 1-2 bytes
    uint64 special_attack  // varint: 1-2 bytes
    uint64 special_defense // varint: 1-2 bytes
    uint64 speed           // varint: 1-2 bytes
    uint64 generation      // varint: 1 byte (1-9)
    bool legendary         // 1 byte
}
```

| Component         | Estimated Size    |
| ----------------- | ----------------- |
| uint64 fields (9) | ~18 bytes         |
| string fields (3) | ~40 bytes         |
| bool field (1)    | 1 byte            |
| Field tags (13)   | 13 bytes          |
| **Total**         | **~72-100 bytes** |

A typical Pokemon message is **~100 bytes**. The 4KB default provides **~40x headroom** for:

- Future schema additions
- Potential padding/alignment
- Safety margin

This tight limit helps reject malformed/malicious payloads faster while being generous enough for legitimate data. Adjust via `POKEPROXY_MAX_BODY_SIZE` if needed.
