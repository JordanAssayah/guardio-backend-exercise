"""
Proxy service - forwards requests to downstream services.
"""
from __future__ import annotations

from typing import Any, Dict

import httpx
from google.protobuf.json_format import MessageToDict


def pokemon_to_json(pokemon: Any) -> Dict[str, Any]:
    """
    Convert a Pokemon protobuf message to JSON-serializable dict.
    Preserves snake_case field names as per protobuf schema.
    """
    return MessageToDict(
        pokemon,
        preserving_proto_field_name=True,
        always_print_fields_with_no_presence=True
    )


async def forward_request(
    url: str,
    json_bytes: bytes,
    reason: str,
    original_headers: Dict[str, str],
    client: httpx.AsyncClient
) -> httpx.Response:
    """
    Forward a Pokemon request to a downstream service.
    
    Args:
        url: The destination URL
        json_bytes: The Pokemon data as pre-encoded JSON bytes
        reason: The reason from the matched rule (for X-Grd-Reason header)
        original_headers: Original request headers
        client: Shared HTTP client for connection pooling
        
    Returns:
        The response from the downstream service
    """
    # Build headers - strip signature and hop-by-hop headers, add reason
    skip_headers = ("x-grd-signature", "content-length", "content-type", "host")
    headers = {k: v for k, v in original_headers.items() if k.lower() not in skip_headers}
    headers["X-Grd-Reason"] = reason
    headers["Content-Type"] = "application/json"
    
    return await client.post(url, content=json_bytes, headers=headers)

