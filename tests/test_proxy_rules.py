"""
Tests for the proxy rules service - config loading and rule matching.
"""
import json

import pytest

from app.proto import pokemon_pb2
from app.services.proxy_rules import (
    ProxyConfig,
    ProxyRule,
    load_proxy_config,
    find_matching_rule,
    _evaluate_condition,
)
from tests.conftest import create_pokemon


class TestLoadProxyConfig:
    """Tests for load_proxy_config function."""

    def test_load_valid_config(self, temp_config_file):
        """Should load valid config file successfully."""
        config = load_proxy_config(temp_config_file)
        
        assert isinstance(config, ProxyConfig)
        assert len(config.rules) == 3

    def test_load_config_preserves_rule_order(self, temp_config_file):
        """Rules should maintain their order from the config file."""
        config = load_proxy_config(temp_config_file)
        
        assert config.rules[0].reason == "legendary pokemon"
        assert config.rules[1].reason == "high attack pokemon"
        assert config.rules[2].reason == "default catch-all"

    def test_load_config_file_not_found(self):
        """Should raise ValueError for missing file."""
        with pytest.raises(ValueError, match="Config file not found"):
            load_proxy_config("/nonexistent/path/config.json")

    def test_load_config_invalid_json(self, tmp_path):
        """Should raise ValueError for invalid JSON."""
        config_path = tmp_path / "invalid.json"
        config_path.write_text("{ not valid json }")
        
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_proxy_config(str(config_path))

    def test_load_config_no_rules(self, tmp_path):
        """Should raise ValueError when no rules defined."""
        config_path = tmp_path / "empty_rules.json"
        config_path.write_text('{"rules": []}')
        
        with pytest.raises(ValueError, match="No rules defined"):
            load_proxy_config(str(config_path))

    def test_load_config_missing_url(self, tmp_path):
        """Should raise ValueError when rule missing url."""
        config_path = tmp_path / "no_url.json"
        config_path.write_text('{"rules": [{"reason": "test"}]}')
        
        with pytest.raises(ValueError, match="missing required 'url' field"):
            load_proxy_config(str(config_path))

    def test_load_config_missing_reason(self, tmp_path):
        """Should raise ValueError when rule missing reason."""
        config_path = tmp_path / "no_reason.json"
        config_path.write_text('{"rules": [{"url": "http://test.com"}]}')
        
        with pytest.raises(ValueError, match="missing required 'reason' field"):
            load_proxy_config(str(config_path))

    def test_load_config_empty_match_array(self, tmp_path):
        """Should handle rules with empty match array (catch-all)."""
        config_path = tmp_path / "catch_all.json"
        config_path.write_text(json.dumps({
            "rules": [{"url": "http://test.com", "reason": "catch-all", "match": []}]
        }))
        
        config = load_proxy_config(str(config_path))
        assert config.rules[0].match == []

    def test_load_config_missing_match_defaults_empty(self, tmp_path):
        """Rules without match field should default to empty list."""
        config_path = tmp_path / "no_match.json"
        config_path.write_text(json.dumps({
            "rules": [{"url": "http://test.com", "reason": "test"}]
        }))
        
        config = load_proxy_config(str(config_path))
        assert config.rules[0].match == []


