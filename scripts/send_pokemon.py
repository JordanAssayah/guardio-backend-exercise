#!/usr/bin/env python3
"""
Test script to send Pokemon to the proxy server.

This script creates Pokemon protobuf messages, signs them, and sends
them to the PokeProxy server for routing to downstream services.

Usage:
    python scripts/send_pokemon.py                    # Send sample Pokemon
    python scripts/send_pokemon.py --legendary        # Send a legendary
    python scripts/send_pokemon.py --powerful         # Send a powerful Pokemon
    python scripts/send_pokemon.py --name Bulbasaur   # Custom Pokemon name
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import os
import sys

import httpx

# Add parent dir to path to import from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.proto import pokemon_pb2


def create_pokemon(
    name: str = "Pikachu",
    number: int = 25,
    type_one: str = "Electric",
    type_two: str = "",
    hit_points: int = 35,
    attack: int = 55,
    defense: int = 40,
    speed: int = 90,
    legendary: bool = False,
    generation: int = 1,
) -> pokemon_pb2.Pokemon:
    """Create a Pokemon protobuf message."""
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
    """Create HMAC-SHA256 signature."""
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


def send_pokemon(pokemon: pokemon_pb2.Pokemon, proxy_url: str, secret: bytes):
    """Send a Pokemon to the proxy server."""
    body = pokemon.SerializeToString()
    signature = sign_body(body, secret)
    
    print(f"\n📤 Sending: {pokemon.name} (#{pokemon.number})")
    print(f"   Type: {pokemon.type_one}" + (f"/{pokemon.type_two}" if pokemon.type_two else ""))
    print(f"   Attack: {pokemon.attack}, HP: {pokemon.hit_points}")
    print(f"   Legendary: {'Yes' if pokemon.legendary else 'No'}")
    
    try:
        response = httpx.post(
            f"{proxy_url}/stream",
            content=body,
            headers={
                "Content-Type": "application/octet-stream",
                "X-Grd-Signature": signature
            },
            timeout=10.0
        )
        
        print(f"\n📥 Response ({response.status_code}):")
        try:
            data = response.json()
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Message: {data.get('message', response.text)}")
            if 'endpoint' in data:
                print(f"   Routed to: {data['endpoint']}")
        except Exception:
            print(f"   {response.text}")
            
    except httpx.RequestError as e:
        print(f"\n❌ Error: {e}")
        print("   Is the proxy server running? (fastapi dev app/main.py)")


def main():
    parser = argparse.ArgumentParser(description="Send Pokemon to PokeProxy")
    parser.add_argument("--name", default="Pikachu", help="Pokemon name")
    parser.add_argument("--number", type=int, default=25, help="Pokemon number")
    parser.add_argument("--attack", type=int, default=55, help="Attack stat")
    parser.add_argument("--hp", type=int, default=35, help="Hit points")
    parser.add_argument("--legendary", action="store_true", help="Make legendary")
    parser.add_argument("--powerful", action="store_true", help="Make powerful (attack>100, hp>50)")
    parser.add_argument("--proxy-url", default="http://localhost:8000", help="Proxy URL")
    parser.add_argument("--secret", help="Base64 secret (or set POKEPROXY_SECRET env)")
    
    args = parser.parse_args()
    
    # Get secret
    secret_b64 = args.secret or os.environ.get("POKEPROXY_SECRET")
    if not secret_b64:
        print("❌ Error: POKEPROXY_SECRET not set")
        print("   Set via --secret or POKEPROXY_SECRET environment variable")
        sys.exit(1)
    
    secret = base64.b64decode(secret_b64)
    
    # Create Pokemon based on flags
    if args.legendary:
        pokemon = create_pokemon(
            name="Mewtwo",
            number=150,
            type_one="Psychic",
            hit_points=106,
            attack=110,
            legendary=True
        )
    elif args.powerful:
        pokemon = create_pokemon(
            name="Dragonite",
            number=149,
            type_one="Dragon",
            type_two="Flying",
            hit_points=91,
            attack=134
        )
    else:
        pokemon = create_pokemon(
            name=args.name,
            number=args.number,
            attack=args.attack,
            hit_points=args.hp,
            legendary=False
        )
    
    send_pokemon(pokemon, args.proxy_url, secret)


if __name__ == "__main__":
    main()

