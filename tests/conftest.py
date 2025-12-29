"""
Shared test fixtures and helpers.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from typing import Generator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.proto import pokemon_pb2
from app.services.proxy_rules import ProxyConfig, ProxyRule
from app.services.stats import StatsCollector
from app.state import AppState, app_state


# Test secret for HMAC validation (base64 encoded)
TEST_SECRET_RAW = b"test-secret-key-for-unit-tests"
TEST_SECRET_B64 = base64.b64encode(TEST_SECRET_RAW).decode()


@pytest.fixture
def test_secret() -> bytes:
    """Return the raw test secret bytes."""
    return TEST_SECRET_RAW


@pytest.fixture
def test_secret_b64() -> str:
    """Return the base64-encoded test secret."""
    return TEST_SECRET_B64


def create_pokemon(
    number: int = 25,
    name: str = "Pikachu",
    type_one: str = "Electric",
    type_two: str = "",
    hit_points: int = 35,
    attack: int = 55,
    defense: int = 40,
    speed: int = 90,
    legendary: bool = False,
    generation: int = 1,
) -> pokemon_pb2.Pokemon:
    """Create a Pokemon protobuf message with default or custom values."""
    pokemon = pokemon_pb2.Pokemon()
    pokemon.number = number
    pokemon.name = name
    pokemon.type_one = type_one
    pokemon.type_two = type_two
    pokemon.hit_points = hit_points
    pokemon.attack = attack
    pokemon.defense = defense
    pokemon.speed = speed
    pokemon.legendary = legendary
    pokemon.generation = generation
    return pokemon


def sign_body(body: bytes, secret: bytes) -> str:
    """Create HMAC-SHA256 signature for a body."""
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


@pytest.fixture
def sample_pokemon() -> pokemon_pb2.Pokemon:
    """A standard Pikachu for testing."""
    return create_pokemon()


@pytest.fixture
def legendary_pokemon() -> pokemon_pb2.Pokemon:
    """A legendary Mewtwo for testing."""
    return create_pokemon(
        number=150,
        name="Mewtwo",
        type_one="Psychic",
        hit_points=106,
        attack=110,
        defense=90,
        speed=130,
        legendary=True,
        generation=1,
    )


@pytest.fixture
def powerful_pokemon() -> pokemon_pb2.Pokemon:
    """A powerful non-legendary Pokemon for testing."""
    return create_pokemon(
        number=149,
        name="Dragonite",
        type_one="Dragon",
        type_two="Flying",
        hit_points=91,
        attack=134,
        defense=95,
        speed=80,
        legendary=False,
        generation=1,
    )


@pytest.fixture
def sample_rules() -> list[ProxyRule]:
    """Sample proxy rules for testing."""
    return [
        ProxyRule(
            url="http://localhost:9001/legendary",
            reason="legendary pokemon",
            match=["legendary==true"],
        ),
        ProxyRule(
            url="http://localhost:9001/powerful",
            reason="high attack pokemon",
            match=["attack>100", "hit_points>50"],
        ),
        ProxyRule(
            url="http://localhost:9001/default",
            reason="default catch-all",
            match=[],
        ),
    ]


@pytest.fixture
def sample_config(sample_rules) -> ProxyConfig:
    """Sample proxy config for testing."""
    return ProxyConfig(rules=sample_rules)


@pytest.fixture
def temp_config_file(tmp_path, sample_rules) -> str:
    """Create a temporary config file for testing."""
    config_data = {
        "rules": [
            {"url": rule.url, "reason": rule.reason, "match": rule.match}
            for rule in sample_rules
        ]
    }
    config_path = tmp_path / "test_config.json"
    config_path.write_text(json.dumps(config_data))
    return str(config_path)


@pytest.fixture
def fresh_stats_collector() -> StatsCollector:
    """Create a fresh StatsCollector instance for testing."""
    return StatsCollector()


@pytest.fixture
def mock_app_state(sample_config, test_secret) -> Generator[AppState, None, None]:
    """
    Set up app_state with test values and reset after test.
    """
    # Store original values
    original_config = app_state.config
    original_secret = app_state.secret
    original_client = app_state.http_client
    
    # Set test values
    app_state.config = sample_config
    app_state.secret = test_secret
    app_state.http_client = httpx.AsyncClient()
    
    yield app_state
    
    # Restore original values
    app_state.config = original_config
    app_state.secret = original_secret
    app_state.http_client = original_client


@pytest.fixture
def mock_env(test_secret_b64, temp_config_file, monkeypatch):
    """Set up environment variables for testing."""
    monkeypatch.setenv("POKEPROXY_SECRET", test_secret_b64)
    monkeypatch.setenv("POKEPROXY_CONFIG", temp_config_file)
    # Clear the cached config
    from app.config import get_config
    get_config.cache_clear()
    yield
    get_config.cache_clear()

