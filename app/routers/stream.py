"""
Stream router - handles incoming Pokemon protobuf stream from Guardio's POST requests.
"""
from __future__ import annotations

import json
import time

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from google.protobuf.message import DecodeError

from app.logging import get_logger
from app.config import get_config

logger = get_logger(__name__)

from app.state import app_state
from app.proto import pokemon_pb2
from app.services.proxy_rules import find_matching_rule
from app.services.proxy import forward_request, pokemon_to_json
from app.services.security import validate_signature
from app.services.stats import stats_collector

router = APIRouter(tags=["stream"])

# Hop-by-hop headers that should not be forwarded
HOP_BY_HOP_HEADERS = frozenset({
    "connection", "keep-alive", "transfer-encoding",
    "content-encoding", "te", "trailers", "upgrade"
})


async def validate_request_signature(request: Request) -> bytes:
    """
    Validate the HMAC-SHA256 signature of an incoming request.
    
    Args:
        request: The incoming FastAPI request
        
    Returns:
        The request body bytes if validation succeeds
        
    Raises:
        HTTPException: 401 if signature is missing or invalid, 500 if secret not configured,
                       413 if body too large, 400 if body is empty
    """
    max_body_size = get_config().pokeproxy_max_body_size
    
    # Check Content-Length header first to reject oversized requests early
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > max_body_size:
                raise HTTPException(status_code=413, detail="Request body too large")
        except ValueError:
            pass  # Invalid content-length header, will check actual body size
    
    signature = request.headers.get("X-Grd-Signature")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing X-Grd-Signature header")
    
    if app_state.secret is None:
        logger.error("HMAC secret not configured")
        raise HTTPException(status_code=500, detail="Internal server error")
    
    body = await request.body()
    
    # Validate body size after reading
    if len(body) > max_body_size:
        raise HTTPException(status_code=413, detail="Request body too large")
    
    # Validate body is not empty
    if not body:
        raise HTTPException(status_code=400, detail="Empty request body")
    
    if not validate_signature(body, signature, app_state.secret):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    return body


def parse_pokemon_protobuf(body: bytes) -> pokemon_pb2.Pokemon:
    """
    Parse a Pokemon protobuf from raw bytes.
    
    Args:
        body: The raw protobuf bytes
        
    Returns:
        The parsed Pokemon protobuf object
        
    Raises:
        HTTPException: 400 if parsing fails or required fields are missing
    """
    pokemon = pokemon_pb2.Pokemon()
    try:
        pokemon.ParseFromString(body)
    except DecodeError as e:
        logger.warning(f"Invalid protobuf data: {e}")
        raise HTTPException(status_code=400, detail="Failed to parse protobuf")
    
    # Validate required fields exist (proto3 defaults to empty string for missing fields)
    if not pokemon.name:
        logger.warning("Pokemon missing required field: name")
        raise HTTPException(status_code=400, detail="Pokemon missing name field")
    
    logger.info(f"Received Pokemon: {pokemon.name} (#{pokemon.number})")
    return pokemon


def match_routing_rule(pokemon: pokemon_pb2.Pokemon):
    """
    Find a matching routing rule for the given Pokemon.
    
    Args:
        pokemon: The parsed Pokemon protobuf object
        
    Returns:
        The matched rule, or None if no rule matches
        
    Raises:
        HTTPException: 500 if routing config is not loaded
    """
    if app_state.config is None:
        logger.error("No routing config loaded")
        raise HTTPException(status_code=500, detail="Internal server error")
    
    matched_rule = find_matching_rule(pokemon, app_state.config.rules)
    if matched_rule is None:
        logger.warning(f"No rule matched for {pokemon.name}")
        return None
    
    logger.info(f"Matched rule: {matched_rule.reason} -> {matched_rule.url}")
    return matched_rule


def _map_downstream_error(error: Exception, url: str) -> HTTPException:
    """Map downstream errors to appropriate HTTP exceptions."""
    if isinstance(error, httpx.TimeoutException):
        logger.error(f"Timeout forwarding to {url}")
        return HTTPException(status_code=504, detail="Downstream service timeout")
    
    if isinstance(error, httpx.RequestError):
        logger.error(f"Connection error to {url}: {error}")
        return HTTPException(status_code=502, detail="Failed to connect to downstream service")
    
    logger.error(f"Unexpected error forwarding request: {error}")
    return HTTPException(status_code=502, detail="Failed to forward request to downstream")


def _filter_response_headers(headers: httpx.Headers) -> dict:
    """Filter hop-by-hop headers from downstream response."""
    return {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}


@router.post(
    "/stream",
    response_class=Response,
    responses={
        200: {
            "description": "Proxied response from downstream service (format varies by downstream). Returns `{\"status\": \"no_match\"}` if no routing rule matched.",
        },
        400: {"description": "Empty body, invalid protobuf data, or missing Pokemon name"},
        401: {"description": "Missing or invalid X-Grd-Signature header"},
        413: {"description": "Request body too large"},
        500: {"description": "Internal server error (config or secret not loaded)"},
        502: {"description": "Failed to connect to downstream service"},
        504: {"description": "Downstream service timeout"}
    }
)
async def stream(request: Request) -> Response:
    """
    Receive Pokemon protobuf stream, validate signature, match rules, and proxy to downstream.
    
    **Headers:**
    - `X-Grd-Signature` (required): HMAC-SHA256 signature of the request body
    
    **Request Body:** Binary Pokemon protobuf data
    
    **Flow:**
    1. Validate HMAC signature
    2. Parse Pokemon protobuf
    3. Match against routing rules
    4. Forward as JSON to matched downstream URL
    5. Return downstream response
    """
    body = await validate_request_signature(request)
    pokemon = parse_pokemon_protobuf(body)
    matched_rule = match_routing_rule(pokemon)
    
    if matched_rule is None:
        await stats_collector.record_request(
            url="__unmatched__",
            incoming_bytes=len(body),
            outgoing_bytes=0,
            response_time_ms=0,
            is_error=False
        )
        return Response(content='{"status": "no_match"}', media_type="application/json")
    
    if app_state.http_client is None:
        logger.error("HTTP client not initialized")
        raise HTTPException(status_code=500, detail="Internal server error")
    
    # Prepare request data
    json_bytes = json.dumps(pokemon_to_json(pokemon)).encode()
    incoming_bytes = len(body)
    outgoing_bytes = len(json_bytes)
    
    # Forward request and track metrics
    start_time = time.time()
    error: Exception | None = None
    downstream_response: httpx.Response | None = None
    
    try:
        downstream_response = await forward_request(
            url=matched_rule.url,
            json_bytes=json_bytes,
            reason=matched_rule.reason,
            original_headers=dict(request.headers),
            client=app_state.http_client
        )
    except Exception as e:
        error = e
    
    # Always record stats
    response_time_ms = (time.time() - start_time) * 1000
    is_error = error is not None or (downstream_response and downstream_response.status_code >= 400)
    
    await stats_collector.record_request(
        url=matched_rule.url,
        incoming_bytes=incoming_bytes,
        outgoing_bytes=outgoing_bytes,
        response_time_ms=response_time_ms,
        is_error=bool(is_error)
    )
    
    # Handle error case
    if error is not None:
        raise _map_downstream_error(error, matched_rule.url)
    
    # Return successful response
    return Response(
        content=downstream_response.content,
        status_code=downstream_response.status_code,
        headers=_filter_response_headers(downstream_response.headers)
    )
