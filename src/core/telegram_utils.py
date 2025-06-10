"""
Telegram Utilities

This module provides utility functions and extensions for Telegram client operations.
It extends the TelegramClient with additional functionality needed by the NewsBot.
"""

from telethon import TelegramClient
from typing import List, Union, Any
import asyncio
import logging
import functools

logger = logging.getLogger(__name__)


async def extend_telegram_client(client: TelegramClient):
    """
    Extend the TelegramClient with additional methods needed by the NewsBot.
    This function adds custom methods to the client instance.

    Args:
        client: The TelegramClient instance to extend
    """
    # Define the get_posts method
    async def get_posts(client_instance, channel: Union[str, int], limit: int = 1) -> List[Any]:
        """
        Get recent posts from a Telegram channel.

        Args:
            client_instance: The TelegramClient instance (added automatically)
            channel: The channel name or ID to get posts from
            limit: Maximum number of posts to fetch (default: 1)

        Returns:
            List of message objects from the channel
        """
        try:
            messages = []
            async for message in client_instance.iter_messages(channel, limit=limit):
                messages.append(message)
            return messages
        except Exception as e:
            logger.error(f"Error fetching posts from {channel}: {str(e)}")
            raise

    # Bind the method properly to the client instance
    # This uses partial to avoid parameter conflicts
    client.get_posts = functools.partial(get_posts, client)

    logger.info("TelegramClient extended with additional methods")
    return client