class TestEvaluateCondition:
    """Tests for _evaluate_condition function."""

    def test_equality_string(self):
        """Test string equality operator."""
        pokemon = create_pokemon(name="Pikachu", type_one="Electric")
        
        assert _evaluate_condition(pokemon, "name==Pikachu") is True
        assert _evaluate_condition(pokemon, "name==Charmander") is False
        assert _evaluate_condition(pokemon, "type_one==Electric") is True

    def test_equality_integer(self):
        """Test integer equality operator."""
        pokemon = create_pokemon(attack=55, hit_points=35)
        
        assert _evaluate_condition(pokemon, "attack==55") is True
        assert _evaluate_condition(pokemon, "attack==100") is False
        assert _evaluate_condition(pokemon, "hit_points==35") is True

    def test_equality_boolean(self):
        """Test boolean equality operator."""
        legendary = create_pokemon(legendary=True)
        normal = create_pokemon(legendary=False)
        
        assert _evaluate_condition(legendary, "legendary==true") is True
        assert _evaluate_condition(legendary, "legendary==false") is False
        assert _evaluate_condition(normal, "legendary==false") is True
        assert _evaluate_condition(normal, "legendary==true") is False

    def test_inequality_operator(self):
        """Test inequality operator."""
        pokemon = create_pokemon(name="Pikachu", legendary=False)
        
        assert _evaluate_condition(pokemon, "name!=Charmander") is True
        assert _evaluate_condition(pokemon, "name!=Pikachu") is False
        assert _evaluate_condition(pokemon, "legendary!=true") is True

    def test_greater_than_operator(self):
        """Test greater than operator."""
        pokemon = create_pokemon(attack=100, hit_points=50)
        
        assert _evaluate_condition(pokemon, "attack>99") is True
        assert _evaluate_condition(pokemon, "attack>100") is False
        assert _evaluate_condition(pokemon, "attack>101") is False
        assert _evaluate_condition(pokemon, "hit_points>49") is True

    def test_less_than_operator(self):
        """Test less than operator."""
        pokemon = create_pokemon(attack=50, speed=80)
        
        assert _evaluate_condition(pokemon, "attack<51") is True
        assert _evaluate_condition(pokemon, "attack<50") is False
        assert _evaluate_condition(pokemon, "speed<100") is True

    def test_invalid_condition_format(self):
        """Invalid condition format should return False."""
        pokemon = create_pokemon()
        
        assert _evaluate_condition(pokemon, "invalid") is False
        assert _evaluate_condition(pokemon, "no_operator_here") is False
        assert _evaluate_condition(pokemon, "") is False

    def test_unknown_field(self):
        """Unknown field in condition should return False."""
        pokemon = create_pokemon()
        
        assert _evaluate_condition(pokemon, "unknown_field==value") is False

    def test_whitespace_handling(self):
        """Conditions with extra whitespace should work."""
        pokemon = create_pokemon(attack=100)
        
        assert _evaluate_condition(pokemon, "  attack == 100  ") is True
        assert _evaluate_condition(pokemon, "attack == 100") is True


class TestFindMatchingRule:
    """Tests for find_matching_rule function."""

    def test_match_legendary_rule(self, sample_rules, legendary_pokemon):
        """Legendary Pokemon should match legendary rule."""
        rule = find_matching_rule(legendary_pokemon, sample_rules)
        
        assert rule is not None
        assert rule.reason == "legendary pokemon"
        assert rule.url == "http://localhost:9001/legendary"

    def test_match_powerful_rule(self, sample_rules, powerful_pokemon):
        """Powerful non-legendary Pokemon should match powerful rule."""
        rule = find_matching_rule(powerful_pokemon, sample_rules)
        
        assert rule is not None
        assert rule.reason == "high attack pokemon"
        assert rule.url == "http://localhost:9001/powerful"

    def test_match_default_rule(self, sample_rules, sample_pokemon):
        """Normal Pokemon should match default catch-all rule."""
        rule = find_matching_rule(sample_pokemon, sample_rules)
        
        assert rule is not None
        assert rule.reason == "default catch-all"
        assert rule.url == "http://localhost:9001/default"

    def test_first_match_wins(self, sample_rules):
        """When multiple rules could match, first one wins."""
        # Create a legendary Pokemon with high attack (could match both rules)
        legendary_powerful = create_pokemon(
            name="Mewtwo",
            attack=150,
            hit_points=100,
            legendary=True
        )
        
        rule = find_matching_rule(legendary_powerful, sample_rules)
        
        # Should match legendary rule first (it's listed first)
        assert rule.reason == "legendary pokemon"

    def test_no_match_without_catch_all(self):
        """Should return None when no rules match and no catch-all."""
        rules = [
            ProxyRule(
                url="http://test.com",
                reason="only legendary",
                match=["legendary==true"]
            )
        ]
        pokemon = create_pokemon(legendary=False)
        
        rule = find_matching_rule(pokemon, rules)
        assert rule is None

    def test_all_conditions_must_match(self):
        """All conditions in a rule must be satisfied (AND logic)."""
        rules = [
            ProxyRule(
                url="http://test.com",
                reason="strong fast",
                match=["attack>100", "speed>100"]  # Both must match
            )
        ]
        
        # Strong but slow
        slow_pokemon = create_pokemon(attack=150, speed=50)
        assert find_matching_rule(slow_pokemon, rules) is None
        
        # Fast but weak
        weak_pokemon = create_pokemon(attack=50, speed=150)
        assert find_matching_rule(weak_pokemon, rules) is None
        
        # Both strong and fast
        strong_fast = create_pokemon(attack=150, speed=150)
        rule = find_matching_rule(strong_fast, rules)
        assert rule is not None
        assert rule.reason == "strong fast"

    def test_empty_rules_list(self):
        """Empty rules list should return None."""
        pokemon = create_pokemon()
        assert find_matching_rule(pokemon, []) is None

