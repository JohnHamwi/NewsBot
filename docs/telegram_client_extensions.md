# TelegramClient Extensions

This document describes the extensions added to the Telethon TelegramClient for use in the NewsBot.

## Overview

The standard Telethon TelegramClient is extended with additional methods to simplify common operations needed by the NewsBot. These extensions are implemented in `src/core/telegram_utils.py` and automatically applied to the client instance during bot initialization.

## Added Methods

### `get_posts(channel, limit=1)`

Retrieves recent posts from a Telegram channel.

#### Parameters:
- `channel` (str or int): The channel username or ID to fetch posts from
- `limit` (int, optional): Maximum number of posts to retrieve, defaults to 1

#### Returns:
- List of message objects from the channel

#### Implementation Details:
This method is a wrapper around Telethon's `iter_messages()` method. It collects all messages from the async iterator into a list for easier handling. This approach offers better compatibility with the bot's existing code.

The implementation uses `functools.partial` to properly bind the method to the client instance while avoiding parameter conflicts. This ensures that when you call `client.get_posts(channel, limit)`, the client instance is automatically passed as the first parameter to the underlying function.

#### Example Usage:
```python
# Get the latest post from a channel
posts = await client.get_posts('channel_name')
if posts:
    latest_post = posts[0]
    print(f"Latest post ID: {latest_post.id}")
    print(f"Message: {latest_post.message}")
    
# Get multiple posts
posts = await client.get_posts('channel_name', limit=5)
for post in posts:
    print(f"Post ID: {post.id}")
```

## How It Works

The extension mechanism uses Python's `functools.partial` to dynamically add methods to an existing TelegramClient instance. During bot initialization in `main.py`, the Telegram client is created and then extended with these additional methods:

```python
# In main.py setup_hook
self.telegram_client = TelegramClient("newsbot_session", api_id, api_hash)
await self.telegram_client.start()

# Extend the client with additional methods
from src.core.telegram_utils import extend_telegram_client
await extend_telegram_client(self.telegram_client)
```

Under the hood, this works by:
1. Defining a standalone async function that takes the client instance as its first parameter
2. Using `functools.partial` to create a new function with the client instance pre-filled
3. Assigning this partial function to the client instance as a method

This approach avoids common issues with parameter conflicts that can occur when dynamically adding methods to existing objects.

## Troubleshooting

If you encounter errors related to the `get_posts` method:

1. Make sure the Telegram client is properly initialized and connected
2. Verify that the extension function has been called on the client instance
3. Check that the channel name or ID is correct and accessible to the bot
4. Ensure the bot has sufficient permissions to access the channel

### Common Errors:

- **`got multiple values for argument 'limit'`**: This indicates a parameter conflict in the method binding. The fix is to use `functools.partial` as implemented in the current version.
- **`'TelegramClient' object has no attribute 'get_posts'`**: This means the extension function was not called on the client instance. Make sure `extend_telegram_client()` is called after initializing the client.

## Future Extensions

Additional methods may be added to the TelegramClient in the future to simplify other common operations. Follow these guidelines when adding new extensions:

1. Document the method clearly in the docstring and in this document
2. Use descriptive parameter and method names
3. Handle exceptions properly and provide meaningful error messages
4. Ensure compatibility with the existing bot architecture
5. Use `functools.partial` to bind methods to avoid parameter conflicts 