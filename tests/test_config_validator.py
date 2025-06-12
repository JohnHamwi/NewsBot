"""
Test suite for the ConfigValidator class.
"""

import pytest

from src.core.config_validator import ConfigValidator, apply_defaults, validate_config


def test_config_validator_basic_validation():
    """Test basic validation of configuration."""
    # Define a simple schema
    schema = {
        "test.string": {
            "type": "str",
            "required": True,
        },
        "test.number": {
            "type": "int",
            "min": 1,
            "max": 100,
        },
        "test.optional": {
            "type": "str",
            "required": False,
        },
    }

    # Valid config
    valid_config = {
        "test": {
            "string": "value",
            "number": 42,
        }
    }

    is_valid, errors = ConfigValidator.validate(valid_config, schema)
    assert is_valid is True
    assert len(errors) == 0

    # Invalid config (missing required field)
    invalid_config = {
        "test": {
            "number": 42,
        }
    }

    is_valid, errors = ConfigValidator.validate(invalid_config, schema)
    assert is_valid is False
    assert len(errors) == 1
    assert "Missing required key: test.string" in errors[0]

    # Invalid config (wrong type)
    invalid_config = {
        "test": {
            "string": "value",
            "number": "not a number",
        }
    }

    is_valid, errors = ConfigValidator.validate(invalid_config, schema)
    assert is_valid is False
    assert len(errors) == 1
    assert "must be an integer" in errors[0]

    # Invalid config (out of range)
    invalid_config = {
        "test": {
            "string": "value",
            "number": 101,
        }
    }

    is_valid, errors = ConfigValidator.validate(invalid_config, schema)
    assert is_valid is False
    assert len(errors) == 1
    assert "greater than maximum" in errors[0]


def test_config_validator_defaults():
    """Test applying defaults to configuration."""
    # Define a schema with defaults
    schema = {
        "test.string": {
            "type": "str",
            "default": "default value",
        },
        "test.number": {
            "type": "int",
            "default": 42,
        },
        "test.nested.value": {
            "type": "str",
            "default": "nested default",
        },
    }

    # Empty config
    config = {}

    # Apply defaults
    result = ConfigValidator.apply_defaults(config, schema)

    # Check direct keys
    assert result.get("test", {}).get("string") == "default value"
    assert result.get("test", {}).get("number") == 42

    # Check nested keys
    assert result.get("test", {}).get("nested", {}).get("value") == "nested default"

    # Original config should be unchanged
    assert config == {}


def test_validate_config_function():
    """Test the validate_config function with the NewsBot schema."""
    # Create a minimal valid config
    config = {
        "bot": {
            "version": "2.0.0",
            "guild_id": 123456789,
            "application_id": "987654321",
            "admin_role_id": 123456,
            "news_role_id": 654321,
        },
        "channels": {
            "news": 111111,
            "errors": 222222,
            "logs": 333333,
        },
        "tokens": {
            "discord": "discord_token_here",
        },
        "telegram": {
            "api_id": 12345,
            "api_hash": "api_hash_here",
        },
    }

    # Should be valid
    is_valid, errors = validate_config(config)
    assert is_valid is True
    assert len(errors) == 0

    # Now make it invalid by removing a required field
    invalid_config = config.copy()
    del invalid_config["bot"]["guild_id"]

    is_valid, errors = validate_config(invalid_config)
    assert is_valid is False
    assert len(errors) >= 1
    assert any("guild_id" in error for error in errors)


def test_apply_defaults_function():
    """Test the apply_defaults function with the NewsBot schema."""
    # Create a minimal config
    config = {
        "bot": {
            "version": "2.0.0",
            "guild_id": 123456789,
            "application_id": "987654321",
            "admin_role_id": 123456,
            "news_role_id": 654321,
        },
        "channels": {
            "news": 111111,
            "errors": 222222,
            "logs": 333333,
        },
        "tokens": {
            "discord": "discord_token_here",
        },
        "telegram": {
            "api_id": 12345,
            "api_hash": "api_hash_here",
        },
    }

    # Apply defaults
    result = apply_defaults(config)

    # Check defaults were applied
    assert "debug_mode" in result["bot"]
    assert result["bot"]["debug_mode"] is False

    assert "monitoring" in result
    assert "metrics" in result["monitoring"]
    assert "port" in result["monitoring"]["metrics"]
    assert result["monitoring"]["metrics"]["port"] == 8000
    assert "collection_interval" in result["monitoring"]["metrics"]
    assert result["monitoring"]["metrics"]["collection_interval"] == 60

    # Original config should not have these
    assert "debug_mode" not in config.get("bot", {})
    assert "monitoring" not in config
