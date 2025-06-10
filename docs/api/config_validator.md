# Configuration Validator API

The configuration validator module provides a schema-based validation system for the NewsBot configuration. This ensures that all configuration values are of the correct type and within acceptable ranges.

## Features

- Type validation for string, integer, boolean, list, and dictionary values
- Required field checking
- Value range validation (min/max)
- String pattern matching
- Default value handling
- Detailed error messages

## Usage

### Basic Validation

```python
from src.core.config_validator import validate_config

# Load your configuration
config = {...}  # Your configuration dictionary

# Validate against the built-in schema
is_valid, errors = validate_config(config)

if not is_valid:
    print("Configuration errors:")
    for error in errors:
        print(f"- {error}")
else:
    print("Configuration is valid")
```

### Applying Defaults

```python
from src.core.config_validator import apply_defaults

# Load your configuration
config = {...}  # Your configuration dictionary

# Apply default values from schema
config_with_defaults = apply_defaults(config)
```

### Custom Schema Validation

```python
from src.core.config_validator import ConfigValidator

# Define a custom schema
custom_schema = {
    "api.url": {
        "type": "str",
        "required": True,
        "pattern": r"^https?://.*$"
    },
    "api.timeout": {
        "type": "int",
        "default": 30,
        "min": 1,
        "max": 120
    }
}

# Validate against custom schema
is_valid, errors = ConfigValidator.validate(config, custom_schema)

# Apply defaults from custom schema
config_with_defaults = ConfigValidator.apply_defaults(config, custom_schema)
```

## Schema Definition

A schema is a dictionary where each key is a configuration path (using dot notation for nested values) and each value is a schema item with validation rules.

### Schema Item Properties

| Property | Type | Description |
| --- | --- | --- |
| `type` | str | The expected data type: "str", "int", "float", "bool", "list", "dict" |
| `required` | bool | Whether the field is required |
| `default` | any | Default value if the field is missing |
| `min` | number | Minimum value (for numeric fields) |
| `max` | number | Maximum value (for numeric fields) |
| `min_length` | int | Minimum length (for strings and lists) |
| `max_length` | int | Maximum length (for strings and lists) |
| `pattern` | str | Regular expression pattern (for strings) |
| `enum` | list | List of allowed values |

## Example Schema

```python
schema = {
    "bot.version": {
        "type": "str",
        "required": True,
    },
    "bot.guild_id": {
        "type": "int",
        "required": True,
    },
    "monitoring.metrics.port": {
        "type": "int",
        "default": 8000,
        "min": 1024,
        "max": 65535,
    },
}
```

## API Reference

### `ConfigValidator` Class

#### `.validate(config: Dict, schema: Dict) -> Tuple[bool, List[str]]`

Validate a configuration against a schema.

- **Parameters:**
  - `config`: Configuration dictionary
  - `schema`: Schema definition
- **Returns:**
  - Tuple of (is_valid, error_messages)

#### `.apply_defaults(config: Dict, schema: Dict) -> Dict`

Apply default values from a schema to a configuration.

- **Parameters:**
  - `config`: Configuration dictionary
  - `schema`: Schema definition
- **Returns:**
  - Updated configuration with defaults applied

### Helper Functions

#### `validate_config(config: Dict) -> Tuple[bool, List[str]]`

Validate a configuration against the built-in NewsBot schema.

- **Parameters:**
  - `config`: Configuration dictionary
- **Returns:**
  - Tuple of (is_valid, error_messages)

#### `apply_defaults(config: Dict) -> Dict`

Apply default values from the built-in NewsBot schema.

- **Parameters:**
  - `config`: Configuration dictionary
- **Returns:**
  - Updated configuration with defaults applied 