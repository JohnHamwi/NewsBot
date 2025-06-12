"""
Syrian NewsBot - Modern Discord Bot for News Aggregation

A sophisticated Discord bot that aggregates news from Telegram channels,
translates Arabic content to English, and posts formatted news to Discord servers.

Features:
    - Real-time Telegram channel monitoring
    - AI-powered Arabic to English translation
    - Intelligent content filtering and cleaning
    - Syrian location detection and categorization
    - Automated posting with configurable intervals
    - Comprehensive admin controls and monitoring
    - Modern Discord.py 2.5+ slash commands
    - Advanced error handling and recovery

Author: حَـــــنَّـــــا
Version: 3.0.0
Python: 3.11+
Discord.py: 2.5+
"""

from __future__ import annotations

import asyncio
import datetime
import os
import sys
from pathlib import Path
from typing import Any, Optional

import discord
from discord.ext import tasks

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cache.json_cache import JSONCache
from components.decorators.performance_tracking import track_auto_post_performance
from core.config_manager import config
from monitoring.health_check import HealthCheckService
from monitoring.performance_metrics import PerformanceMetrics
from security.rbac import RBACManager
from utils.base_logger import base_logger as logger
from utils.error_handler import error_handler
from utils.structured_logger import structured_logger
from utils.task_manager import set_bot_instance, task_manager


