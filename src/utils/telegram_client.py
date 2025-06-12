"""
Telegram Client Module

This module handles the Telegram bot integration, including:
- Connection management
- Message handling
- Error handling
- Event forwarding to Discord
"""

import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

import discord
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, RPCError, SessionPasswordNeededError

from src.utils.base_logger import base_logger as logger
from src.utils.config import Config
from src.utils.content_cleaner import clean_news_content
from src.utils.error_handler import ErrorContext, error_handler
from src.utils.rate_limiter import rate_limited, rate_limiter_manager
from src.utils.structured_logger import structured_logger
from src.utils.syrian_locations import format_syrian_location_tags
from src.utils.syrian_time import format_syrian_time, now_syrian
from src.utils.translator import generate_arabic_title, translate_arabic_to_english


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

    def __init__(self, discord_bot: discord.Client):
        """
        Initialize the Telegram manager.

        Args:
            discord_bot (discord.Client): The Discord bot instance for forwarding messages
        """
        self.client: Optional[TelegramClient] = None
        self.discord_bot = discord_bot
        self.connected = False
        self.retrying = False
        self.message_cache: Dict[int, datetime] = {}
        self.max_cache_size = 1000

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

            # Connect to Telegram using user authentication (not bot)
            logger.info("Connecting to Telegram...")
            await self.client.start()  # This will prompt for phone/code if needed

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
                    "error": str(e),
                },
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
                logger.warning(
                    f"Telegram FloodWaitError: waiting for {wait_time} seconds"
                )
                await asyncio.sleep(wait_time)
                # Retry after waiting
                return await original_method(*args, **kwargs)
            except RPCError as e:
                # Handle RPC errors (often rate-limit related)
                logger.error(f"Telegram RPC error: {str(e)}")
                # Add exponential backoff
                await asyncio.sleep(2)
                return await original_method(*args, **kwargs)

        # Apply patches
        self.client.get_entity = lambda *args, **kwargs: rate_limited_method(
            original_get_entity, *args, **kwargs
        )
        self.client.get_messages = lambda *args, **kwargs: rate_limited_method(
            original_get_messages, *args, **kwargs
        )
        self.client.send_message = lambda *args, **kwargs: rate_limited_method(
            original_send_message, *args, **kwargs
        )
        self.client.download_media = lambda *args, **kwargs: rate_limited_method(
            original_download_media, *args, **kwargs
        )

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
                if (
                    not channel_username
                    or channel_username.lower() not in tracked_channels
                ):
                    return

                # Avoid duplicate messages
                if event.message.id in self.message_cache:
                    return

                # Add to cache and maintain cache size
                self.message_cache[event.message.id] = datetime.now()
                if len(self.message_cache) > self.max_cache_size:
                    oldest_id = min(self.message_cache, key=self.message_cache.get)
                    del self.message_cache[oldest_id]

                # Create Discord embed
                embed = await self._create_message_embed(event)

                # Send to Discord news channel
                news_channel = self.discord_bot.get_channel(Config.NEWS_CHANNEL_ID)
                if news_channel:
                    await news_channel.send(embed=embed)
                    logger.info(
                        f"Forwarded Telegram message {event.message.id} to Discord"
                    )
                else:
                    logger.error("Could not find Discord news channel")

            except Exception as e:
                structured_logger.error(
                    "Error handling Telegram message",
                    extra_data={
                        "message_id": event.message.id if event.message else None,
                        "channel_id": event.chat_id if event.chat else None,
                        "error": str(e),
                    },
                )
                await error_handler.send_error_embed(
                    "Telegram Message Error",
                    e,
                    context=f"Failed to process message ID: {event.message.id if event.message else 'Unknown'}",
                    bot=self.discord_bot,
                )

    async def _create_message_embed(self, event) -> discord.Embed:
        """
        Create a Discord embed from a Telegram message with enhanced processing.

        Args:
            event: The Telegram message event

        Returns:
            discord.Embed: Formatted Discord embed with cleaned content, ChatGPT translation, and location tags
        """
        # Get channel/chat information
        chat = await event.get_chat()

        # Get original message text
        original_text = event.message.message or ""

        # Clean the content (remove sources, emojis, links, hashtags)
        cleaned_text = clean_news_content(original_text)

        # Generate Arabic title using ChatGPT (3-6 words)
        arabic_title = generate_arabic_title(cleaned_text)

        # Translate the cleaned content to English using ChatGPT
        english_translation = translate_arabic_to_english(cleaned_text)

        # Detect Syrian locations in the cleaned text
        location_tags = format_syrian_location_tags(cleaned_text)

        # Convert message timestamp to Syrian time
        syrian_time = format_syrian_time(event.message.date, format_style="short")
        message_date = format_syrian_time(event.message.date, format_style="date_only")

        # Create title with calendar emoji, date, and ChatGPT-generated Arabic title
        title = (
            f"📅 {message_date} | {arabic_title}"
            if arabic_title
            else f"📅 {message_date} | أخبار سورية"
        )

        # Create description with Arabic text and English translation
        description_parts = []
        if cleaned_text:
            description_parts.append(f"**العربية:**\n{cleaned_text}")
        if english_translation and english_translation != cleaned_text:
            description_parts.append(f"**English:**\n{english_translation}")

        description = (
            "\n\n".join(description_parts)
            if description_parts
            else "*(Content removed during cleaning)*"
        )

        # Create embed with enhanced content
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue(),
            timestamp=event.message.date,
        )

        # Add Syrian location tags if detected
        if location_tags:
            embed.add_field(name="📍 Locations", value=location_tags, inline=False)

        # Add Syrian time
        embed.add_field(name="🕐 Syrian Time", value=syrian_time, inline=True)

        # Add media info if present (but don't include source links)
        if event.message.media:
            media_type = type(event.message.media).__name__
            if "Photo" in media_type:
                embed.add_field(name="📷 Media", value="Image attached", inline=True)
            elif "Video" in media_type or "Document" in media_type:
                embed.add_field(name="🎥 Media", value="Video attached", inline=True)
            else:
                embed.add_field(name="📎 Media", value="Media attached", inline=True)

        # Add footer with Syrian time and no source info
        embed.set_footer(
            text=f"Syrian News • {format_syrian_time(now_syrian(), format_style='time_only')}"
        )

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
        """Get list of tracked Telegram channels."""
        # This would typically come from config or database
        # For now, return empty list - implement based on your needs
        return []

    async def get_entity(self, entity):
        """
        Get a Telegram entity (channel, user, etc.) by username or ID.
        
        Args:
            entity: Channel username, ID, or entity object
            
        Returns:
            Telegram entity object
        """
        if not self.client or not self.connected:
            raise Exception("Telegram client not connected")
            
        try:
            return await self.client.get_entity(entity)
        except Exception as e:
            logger.error(f"Failed to get entity {entity}: {e}")
            raise

    async def get_messages(self, entity, limit=10, offset_date=None):
        """
        Get messages from a Telegram channel.
        
        Args:
            entity: Channel entity or username
            limit: Number of messages to fetch
            offset_date: Date to start fetching from
            
        Returns:
            List of messages
        """
        if not self.client or not self.connected:
            raise Exception("Telegram client not connected")
            
        try:
            return await self.client.get_messages(
                entity, limit=limit, offset_date=offset_date
            )
        except Exception as e:
            logger.error(f"Failed to get messages from {entity}: {e}")
            raise

    async def download_media(self, message, file=None, progress_callback=None):
        """
        Download media from a Telegram message.
        
        Args:
            message: Telegram message with media
            file: File path or file-like object to save to
            progress_callback: Optional callback for download progress
            
        Returns:
            Path to downloaded file or file-like object
        """
        if not self.client or not self.connected:
            raise Exception("Telegram client not connected")
            
        try:
            return await self.client.download_media(
                message, file=file, progress_callback=progress_callback
            )
        except Exception as e:
            logger.error(f"Failed to download media: {e}")
            raise
