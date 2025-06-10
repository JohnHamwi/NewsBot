"""
Telegram Client Module

This module handles the Telegram bot integration, including:
- Connection management
- Message handling
- Error handling
- Event forwarding to Discord
"""

from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, FloodWaitError, RpcError
import asyncio
from typing import Optional, Dict, Any, List, Union, Callable
from datetime import datetime
import discord
from src.utils.base_logger import base_logger as logger
from src.utils.config import Config
from src.utils.error_handler import error_handler, ErrorContext
from src.utils.rate_limiter import rate_limiter_manager, rate_limited
from discord.ext import commands
from src.utils.structured_logger import structured_logger


class TelegramManager:
    """
    Manages Telegram client connection and message handling.

    Features:
    - Secure connection management
    - Message forwarding to Discord
    - Error handling and retry logic
    - Rate limit management
    - Event logging
    """

    def __init__(self, discord_bot: commands.Bot):
        """
        Initialize the Telegram manager.

        Args:
            discord_bot (commands.Bot): The Discord bot instance for forwarding messages
        """
        self.client: Optional[TelegramClient] = None
        self.discord_bot = discord_bot
        self.connected = False
        self.retrying = False
        self.message_cache: Dict[int, datetime] = {}
        self.max_cache_size = 1000

    @error_handler.with_error_handling(retries=3, retry_delay=5.0)
    @rate_limited("telegram")
    async def connect(self) -> None:
        """
        Connect to Telegram using credentials from config.
        """
        if self.client and self.client.is_connected():
            return

        try:
            # Create the client
            self.client = TelegramClient(
                "newsbot_session", Config.TELEGRAM_API_ID, Config.TELEGRAM_API_HASH
            )

            # Connect to Telegram
            logger.info("Connecting to Telegram...")
            await self.client.start(bot_token=Config.TELEGRAM_TOKEN)

            # Set up event handlers
            self._setup_event_handlers()

            # Add custom rate limiting for Telegram client
            self._patch_telegram_methods()

            self.connected = True
            logger.info("Successfully connected to Telegram")

            # Send connection status to Discord
            await self._send_connection_status()

        except Exception as e:
            self.connected = False
            structured_logger.error(
                "Failed to connect to Telegram",
                extra_data={
                    "api_id": Config.TELEGRAM_API_ID,
                    "connection_state": self.connected,
                    "error": str(e)
                }
            )
            raise

    def _patch_telegram_methods(self):
        """
        Patch Telegram client methods to add rate limiting.
        """
        if not self.client:
            return

        # Patch key methods with rate limiting
        original_get_entity = self.client.get_entity
        original_get_messages = self.client.get_messages
        original_send_message = self.client.send_message
        original_download_media = self.client.download_media

        async def rate_limited_method(original_method, *args, **kwargs):
            """Generic wrapper for rate-limited methods."""
            # Apply rate limiting
            await rate_limiter_manager.acquire("telegram")

            # Call original method with rate limiting and error handling
            try:
                return await original_method(*args, **kwargs)
            except FloodWaitError as e:
                # Handle Telegram's built-in rate limiting
                wait_time = e.seconds
                logger.warning(f"Telegram FloodWaitError: waiting for {wait_time} seconds")
                await asyncio.sleep(wait_time)
                # Retry after waiting
                return await original_method(*args, **kwargs)
            except RpcError as e:
                # Handle RPC errors (often rate-limit related)
                logger.error(f"Telegram RPC error: {str(e)}")
                # Add exponential backoff
                await asyncio.sleep(2)
                return await original_method(*args, **kwargs)

        # Apply patches
        self.client.get_entity = lambda *args, **kwargs: rate_limited_method(original_get_entity, *args, **kwargs)
        self.client.get_messages = lambda *args, **kwargs: rate_limited_method(original_get_messages, *args, **kwargs)
        self.client.send_message = lambda *args, **kwargs: rate_limited_method(original_send_message, *args, **kwargs)
        self.client.download_media = lambda *args, **kwargs: rate_limited_method(
            original_download_media, *args, **kwargs)

        logger.debug("Applied rate limiting to Telegram client methods")

    def _setup_event_handlers(self) -> None:
        """Set up Telegram event handlers."""

        @self.client.on(events.NewMessage)
        async def handle_new_message(event):
            """Handle new messages from Telegram."""
            try:
                # Check if message is from a channel
                if not event.is_channel:
                    return
                # Only process if channel is in the tracked list
                tracked_channels = await self.get_tracked_channels()
                chat = await event.get_chat()
                channel_username = getattr(chat, "username", None)
                if not channel_username or channel_username.lower() not in tracked_channels:
                    return

                # Avoid duplicate messages
                if event.message.id in self.message_cache:
                    return

                # Add to cache and maintain cache size
                self.message_cache[event.message.id] = datetime.now()
                if len(self.message_cache) > self.max_cache_size:
                    oldest_id = min(self.message_cache,
                                    key=self.message_cache.get)
                    del self.message_cache[oldest_id]

                # Create Discord embed
                embed = await self._create_message_embed(event)

                # Send to Discord news channel
                news_channel = self.discord_bot.get_channel(
                    Config.NEWS_CHANNEL_ID)
                if news_channel:
                    await news_channel.send(embed=embed)
                    logger.info(
                        f"Forwarded Telegram message {event.message.id} to Discord")
                else:
                    logger.error("Could not find Discord news channel")

            except Exception as e:
                structured_logger.error(
                    "Error handling Telegram message",
                    extra_data={
                        "message_id": event.message.id if event.message else None,
                        "channel_id": event.chat_id if event.chat else None,
                        "error": str(e)
                    }
                )
                await error_handler.send_error_embed(
                    "Telegram Message Error",
                    e,
                    context=f"Failed to process message ID: {event.message.id if event.message else 'Unknown'}",
                    bot=self.discord_bot,
                )

    async def _create_message_embed(self, event) -> discord.Embed:
        """
        Create a Discord embed from a Telegram message.

        Args:
            event: The Telegram message event

        Returns:
            discord.Embed: Formatted Discord embed
        """
        # Get channel/chat information
        chat = await event.get_chat()

        embed = discord.Embed(
            title=f"📰 {chat.title if hasattr(chat, 'title') else 'Telegram Update'}",
            description=event.message.message,
            color=discord.Color.blue(),
            timestamp=event.message.date,
        )

        # Add media if present
        if event.message.media:
            embed.add_field(
                name="Media", value=f"Type: {type(event.message.media).__name__}", inline=False
            )

        # Add message link if available
        if hasattr(chat, "username"):
            message_link = f"https://t.me/{chat.username}/{event.message.id}"
            embed.add_field(
                name="Source", value=f"[View on Telegram]({message_link})", inline=False
            )

        # Add footer with message ID
        embed.set_footer(text=f"Message ID: {event.message.id}")

        return embed

    async def _send_connection_status(self) -> None:
        """Send Telegram connection status to Discord."""
        if not self.discord_bot:
            return

        embed = discord.Embed(
            title="📱 Telegram Connection Status",
            description="Connection established successfully!",
            color=discord.Color.green(),
            timestamp=datetime.now(),
        )

        # Add client info
        me = await self.client.get_me()
        embed.add_field(
            name="Bot Info",
            value=f"Name: {me.first_name}\nUsername: @{me.username}\nID: {me.id}",
            inline=False,
        )

        # Send to log channel
        log_channel = self.discord_bot.get_channel(Config.LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(embed=embed)

    async def disconnect(self) -> None:
        """Safely disconnect from Telegram."""
        if self.client:
            try:
                await self.client.disconnect()
                self.connected = False
                logger.info("Disconnected from Telegram")
            except Exception as e:
                logger.error(f"Error disconnecting from Telegram: {str(e)}")

    async def is_connected(self) -> bool:
        """Check if connected to Telegram."""
        return self.connected and self.client and self.client.is_connected()

    async def reconnect(self) -> None:
        """Attempt to reconnect to Telegram."""
        if self.retrying:
            return

        self.retrying = True
        try:
            await self.disconnect()
            await asyncio.sleep(5)  # Wait before reconnecting
            await self.connect()
        finally:
            self.retrying = False

    async def get_tracked_channels(self) -> list:
        """Fetch the current list of tracked Telegram channels from JSONCache."""
        if hasattr(self.discord_bot, "json_cache"):
            return await self.discord_bot.json_cache.list_telegram_channels()
        return []
