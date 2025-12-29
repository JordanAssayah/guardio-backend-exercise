"""
Tests for the stream router - full end-to-end flow with mocked downstream.
"""
import json

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_httpx import HTTPXMock

from app.routers import stream
from app.state import app_state
from app.services.proxy_rules import ProxyConfig, ProxyRule
from app.services.stats import StatsCollector, stats_collector
from tests.conftest import create_pokemon, sign_body, TEST_SECRET_RAW


@pytest.fixture
def app_with_state(sample_config, test_secret):
    """Create a test FastAPI app with mocked state (without http_client)."""
    # Store original state
    original_config = app_state.config
    original_secret = app_state.secret
    original_client = app_state.http_client
    
    # Set up test state (but NOT the http_client yet - it will be set per test)
    app_state.config = sample_config
    app_state.secret = test_secret
    
    test_app = FastAPI()
    test_app.include_router(stream.router)
    
    yield test_app
    
    # Restore original state
    app_state.config = original_config
    app_state.secret = original_secret
    app_state.http_client = original_client


@pytest.fixture
def client_without_downstream(app_with_state, test_secret):
    """
    Create a test client for tests that don't need downstream mocking.
    Sets http_client to None so downstream forwarding will fail gracefully.
    """
    original_client = app_state.http_client
    app_state.http_client = None
    
    client = TestClient(app_with_state)
    yield client
    
    app_state.http_client = original_client


class TestStreamEndpointValidation:
    """Tests for /stream endpoint validation (no downstream mocking needed)."""

    def test_missing_signature_returns_401(self, client_without_downstream):
        """Request without signature should return 401."""
        pokemon = create_pokemon()
        body = pokemon.SerializeToString()
        
        response = client_without_downstream.post("/stream", content=body)
        
        assert response.status_code == 401
        assert "X-Grd-Signature" in response.json()["detail"]

    def test_invalid_signature_returns_401(self, client_without_downstream):
        """Request with invalid signature should return 401."""
        pokemon = create_pokemon()
        body = pokemon.SerializeToString()
        
        response = client_without_downstream.post(
            "/stream",
            content=body,
            headers={"X-Grd-Signature": "invalid-signature"}
        )
        
        assert response.status_code == 401
        assert "Invalid signature" in response.json()["detail"]

    def test_empty_body_returns_400(self, client_without_downstream, test_secret):
        """Request with empty body should return 400."""
        body = b""
        signature = sign_body(body, test_secret)
        
        response = client_without_downstream.post(
            "/stream",
            content=body,
            headers={"X-Grd-Signature": signature}
        )
        
        assert response.status_code == 400
        assert "Empty" in response.json()["detail"]

    def test_invalid_protobuf_returns_400(self, client_without_downstream, test_secret):
        """Request with invalid protobuf should return 400."""
        body = b"not a valid protobuf"
        signature = sign_body(body, test_secret)
        
        response = client_without_downstream.post(
            "/stream",
            content=body,
            headers={"X-Grd-Signature": signature}
        )
        
        assert response.status_code == 400
        assert "protobuf" in response.json()["detail"].lower()

    def test_pokemon_missing_name_returns_400(self, client_without_downstream, test_secret):
        """Pokemon without name should return 400."""
        pokemon = create_pokemon(name="")  # Empty name
        body = pokemon.SerializeToString()
        signature = sign_body(body, test_secret)
        
        response = client_without_downstream.post(
            "/stream",
            content=body,
            headers={"X-Grd-Signature": signature}
        )
        
        assert response.status_code == 400
        assert "name" in response.json()["detail"].lower()

    def test_body_too_large_returns_413(self, client_without_downstream, test_secret, monkeypatch):
        """Request with body exceeding limit should return 413."""
        from app.config import get_config
        get_config.cache_clear()
        monkeypatch.setenv("POKEPROXY_MAX_BODY_SIZE", "10")  # Very small limit
        
        pokemon = create_pokemon()
        body = pokemon.SerializeToString()  # Will be > 10 bytes
        signature = sign_body(body, test_secret)
        
        response = client_without_downstream.post(
            "/stream",
            content=body,
            headers={
                "X-Grd-Signature": signature,
                "Content-Length": str(len(body))
            }
        )
        
        # Restore
        get_config.cache_clear()
        
        assert response.status_code == 413


