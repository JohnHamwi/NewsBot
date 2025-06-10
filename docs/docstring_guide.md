# Docstring Guide

This guide provides standards and examples for adding comprehensive docstrings to the NewsBot codebase.

## Table of Contents
1. [General Standards](#general-standards)
2. [Module Docstrings](#module-docstrings)
3. [Class Docstrings](#class-docstrings)
4. [Method/Function Docstrings](#methodfunction-docstrings)
5. [Property Docstrings](#property-docstrings)
6. [Examples by Component Type](#examples-by-component-type)

---

## General Standards

All docstrings should follow these general standards:

1. Use triple double-quotes (`"""`) for all docstrings
2. Write in clear, concise language
3. Begin with a one-line summary
4. Include a more detailed description after the summary if needed
5. Use Google-style formatting for parameters, returns, raises, etc.
6. Include examples where appropriate
7. Document all parameters, return values, and exceptions

## Module Docstrings

Module docstrings should be placed at the top of the file and describe the module's purpose and contents.

```python
"""
Module Name

A brief description of what this module does and why it exists.

This module provides functionality for X, Y, and Z.
It is used by A and B to accomplish C.
"""

import ...
```

## Class Docstrings

Class docstrings should describe the class's purpose, behavior, and important attributes.

```python
class ClassName:
    """
    Brief description of the class.
    
    More detailed description of what this class does, its behavior,
    and any important information users of this class should know.
    
    Attributes:
        attribute_name (type): Description of the attribute.
        another_attribute (type): Description of another attribute.
    """
```

## Method/Function Docstrings

Method and function docstrings should describe what the function does, its parameters, return values, and exceptions.

```python
def function_name(param1, param2, optional_param=None):
    """
    Brief description of what the function does.
    
    More detailed description if needed. Explain the function's behavior,
    any algorithms it uses, and other relevant details.
    
    Args:
        param1 (type): Description of param1.
        param2 (type): Description of param2.
        optional_param (type, optional): Description of optional_param. Defaults to None.
    
    Returns:
        type: Description of the return value.
        
    Raises:
        ExceptionType: When and why this exception is raised.
    
    Example:
        >>> function_name("example", 123)
        "result"
    """
```

## Property Docstrings

Property docstrings should describe what the property represents and any side effects of accessing it.

```python
@property
def property_name(self):
    """
    Brief description of what this property represents.
    
    More detailed description if needed. Mention any calculations
    that happen when this property is accessed.
    
    Returns:
        type: Description of the return value.
    """
    return self._property_name
```

## Examples by Component Type

### Core Component Example

```python
"""
Configuration Manager

This module handles loading and managing configuration from YAML files and environment variables.
It provides type conversion, validation, and dot-notation access to configuration values.
"""

class ConfigManager:
    """
    Manages configuration loading and access for the NewsBot application.
    
    This class follows the singleton pattern to ensure only one configuration
    instance exists. It handles loading from YAML files, environment variable
    substitution, and validation of required configuration keys.
    
    Attributes:
        _instance (ConfigManager): The singleton instance.
        _config (Dict[str, Any]): The loaded configuration dictionary.
    """
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Retrieves a value from the configuration using dot notation to access
        nested dictionaries. Returns the default value if the key is not found.
        
        Args:
            key (str): The configuration key in dot notation (e.g., 'bot.version').
            default (Any, optional): Default value to return if key not found. Defaults to None.
            
        Returns:
            Any: The configuration value with its proper type, or the default value.
        
        Example:
            >>> config.get('bot.version')
            '1.0.0'
            >>> config.get('nonexistent.key', 'default')
            'default'
        """
```

### Command Cog Example

```python
"""
Fetch Cog

This module implements the FetchCog for fetching, processing, and posting news
from Telegram channels to Discord. It handles media download, content translation,
and post formatting.
"""

class FetchCog(commands.Cog):
    """
    Cog for fetching and posting Telegram news to Discord.
    
    This cog handles fetching posts from Telegram channels, downloading media,
    translating content, and posting to Discord channels. It includes commands
    for manual fetching and blacklist management.
    
    Attributes:
        bot (commands.Bot): The bot instance.
        logger (Logger): Logger for this cog.
        news_role_id (int): Role ID for news notifications.
    """
    
    @app_commands.command(name="fetch", description="Fetch latest posts from a Telegram channel")
    async def fetch(self, interaction: discord.Interaction, channel: str, number: Optional[int] = None) -> None:
        """
        Fetch and process posts from a specified Telegram channel.
        
        This command fetches the latest posts from a Telegram channel,
        downloads any media, translates the content, and sends it to
        the interaction channel.
        
        Args:
            interaction (discord.Interaction): The command interaction.
            channel (str): The Telegram channel username to fetch from.
            number (Optional[int], optional): Number of posts to fetch (1-10). Defaults to 1.
        
        Raises:
            Exception: Various exceptions during fetching or processing.
        """
```

### Background Task Example

```python
async def auto_post_task(self):
    """
    Background task for automatically posting news at scheduled intervals.
    
    This task runs continuously in the background, checking if it's time
    to post based on the configured interval. It uses a round-robin approach
    to select channels and attempts to find and post valid content.
    
    The task handles its own exceptions to ensure it continues running
    even if individual post attempts fail.
    
    State Variables:
        auto_post_interval (int): Seconds between posts (0 = disabled)
        last_post_time (datetime): When the last post was made
        force_auto_post (bool): Flag to trigger immediate posting
        next_post_time (datetime): When the next post is scheduled
    """
```

### Utility Function Example

```python
def remove_emojis(text: str) -> str:
    """
    Remove emoji characters from text.
    
    Uses regex pattern matching to identify and remove emoji characters
    from the input text.
    
    Args:
        text (str): The text to process.
        
    Returns:
        str: The text with emojis removed.
        
    Example:
        >>> remove_emojis("Hello 👋 World! 🌍")
        "Hello  World! "
    """
```

## Implementation Strategy

When adding docstrings to the codebase, follow this strategy:

1. **Start with Core Components** - Begin with the most critical components
2. **Be Consistent** - Use the same style throughout the codebase
3. **Update Gradually** - Add docstrings when modifying code
4. **Prioritize Public API** - Focus on public methods and classes first
5. **Include Examples** - Add examples for complex functionality
6. **Reference Types** - Use accurate type annotations

## Tools

Consider using these tools to help with docstring management:

- **Sphinx** - Documentation generator
- **pydocstyle** - Docstring style checker
- **VS Code docstring extensions** - For auto-generating docstring templates

## Best Practices

1. **Keep Docstrings Updated** - Update docstrings when changing code
2. **Avoid Redundancy** - Don't repeat what's obvious from the code
3. **Focus on Why, Not How** - Explain the purpose more than the implementation
4. **Document Edge Cases** - Note any special cases or limitations
5. **Use Examples for Clarity** - Show how to use complex functions 