class NewsBot(discord.Client):
    """
    Modern Syrian NewsBot implementation using Discord.py 2.5+.
    
    This bot serves as a bridge between Telegram news channels and Discord servers,
    providing real-time news aggregation with AI-powered translation and formatting.
    
    Attributes:
        tree: Discord application command tree for slash commands
        startup_time: Bot startup timestamp for uptime calculations
        auto_post_interval: Interval in minutes between automatic posts
        last_post_time: Timestamp of the last successful post
        force_auto_post: Flag to trigger immediate posting
        telegram_auth_failed: Track Telegram authentication status
        json_cache: JSON-based caching system for persistent data
        rbac: Role-based access control manager
        telegram_client: Telegram client for channel monitoring
        rich_presence_mode: Rich presence mode
        _just_posted: Flag for "just posted" status
        
    Example:
        ```python
        bot = NewsBot()
        await bot.start(token)
        ```
    """

    def __init__(self) -> None:
        """
        Initialize the NewsBot with modern Discord.py patterns.
        
        Sets up intents, command tree, caching, security, and background tasks.
        """
        # Configure Discord intents for modern bot functionality
        intents = discord.Intents.default()
        intents.message_content = True  # Required for message processing
        intents.guilds = True  # Required for guild management
        intents.members = True  # Required for member management
        
        super().__init__(intents=intents)
        
        # Initialize Discord application command tree
        self.tree = discord.app_commands.CommandTree(self)
        
        # Bot state tracking
        self.startup_time: Optional[datetime.datetime] = None
        self.auto_post_interval: int = 0  # Minutes between posts
        self.last_post_time: Optional[datetime.datetime] = None
        self.force_auto_post: bool = False
        self.telegram_auth_failed: bool = False  # Track Telegram authentication status
        self.rich_presence_mode: str = "automatic"  # Rich presence mode
        self._just_posted: bool = False  # Flag for "just posted" status
        
        # Core systems initialization
        self.json_cache: Optional[JSONCache] = None
        self.rbac: Optional[RBACManager] = None
        self.telegram_client: Optional[Any] = None
        
        # Monitoring systems
        self.health_check: Optional[HealthCheckService] = None
        self.performance_metrics: Optional[PerformanceMetrics] = None
        
        logger.info("🤖 NewsBot initialized with modern Discord.py 2.5+ architecture")

    async def setup_hook(self) -> None:
        """
        Async setup hook called when the bot is starting up.
        
        This method initializes all core systems, loads commands, and starts
        background tasks. It's called automatically by Discord.py.
        """
        try:
            logger.info("🚀 Starting NewsBot setup process...")
            
            # Record startup time for uptime tracking
            self.startup_time = datetime.datetime.now(datetime.timezone.utc)
            
            # Initialize core systems
            await self._initialize_core_systems()
            
            # Load all slash commands
            await self._load_commands()
            
            # Sync commands with Discord
            await self._sync_commands()
            
            # Start background tasks
            await self._start_background_tasks()
            
            logger.info("✅ NewsBot setup completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup NewsBot: {e}")
            structured_logger.error(
                "Bot setup failed",
                extra_data={"error": str(e), "startup_time": self.startup_time}
            )
            raise

    async def _initialize_core_systems(self) -> None:
        """
        Initialize core bot systems including caching, security, and monitoring.
        
        Raises:
            Exception: If any core system fails to initialize
        """
        try:
            # Initialize JSON cache for persistent data storage
            self.json_cache = JSONCache()
            await self.json_cache.initialize()
            logger.info("✅ JSON cache system initialized")
            
            # Initialize role-based access control
            self.rbac = RBACManager()
            await self.rbac.initialize()
            logger.info("✅ RBAC security system initialized")
            
            # Set bot instance for task manager
            set_bot_instance(self)
            logger.info("✅ Task manager configured")
            
            # Initialize monitoring systems
            await self._initialize_monitoring_systems()
            
            # Initialize Telegram client if configured
            await self._initialize_telegram_client()
            
        except Exception as e:
            logger.error(f"❌ Core system initialization failed: {e}")
            raise

    async def _initialize_monitoring_systems(self) -> None:
        """
        Initialize monitoring systems including health checks and performance metrics.
        
        These systems provide comprehensive monitoring capabilities for production use.
        """
        try:
            # Initialize performance metrics
            self.performance_metrics = PerformanceMetrics(self, retention_hours=24)
            await self.performance_metrics.start_monitoring()
            logger.info("✅ Performance metrics system initialized")
            
            # Initialize health check service
            health_check_port = config.get("monitoring.health_check_port", 8080)
            self.health_check = HealthCheckService(self, port=health_check_port)
            await self.health_check.start()
            logger.info(f"✅ Health check service started on port {health_check_port}")
            
        except Exception as e:
            logger.warning(f"⚠️ Monitoring systems initialization failed: {e}")
            # Continue without monitoring - not critical for basic operation

    async def _initialize_telegram_client(self) -> None:
        """
        Initialize Telegram client for news channel monitoring.
        
        This is optional and will gracefully handle missing credentials.
        """
        try:
            from src.utils.telegram_client import TelegramManager
            
            self.telegram_client = TelegramManager(self)
            await self.telegram_client.connect()
            self.telegram_auth_failed = False
            logger.info("✅ Telegram client connected successfully")
            
        except ImportError:
            logger.warning("⚠️ Telegram client not available (missing dependencies)")
            self.telegram_auth_failed = True
        except Exception as e:
            logger.warning(f"⚠️ Telegram client initialization failed: {e}")
            self.telegram_auth_failed = True
            # Continue without Telegram - bot can still function

    async def _load_commands(self) -> None:
        """
        Load all slash commands from command modules.
        
        Uses the modern Discord.py approach with direct command tree registration
        instead of the legacy cog system for better performance and maintainability.
        """
        try:
            logger.info("📥 Loading slash commands...")
            
            # Load fetch commands
            try:
                from cogs.fetch_cog import setup_fetch_commands
                setup_fetch_commands(self)
                logger.info("✅ Fetch commands loaded")
            except ImportError as e:
                logger.warning(f"Could not load fetch commands: {e}")
            
            # Load admin commands
            try:
                from cogs.admin import setup_admin_commands
                setup_admin_commands(self)
                logger.info("✅ Admin commands loaded")
            except ImportError as e:
                logger.warning(f"Could not load admin commands: {e}")
            
            # Load info commands
            try:
                from cogs.info import setup_info_commands
                setup_info_commands(self)
                logger.info("✅ Info commands loaded")
            except ImportError as e:
                logger.warning(f"Could not load info commands: {e}")
            
            # Load status commands
            try:
                from cogs.status import setup_status_commands
                setup_status_commands(self)
                logger.info("✅ Status commands loaded")
            except ImportError as e:
                logger.warning(f"Could not load status commands: {e}")
                
            logger.info("✅ All commands loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Error loading commands: {e}")
            raise

    async def _sync_commands(self) -> None:
        """
        Sync slash commands with Discord.
        
        This uploads all registered commands to Discord's servers,
        making them available to users.
        """
        try:
            logger.info("🔄 Starting command sync with Discord...")
            
            # Check if we have any commands to sync
            commands = self.tree.get_commands()
            logger.info(f"📋 Found {len(commands)} commands to sync")
            
            # Log command names for debugging
            command_names = [cmd.name for cmd in commands]
            logger.info(f"📝 Commands to sync: {', '.join(command_names)}")
            
            # Perform the sync with timeout
            import asyncio
            try:
                synced = await asyncio.wait_for(self.tree.sync(), timeout=30.0)
                logger.info(f"✅ Synced {len(synced)} slash commands")
            except asyncio.TimeoutError:
                logger.error("❌ Command sync timed out after 30 seconds")
                raise Exception("Command sync timeout")
            
        except Exception as e:
            logger.error(f"❌ Failed to sync commands: {e}")
            # Don't raise the exception - continue without syncing
            logger.warning("⚠️ Continuing without command sync - commands may not be available")

    async def _start_background_tasks(self) -> None:
        """
        Start all background tasks for automated functionality.
        
        Background tasks handle auto-posting, monitoring, logging, and maintenance.
        """
        try:
            # Load auto-post configuration
            await self._load_auto_post_config()
            
            # Start monitoring tasks (auto-post, rich presence, etc.)
            from src.bot.background_tasks import start_monitoring_tasks
            await start_monitoring_tasks(self)
            
            # Start task manager (for any additional tasks)
            await task_manager.start_all_tasks()
            logger.info("✅ Background tasks started")
            
        except Exception as e:
            logger.error(f"❌ Failed to start background tasks: {e}")
            raise

    async def _load_auto_post_config(self) -> None:
        """
        Load auto-posting configuration from cache.
        
        Restores the posting interval and last post time from persistent storage.
        """
        try:
            logger.info("🔄 Loading auto-post configuration from cache")
            
            if self.json_cache:
                # Load interval (default to 60 minutes = 3600 seconds)
                cached_interval = await self.json_cache.get("auto_post_interval", 60)
                
                # Check if the cached value is in minutes (legacy) or seconds (new)
                # If it's a small number (< 1440 = 24 hours), assume it's in minutes
                if cached_interval > 0 and cached_interval <= 1440:
                    # Likely in minutes, convert to seconds
                    self.auto_post_interval = cached_interval * 60
                    logger.info(f"🔄 Converted legacy interval from {cached_interval} minutes to {self.auto_post_interval} seconds")
                else:
                    # Already in seconds or disabled (0)
                    self.auto_post_interval = cached_interval
                
                # Load last post time
                last_post_str = await self.json_cache.get("last_post_time")
                if last_post_str:
                    self.last_post_time = datetime.datetime.fromisoformat(last_post_str)
                
                # Calculate display values
                if self.auto_post_interval > 0:
                    total_minutes = self.auto_post_interval // 60
                    hours = total_minutes // 60
                    minutes = total_minutes % 60
                    time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                    logger.info(f"📅 Auto-posting enabled: every {time_str} ({self.auto_post_interval} seconds)")
                else:
                    logger.info("📅 Auto-posting disabled")
                
                logger.info(
                    f"✅ Auto-post configuration loaded: "
                    f"interval={self.auto_post_interval}s, "
                    f"last_post={self.last_post_time}"
                )
                    
        except Exception as e:
            logger.error(f"❌ Failed to load auto-post config: {e}")
            # Continue with defaults

    async def on_ready(self) -> None:
        """
        Event handler called when the bot is fully ready and connected.
        
        This is called after successful login and initial setup completion.
        """
        try:
            logger.info(f"🤖 {self.user} has connected to Discord!")
            
            # Set up log channel
            from src.utils.config import Config
            if Config.LOG_CHANNEL_ID:
                self.log_channel = self.get_channel(Config.LOG_CHANNEL_ID)
                if not self.log_channel:
                    logger.warning(f"⚠️ Could not find log channel with ID {Config.LOG_CHANNEL_ID}")
            else:
                logger.warning("⚠️ LOG_CHANNEL_ID not configured - startup notifications disabled")
                self.log_channel = None
            
            # Set up errors channel
            if Config.ERRORS_CHANNEL_ID:
                self.errors_channel = self.get_channel(Config.ERRORS_CHANNEL_ID)
                if not self.errors_channel:
                    logger.warning(f"⚠️ Could not find errors channel with ID {Config.ERRORS_CHANNEL_ID}")
            else:
                logger.warning("⚠️ ERRORS_CHANNEL_ID not configured - error alerts disabled")
                self.errors_channel = None
            
            # Log guild information
            for guild in self.guilds:
                logger.info(f"🏰 Connected to guild: {guild.name}")
            
            # Send startup notification if log channel is available
            if self.log_channel:
                try:
                    from src.bot.background_tasks import send_startup_notification
                    await send_startup_notification(self)
                except Exception as e:
                    logger.error(f"❌ Failed to send startup notification: {e}")
            
            logger.info("✅ Bot is fully ready and operational")
            
        except Exception as e:
            logger.error(f"❌ Error in on_ready: {e}")

    async def on_application_command_error(
        self, 
        interaction: discord.Interaction, 
        error: discord.app_commands.AppCommandError
    ) -> None:
        """
        Global error handler for application commands.
        
        Args:
            interaction: The Discord interaction that caused the error
            error: The error that occurred
        """
        try:
            command_name = interaction.command.name if interaction.command else "Unknown"
            
            # Record error in performance metrics
            if self.performance_metrics:
                self.performance_metrics.record_error(
                    error_type=type(error).__name__,
                    error_message=str(error),
                    context=f"Command: {command_name}, User: {interaction.user.id}"
                )
            
            # Log the error with context
            structured_logger.error(
                "Application command error",
                extra_data={
                    "command": command_name,
                    "user_id": interaction.user.id,
                    "guild_id": interaction.guild_id,
                    "error": str(error),
                    "error_type": type(error).__name__
                }
            )
            
            # Send user-friendly error message
            error_message = "An unexpected error occurred. Please try again later."
            
            if isinstance(error, discord.app_commands.CommandOnCooldown):
                error_message = f"Command is on cooldown. Try again in {error.retry_after:.1f} seconds."
            elif isinstance(error, discord.app_commands.MissingPermissions):
                error_message = "You don't have permission to use this command."
            elif isinstance(error, discord.app_commands.BotMissingPermissions):
                error_message = "I don't have the required permissions to execute this command."
            
            # Send error response
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(error_message, ephemeral=True)
                else:
                    await interaction.response.send_message(error_message, ephemeral=True)
            except discord.NotFound:
                # Interaction expired, log but don't crash
                logger.warning("Could not send error response - interaction expired")
                
        except Exception as e:
            logger.error(f"❌ Error in error handler: {e}")

    def set_auto_post_interval(self, minutes: int) -> None:
        """
        Set the auto-posting interval.
        
        Args:
            minutes: Interval in minutes between automatic posts (0 to disable)
        """
        # Convert minutes to seconds for internal storage
        self.auto_post_interval = minutes * 60 if minutes > 0 else 0
        logger.info(f"⏰ Auto-post interval set to {minutes} minutes ({self.auto_post_interval} seconds)")

    def mark_just_posted(self) -> None:
        """
        Mark that news was just posted for rich presence display.
        """
        self._just_posted = True
        logger.debug("📱 Marked as just posted for rich presence")

    async def save_auto_post_config(self) -> None:
        """
        Save auto-posting configuration to persistent storage.
        """
        try:
            if self.json_cache:
                await self.json_cache.set("auto_post_interval", self.auto_post_interval)
                
                if self.last_post_time:
                    await self.json_cache.set(
                        "last_post_time", 
                        self.last_post_time.isoformat()
                    )
                
                await self.json_cache.save()
                logger.debug("💾 Auto-post configuration saved")
                
        except Exception as e:
            logger.error(f"❌ Failed to save auto-post config: {e}")

    @track_auto_post_performance
    async def fetch_and_post_auto(self, channel_name: str = None) -> bool:
        """
        Fetch and post news automatically.
        
        This method is called by the background task system for automated posting.
        
        Args:
            channel_name: Name of the Telegram channel to fetch from
        
        Returns:
            bool: True if posting was successful, False otherwise
        """
        try:
            # Import here to avoid circular imports
            from cogs.fetch_cog import FetchCog
            
            # Create a temporary fetch cog instance
            fetch_cog = FetchCog(self)
            
            # If no channel specified, get the first active channel
            if not channel_name:
                active_channels = await self.json_cache.list_telegram_channels("activated")
                if not active_channels:
                    logger.warning("⚠️ No active channels configured for auto-posting")
                    return False
                channel_name = active_channels[0]
                logger.info(f"📡 Using first active channel: {channel_name}")
            
            # Attempt to fetch and post
            success = await fetch_cog.fetch_and_post_auto(channel_name)
            
            if success:
                self.last_post_time = datetime.datetime.now(datetime.timezone.utc)
                await self.save_auto_post_config()
                logger.info(f"✅ Auto-post completed successfully from {channel_name}")
            else:
                logger.warning(f"⚠️ Auto-post completed but no new content was posted from {channel_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Auto-post failed: {e}")
            await error_handler.send_error_embed(
                "Auto-Post Error",
                e,
                context=f"Automatic news posting failed for channel: {channel_name}",
                bot=self
            )
            return False

    async def close(self) -> None:
        """
        Clean shutdown of the bot and all its systems.
        
        This method ensures all background tasks are stopped and resources
        are properly cleaned up before the bot shuts down.
        """
        try:
            logger.info("🔄 Starting bot shutdown...")
            
            # Stop background tasks
            await task_manager.stop_all_tasks()
            
            # Stop monitoring systems
            if self.performance_metrics:
                await self.performance_metrics.stop_monitoring()
                logger.info("📊 Performance metrics stopped")
            
            if self.health_check:
                await self.health_check.stop()
                logger.info("🏥 Health check service stopped")
            
            # Disconnect Telegram client
            if self.telegram_client:
                await self.telegram_client.disconnect()
                logger.info("📱 Telegram client disconnected")
            
            # Save final cache state
            if self.json_cache:
                await self.json_cache.save()
                logger.info("💾 Final cache save completed")
            
            # Call parent close method
            await super().close()
            
            logger.info("✅ Bot shutdown completed")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")
            # Continue with shutdown even if there are errors
