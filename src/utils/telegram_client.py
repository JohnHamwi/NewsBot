# =============================================================================
# NewsBot Telegram Client Module
# =============================================================================
# This module handles the Telegram bot integration including connection management,
# message handling, error handling, and event forwarding to Discord with
# comprehensive rate limiting and retry logic.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import discord
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, RPCError, SessionPasswordNeededError

# =============================================================================
# Local Application Imports
# =============================================================================
from src.utils.base_logger import base_logger as logger
from src.core.unified_config import unified_config as config
from src.utils.content_cleaner import clean_news_content
from src.utils.error_handler import ErrorContext, error_handler
from src.utils.rate_limiter import rate_limited, rate_limiter_manager
from src.utils.structured_logger import structured_logger
from src.utils.syrian_locations import format_syrian_location_tags
from src.utils.syrian_time import format_syrian_time, now_syrian
from src.utils.translator import generate_arabic_title, translate_arabic_to_english


# =============================================================================
# Telegram Manager Main Class
# =============================================================================
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

    # =========================================================================
    # Connection Management Methods
    # =========================================================================
    @rate_limited("telegram")
    async def connect(self) -> None:
        """
        Connect to Telegram using credentials from config.
        """
        if self.client and self.client.is_connected():
            return

        try:
            # Get Telegram credentials from config manager
            api_id = config.get("telegram.api_id")
            api_hash = config.get("telegram.api_hash")
            
            if not api_id or not api_hash:
                raise Exception("Your API ID or Hash cannot be empty or None. Refer to telethon.rtfd.io for more information.")
            
            logger.debug(f"Using Telegram API ID: {api_id}")
            
            # Create the client with session file
            # Use data/sessions/newsbot.session (works both locally and on VPS)
            import os
            session_dir = "data/sessions"
            os.makedirs(session_dir, exist_ok=True)
            session_file = os.path.join(session_dir, "newsbot.session")
            
            self.client = TelegramClient(session_file, api_id, api_hash)
            
            logger.info("Connecting to Telegram...")
            
            # Connect and start (will use existing session or prompt for auth)
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                logger.error("❌ Telegram user not authorized. Session file missing or invalid.")
                logger.error("💡 You need to authenticate the Telegram client first.")
                logger.error("📱 Run 'python authenticate_telegram.py' to create a session file.")
                raise Exception("Telegram user not authorized - session required")
            
            # Set up event handlers and other initialization
            self._setup_event_handlers()
            self._patch_telegram_methods()
            self.connected = True
            
            logger.info("✅ Telegram client connected successfully")
            await self._send_connection_status()
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Telegram: {e}")
            self.client = None
            raise

    # =========================================================================
    # Rate Limiting and Method Patching
    # =========================================================================
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

    # =========================================================================
    # Event Handler Setup
    # =========================================================================
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
                news_channel_id = config.get("discord.channels.news") or config.get("channels.news")
                news_channel = self.discord_bot.get_channel(news_channel_id) if news_channel_id else None
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
        log_channel_id = config.get("discord.channels.logs") or config.get("channels.logs")
        log_channel = self.discord_bot.get_channel(log_channel_id) if log_channel_id else None
        if log_channel:
            await log_channel.send(embed=embed)

    async def disconnect(self) -> None:
        """Safely disconnect from Telegram."""
        if self.client:
            try:
                # Cancel any pending keepalive tasks to prevent database lock issues
                if hasattr(self.client, '_sender') and hasattr(self.client._sender, '_keepalive_handle'):
                    try:
                        self.client._sender._keepalive_handle.cancel()
                        # Wait a moment for the task to be cancelled
                        await asyncio.sleep(0.1)
                    except Exception:
                        pass
                
                # Try to disconnect gracefully with timeout
                await asyncio.wait_for(self.client.disconnect(), timeout=3.0)
                self.connected = False
                logger.info("Disconnected from Telegram")
            except asyncio.TimeoutError:
                logger.warning("Telegram disconnect timeout - forcing closure")
                self.connected = False
                # Force close the client without waiting for session save
                if hasattr(self.client, '_connection'):
                    try:
                        await self.client._connection.disconnect()
                    except Exception:
                        pass
            except Exception as e:
                error_msg = str(e)
                if "database is locked" in error_msg or "disk I/O error" in error_msg:
                    logger.debug(f"Telegram session save warning during disconnect: {error_msg}")
                    # Clear the session file to prevent future issues
                    try:
                        await self.clean_session_files()
                    except Exception:
                        pass
                    # Force close any remaining connections
                    try:
                        if hasattr(self.client, '_connection') and self.client._connection:
                            await asyncio.wait_for(self.client._connection.disconnect(), timeout=1.0)
                    except Exception:
                        pass
                elif "sqlite3.OperationalError" in error_msg:
                    logger.warning(f"SQLite error during Telegram disconnect: {error_msg}")
                    # Handle SQLite-specific issues
                    try:
                        await self.clean_session_files()
                    except Exception:
                        pass
                else:
                    logger.error(f"Error disconnecting from Telegram: {error_msg}")
                self.connected = False
            finally:
                # Ensure client reference is cleared
                try:
                    if self.client and hasattr(self.client, '_connection'):
                        self.client._connection = None
                except:
                    pass
                self.client = None

    def is_connected_sync(self) -> bool:
        """Check if connected to Telegram (synchronous version)."""
        return self.connected and self.client and self.client.is_connected()
    
    async def is_connected(self) -> bool:
        """Check if connected to Telegram (async version)."""
        return self.is_connected_sync()

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
            
    async def clean_session_files(self) -> None:
        """Clean up corrupted session files."""
        import os
        import glob
        
        try:
            # Remove all session files to force fresh authentication
            session_files = glob.glob("*.session*")
            for file in session_files:
                try:
                    os.remove(file)
                    logger.info(f"Removed corrupted session file: {file}")
                except Exception as e:
                    logger.warning(f"Could not remove session file {file}: {e}")
                    
            # Also clear any session data in data directory
            data_sessions = glob.glob("data/sessions/*.session*")
            for file in data_sessions:
                try:
                    os.remove(file)
                    logger.info(f"Removed corrupted session file: {file}")
                except Exception as e:
                    logger.warning(f"Could not remove session file {file}: {e}")
                    
        except Exception as e:
            logger.error(f"Error cleaning session files: {e}")

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
            error_msg = str(e)
            
            # Handle specific protocol errors more gracefully
            if "Could not find a matching Constructor ID" in error_msg:
                logger.warning(f"Telegram protocol error for {entity} - corrupted data stream, skipping")
                # Force session reconnection for next attempt
                if hasattr(self, '_protocol_errors'):
                    self._protocol_errors += 1
                else:
                    self._protocol_errors = 1
                    
                # If we get too many protocol errors, force reconnection
                if self._protocol_errors >= 3:
                    logger.warning("Multiple protocol errors detected - will reconnect on next attempt")
                    self.connected = False
                    self._protocol_errors = 0
                    
                return []  # Return empty list instead of crashing
                
            elif "Nobody is using this username" in error_msg:
                logger.warning(f"Channel {entity} not found or username invalid")
                return []  # Return empty list for invalid channels
                
            elif "FloodWaitError" in error_msg or "flood" in error_msg.lower():
                logger.warning(f"Rate limited on {entity} - will retry later")
                return []  # Return empty list when rate limited
                
            else:
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
