# Configuration System

This document explains how to use NewsBot's configuration system.

## Overview

NewsBot uses a flexible, developer-friendly configuration system that combines:

1. **YAML Configuration Files** - Main settings defined in YAML
2. **Environment Variables** - Secret values stored in `.env` files
3. **Configuration Profiles** - Different settings for development, testing, and production
4. **Live Reloading** - Changes to config files are detected automatically
5. **Runtime Overrides** - Temporary changes via Discord commands

## Basic Usage

### Config File Structure

The main configuration file is `config.yaml` in the project root. It uses a hierarchical structure with dot notation:

```yaml
# Bot settings
bot:
  version: "4.5.0"
  debug_mode: true

# Channel IDs
channels:
  news: 123456789
  errors: 987654321
```

### Reading Configuration Values

```python
from src.core.simple_config import config

# Get a value with dot notation
version = config.get('bot.version')  # "4.5.0"
news_channel = config.get('channels.news')  # 123456789

# Provide a default value if key doesn't exist
debug = config.get('bot.verbose_logging', False)  # Falls back to False if not found
```

## Environment Variables

Store sensitive information in a `.env` file, then reference them in your YAML:

```yaml
# config.yaml
tokens:
  discord: ${DISCORD_TOKEN}
  telegram:
    api_id: ${TELEGRAM_API_ID}
    api_hash: ${TELEGRAM_API_HASH}
```

```
# .env
DISCORD_TOKEN=your_discord_token_here
TELEGRAM_API_ID=12345
TELEGRAM_API_HASH=abcdef123456
```

The system automatically substitutes environment variables and converts them to the appropriate type:
- Numbers become integers/floats
- "true"/"false" become booleans
- Other values remain strings

## Configuration Profiles

### Understanding Profiles

Profiles let you define different settings for different environments. The main config file contains the default settings, and profiles can override specific values:

```yaml
# Base configuration
logging:
  level: "INFO"
  file: "logs/NewsBot.log"

# Profile-specific overrides
profiles:
  dev:
    logging:
      level: "DEBUG"
  
  prod:
    logging:
      level: "WARNING"
```

### Setting the Active Profile

Set the active profile in three ways:

1. **Environment Variable**:
   ```
   # .env
   CONFIG_PROFILE=dev
   ```

2. **Runtime Method**:
   ```python
   from src.core.simple_config import config
   
   config.set_profile("dev")
   ```

3. **Discord Command**:
   ```
   /config_profile Development
   ```

## Discord Commands

NewsBot provides slash commands for managing configuration:

| Command | Description |
|---------|-------------|
| `/config_profile [profile]` | Set or show the current profile |
| `/config_get <key>` | Get a configuration value |
| `/config_set <key> <value>` | Set a temporary override |
| `/config_clear` | Clear all overrides |
| `/config_reload` | Reload configuration from file |
| `/config_save <filename> <format>` | Save current configuration |

## Advanced Features

### Auto-Reload

The configuration system automatically checks for changes to the config file every 5 seconds when accessing values.

### Temporary Overrides

Use runtime overrides for testing without changing the config file:

```python
from src.core.simple_config import config

# Override a value temporarily
config.set_override('bot.debug_mode', True)

# Clear all overrides
config.clear_overrides()
```

### Configuration Validation

The system validates that all required keys are present:

```python
from src.core.simple_config import config

if not config.validate():
    print("Missing required configuration!")
```

## Sample Configuration Files

### config.yaml (Main Config)

```yaml
bot:
  version: "4.5.0"
  application_id: ${APPLICATION_ID}
  guild_id: ${GUILD_ID}
  admin_role_id: ${ADMIN_ROLE_ID}
  admin_user_id: ${ADMIN_USER_ID}
  debug_mode: false

channels:
  news: ${NEWS_CHANNEL_ID}
  errors: ${ERRORS_CHANNEL_ID}
  logs: ${LOG_CHANNEL_ID}

tokens:
  discord: ${DISCORD_TOKEN}

telegram:
  api_id: ${TELEGRAM_API_ID}
  api_hash: ${TELEGRAM_API_HASH}
  token: ${TELEGRAM_TOKEN}

monitoring:
  metrics:
    port: 8000
    collection_interval: 300
```

### Sample .env File

```
# Discord Bot Configuration
DISCORD_TOKEN=your_token_here
APPLICATION_ID=1234567890

# Discord Server Configuration
GUILD_ID=9876543210

# Discord Channel IDs
NEWS_CHANNEL_ID=1111111111
ERRORS_CHANNEL_ID=2222222222
LOG_CHANNEL_ID=3333333333

# Admin Configuration
ADMIN_ROLE_ID=4444444444
ADMIN_USER_ID=5555555555

# Telegram Configuration
TELEGRAM_API_ID=12345
TELEGRAM_API_HASH=abcdef123456
TELEGRAM_TOKEN=your_telegram_token

# Environment
CONFIG_PROFILE=dev
```

## Best Practices

1. **Keep Secrets in .env**: Never commit API keys or tokens to git
2. **Use Profiles**: Create profiles for development, testing, and production
3. **Validate Configuration**: Always validate at startup
4. **Provide Defaults**: Use default values for non-critical settings
5. **Document Settings**: Comment your YAML files to explain what settings do
6. **Backup Configs**: Use `/config_save` to backup working configurations 