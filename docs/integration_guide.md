# Configuration Integration Guide

This guide demonstrates how to integrate and use the configuration system in various parts of the NewsBot codebase.

## Basic Usage

### Importing the Configuration

```python
from src.core.simple_config import config
```

### Reading Configuration Values

```python
# Get a basic value
debug_mode = config.get('bot.debug_mode', False)

# Get a nested value
metrics_port = config.get('monitoring.metrics.port', 8000)

# Get a complex structure
redis_config = config.get('cache.redis', {})
if redis_config:
    redis_host = redis_config.get('host', 'localhost')
    redis_port = redis_config.get('port', 6379)
```

## Integration Examples

### Example 1: Using Configuration in a Cog

```python
import discord
from discord.ext import commands
from src.core.simple_config import config

class ExampleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.debug_mode = config.get('bot.debug_mode', False)
        self.admin_role_id = config.get('bot.admin_role_id')
    
    @commands.command()
    async def example(self, ctx):
        # Get configuration dynamically (will detect file changes)
        post_interval = config.get('auto_post.default_interval_hours', 6)
        
        await ctx.send(f"Current post interval: {post_interval} hours")
        
        # Check if in debug mode
        if self.debug_mode:
            await ctx.send("Debug mode is enabled")
```

### Example 2: Using Configuration in a Background Task

```python
import asyncio
import logging
from src.core.simple_config import config

logger = logging.getLogger("NewsBot")

async def monitoring_task(bot):
    while not bot.is_closed():
        try:
            # Get configuration values with defaults
            check_interval = config.get('monitoring.resource_alerts.check_interval', 60)
            cpu_threshold = config.get('monitoring.resource_alerts.cpu_threshold', 80.0)
            ram_threshold = config.get('monitoring.resource_alerts.ram_threshold', 70.0)
            
            # Use the values
            logger.debug(f"Monitoring with CPU threshold: {cpu_threshold}%, "
                         f"RAM threshold: {ram_threshold}%")
            
            # Wait for the configured interval
            await asyncio.sleep(check_interval)
            
        except Exception as e:
            logger.error(f"Error in monitoring task: {e}")
            await asyncio.sleep(60)  # Fall back to 60 seconds on error
```

### Example 3: Using Profiles for Feature Flags

```python
from src.core.simple_config import config

def init_ai_features():
    # Check if AI features are enabled in the current profile
    ai_enabled = config.get('features.ai.enabled', False)
    
    if not ai_enabled:
        return None
    
    # If enabled, initialize with appropriate model
    model_name = config.get('features.ai.model', 'gpt-3.5-turbo')
    api_key = config.get('features.ai.api_key')
    
    if not api_key:
        # Fall back to environment variable if not in config
        import os
        api_key = os.getenv("OPENAI_API_KEY")
    
    # Initialize AI client
    from src.utils.ai_client import AIClient
    return AIClient(model_name, api_key)
```

### Example 4: Validating Configuration at Startup

```python
from src.core.simple_config import config
import sys
import logging

logger = logging.getLogger("NewsBot")

def validate_required_config():
    required_sections = [
        'bot',
        'channels',
        'tokens',
        'telegram'
    ]
    
    missing_sections = []
    
    for section in required_sections:
        if not config.get(section):
            missing_sections.append(section)
    
    if missing_sections:
        logger.critical(f"Missing required configuration sections: {', '.join(missing_sections)}")
        return False
    
    # Validate specific required values
    if not config.validate():
        return False
    
    return True

# Use in main.py
if not validate_required_config():
    logger.critical("Invalid configuration. Exiting.")
    sys.exit(1)
```

## Tips and Best Practices

### 1. Always Provide Default Values

When accessing configuration values, always provide sensible defaults:

```python
# Good
interval = config.get('some.setting', 60)

# Not recommended
interval = config.get('some.setting')  # Could return None
```

### 2. Cache Configuration Values When Appropriate

For values that are used frequently but don't need to be dynamic:

```python
class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cache values that don't change often
        self.admin_role_id = config.get('bot.admin_role_id')
        
    @commands.command()
    async def some_command(self, ctx):
        # Get dynamic values that might change at runtime
        debug_mode = config.get('bot.debug_mode')
```

### 3. Use Type Hints for Better Code Clarity

```python
from typing import Dict, Any, Optional
from src.core.simple_config import config

def init_feature() -> Optional[Dict[str, Any]]:
    feature_config = config.get('features.my_feature', {})
    if not feature_config:
        return None
    
    return {
        'name': feature_config.get('name', 'default'),
        'enabled': feature_config.get('enabled', False),
        'parameters': feature_config.get('parameters', {})
    }
```

### 4. Testing with Configuration Overrides

For testing, use configuration overrides:

```python
import pytest
from src.core.simple_config import config

@pytest.fixture
def test_config():
    # Set up test configuration
    config.set_override('bot.debug_mode', True)
    config.set_override('features.test_feature.enabled', True)
    
    yield config
    
    # Clear overrides after test
    config.clear_overrides()

def test_feature(test_config):
    from src.features import my_feature
    
    # Feature should use the overridden config values
    result = my_feature.initialize()
    assert result.debug_mode is True
```

## Handling Environment Variables

For sensitive data that shouldn't be in the config file:

```python
# In your code
from src.core.simple_config import config
import os

# Try config first, then environment variable as fallback
api_key = config.get('services.external_api.key') or os.getenv("EXTERNAL_API_KEY")

# In config.yaml
services:
  external_api:
    key: ${EXTERNAL_API_KEY}  # Will be loaded from .env
```

## Configuration and Logging

Use the configuration to control logging behavior:

```python
import logging
from src.core.simple_config import config

def setup_logging():
    log_level_name = config.get('logging.level', 'INFO')
    log_file = config.get('logging.file', 'logs/NewsBot.log')
    
    # Convert string to logging level
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        filename=log_file,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger("NewsBot")
    logger.info(f"Logging initialized with level {log_level_name}")
    
    return logger
``` 