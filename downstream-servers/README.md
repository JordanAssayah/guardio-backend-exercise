# Downstream Test Server

Simple FastAPI server to receive Pokemon JSON requests from the PokeProxy.

## Server

### Test Server (port 9001)

Handles the routes defined in `example-config.json`:

- `POST /legendary` - Legendary Pokemon
- `POST /powerful` - High attack Pokemon
- `POST /default` - Default catch-all

## Running

**Note:** This server uses the same virtual environment as the main project. Make sure you have activated the project's virtual environment before running.

### Using uvicorn directly:

```bash
uvicorn server_main:app --port 9001 --reload
```

### Using Python:

```bash
python server_main.py
```

## Expected Pokemon JSON Format

The proxy forwards Pokemon data as JSON:

```json
{
  "number": 150,
  "name": "Mewtwo",
  "type_one": "Psychic",
  "type_two": "",
  "total": 680,
  "hit_points": 106,
  "attack": 110,
  "defense": 90,
  "special_attack": 154,
  "special_defense": 90,
  "speed": 130,
  "generation": 1,
  "legendary": true
}
```

## Response Format

All endpoints return:

```json
{
    "status": "accepted",
    "route": "legendary|powerful|default",
    "message": "...",
    "pokemon": { ... }
}
```
