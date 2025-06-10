# Rate Limiter API

The Rate Limiter module provides efficient rate limiting for API calls using the token bucket algorithm. It helps prevent hitting API rate limits, especially for the Telegram API.

## Features

- Token bucket algorithm for smooth rate limiting
- Per-endpoint rate limiters
- Automatic waiting when rate limited
- Decorator for easy application to functions
- Detailed statistics for monitoring
- Handling of Telegram's FloodWaitError

## Usage

### Basic Rate Limiting

```python
import asyncio
from src.utils.rate_limiter import rate_limiter_manager

async def main():
    # Get a pre-configured rate limiter for Telegram
    # This will wait automatically if rate limited
    await rate_limiter_manager.acquire("telegram")
    
    # Make your API call here
    await telegram_api_call()
    
    # Get stats about rate limiting
    stats = rate_limiter_manager.get_all_stats()
    print(stats["telegram"])
```

### Using the Decorator

```python
from src.utils.rate_limiter import rate_limited

# Apply rate limiting to a function
@rate_limited("telegram")
async def fetch_telegram_messages(chat_id):
    # This function will be automatically rate limited
    # Make your API call here
    return await client.get_messages(chat_id, limit=10)
```

### Custom Rate Limiters

```python
from src.utils.rate_limiter import rate_limiter_manager

# Add a custom rate limiter
rate_limiter_manager.add_limiter(
    name="my_api",
    calls_per_second=5.0,
    burst_limit=10,
    auto_wait=True
)

# Use the custom rate limiter
await rate_limiter_manager.acquire("my_api")
```

## Default Rate Limiters

The following rate limiters are created by default:

| Name | Calls Per Second | Burst Limit | Description |
| --- | --- | --- | --- |
| `telegram` | 20.0 | 30 | For Telegram API calls |
| `discord` | 30.0 | 50 | For Discord API calls |
| `default` | 5.0 | 10 | Default for other services |

## Token Bucket Algorithm

The rate limiter uses the token bucket algorithm:

1. Each rate limiter has a bucket of tokens (initially full with `burst_limit` tokens)
2. Tokens are refilled at a rate of `calls_per_second` per second
3. Each API call consumes one token
4. If no tokens are available, the call waits until a token is available
5. This allows for bursts of activity while maintaining a long-term average rate

## API Reference

### `RateLimiter` Class

#### `__init__(name: str, calls_per_second: float = 1.0, burst_limit: int = 5, auto_wait: bool = True)`

Initialize a rate limiter.

- **Parameters:**
  - `name`: Name for this rate limiter
  - `calls_per_second`: Maximum calls per second
  - `burst_limit`: Maximum burst of calls allowed
  - `auto_wait`: Whether to automatically wait when rate limited

#### `async acquire() -> float`

Acquire a token from the bucket.

- **Returns:**
  - Time waited in seconds (0.0 if no wait)

#### `get_stats() -> Dict[str, Any]`

Get rate limiter statistics.

- **Returns:**
  - Dictionary of stats including total calls, waited calls, etc.

### `RateLimiterManager` Class

#### `add_limiter(name: str, calls_per_second: float = 1.0, burst_limit: int = 5, auto_wait: bool = True) -> RateLimiter`

Add a new rate limiter.

- **Parameters:**
  - `name`: Name for the rate limiter
  - `calls_per_second`: Maximum calls per second
  - `burst_limit`: Maximum burst of calls allowed
  - `auto_wait`: Whether to automatically wait when rate limited
- **Returns:**
  - The created rate limiter

#### `get_limiter(name: str) -> RateLimiter`

Get a rate limiter by name.

- **Parameters:**
  - `name`: Name of the rate limiter
- **Returns:**
  - The rate limiter (falls back to "default" if not found)

#### `async acquire(name: str) -> float`

Acquire a token from a rate limiter.

- **Parameters:**
  - `name`: Name of the rate limiter
- **Returns:**
  - Time waited in seconds

#### `get_all_stats() -> Dict[str, Dict[str, Any]]`

Get statistics for all rate limiters.

- **Returns:**
  - Dictionary of rate limiter stats

### Decorator

#### `@rate_limited(limiter_name: str)`

Decorator to apply rate limiting to a function.

- **Parameters:**
  - `limiter_name`: Name of the rate limiter to use
- **Returns:**
  - Decorated function that acquires a token before execution

## Global Instance

A global `rate_limiter_manager` instance is provided for convenience. This can be used throughout the application without creating new instances. 