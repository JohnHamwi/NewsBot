"""
NewsBot Core Class

This module contains the main NewsBot class with initialization,
setup, and core Discord bot functionality.
"""

import asyncio
import glob
import os
from typing import Optional

import discord
from discord.ext import commands
from telethon import TelegramClient

from src.cache.redis_cache import JSONCache
from src.core.circuit_breaker import CircuitBreaker
from src.core.config_manager import config
from src.monitoring.metrics import MetricsManager
from src.security.rbac import RBACManager
from src.utils.base_logger import base_logger as logger
from src.utils.task_manager import task_manager, set_bot_instance

# Configuration constants
APPLICATION_ID = config.get('bot.application_id')
GUILD_ID = config.get('bot.guild_id')
NEWS_CHANNEL_ID = config.get('channels.news')
ERRORS_CHANNEL_ID = config.get('channels.errors')
LOG_CHANNEL_ID = config.get('channels.logs')


class NewsBot(commands.Bot):
    """
    Custom Discord bot class with additional features for news aggregation and posting.

    Handles initialization, background tasks, error handling, and integration with
    Discord and Telegram services.
    """

    def __init__(self):
        """Initialize the NewsBot with all required components."""
        # Initialize Discord bot with required intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        super().__init__(
            command_prefix=None,  # No prefix commands, slash only
            intents=intents,
            application_id=APPLICATION_ID
        )

        # Bot state
        self._hook_called = False
        self._ready_called = False  # Flag to prevent multiple on_ready calls

        # Initialize core components
        self.json_cache = JSONCache()
        self.metrics = MetricsManager()
        self.rbac = RBACManager()

        # Initialize services (will be set up properly in setup_hook)
        self.media_service = None
        self.ai_service = None
        self.posting_service = None

        # Telegram client (initialized later)
        self.telegram_client: Optional[TelegramClient] = None
        self.telegram_auth_failed = False

        # Channel references (set in on_ready)
        self.news_channel: Optional[discord.TextChannel] = None
        self.errors_channel: Optional[discord.TextChannel] = None
        self.log_channel: Optional[discord.TextChannel] = None

        # Auto-posting configuration
        self.auto_post_interval = 0  # seconds, 0 = disabled
        self.last_post_time = None
        self.next_post_time = None
        self.force_auto_post = False
        self._just_posted = False

        # Rich presence configuration
        self.rich_presence_mode = "automatic"  # or "maintenance"

        # Circuit breakers for external services
        self.telegram_circuit_breaker = CircuitBreaker("telegram", failure_threshold=3)
        self.openai_circuit_breaker = CircuitBreaker("openai", failure_threshold=5)

        # Startup time tracking
        self.startup_time = discord.utils.utcnow()

    @property
    def hook_called(self) -> bool:
        """Check if setup_hook was called."""
        return getattr(self, "_hook_called", False)

    @property
    def is_debug_mode(self) -> bool:
        """Get current debug mode status."""
        return self.debug_mode

    async def setup_hook(self) -> None:
        """
        Set up the bot's internal components, load cogs, and prepare for connection.
        Command syncing happens in on_ready() after Discord connection is established.
        """
        try:
            logger.debug("🔄 Setting up bot components")

            # Initialize services
            await self._initialize_services()

            # Initialize Telegram client
            await self._initialize_telegram_client()

            # Load all cogs dynamically
            await self._load_cogs()

            # Start background tasks
            await self._start_background_tasks()

            logger.info("✅ Bot setup completed successfully")

        except Exception as e:
            logger.error(f"❌ Failed to set up bot: {str(e)}", exc_info=True)
            raise

    async def _initialize_services(self) -> None:
        """Initialize bot services and components."""
        try:
            logger.debug("🔧 Initializing bot services")

            # Set hook called flag
            self._hook_called = True

            # Load RBAC permissions
            self.rbac.load_permissions()
            logger.debug("✅ RBAC permissions loaded")

            # Initialize services with bot instance
            from src.services.media_service import MediaService
            from src.services.ai_service import AIService
            from src.services.posting_service import PostingService

            self.media_service = MediaService(self)
            self.ai_service = AIService(self)
            self.posting_service = PostingService(self)
            logger.debug("✅ Services initialized")

        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {str(e)}")
            raise

    async def _initialize_telegram_client(self) -> None:
        """Initialize and configure the Telegram client."""
        try:
            # Get API credentials
            api_id = config.get('telegram.api_id') or os.getenv("TELEGRAM_API_ID")
            api_hash = config.get('telegram.api_hash') or os.getenv("TELEGRAM_API_HASH")

            logger.debug(f"📱 Telegram API credentials available: {bool(api_id and api_hash)}")

            if not api_id or not api_hash:
                raise ValueError("Telegram API credentials missing. Check environment variables or config.")

            # Initialize Telegram client
            self.telegram_client = TelegramClient("data/sessions/newsbot_session", api_id, api_hash)

            # Start client with timeout
            try:
                await asyncio.wait_for(self.telegram_client.start(), timeout=15.0)
                logger.debug("✅ Telegram client started successfully")
            except asyncio.TimeoutError:
                logger.error("❌ Telegram client connection timed out")
                logger.error("❌ Run 'python fix_telegram_auth.py' to authenticate")
                self.telegram_auth_failed = True
                return
            except Exception as e:
                error_str = str(e).lower()
                if "key is not registered" in error_str or "resolve" in error_str:
                    logger.error("❌ Telegram authentication error: Key not registered")
                    logger.error("❌ Run 'python fix_telegram_auth.py' to authenticate")
                    self.telegram_auth_failed = True
                    return
                else:
                    raise

            # Extend client with additional methods
            from src.core.telegram_utils import extend_telegram_client
            await extend_telegram_client(self.telegram_client)
            logger.debug("✅ Telegram client extended with additional methods")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Telegram client: {str(e)}")
            self.telegram_auth_failed = True

    async def _load_cogs(self) -> None:
        """Load all cogs dynamically from the cogs directory."""
        logger.info("📥 Loading cogs from src/cogs/")

        cogs_dir = os.path.join(os.path.dirname(__file__), "..", "cogs")
        loaded_cogs = []
        failed_cogs = []

        for cog_path in glob.glob(os.path.join(cogs_dir, "*.py")):
            cog_file = os.path.basename(cog_path)

            # Skip non-cog files
            if cog_file.startswith("_") or cog_file == "__init__.py":
                logger.info(f"📥 Skipping system file: {cog_file}")
                continue

            # Skip helper files and old system.py (now split into separate cogs)
            if cog_file in ["fetch_view.py", "ai_utils.py", "media_utils.py", "fetch.py", "system.py"]:
                logger.info(f"📥 Skipping helper file: {cog_file}")
                continue

            cog_name = f"src.cogs.{cog_file[:-3]}"
            logger.info(f"📥 Attempting to load cog: {cog_name}")

            try:
                await self.load_extension(cog_name)
                loaded_cogs.append(cog_name)
                logger.info(f"✅ Successfully loaded cog: {cog_name}")
            except Exception as e:
                failed_cogs.append((cog_name, str(e)))
                logger.error(f"❌ Failed to load cog {cog_name}: {str(e)}")

        # Ensure fetch cog is loaded
        if not any("fetch" in ext for ext in self.extensions):
            try:
                await self.load_extension("src.cogs.fetch_cog")
                loaded_cogs.append("src.cogs.fetch_cog")
                logger.info("📥 Explicitly loaded fetch cog")
            except Exception as e:
                failed_cogs.append(("src.cogs.fetch_cog", str(e)))
                logger.error(f"❌ Failed to load fetch cog: {str(e)}")

        logger.info(f"📥 Loaded {len(loaded_cogs)} cogs successfully")
        if failed_cogs:
            logger.warning(f"❌ Failed to load {len(failed_cogs)} cogs")
            for failed_cog, error_msg in failed_cogs:
                logger.warning(f"   - {failed_cog}: {error_msg}")

        # Log all loaded extensions for verification
        logger.info(f"📋 Currently loaded extensions: {list(self.extensions.keys())}")

    async def _sync_commands(self) -> None:
        """Sync slash commands with Discord."""
        try:
            logger.debug("🔄 Syncing slash commands")
            synced = await self.tree.sync()
            logger.info(f"✅ Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"❌ Failed to sync commands: {str(e)}", exc_info=True)

    async def _start_background_tasks(self) -> None:
        """Start all background tasks."""
        try:
            logger.debug("🔄 Starting background tasks")

            # Set bot instance for task manager
            set_bot_instance(self)

            # Start metrics collection
            if hasattr(self, 'metrics') and self.metrics:
                self.metrics.start_collection()
                logger.debug("📊 Started metrics collection")

            logger.debug("✅ Background tasks started")

        except Exception as e:
            logger.error(f"❌ Failed to start background tasks: {str(e)}", exc_info=True)

    async def on_ready(self) -> None:
        """Handle bot ready event and send startup notification."""
        # Prevent multiple on_ready calls from running the initialization
        if self._ready_called:
            logger.debug("🔄 on_ready called again, skipping initialization")
            return

        self._ready_called = True

        try:
            logger.info(f"🤖 {self.user} has connected to Discord!")
            logger.info(f"🏰 Connected to guild: {self.get_guild(GUILD_ID)}")

            # Sync slash commands now that we're connected
            await self._sync_commands()

            # Get channel references
            guild = self.get_guild(GUILD_ID)
            if not guild:
                raise ValueError(f"Could not find guild with ID {GUILD_ID}")

            self.news_channel = guild.get_channel(NEWS_CHANNEL_ID)
            self.errors_channel = guild.get_channel(ERRORS_CHANNEL_ID)
            self.log_channel = guild.get_channel(LOG_CHANNEL_ID)

            # Validate all channels are found
            missing_channels = []
            if not self.news_channel:
                missing_channels.append(f"News ({NEWS_CHANNEL_ID})")
            if not self.errors_channel:
                missing_channels.append(f"Errors ({ERRORS_CHANNEL_ID})")
            if not self.log_channel:
                missing_channels.append(f"Log ({LOG_CHANNEL_ID})")

            if missing_channels:
                raise ValueError(f"Could not find channels: {', '.join(missing_channels)}")

            logger.debug("✅ All required channels found")

            # Load auto-post configuration
            await self.load_auto_post_config()

            # Send startup notification
            from .background_tasks import send_startup_notification
            await send_startup_notification(self)

            # Start background tasks
            from .background_tasks import start_monitoring_tasks
            await start_monitoring_tasks(self)

            logger.info("✅ Bot is fully ready and operational")

        except Exception as e:
            logger.error(f"❌ Error in on_ready: {str(e)}", exc_info=True)
            raise

    async def close(self) -> None:
        """Clean shutdown of the bot and all its components."""
        try:
            logger.info("🔄 Starting bot shutdown...")

            # Send shutdown notification
            from .background_tasks import send_shutdown_notification
            await send_shutdown_notification(self)

            # Stop background tasks
            await task_manager.stop_all_tasks()
            logger.debug("✅ All background tasks stopped")

            # Close Telegram client
            if hasattr(self, 'telegram_client') and self.telegram_client:
                try:
                    await self.telegram_client.disconnect()
                    logger.debug("✅ Telegram client disconnected")
                except Exception as e:
                    logger.warning(f"⚠️ Error disconnecting Telegram client: {str(e)}")

            # Stop metrics collection
            if hasattr(self, 'metrics') and self.metrics:
                try:
                    self.metrics.stop_collection()
                    logger.debug("✅ Metrics collection stopped")
                except Exception as e:
                    logger.warning(f"⚠️ Error stopping metrics: {str(e)}")

            # Save cache
            if hasattr(self, 'json_cache') and self.json_cache:
                try:
                    await self.json_cache.save()
                    logger.debug("✅ Cache saved")
                except Exception as e:
                    logger.warning(f"⚠️ Error saving cache: {str(e)}")

            # Call parent close
            await super().close()
            logger.info("✅ Bot shutdown completed")

        except Exception as e:
            logger.error(f"❌ Error during bot shutdown: {str(e)}", exc_info=True)

    async def on_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """
        Global error handler for all slash commands. Logs, reports, and provides user feedback.
        """
        from src.utils.error_handler import error_handler
        # Log error with context
        user = getattr(interaction, 'user', None)
        channel = getattr(interaction, 'channel', None)
        command = getattr(interaction, 'command', None)
        context = (f"User: {user} ({getattr(user, 'id', None)}) | "
                   f"Channel: {channel} | Command: {getattr(command, 'name', None)}")
        await error_handler.send_error_embed(
            error_title="Slash Command Error",
            error=error,
            context=context,
            user=user,
            channel=channel,
            bot=self
        )
        # Provide clear, public feedback to the user
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ An error occurred: {error}", ephemeral=False)
            else:
                await interaction.followup.send(f"❌ An error occurred: {error}", ephemeral=False)
        except Exception:
            pass

    # Auto-posting configuration methods
    def set_auto_post_interval(self, hours: int):
        """Set the auto-post interval in hours."""
        self.auto_post_interval = hours * 3600  # Convert to seconds
        # Save to cache
        asyncio.create_task(self.save_auto_post_config())

    def get_auto_post_interval(self):
        """Get the current auto-post interval in hours."""
        return self.auto_post_interval // 3600

    def set_auto_post_channel(self, channel: str):
        """Set the auto-post channel (legacy, for single-channel mode)."""
        self.auto_post_channel = channel
        # Save to cache if needed
        asyncio.create_task(self.save_auto_post_config())

    async def load_auto_post_config(self):
        """Load auto-post configuration from cache."""
        try:
            logger.info("🔄 Loading auto-post configuration from cache")
            config_data = await self.json_cache.get('auto_post_config')
            if config_data:
                self.auto_post_interval = config_data.get('interval', 0)
                last_post_str = config_data.get('last_post_time')
                if last_post_str:
                    from datetime import datetime
                    self.last_post_time = datetime.fromisoformat(last_post_str)
                    logger.info(
                        f"✅ Auto-post configuration loaded: interval={self.auto_post_interval}s, "
                        f"last_post={self.last_post_time}"
                    )
                else:
                    logger.info(
                        f"✅ Auto-post configuration loaded: interval={self.auto_post_interval}s, no previous post time")

                # Log human-readable interval
                if self.auto_post_interval > 0:
                    hours = self.auto_post_interval // 3600
                    minutes = (self.auto_post_interval % 3600) // 60
                    if hours > 0:
                        logger.info(f"📅 Auto-posting enabled: every {hours}h {minutes}m")
                    else:
                        logger.info(f"📅 Auto-posting enabled: every {minutes}m")
                else:
                    logger.info("⏸️ Auto-posting is disabled")
            else:
                logger.info("ℹ️ No auto-post configuration found in cache - using defaults")
                self.auto_post_interval = 0
                self.last_post_time = None
        except Exception as e:
            logger.error(f"❌ Failed to load auto-post config: {str(e)}")

    async def save_auto_post_config(self):
        """Save auto-post configuration to cache."""
        try:
            config_data = {
                'interval': self.auto_post_interval,
                'last_post_time': self.last_post_time.isoformat() if self.last_post_time else None,
            }
            await self.json_cache.set('auto_post_config', config_data)
            logger.debug("✅ Auto-post configuration saved")
        except Exception as e:
            logger.error(f"❌ Failed to save auto-post config: {str(e)}")

    # Rich presence methods
    def set_rich_presence_mode(self, mode: str):
        """Set the rich presence mode."""
        self.rich_presence_mode = mode

    def set_next_post_time(self, dt):
        """Set the next post time for rich presence display."""
        self.next_post_time = dt

    def mark_just_posted(self):
        """Mark that a post just occurred."""
        self._just_posted = True
