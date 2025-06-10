# Core Modules Documentation

This document provides detailed information about the core modules that power NewsBot.

## Table of Contents
1. [Configuration Manager](#configuration-manager)
2. [Circuit Breaker](#circuit-breaker)
3. [Role-Based Access Control](#role-based-access-control)
4. [Rich Presence](#rich-presence)
5. [JSON Cache](#json-cache)
6. [Metrics Manager](#metrics-manager)

---

## Configuration Manager

**File**: `src/core/config_manager.py`

The Configuration Manager is responsible for loading, validating, and providing access to configuration values from YAML files and environment variables.

### Key Features

- **Singleton Pattern**: Ensures only one instance of the configuration exists throughout the application
- **Environment Variable Substitution**: Automatically replaces `${VARIABLE}` patterns with values from environment variables
- **Type Conversion**: Converts numeric and boolean values to appropriate Python types
- **Dot Notation Access**: Allows accessing nested configuration with dot notation (e.g., `config.get('bot.version')`)
- **Validation**: Verifies that all required configuration values are present

### API Reference

#### `ConfigManager()`
Constructor that loads configuration on first instantiation.

#### `reload_config() -> None`
Reloads configuration from the YAML file and applies environment variable substitution.

#### `get(key: str, default: Any = None) -> Any`
Retrieves a configuration value using dot notation.

**Parameters**:
- `key`: The configuration key in dot notation (e.g., 'bot.version')
- `default`: Default value if key not found

**Returns**:
- The configuration value with its proper type (int, bool, str, dict, etc.)

#### `validate() -> bool`
Validates that all required configuration keys are present.

**Returns**:
- `True` if configuration is valid, `False` otherwise

#### `raw_config -> Dict[str, Any]`
Property that returns a deep copy of the entire configuration dictionary.

### Usage Example

```python
from src.core.config_manager import config

# Get configuration values
discord_token = config.get('tokens.discord')
guild_id = config.get('bot.guild_id')  # Returns an integer
debug_mode = config.get('bot.debug_mode', False)  # Returns a boolean

# Validate configuration
if not config.validate():
    print("Configuration is invalid!")
```

---

## Circuit Breaker

**File**: `src/core/circuit_breaker.py`

The Circuit Breaker pattern prevents cascading failures in distributed systems by temporarily cutting off communication with failing external services.

### States

1. **CLOSED**: Normal operation - requests are allowed
2. **OPEN**: Service is unavailable - requests are rejected without attempting
3. **HALF_OPEN**: Testing period - limited requests are allowed to test if service has recovered

### Key Features

- **Automatic State Transitions**: Changes state based on failure thresholds
- **Failure Counting**: Tracks consecutive failures to determine state changes
- **Timeout Management**: Automatically resets after specified timeout periods
- **Context Manager Support**: Can be used with Python's `with` statement
- **Service Isolation**: Prevents cascading failures by isolating problematic services

### API Reference

#### `CircuitBreaker(service_name: str, failure_threshold: int = 5, reset_timeout: int = 60, half_open_timeout: int = 30)`

Constructor for the circuit breaker.

**Parameters**:
- `service_name`: Name of the service being protected
- `failure_threshold`: Number of failures before opening circuit (default: 5)
- `reset_timeout`: Seconds to wait before trying to recover (default: 60)
- `half_open_timeout`: Seconds to stay in half-open state before closing (default: 30)

#### `async __aenter__() -> CircuitBreaker`
Async context manager entry - verifies circuit state.

**Raises**:
- `CircuitBreakerOpenError`: If the circuit is open

**Returns**:
- The circuit breaker instance

#### `async __aexit__(exc_type, exc_val, exc_tb) -> None`
Async context manager exit - handles success or failure.

#### `record_success() -> None`
Records a successful operation, potentially closing the circuit.

#### `record_failure() -> None`
Records a failed operation, potentially opening the circuit.

#### `get_state() -> CircuitState`
Gets the current state of the circuit.

**Returns**:
- `CircuitState` enum value (OPEN, CLOSED, or HALF_OPEN)

#### `get_stats() -> Dict[str, Any]`
Gets statistics about the circuit breaker.

**Returns**:
- Dictionary with circuit breaker statistics

### Usage Example

```python
from src.core.circuit_breaker import CircuitBreaker

# Create a circuit breaker for Telegram API
telegram_cb = CircuitBreaker("telegram_service", failure_threshold=3)

async def fetch_telegram_messages():
    try:
        async with telegram_cb:
            # API call that might fail
            messages = await telegram_client.get_messages("channel_name")
            telegram_cb.record_success()
            return messages
    except CircuitBreakerOpenError:
        # Circuit is open, don't attempt the call
        return "Service temporarily unavailable"
    except Exception as e:
        # Operation failed
        telegram_cb.record_failure()
        raise
```

---

## Role-Based Access Control

**File**: `src/security/rbac.py`

The RBAC Manager provides role-based access control for bot commands, ensuring only authorized users can execute certain actions.

### Key Features

- **Role Management**: Define roles with specific permissions
- **Permission Checks**: Verify if users have required permissions
- **Dynamic Loading**: Load permissions and role assignments from configuration
- **User-Role Mapping**: Associate Discord user IDs with roles
- **Permission Hierarchy**: Permissions can be organized hierarchically

### API Reference

#### `RBACManager()`
Constructor for the RBAC manager.

#### `load_permissions() -> None`
Loads permissions and role definitions from configuration.

#### `add_permission(permission: str) -> bool`
Adds a new permission to the system.

**Parameters**:
- `permission`: The permission identifier (e.g., "admin.access")

**Returns**:
- `True` if added successfully, `False` otherwise

#### `add_role(role_name: str, role_id: Optional[int] = None) -> bool`
Adds a new role to the system.

**Parameters**:
- `role_name`: The name of the role
- `role_id`: Discord role ID (optional)

**Returns**:
- `True` if added successfully, `False` otherwise

#### `assign_permission_to_role(role_name: str, permission: str) -> bool`
Assigns a permission to a role.

**Parameters**:
- `role_name`: The name of the role
- `permission`: The permission identifier

**Returns**:
- `True` if assigned successfully, `False` otherwise

#### `has_permission(user_id: int, permission: str) -> bool`
Checks if a user has a specific permission.

**Parameters**:
- `user_id`: Discord user ID
- `permission`: The permission identifier

**Returns**:
- `True` if the user has the permission, `False` otherwise

### Usage Example

```python
from src.security.rbac import RBACManager

rbac = RBACManager()
rbac.load_permissions()

# Check if a user can access admin features
if rbac.has_permission(interaction.user.id, "admin.access"):
    # Allow admin action
    await perform_admin_action()
else:
    # Deny access
    await interaction.response.send_message("You don't have permission to use this command.")
```

---

## Rich Presence

**File**: `src/core/rich_presence.py`

The Rich Presence module manages the bot's Discord presence status, providing visual indicators of the bot's current state.

### Key Features

- **Multiple Status Modes**: Supports different modes (automatic, maintenance, posted)
- **Dynamic Updates**: Updates status based on next post time
- **Visual Indicators**: Uses emojis and status descriptions to convey state
- **Activity Tracking**: Shows relevant activities based on bot state

### API Reference

#### `async set_automatic_presence(bot, countdown_seconds: int = 0) -> None`
Sets the bot's presence to automatic mode with countdown.

**Parameters**:
- `bot`: The NewsBot instance
- `countdown_seconds`: Seconds until next post (for countdown display)

#### `async set_maintenance_presence(bot) -> None`
Sets the bot's presence to maintenance mode.

**Parameters**:
- `bot`: The NewsBot instance

#### `async set_posted_presence(bot) -> None`
Sets the bot's presence to indicate a post was just made.

**Parameters**:
- `bot`: The NewsBot instance

### Usage Example

```python
from src.core.rich_presence import set_automatic_presence, set_maintenance_presence, set_posted_presence

# After posting content
await set_posted_presence(bot)

# When entering maintenance mode
await set_maintenance_presence(bot)

# During normal operation
next_post_seconds = (next_post_time - current_time).total_seconds()
await set_automatic_presence(bot, next_post_seconds)
```

---

## JSON Cache

**File**: `src/cache/redis_cache.py`

The JSON Cache provides persistent storage for bot state and configuration, reducing API calls and maintaining state across restarts.

### Key Features

- **Key-Value Storage**: Simple interface for storing and retrieving JSON-serializable data
- **Persistence**: Saves data to disk for recovery after restarts
- **Channel Management**: Special functions for managing Telegram channels
- **Post Blacklisting**: Tracks blacklisted post IDs to avoid reposting

### API Reference

#### `JSONCache()`
Constructor for the JSON cache.

#### `async get(key: str) -> Any`
Gets a value from the cache.

**Parameters**:
- `key`: The cache key

**Returns**:
- The cached value, or None if not found

#### `async set(key: str, value: Any) -> bool`
Sets a value in the cache.

**Parameters**:
- `key`: The cache key
- `value`: The value to cache (must be JSON-serializable)

**Returns**:
- `True` if successful, `False` otherwise

#### `async save() -> bool`
Saves the cache to disk.

**Returns**:
- `True` if successful, `False` otherwise

#### `async list_telegram_channels(status: str = "all") -> List[str]`
Lists Telegram channels by status.

**Parameters**:
- `status`: Filter by status ("all", "activated", or "deactivated")

**Returns**:
- List of channel usernames

### Usage Example

```python
from src.cache.redis_cache import JSONCache

cache = JSONCache()

# Save post configuration
await cache.set("auto_post_config", {
    "interval": 3600,
    "last_post_time": datetime.datetime.utcnow().isoformat()
})

# Get configuration later
config = await cache.get("auto_post_config")
interval = config.get("interval", 0)

# List active channels
channels = await cache.list_telegram_channels("activated")
```

---

## Metrics Manager

**File**: `src/monitoring/metrics.py`

The Metrics Manager collects and exposes Prometheus metrics for monitoring bot performance and resource usage.

### Key Features

- **Prometheus Integration**: Exposes metrics in Prometheus format
- **Command Metrics**: Tracks command execution times
- **Error Tracking**: Counts errors by type
- **Resource Monitoring**: Tracks memory usage and system resources
- **Message Counting**: Tracks message processing

### API Reference

#### `MetricsManager(port: int = 8000)`
Constructor for the metrics manager.

**Parameters**:
- `port`: HTTP port to expose metrics on

#### `start() -> None`
Starts the metrics server.

#### `record_command(command_name: str, duration: float) -> None`
Records command execution metrics.

**Parameters**:
- `command_name`: Name of the command
- `duration`: Execution time in seconds

#### `record_error(error_type: str) -> None`
Records error occurrence.

**Parameters**:
- `error_type`: Type of error

#### `record_message(source: str, _: float = None) -> None`
Records message count.

**Parameters**:
- `source`: Message source

#### `update_system_metrics() -> None`
Updates system metrics (memory usage, etc.).

#### `get_metrics_summary() -> Dict[str, Any]`
Gets a summary of collected metrics.

**Returns**:
- Dictionary with metrics summary

### Usage Example

```python
from src.monitoring.metrics import MetricsManager

metrics = MetricsManager(port=8000)
metrics.start()

# Record command execution
start_time = time.time()
await execute_command()
duration = time.time() - start_time
metrics.record_command("fetch", duration)

# Record error
try:
    await risky_operation()
except Exception as e:
    metrics.record_error(type(e).__name__)
    raise

# Update system metrics
metrics.update_system_metrics()
``` 