class TestStreamEndpointRouting:
    """Tests for /stream endpoint routing to downstream services."""

    @pytest.fixture
    def client_with_mock(self, app_with_state, httpx_mock: HTTPXMock):
        """Create test client with mocked downstream HTTP."""
        # Create the HTTP client AFTER httpx_mock is set up
        app_state.http_client = httpx.AsyncClient()
        client = TestClient(app_with_state)
        yield client
        # Cleanup is handled by app_with_state fixture

    def test_legendary_pokemon_routes_to_legendary_endpoint(
        self, client_with_mock, test_secret, httpx_mock: HTTPXMock
    ):
        """Legendary Pokemon should route to legendary endpoint."""
        httpx_mock.add_response(
            url="http://localhost:9001/legendary",
            json={"status": "caught"},
            status_code=200
        )
        
        pokemon = create_pokemon(name="Mewtwo", legendary=True)
        body = pokemon.SerializeToString()
        signature = sign_body(body, test_secret)
        
        response = client_with_mock.post(
            "/stream",
            content=body,
            headers={"X-Grd-Signature": signature}
        )
        
        assert response.status_code == 200
        assert response.json() == {"status": "caught"}
        
        # Verify the downstream request
        request = httpx_mock.get_request()
        assert request.url == "http://localhost:9001/legendary"
        assert request.headers["X-Grd-Reason"] == "legendary pokemon"

    def test_powerful_pokemon_routes_to_powerful_endpoint(
        self, client_with_mock, test_secret, httpx_mock: HTTPXMock
    ):
        """Powerful Pokemon should route to powerful endpoint."""
        httpx_mock.add_response(
            url="http://localhost:9001/powerful",
            json={"status": "stored"},
            status_code=200
        )
        
        pokemon = create_pokemon(
            name="Dragonite",
            attack=134,
            hit_points=91,
            legendary=False
        )
        body = pokemon.SerializeToString()
        signature = sign_body(body, test_secret)
        
        response = client_with_mock.post(
            "/stream",
            content=body,
            headers={"X-Grd-Signature": signature}
        )
        
        assert response.status_code == 200
        request = httpx_mock.get_request()
        assert request.url == "http://localhost:9001/powerful"
        assert request.headers["X-Grd-Reason"] == "high attack pokemon"

    def test_normal_pokemon_routes_to_default_endpoint(
        self, client_with_mock, test_secret, httpx_mock: HTTPXMock
    ):
        """Normal Pokemon should route to default catch-all endpoint."""
        httpx_mock.add_response(
            url="http://localhost:9001/default",
            json={"status": "ok"},
            status_code=200
        )
        
        pokemon = create_pokemon(name="Pikachu", attack=55, legendary=False)
        body = pokemon.SerializeToString()
        signature = sign_body(body, test_secret)
        
        response = client_with_mock.post(
            "/stream",
            content=body,
            headers={"X-Grd-Signature": signature}
        )
        
        assert response.status_code == 200
        request = httpx_mock.get_request()
        assert request.url == "http://localhost:9001/default"

    def test_downstream_error_returns_502(
        self, client_with_mock, test_secret, httpx_mock: HTTPXMock
    ):
        """Downstream connection error should return 502."""
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url="http://localhost:9001/default"
        )
        
        pokemon = create_pokemon()
        body = pokemon.SerializeToString()
        signature = sign_body(body, test_secret)
        
        response = client_with_mock.post(
            "/stream",
            content=body,
            headers={"X-Grd-Signature": signature}
        )
        
        assert response.status_code == 502

    def test_downstream_timeout_returns_504(
        self, client_with_mock, test_secret, httpx_mock: HTTPXMock
    ):
        """Downstream timeout should return 504."""
        httpx_mock.add_exception(
            httpx.ReadTimeout("Read timed out"),
            url="http://localhost:9001/default"
        )
        
        pokemon = create_pokemon()
        body = pokemon.SerializeToString()
        signature = sign_body(body, test_secret)
        
        response = client_with_mock.post(
            "/stream",
            content=body,
            headers={"X-Grd-Signature": signature}
        )
        
        assert response.status_code == 504

    def test_downstream_response_headers_forwarded(
        self, client_with_mock, test_secret, httpx_mock: HTTPXMock
    ):
        """Response headers from downstream should be forwarded."""
        httpx_mock.add_response(
            url="http://localhost:9001/default",
            json={"status": "ok"},
            headers={"X-Custom-Response": "from-downstream"}
        )
        
        pokemon = create_pokemon()
        body = pokemon.SerializeToString()
        signature = sign_body(body, test_secret)
        
        response = client_with_mock.post(
            "/stream",
            content=body,
            headers={"X-Grd-Signature": signature}
        )
        
        assert response.headers.get("X-Custom-Response") == "from-downstream"

    def test_json_body_sent_to_downstream(
        self, client_with_mock, test_secret, httpx_mock: HTTPXMock
    ):
        """Pokemon should be converted to JSON before sending downstream."""
        httpx_mock.add_response(url="http://localhost:9001/default")
        
        pokemon = create_pokemon(
            name="Pikachu",
            number=25,
            type_one="Electric",
            attack=55
        )
        body = pokemon.SerializeToString()
        signature = sign_body(body, test_secret)
        
        client_with_mock.post(
            "/stream",
            content=body,
            headers={"X-Grd-Signature": signature}
        )
        
        request = httpx_mock.get_request()
        sent_json = json.loads(request.content)
        
        assert sent_json["name"] == "Pikachu"
        # Note: uint64 fields are converted to strings in JSON (per protobuf spec)
        assert sent_json["number"] == "25"
        assert sent_json["type_one"] == "Electric"
        assert sent_json["attack"] == "55"


class TestStreamEndpointNoMatchingRule:
    """Tests for when no routing rule matches."""

    @pytest.fixture
    def app_no_catch_all(self, test_secret):
        """App with rules that might not match."""
        # Store original state
        original_config = app_state.config
        original_secret = app_state.secret
        original_client = app_state.http_client
        
        # Set up test state with no catch-all
        app_state.config = ProxyConfig(rules=[
            ProxyRule(
                url="http://localhost:9001/legendary",
                reason="legendary only",
                match=["legendary==true"]
            )
        ])
        app_state.secret = test_secret
        app_state.http_client = httpx.AsyncClient()
        
        test_app = FastAPI()
        test_app.include_router(stream.router)
        
        yield test_app
        
        # Restore original state
        app_state.config = original_config
        app_state.secret = original_secret
        app_state.http_client = original_client

    def test_no_match_returns_no_match_response(self, app_no_catch_all, test_secret):
        """When no rule matches, should return no_match response."""
        client = TestClient(app_no_catch_all)
        
        pokemon = create_pokemon(legendary=False)  # Won't match legendary rule
        body = pokemon.SerializeToString()
        signature = sign_body(body, test_secret)
        
        response = client.post(
            "/stream",
            content=body,
            headers={"X-Grd-Signature": signature}
        )
        
        assert response.status_code == 200
        assert response.json() == {"status": "no_match"}
