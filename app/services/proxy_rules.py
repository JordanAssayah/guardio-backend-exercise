"""
Proxy rules service - loads and matches routing rules for Pokemon forwarding.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class ProxyRule:
    """A routing rule that maps matched Pokemon to a downstream URL."""
    url: str
    reason: str
    match: List[str]


@dataclass
class ProxyConfig:
    """Proxy configuration containing routing rules."""
    rules: List[ProxyRule]


# Regex to parse match expressions like "hit_points==20", "type_two!=word"
_MATCH_PATTERN = re.compile(r"^\s*(\w+)\s*(==|!=|>|<)\s*(.+?)\s*$")


def load_proxy_config(path: str) -> ProxyConfig:
    """
    Load proxy configuration from a JSON file.
    
    Args:
        path: Path to the config JSON file
        
    Returns:
        ProxyConfig object with parsed rules
        
    Raises:
        ValueError: If config file not found, invalid JSON, or missing required fields
    """
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise ValueError(f"Config file not found: {path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")
    
    rules_data = data.get("rules", [])
    if not rules_data:
        raise ValueError("No rules defined in config")
    
    rules = []
    for i, rule_data in enumerate(rules_data):
        # Validate required fields
        if "url" not in rule_data:
            raise ValueError(f"Rule {i} missing required 'url' field")
        if "reason" not in rule_data:
            raise ValueError(f"Rule {i} missing required 'reason' field")
        
        rules.append(ProxyRule(
            url=rule_data["url"],
            reason=rule_data["reason"],
            match=rule_data.get("match", [])
        ))
    
    return ProxyConfig(rules=rules)


def _evaluate_condition(pokemon: Any, condition: str) -> bool:
    """Evaluate a single match condition against a Pokemon."""
    match = _MATCH_PATTERN.match(condition)
    if not match:
        return False
    
    field_name, operator, expected_value = match.groups()
    
    # Check if field actually exists on the protobuf message
    if not hasattr(pokemon, field_name):
        return False  # Unknown field in condition
    
    field_value = getattr(pokemon, field_name)
    
    # Convert expected value to match field type
    try:
        if isinstance(field_value, bool):
            expected = expected_value.lower() in ("true", "1", "yes")
        elif isinstance(field_value, int):
            expected = int(expected_value)
        else:
            expected = expected_value
    except (ValueError, TypeError):
        expected = expected_value
    
    # Evaluate operator
    if operator == "==":
        return field_value == expected
    elif operator == "!=":
        return field_value != expected
    elif operator == ">":
        return field_value > expected
    elif operator == "<":
        return field_value < expected
    
    return False


def find_matching_rule(pokemon: Any, rules: List[ProxyRule]) -> Optional[ProxyRule]:
    """
    Find the first matching rule for a Pokemon.
    All conditions in a rule must match (AND logic).
    
    Returns:
        The first matching ProxyRule, or None if no rules match
    """
    for rule in rules:
        if all(_evaluate_condition(pokemon, cond) for cond in rule.match):
            return rule
    return None

