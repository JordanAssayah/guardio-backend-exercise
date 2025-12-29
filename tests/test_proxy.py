"""
Tests for the proxy service - JSON conversion and request forwarding.
"""
import json

import httpx
import pytest
from pytest_httpx import HTTPXMock

from app.proto import pokemon_pb2
from app.services.proxy import pokemon_to_json, forward_request
from tests.conftest import create_pokemon


class TestPokemonToJson:
    """Tests for pokemon_to_json function."""

    def test_basic_conversion(self, sample_pokemon):
        """Should convert Pokemon to dict with all fields."""
        result = pokemon_to_json(sample_pokemon)
        
        assert isinstance(result, dict)
        assert result["name"] == "Pikachu"
        # Note: uint64 fields are converted to strings in JSON (per protobuf spec)
        assert result["number"] == "25"
        assert result["type_one"] == "Electric"

    def test_preserves_snake_case(self, sample_pokemon):
        """Should preserve snake_case field names."""
        result = pokemon_to_json(sample_pokemon)
        
        assert "hit_points" in result
        assert "type_one" in result
        assert "type_two" in result
        # These should NOT be camelCase
        assert "hitPoints" not in result
        assert "typeOne" not in result

    def test_includes_default_values(self):
        """Should include fields even with default/zero values."""
        pokemon = create_pokemon(
            type_two="",  # Empty string
            legendary=False  # Boolean false
        )
        result = pokemon_to_json(pokemon)
        
        assert "type_two" in result
        assert result["type_two"] == ""
        assert "legendary" in result
        assert result["legendary"] is False

    def test_legendary_pokemon(self, legendary_pokemon):
        """Should correctly convert legendary Pokemon."""
        result = pokemon_to_json(legendary_pokemon)
        
        assert result["name"] == "Mewtwo"
        assert result["legendary"] is True

    def test_all_fields_present(self):
        """Should include all Pokemon fields."""
        pokemon = create_pokemon(
            number=1,
            name="Bulbasaur",
            type_one="Grass",
            type_two="Poison",
            hit_points=45,
            attack=49,
            defense=49,
            speed=45,
            legendary=False,
            generation=1,
        )
        result = pokemon_to_json(pokemon)
        
        expected_fields = [
            "number", "name", "type_one", "type_two", "total",
            "hit_points", "attack", "defense", "special_attack",
            "special_defense", "speed", "generation", "legendary"
        ]
        for field in expected_fields:
            assert field in result, f"Missing field: {field}"

    def test_json_serializable(self, sample_pokemon):
        """Result should be JSON serializable."""
        result = pokemon_to_json(sample_pokemon)
        
        # Should not raise
        json_str = json.dumps(result)
        assert isinstance(json_str, str)
        
        # Should round-trip
        parsed = json.loads(json_str)
        assert parsed["name"] == "Pikachu"


class TestForwardRequest:
    """Tests for forward_request function."""

    @pytest.fixture
    def http_client(self):
        """Create an HTTP client for tests."""
        return httpx.AsyncClient()

    async def test_forward_request_success(self, httpx_mock: HTTPXMock, http_client):
        """Should forward request and return response."""
        httpx_mock.add_response(
            url="http://downstream.com/pokemon",
            json={"received": True},
            status_code=200
        )
        
        json_bytes = b'{"name": "Pikachu"}'
        
        response = await forward_request(
            url="http://downstream.com/pokemon",
            json_bytes=json_bytes,
            reason="test reason",
            original_headers={"User-Agent": "TestClient"},
            client=http_client
        )
        
        assert response.status_code == 200
        assert response.json() == {"received": True}

    async def test_adds_grd_reason_header(self, httpx_mock: HTTPXMock, http_client):
        """Should add X-Grd-Reason header from matched rule."""
        httpx_mock.add_response(url="http://downstream.com/pokemon")
        
        await forward_request(
            url="http://downstream.com/pokemon",
            json_bytes=b'{}',
            reason="legendary pokemon",
            original_headers={},
            client=http_client
        )
        
        request = httpx_mock.get_request()
        assert request.headers["X-Grd-Reason"] == "legendary pokemon"

    async def test_sets_content_type_json(self, httpx_mock: HTTPXMock, http_client):
        """Should set Content-Type to application/json."""
        httpx_mock.add_response(url="http://downstream.com/pokemon")
        
        await forward_request(
            url="http://downstream.com/pokemon",
            json_bytes=b'{}',
            reason="test",
            original_headers={},
            client=http_client
        )
        
        request = httpx_mock.get_request()
        assert request.headers["Content-Type"] == "application/json"

    async def test_strips_signature_header(self, httpx_mock: HTTPXMock, http_client):
        """Should not forward X-Grd-Signature header."""
        httpx_mock.add_response(url="http://downstream.com/pokemon")
        
        await forward_request(
            url="http://downstream.com/pokemon",
            json_bytes=b'{}',
            reason="test",
            original_headers={"X-Grd-Signature": "secret-signature"},
            client=http_client
        )
        
        request = httpx_mock.get_request()
        assert "X-Grd-Signature" not in request.headers
        assert "x-grd-signature" not in [h.lower() for h in request.headers.keys()]

    async def test_preserves_other_headers(self, httpx_mock: HTTPXMock, http_client):
        """Should forward other original headers."""
        httpx_mock.add_response(url="http://downstream.com/pokemon")
        
        await forward_request(
            url="http://downstream.com/pokemon",
            json_bytes=b'{}',
            reason="test",
            original_headers={
                "X-Custom-Header": "custom-value",
                "Authorization": "Bearer token123"
            },
            client=http_client
        )
        
        request = httpx_mock.get_request()
        assert request.headers["X-Custom-Header"] == "custom-value"
        assert request.headers["Authorization"] == "Bearer token123"

    async def test_sends_json_body(self, httpx_mock: HTTPXMock, http_client):
        """Should send the JSON body correctly."""
        httpx_mock.add_response(url="http://downstream.com/pokemon")
        
        pokemon_json = json.dumps({"name": "Pikachu", "number": 25}).encode()
        
        await forward_request(
            url="http://downstream.com/pokemon",
            json_bytes=pokemon_json,
            reason="test",
            original_headers={},
            client=http_client
        )
        
        request = httpx_mock.get_request()
        assert request.content == pokemon_json

    async def test_handles_downstream_error(self, httpx_mock: HTTPXMock, http_client):
        """Should return error response from downstream."""
        httpx_mock.add_response(
            url="http://downstream.com/pokemon",
            json={"error": "server error"},
            status_code=500
        )
        
        response = await forward_request(
            url="http://downstream.com/pokemon",
            json_bytes=b'{}',
            reason="test",
            original_headers={},
            client=http_client
        )
        
        assert response.status_code == 500

    async def test_connection_error_raises(self, http_client):
        """Should raise exception on connection failure."""
        with pytest.raises(httpx.RequestError):
            await forward_request(
                url="http://nonexistent-domain-12345.invalid/pokemon",
                json_bytes=b'{}',
                reason="test",
                original_headers={},
                client=http_client
            )

