"""
Configuration Validator Module

This module provides schema-based validation for the NewsBot configuration.
Features:
- Type validation
- Required field checking
- Default value handling
- Detailed error messages
"""

from typing import Any, Dict, List, Optional, Tuple, Union, Set
import re
import logging

logger = logging.getLogger("NewsBot")


class ValidationError(Exception):
    """Exception raised for configuration validation errors."""
    pass


class ConfigValidator:
    """
    Validates configuration against a schema.
    """

    @staticmethod
    def validate(config: Dict, schema: Dict) -> Tuple[bool, List[str]]:
        """
        Validate configuration against a schema.

        Args:
            config: Configuration dictionary
            schema: Schema definition

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        for key, schema_item in schema.items():
            if "." in key:
                # Handle nested keys with dot notation
                parts = key.split(".")
                value = config
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        if schema_item.get("required", False):
                            errors.append(f"Missing required key: {key}")
                        break
                else:
                    # We found the value, validate it
                    result = ConfigValidator._validate_value(key, value, schema_item)
                    if not result[0]:
                        errors.extend(result[1])
            elif key in config:
                # Direct key
                result = ConfigValidator._validate_value(key, config[key], schema_item)
                if not result[0]:
                    errors.extend(result[1])
            elif schema_item.get("required", False):
                errors.append(f"Missing required key: {key}")

        return len(errors) == 0, errors

    @staticmethod
    def _validate_value(key: str, value: Any, schema_item: Dict) -> Tuple[bool, List[str]]:
        """
        Validate a single value against its schema.

        Args:
            key: Key name
            value: Value to validate
            schema_item: Schema for this value

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check type
        expected_type = schema_item.get("type")
        if expected_type:
            if expected_type == "str" and not isinstance(value, str):
                errors.append(f"Key '{key}' must be a string, got {type(value).__name__}")
            elif expected_type == "int" and not isinstance(value, int):
                errors.append(f"Key '{key}' must be an integer, got {type(value).__name__}")
            elif expected_type == "float" and not isinstance(value, (int, float)):
                errors.append(f"Key '{key}' must be a number, got {type(value).__name__}")
            elif expected_type == "bool" and not isinstance(value, bool):
                errors.append(f"Key '{key}' must be a boolean, got {type(value).__name__}")
            elif expected_type == "list" and not isinstance(value, list):
                errors.append(f"Key '{key}' must be a list, got {type(value).__name__}")
            elif expected_type == "dict" and not isinstance(value, dict):
                errors.append(f"Key '{key}' must be a dictionary, got {type(value).__name__}")
            elif expected_type == "str_or_int" and not isinstance(value, (str, int)):
                errors.append(f"Key '{key}' must be a string or integer, got {type(value).__name__}")

        # Check required
        if schema_item.get("required", False) and (value is None or (isinstance(value, str) and value == "")):
            errors.append(f"Key '{key}' is required and cannot be empty")

        # Check pattern
        pattern = schema_item.get("pattern")
        if pattern and isinstance(value, str):
            if not re.match(pattern, value):
                errors.append(f"Key '{key}' value '{value}' does not match pattern '{pattern}'")

        # Check min/max for numeric values
        if isinstance(value, (int, float)):
            min_val = schema_item.get("min")
            if min_val is not None and value < min_val:
                errors.append(f"Key '{key}' value {value} is less than minimum {min_val}")

            max_val = schema_item.get("max")
            if max_val is not None and value > max_val:
                errors.append(f"Key '{key}' value {value} is greater than maximum {max_val}")

        # Check min/max length for strings and lists
        if isinstance(value, (str, list)):
            min_length = schema_item.get("min_length")
            if min_length is not None and len(value) < min_length:
                errors.append(f"Key '{key}' length {len(value)} is less than minimum length {min_length}")

            max_length = schema_item.get("max_length")
            if max_length is not None and len(value) > max_length:
                errors.append(f"Key '{key}' length {len(value)} is greater than maximum length {max_length}")

        # Check enum values
        enum_values = schema_item.get("enum")
        if enum_values and value not in enum_values:
            errors.append(f"Key '{key}' value '{value}' must be one of: {', '.join(str(v) for v in enum_values)}")

        return len(errors) == 0, errors

    @staticmethod
    def apply_defaults(config: Dict, schema: Dict) -> Dict:
        """
        Apply default values from schema to config.

        Args:
            config: Configuration dictionary
            schema: Schema definition

        Returns:
            Updated configuration with defaults applied
        """
        # Create a deep copy to avoid modifying the original
        import copy
        result = copy.deepcopy(config)

        for key, schema_item in schema.items():
            if "default" in schema_item:
                if "." in key:
                    # Handle nested keys with dot notation
                    parts = key.split(".")
                    current = result
                    # Navigate to the parent dictionary
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]

                    # Set the default if the key doesn't exist
                    if parts[-1] not in current:
                        current[parts[-1]] = schema_item["default"]
                elif key not in result:
                    # Direct key
                    result[key] = schema_item["default"]

        return result


# NewsBot configuration schema
NEWSBOT_CONFIG_SCHEMA = {
    "bot.version": {
        "type": "str",
        "required": True,
    },
    "bot.guild_id": {
        "type": "int",
        "required": True,
    },
    "bot.application_id": {
        "type": "str_or_int",
        "required": True,
    },
    "bot.debug_mode": {
        "type": "bool",
        "default": False,
    },
    "bot.admin_role_id": {
        "type": "int",
        "required": True,
    },
    "bot.news_role_id": {
        "type": "int",
        "required": True,
    },
    "channels.news": {
        "type": "int",
        "required": True,
    },
    "channels.errors": {
        "type": "int",
        "required": True,
    },
    "channels.logs": {
        "type": "int",
        "required": True,
    },
    "tokens.discord": {
        "type": "str",
        "required": True,
        "min_length": 10,
    },
    "telegram.api_id": {
        "type": "int",
        "required": True,
    },
    "telegram.api_hash": {
        "type": "str",
        "required": True,
    },
    "monitoring.metrics.port": {
        "type": "int",
        "default": 8000,
        "min": 1024,
        "max": 65535,
    },
    "monitoring.metrics.collection_interval": {
        "type": "int",
        "default": 60,
        "min": 10,
        "max": 3600,
    },
    "security.rate_limits.default": {
        "type": "int",
        "default": 5,
        "min": 1,
    },
    "security.rate_limits.cooldown": {
        "type": "int",
        "default": 60,
        "min": 1,
    },
}


def validate_config(config: Dict) -> Tuple[bool, List[str]]:
    """
    Validate the NewsBot configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Tuple of (is_valid, error_messages)
    """
    return ConfigValidator.validate(config, NEWSBOT_CONFIG_SCHEMA)


def apply_defaults(config: Dict) -> Dict:
    """
    Apply default values to configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Updated configuration with defaults
    """
    return ConfigValidator.apply_defaults(config, NEWSBOT_CONFIG_SCHEMA)
