# =============================================================================
# NewsBot Core Module - Streamlined for Full Automation
# =============================================================================
# A sophisticated Discord bot that aggregates news from Telegram channels,
# translates Arabic content to English, and posts formatted news to Discord servers.
#
# Features:
# - Real-time Telegram channel monitoring with intelligent analysis
# - AI-powered Arabic to English translation and content processing
# - Intelligent content filtering, cleaning, and quality assessment
# - Syrian location detection and categorization
# - Automated posting with configurable intervals and smart timing
# - Essential admin controls for monitoring and emergency management
# - Modern Discord.py 2.5+ slash commands and interactions
# - Advanced error handling, recovery, and performance metrics
#
# Streamlined Version: Focused on 100% automation with minimal manual commands
# Last updated: 2025-01-16

# =============================================================================
# Future Imports
# =============================================================================
from __future__ import annotations

# =============================================================================
# Standard Library Imports
# =============================================================================
import asyncio
import datetime
import os
import sys
from pathlib import Path
from typing import Any, Optional
import traceback
import time

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import discord
from discord.ext import commands, tasks

# =============================================================================
# Path Configuration
# =============================================================================
# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# =============================================================================
# Local Application Imports
# =============================================================================
from src.cache.json_cache import JSONCache
from src.components.decorators.performance_tracking import track_auto_post_performance
from src.core.unified_config import unified_config as config
from src.monitoring.health_check import HealthCheckService
from src.monitoring.performance_metrics import PerformanceMetrics
from src.security.rbac import RBACManager
from src.utils.base_logger import base_logger as logger
from src.utils.error_handler import error_handler
from src.utils.logger import get_logger
from src.utils.structured_logger import structured_logger, StructuredLogger
from src.utils.task_manager import set_bot_instance, task_manager
from src.utils.timezone_utils import now_eastern


# =============================================================================
# NewsBot Main Class - Streamlined for Automation
# =============================================================================
class NewsBot(discord.Client):
    """
    Modern Syrian NewsBot implementation using Discord.py 2.5+ - Streamlined Version.

    This bot serves as a bridge between Telegram news channels and Discord servers,
    providing real-time news aggregation with AI-powered translation and formatting.
    
    Streamlined for 100% automated operation with minimal manual intervention.

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

        # Post tracking and statistics
        posts_today: int - Number of posts made today
        total_posts: int - Total posts made by the bot
        last_error: Optional[str] - Last error message recorded
        error_count: int - Total number of errors encountered
        last_error_time: Optional[datetime.datetime] - Timestamp of last error

    Example:
        ```python
        bot = NewsBot()
        await bot.start(token)
        ```
    """

    def __init__(self) -> None:
        """
        Initialize the NewsBot with modern Discord.py patterns.
        
        Sets up intents, command tree, caching, security, and background tasks
        for streamlined automated operation.
        """
        # Configure Discord intents for modern bot functionality
        intents = discord.Intents.default()
        intents.message_content = True  # Required for message processing
        intents.guilds = True           # Required for guild management
        intents.members = True          # Required for member management

        super().__init__(intents=intents)

        # Initialize Discord application command tree
        self.tree = discord.app_commands.CommandTree(self)

        # Bot state tracking
        self.startup_time: Optional[datetime.datetime] = None
        self.last_post_time: Optional[datetime.datetime] = None
        self.force_auto_post: bool = False
        
        # Initialize auto_post_interval from simple config manager (in seconds)
        try:
            from src.utils.config_manager import get_posting_interval
            self.auto_post_interval: int = get_posting_interval() * 60  # Convert minutes to seconds
        except Exception:
            self.auto_post_interval: int = 3600  # 1 hour default in seconds
        self.telegram_auth_failed: bool = False  # Track Telegram authentication status
        self.rich_presence_mode: str = "automatic"  # Rich presence mode
        self._just_posted: bool = False  # Flag for "just posted" status

        # Post tracking and statistics
        self.posts_today: int = 0
        self.total_posts: int = 0
        self.last_error: Optional[str] = None
        self.error_count: int = 0
        self.last_error_time: Optional[datetime.datetime] = None

        # Startup protection - prevents auto-posting for first 2 minutes after launch
        self.startup_grace_period_minutes: int = 2
        self.disable_auto_post_on_startup: bool = True

        # Core systems initialization
        self.json_cache: Optional[JSONCache] = None
        self.rbac: Optional[RBACManager] = None
        self.telegram_client: Optional[Any] = None

        # Streamlined command cogs/handlers
        self.streamlined_admin: Optional[Any] = None
        self.streamlined_fetch: Optional[Any] = None

        # Monitoring systems
        self.health_check: Optional[HealthCheckService] = None
        self.performance_metrics: Optional[PerformanceMetrics] = None

        # Initialize logger with debug mode if enabled
        debug_mode = config.get("bot", {}).get("debug_mode", False)
        self.logger = get_logger("NewsBot", enable_debug_mode=debug_mode)
        
        if debug_mode:
            self.logger.info("🐛 DEBUG MODE ENABLED - Enhanced logging active for testing phase")
            # Set logger to debug level
            import logging
            self.logger.logger.setLevel(logging.DEBUG)
            for handler in self.logger.logger.handlers:
                handler.setLevel(logging.DEBUG)

        logger.info("🤖 NewsBot initialized with modern Discord.py 2.5+ architecture")

    # =========================================================================
    # Setup and Initialization Methods
    # =========================================================================
    async def setup_hook(self) -> None:
        """
        Setup hook called when the bot is starting up.
        Loads streamlined cogs and initializes components for automation.
        """
        try:
            logger.info("🔧 Setting up streamlined bot components...")

            # Load only essential streamlined cogs for automation
            await self._load_streamlined_commands()

            # Record startup time for uptime tracking
            self.startup_time = datetime.datetime.now(datetime.timezone.utc)
            logger.info(f"🛡️ Auto-posting disabled for {self.startup_grace_period_minutes} minutes after startup")

            # Initialize core systems for automation
            await self._initialize_core_systems()

        except Exception as e:
            logger.error(f"❌ Setup hook failed: {e}")
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

            # Initialize VPS optimizations for better performance
            await self._initialize_vps_optimizations()

            # Initialize Telegram client if configured
            await self._initialize_telegram_client()
            
            # Initialize backup scheduler
            await self._initialize_backup_scheduler()
            
            # Load persistent statistics
            await self.load_statistics_from_cache()

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

    async def _initialize_backup_scheduler(self) -> None:
        """
        Initialize automated backup scheduler for data protection.
        
        This system provides automated backups of bot data, configuration,
        and logs on a configurable schedule with retention policies.
        """
        try:
            from src.monitoring.backup_scheduler import integrate_backup_scheduler
            
            self.backup_scheduler = await integrate_backup_scheduler(self)
            logger.info("✅ Automated backup scheduler initialized")
            
            # Log backup configuration
            if hasattr(self.backup_scheduler, 'config'):
                config = self.backup_scheduler.config
                logger.info(f"🗄️ Backup schedule: every {config.backup_interval_hours}h, retention: {config.retention_days} days")
            
        except ImportError:
            logger.warning("⚠️ Backup scheduler not available (missing dependencies)")
            self.backup_scheduler = None
        except Exception as e:
            logger.warning(f"⚠️ Backup scheduler initialization failed: {e}")
            self.backup_scheduler = None
            # Continue without backup scheduler - not critical for basic operation

    async def _load_streamlined_commands(self) -> None:
        """
        Load essential commands for automated operation.

        Streamlined command structure:
        - /admin - Essential admin controls (status, emergency, maintenance, info)
        - Background automation runs independently (no manual commands needed)
        """
        try:
            logger.info("📥 Loading streamlined command structure for automated operation...")

            # Load streamlined admin commands only
            try:
                from src.cogs.streamlined_admin import StreamlinedAdminCommands
                admin_cog = StreamlinedAdminCommands(self)
                self.tree.add_command(admin_cog.admin_group)
                logger.info("✅ Streamlined admin commands loaded")
            except Exception as e:
                logger.warning(f"Could not load streamlined admin commands: {e}")

            # Load streamlined fetch commands (essential for automation - background only)
            try:
                from src.cogs.streamlined_fetch import setup_fetch_commands
                setup_fetch_commands(self)
                logger.info("✅ Streamlined fetch command setup completed (automation support)")
            except Exception as e:
                logger.warning(f"Could not load streamlined fetch commands: {e}")

            # Load notification system (background monitoring only)
            try:
                from src.cogs.notification_system import NotificationSystem
                notification_cog = NotificationSystem(self)
                await self.add_cog(notification_cog)
                # Store reference for background notifications
                self.notification_system = notification_cog
                logger.info("✅ Notification system loaded (background monitoring)")
            except Exception as e:
                logger.warning(f"Could not load notification system: {e}")
                self.notification_system = None

            logger.info("✅ Streamlined command structure loaded successfully")
            logger.info("🎯 Available: /admin (status, emergency, maintenance, info) + background automation")

        except Exception as e:
            logger.error(f"❌ Error loading commands: {e}")
            raise

    async def on_ready(self) -> None:
        """Handle bot startup and initialization."""
        try:
            self.logger.info("=" * 50)
            self.logger.info("🤖 NEWSBOT STARTUP SEQUENCE")
            self.logger.info("=" * 50)
            
            # Initialize enhanced systems
            await self._initialize_enhanced_systems()
            
            # Validate configuration
            self._validate_startup_configuration()
            
            # Log bot information
            self.logger.info(f"Bot User: {self.user.name}#{self.user.discriminator}")
            self.logger.info(f"Bot ID: {self.user.id}")
            
            # Check guild access
            guild_id = config.get("discord.guild_id")
            guild = self.get_guild(guild_id)
            if guild:
                self.logger.info(f"Connected to Guild: {guild.name} ({guild.id})")
                self.logger.info(f"Guild Members: {guild.member_count}")
            else:
                self.logger.error(f"Cannot access guild with ID: {guild_id}")
            
            # Load and display automation config
            if self.json_cache:
                try:
                    # Use simple configuration manager
                    from src.utils.config_manager import get_posting_interval, get_active_channels
                    
                    active_channels = get_active_channels()
                    auto_post_interval = get_posting_interval()
                    
                    self.logger.info(f"Active channels for rotation: {len(active_channels)}")
                    for channel in active_channels:
                        self.logger.info(f"  • {channel}")
                    self.logger.info(f"Auto-post interval: {auto_post_interval} minutes")
                except Exception as e:
                    self.logger.warning(f"Failed to load automation config from cache: {e}")
            else:
                self.logger.warning("JSON cache not available")
            
            # Check feature status
            self._log_feature_status()
            
            # Run initial health check
            await self._run_initial_health_check()
            
            # Initialize channel references after bot is fully ready
            await self._initialize_channel_references()
            
            # Send startup notification
            await self._send_startup_notification()
            
            # Load auto-posting configuration from cache (CRITICAL for rich presence countdown)
            await self.load_auto_post_config()
            
            # Initialize rich presence
            await self._initialize_rich_presence()
            
            # Start background tasks (CRITICAL: This was missing!)
            await self._start_background_tasks()
            
            self.logger.info("=" * 50)
            self.logger.info("✅ NEWSBOT STARTUP COMPLETE")
            self.logger.info("=" * 50)
            
        except Exception as e:
            self.logger.error(f"❌ Startup failed: {e}")
            import traceback
            traceback.print_exc()

    async def _initialize_enhanced_systems(self):
        """Initialize enhanced debugging and monitoring systems."""
        from src.utils.debug_logger import debug_logger
        from src.monitoring.health_monitor import initialize_health_monitor
        from src.core.feature_manager import feature_manager
        
        # Initialize debug logger
        debug_logger.info("Initializing enhanced debugging system")
        
        # Initialize health monitor
        health_monitor = initialize_health_monitor(self)
        debug_logger.info("Initialized health monitoring system")
        
        # Log feature manager status
        enabled_features = feature_manager.get_enabled_features()
        disabled_features = feature_manager.get_disabled_features()
        debug_logger.info(f"Feature manager loaded: {len(enabled_features)} enabled, {len(disabled_features)} disabled")
        
    def _validate_startup_configuration(self):
        """Validate configuration during startup."""
        from src.core.config_validator import config_validator
        from src.utils.debug_logger import debug_logger
        
        debug_logger.info("Running startup configuration validation")
        
        is_valid = config_validator.validate_all(config.config_data)
        if not is_valid:
            self.logger.warning("⚠️ Configuration validation found issues:")
            for error in config_validator.errors:
                self.logger.warning(f"  • {error}")
            for warning in config_validator.warnings:
                self.logger.warning(f"  • {warning}")
        else:
            self.logger.info("✅ Configuration validation passed")
    
    def _log_feature_status(self):
        """Log the status of key features."""
        from src.core.feature_manager import feature_manager
        
        self.logger.info("🎛️ Feature Status:")
        
        # Key features to check
        key_features = [
            "auto_posting", "ai_translation", "ai_categorization", 
            "location_detection", "news_role_pinging", "forum_tags"
        ]
        
        for feature_name in key_features:
            status = "✅" if feature_manager.is_enabled(feature_name) else "❌"
            self.logger.info(f"  {status} {feature_name}")
        
        # Check dependencies
        issues = feature_manager.validate_feature_dependencies()
        if issues:
            self.logger.warning("⚠️ Feature dependency issues found:")
            for issue in issues:
                self.logger.warning(f"  • {issue}")
    
    async def _run_initial_health_check(self):
        """Run an initial health check during startup."""
        from src.monitoring.health_monitor import health_monitor
        from src.utils.debug_logger import debug_logger
        
        if health_monitor:
            try:
                self.logger.info("🏥 Running initial health check...")
                health = await health_monitor.run_full_health_check()
                
                healthy_count = len([c for c in health.checks if c.status.value == "healthy"])
                total_checks = len(health.checks)
                
                self.logger.info(f"Health check complete: {healthy_count}/{total_checks} systems healthy")
                
                # Log any critical issues
                critical_issues = [c for c in health.checks if c.status.value == "critical"]
                if critical_issues:
                    self.logger.error("❌ Critical health issues found:")
                    for issue in critical_issues:
                        self.logger.error(f"  • {issue.name}: {issue.message}")
                
            except Exception as e:
                debug_logger.error("Initial health check failed", error=e)
        
    async def _initialize_channel_references(self):
        """Initialize Discord channel references for easier access."""
        try:
            # Get channel IDs from config
            log_channel_id = config.get("discord.channels.logs")
            errors_channel_id = config.get("discord.channels.errors") 
            news_channel_id = config.get("discord.channels.news")
            
            # Log the IDs we're trying to use
            self.logger.debug(f"Channel IDs from config: logs={log_channel_id}, errors={errors_channel_id}, news={news_channel_id}")
            
            # Set channel references
            self.log_channel = self.get_channel(log_channel_id) if log_channel_id else None
            self.errors_channel = self.get_channel(errors_channel_id) if errors_channel_id else None
            self.news_channel = self.get_channel(news_channel_id) if news_channel_id else None
            
            # Log channel availability
            channels_status = []
            if self.log_channel:
                channels_status.append(f"✅ logs: #{self.log_channel.name}")
            else:
                channels_status.append("❌ logs: not found")
                
            if self.errors_channel:
                channels_status.append(f"✅ errors: #{self.errors_channel.name}")
            else:
                channels_status.append("❌ errors: not found")
                
            if self.news_channel:
                channels_status.append(f"✅ news: #{self.news_channel.name}")
            else:
                channels_status.append("❌ news: not found")
            
            self.logger.info("📡 Channel References:")
            for status in channels_status:
                self.logger.info(f"  {status}")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize channel references: {e}")

    def get_errors_channel(self):
        """
        Get the errors channel with fallback logic.
        
        Returns:
            discord.TextChannel or None: The errors channel if available
        """
        # Try the pre-initialized reference first
        if hasattr(self, 'errors_channel') and self.errors_channel:
            return self.errors_channel
            
        # Fallback: Get from config directly
        errors_channel_id = config.get("discord.channels.errors")
        if errors_channel_id:
            return self.get_channel(errors_channel_id)
            
        return None
    
    async def _send_startup_notification(self):
        """Send startup notification to log channel."""
        try:
            from src.bot.background_tasks import send_startup_notification
            await send_startup_notification(self)
        except Exception as e:
            self.logger.error(f"❌ Failed to send startup notification: {e}")

    async def _initialize_rich_presence(self):
        """Initialize rich presence system."""
        try:
            from src.core.rich_presence import set_startup_presence
            await set_startup_presence(self)
            self.logger.info("✅ Rich presence initialized")
        except Exception as e:
            self.logger.error(f"Rich presence initialization failed: {e}")

    async def _start_background_tasks(self):
        """Start all background tasks including auto-posting."""
        try:
            from src.bot.background_tasks import start_monitoring_tasks
            await start_monitoring_tasks(self)
            self.logger.info("🔄 Background tasks started successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to start background tasks: {e}")
            raise
            
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

            # Record error in bot statistics
            self.record_error(f"Command error: {str(error)}", f"command_{command_name}")

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

    def enable_auto_post_after_startup(self) -> None:
        """
        Enable auto-posting after startup.

        This allows the bot to start posting automatically according to the interval.
        """
        self.disable_auto_post_on_startup = False
        logger.info("🚀 Auto-posting enabled - bot can now post automatically")

    def mark_just_posted(self) -> None:
        """
        Mark that news was just posted and update the last post time.
        
        This method is critical for the auto-posting interval system as it:
        1. Records the exact time when content was posted (in Eastern timezone)
        2. Sets the _just_posted flag for rich presence display
        3. Automatically saves the updated time to persistent cache
        4. Increments post counters for statistics
        
        This ensures that the bot respects the configured posting interval
        even across restarts and prevents duplicate posts.
        
        Called by:
        - Delayed post completion (_schedule_delayed_post)
        - Auto-post completion (auto_post_from_channel) 
        - Manual post completion (via background task)
        """
        # Record the exact post time in Eastern timezone for consistency
        self.last_post_time = now_eastern()
        
        # Set flag for rich presence to show "just posted" status
        self._just_posted = True
        
        # Increment post counters for statistics
        self.increment_post_count(success=True)
        
        logger.info(f"📅 Post time marked: {self.last_post_time}")
        
        # Save to cache immediately to persist across restarts
        # This is crucial for interval respect after bot restarts
        asyncio.create_task(self.save_auto_post_config())
        asyncio.create_task(self.save_statistics_to_cache())

    def should_wait_for_startup_delay(self) -> tuple[bool, int]:
        """
        Check if we should wait for the startup grace period.

        The startup grace period prevents auto-posting immediately after bot startup
        to avoid posting duplicate content or posting during maintenance windows.

        Returns:
            Tuple of (should_wait, seconds_to_wait)
            - If within grace period: (True, seconds_remaining)
            - If grace period expired or disabled: (False, 0)
        """
        # If startup protection is manually disabled, allow posting immediately
        if not self.disable_auto_post_on_startup:
            # Only log this once every 5 minutes using a class variable with thread safety
            now = time.time()
            if not hasattr(NewsBot, '_last_startup_protection_log_time') or \
               (now - getattr(NewsBot, '_last_startup_protection_log_time', 0)) > 300:
                logger.debug("🚀 Startup protection disabled - auto-posting allowed")
                NewsBot._last_startup_protection_log_time = now
            return False, 0

        # Calculate time since startup
        time_since_startup = (
            datetime.datetime.now(datetime.timezone.utc) - self.startup_time
        ).total_seconds()

        # If grace period has expired, allow posting
        if time_since_startup >= self.startup_grace_period_minutes * 60:
            # Only log this transition once using class variable
            if not hasattr(NewsBot, '_grace_period_expired_logged'):
                logger.info("🚀 Startup grace period expired - auto-posting now enabled")
                NewsBot._grace_period_expired_logged = True
            return False, 0

        # Still in grace period
        seconds_remaining = int(self.startup_grace_period_minutes * 60 - time_since_startup)
        
        # Only log grace period status every 30 seconds
        now = time.time()
        if not hasattr(NewsBot, '_last_grace_period_log_time') or \
           (now - getattr(NewsBot, '_last_grace_period_log_time', 0)) > 30:
            logger.debug(
                f"🕐 Grace period check: startup_time={self.startup_time}, "
                f"now={datetime.datetime.now(datetime.timezone.utc)}, "
                f"time_since_startup={time_since_startup:.1f}s, "
                f"grace_period={self.startup_grace_period_minutes * 60}s, "
                f"disable_auto_post_on_startup={self.disable_auto_post_on_startup}"
            )
            if seconds_remaining > 60:
                logger.info(f"🛡️ Still in startup grace period: {seconds_remaining//60}m {seconds_remaining%60}s remaining (will not auto-post)")
            else:
                logger.info(f"🛡️ Still in startup grace period: {seconds_remaining}s remaining (will not auto-post)")
            NewsBot._last_grace_period_log_time = now

        return True, seconds_remaining

    async def load_auto_post_config(self) -> None:
        """
        Load auto-posting configuration from persistent storage.
        """
        try:
            if self.json_cache:
                # Load auto_post_interval
                cached_interval = await self.json_cache.get("auto_post_interval")
                if cached_interval:
                    self.auto_post_interval = cached_interval
                    logger.debug(f"📄 Auto-post interval loaded: {self.auto_post_interval}s")

                # Load last_post_time
                cached_last_post = await self.json_cache.get("last_post_time")
                if cached_last_post:
                    from src.utils.timezone_utils import EASTERN
                    self.last_post_time = datetime.datetime.fromisoformat(cached_last_post)
                    # Ensure timezone-aware
                    if self.last_post_time.tzinfo is None:
                        self.last_post_time = self.last_post_time.replace(tzinfo=EASTERN)
                    logger.debug(f"📄 Last post time loaded: {self.last_post_time}")
                else:
                    # If no cached time exists, set initial time for rich presence countdown
                    # This allows the countdown to work immediately instead of showing "monitoring"
                    from src.utils.timezone_utils import now_eastern
                    self.last_post_time = now_eastern() - datetime.timedelta(seconds=self.auto_post_interval)
                    logger.info(f"📄 No cached last_post_time - setting initial time for countdown: {self.last_post_time}")

                logger.debug("📄 Auto-post configuration loaded")

        except Exception as e:
            logger.error(f"❌ Failed to load auto-post config: {e}")

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
                    logger.debug(f"💾 Last post time saved: {self.last_post_time}")

                await self.json_cache.save()
                logger.debug("💾 Auto-post configuration saved")

        except Exception as e:
            logger.error(f"❌ Failed to save auto-post config: {e}")

    @track_auto_post_performance
    async def fetch_and_post_auto(self, channel_name: str = None) -> bool:
        """
        Fetch and post news automatically from specified Telegram channel.

        This method serves as the main entry point for automated news posting.
        It delegates the actual fetching and processing to the FetchCommands
        instance while handling validation and error cases.

        Args:
            channel_name (str): Name of the Telegram channel to fetch from.
                              Must be an active channel configured in the system.

        Returns:
            bool: True if content was successfully fetched and posted,
                  False if no suitable content found or operation failed.

        Raises:
            Exception: Logs errors but doesn't re-raise to avoid breaking
                      the background task loop.

        Note:
            This method does NOT update last_post_time itself - that's handled
            by the specific posting implementations (delayed_post, auto_post_from_channel)
            to ensure consistent timing regardless of posting path.
        """
        try:
            logger.info(f"🔄 Starting auto-post for channel: {channel_name}")

            # Validate channel name is provided
            if not channel_name:
                logger.error("❌ No channel name provided for auto-posting")
                return False

            # Verify Telegram client is available and connected
            if not hasattr(self, 'telegram_client') or not self.telegram_client:
                logger.warning("⚠️ Telegram client not available for auto-posting")
                return False

            if not await self.telegram_client.is_connected():
                logger.warning("⚠️ Telegram client not connected for auto-posting")
                return False

            # Verify FetchCommands instance is available
            if not hasattr(self, 'fetch_commands') or not self.fetch_commands:
                logger.error("⚠️ FetchCommands instance not found for auto-posting")
                return False

            # Delegate to FetchCommands for actual posting logic
            logger.info(f"📡 Delegating auto-post to FetchCommands for channel: {channel_name}")
            result = await self.fetch_commands.fetch_and_post_auto(channel_name)

            if result:
                logger.info(f"✅ Auto-post completed successfully for {channel_name}")
            else:
                logger.info(f"ℹ️ No suitable content found in {channel_name}")

            return result

        except Exception as e:
            logger.error(f"❌ Auto-post failed: {e}")
            # Record the error for statistics
            self.record_error(f"Auto-post failed: {str(e)}", "auto_post")
            # Don't send error embeds for auto-posting to avoid spam
            # Just log the error and continue
            return False

    async def close(self) -> None:
        """
        Clean shutdown of the bot and all its systems.

        This method ensures all background tasks are stopped and resources
        are properly cleaned up before the bot shuts down.
        """
        try:
            logger.info("🔄 Starting bot shutdown...")

            # Stop background tasks first with shorter timeout
            try:
                await asyncio.wait_for(task_manager.stop_all_tasks(), timeout=3.0)  # Reduced from 5.0
            except asyncio.TimeoutError:
                logger.warning("🛑 Background task shutdown timeout")
            except Exception as e:
                logger.error(f"❌ Error stopping background tasks: {e}")

            # Stop monitoring systems in parallel
            shutdown_tasks = []
            
            if self.performance_metrics:
                shutdown_tasks.append(self.performance_metrics.stop_monitoring())
                
            if self.health_check:
                shutdown_tasks.append(self.health_check.stop())
                
            # Run monitoring shutdowns in parallel with short timeout
            if shutdown_tasks:
                try:
                    await asyncio.wait_for(asyncio.gather(*shutdown_tasks, return_exceptions=True), timeout=2.0)
                    logger.info("📊 Monitoring systems stopped")
                except asyncio.TimeoutError:
                    logger.warning("🛑 Monitoring shutdown timeout")
                except Exception as e:
                    logger.error(f"❌ Error stopping monitoring: {e}")
            
            # Stop backup scheduler (non-async operation)
            try:
                if self.backup_scheduler:
                    self.backup_scheduler.stop_scheduler()
                    logger.info("🗄️ Backup scheduler stopped")
            except Exception as e:
                logger.error(f"❌ Error stopping backup scheduler: {e}")

            # Disconnect Telegram client with shorter timeout and better error handling
            if self.telegram_client:
                try:
                    await asyncio.wait_for(self.telegram_client.disconnect(), timeout=3.0)  # Reduced from 5.0
                    logger.info("📱 Telegram client disconnected")
                except asyncio.TimeoutError:
                    logger.warning("🛑 Telegram disconnect timeout - continuing shutdown")
                    # Force cleanup without waiting
                    try:
                        if hasattr(self.telegram_client, 'client') and self.telegram_client.client:
                            self.telegram_client.client = None
                    except:
                        pass
                except Exception as e:
                    error_msg = str(e)
                    if "database is locked" in error_msg or "disk I/O error" in error_msg:
                        logger.debug(f"📱 Telegram session save warning: {error_msg}")
                    else:
                        logger.error(f"❌ Error disconnecting Telegram: {error_msg}")

            # Save final cache state with timeout
            try:
                if self.json_cache:
                    await asyncio.wait_for(self.json_cache.save(), timeout=2.0)  # Reduced from 3.0
                    logger.info("💾 Final cache save completed")
            except asyncio.TimeoutError:
                logger.warning("🛑 Cache save timeout")
            except Exception as e:
                logger.error(f"❌ Error saving cache: {e}")

            # Call parent close method with shorter timeout
            try:
                await asyncio.wait_for(super().close(), timeout=3.0)  # Reduced from 5.0
            except asyncio.TimeoutError:
                logger.warning("🛑 Discord client close timeout")
            except Exception as e:
                logger.error(f"❌ Error closing Discord client: {e}")

            logger.info("✅ Bot shutdown completed")

        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")
            # Continue with shutdown even if there are errors

    async def update_automation_config(self, **kwargs) -> bool:
        """
        Update automation configuration dynamically.

        Args:
            **kwargs: Configuration parameters to update
                - enabled: bool - Enable/disable automation
                - interval_minutes: int - Auto-posting interval in minutes
                - startup_delay_minutes: int - Startup delay in minutes
                - max_posts_per_session: int - Max posts per automation cycle
                - require_media: bool - Require media in posts
                - require_text: bool - Require text in posts
                - min_content_length: int - Minimum content length
                - use_ai_filtering: bool - Use AI for content filtering
                - silent_mode: bool - Run in silent mode
                - notify_on_success: bool - Notify on successful posts
                - notify_on_errors: bool - Notify on errors

        Returns:
            bool: True if update was successful
        """
        try:
            if not self.json_cache:
                logger.error("❌ JSON cache not available for config update")
                return False

            # Get current config or create default
            current_config = getattr(self, 'automation_config', {}) or {}

            # Update with new values
            current_config.update(kwargs)

            # Validate critical settings
            if 'interval_minutes' in kwargs:
                interval = kwargs['interval_minutes']
                if not isinstance(interval, int) or interval < 1:
                    logger.error(f"❌ Invalid interval: {interval}. Must be >= 1 minute")
                    return False

                # Update the bot's interval
                self.set_auto_post_interval(interval)
                logger.info(f"⏰ Auto-post interval updated to {interval} minutes")

            if 'startup_delay_minutes' in kwargs:
                delay = kwargs['startup_delay_minutes']
                if isinstance(delay, int) and delay >= 0:
                    self.startup_grace_period_minutes = delay
                    logger.info(f"⏰ Startup delay updated to {delay} minutes")

            if 'enabled' in kwargs:
                enabled = kwargs['enabled']
                if enabled:
                    self.enable_auto_post_after_startup()
                    logger.info("✅ Automation enabled")
                else:
                    self.disable_auto_post_on_startup = True
                    logger.info("🛑 Automation disabled")

            # Save updated config
            self.automation_config = current_config
            await self.json_cache.set("automation_config", current_config)
            await self.json_cache.save()

            logger.info("💾 Automation configuration updated and saved")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to update automation config: {e}")
            return False

    async def get_automation_config(self) -> dict:
        """
        Get current automation configuration.

        Returns:
            dict: Current automation configuration
        """
        try:
            if hasattr(self, 'automation_config'):
                return self.automation_config.copy()

            # Fallback to cache
            if self.json_cache:
                config = await self.json_cache.get("automation_config", {})
                return config

            return {}

        except Exception as e:
            logger.error(f"❌ Failed to get automation config: {e}")
            return {}

    async def reload_automation_config(self) -> bool:
        """
        Reload automation configuration from unified config.
        
        This allows you to edit unified_config.yaml manually and reload without restart.
        """
        try:
            logger.info("🔄 Reloading automation configuration...")
            await self._load_streamlined_commands()
            logger.info("✅ Automation configuration reloaded")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to reload automation config: {e}")
            return False

    def get_automation_status(self) -> dict:
        """
        Get current automation status and statistics.

        Returns:
            dict: Automation status information
        """
        try:
            config = getattr(self, 'automation_config', {})

            # Calculate next post time
            next_post_time = None
            if self.last_post_time and self.auto_post_interval > 0:
                next_post_time = self.last_post_time + datetime.timedelta(seconds=self.auto_post_interval)

            # Check if in grace period
            in_grace_period, grace_remaining = self.should_wait_for_startup_delay()

            status = {
                "enabled": config.get("enabled", True) and not self.disable_auto_post_on_startup,
                "interval_minutes": config.get("interval_minutes", 60),
                "last_post_time": self.last_post_time.isoformat() if self.last_post_time else None,
                "next_post_time": next_post_time.isoformat() if next_post_time else None,
                "in_grace_period": in_grace_period,
                "grace_remaining_seconds": grace_remaining,
                "posts_today": self.posts_today,
                "total_posts": self.total_posts,
                "last_error": self.last_error,
                "error_count": self.error_count,
                "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
                "uptime_hours": self._calculate_uptime_hours()
            }

            return status

        except Exception as e:
            logger.error(f"❌ Failed to get automation status: {e}")
            return {"enabled": False, "error": str(e)}

    def _calculate_uptime_hours(self) -> float:
        """Calculate bot uptime in hours."""
        if self.startup_time is None:
            return 0.0
        
        now = datetime.datetime.now(datetime.timezone.utc)
        uptime_delta = now - self.startup_time
        return round(uptime_delta.total_seconds() / 3600, 2)

    def increment_post_count(self, success: bool = True) -> None:
        """
        Increment post counters and track posting statistics.
        
        Args:
            success: Whether the post was successful
        """
        try:
            if success:
                self.posts_today += 1
                self.total_posts += 1
                
                # Reset daily counter if it's a new day
                now = datetime.datetime.now()
                if self.last_post_time:
                    last_date = self.last_post_time.date()
                    today = now.date()
                    if last_date != today:
                        self.posts_today = 1  # Reset to 1 for today's first post
                
                self.last_post_time = now
                logger.debug(f"📊 Post count updated: today={self.posts_today}, total={self.total_posts}")
            
        except Exception as e:
            logger.error(f"❌ Error updating post count: {e}")

    def record_error(self, error_message: str, component: str = None) -> None:
        """
        Record an error for tracking and statistics.
        
        Args:
            error_message: The error message to record
            component: Optional component where the error occurred
        """
        try:
            self.last_error = error_message
            self.last_error_time = datetime.datetime.now(datetime.timezone.utc)
            self.error_count += 1
            
            if component:
                logger.error(f"❌ [{component}] {error_message}")
            else:
                logger.error(f"❌ {error_message}")
                
            logger.debug(f"📊 Error count updated: {self.error_count}")
            
        except Exception as e:
            logger.error(f"❌ Error recording error: {e}")

    async def load_statistics_from_cache(self) -> None:
        """Load persistent statistics from cache."""
        try:
            if self.json_cache:
                stats = await self.json_cache.get("bot_statistics", {})
                
                self.total_posts = stats.get("total_posts", 0)
                self.error_count = stats.get("error_count", 0)
                
                # Load last error info
                if "last_error" in stats:
                    self.last_error = stats["last_error"]
                if "last_error_time" in stats:
                    self.last_error_time = datetime.datetime.fromisoformat(stats["last_error_time"])
                
                # Reset daily posts counter
                self.posts_today = 0
                
                logger.debug(f"📊 Loaded statistics: total_posts={self.total_posts}, error_count={self.error_count}")
                
        except Exception as e:
            logger.warning(f"⚠️ Could not load statistics from cache: {e}")

    async def save_statistics_to_cache(self) -> None:
        """Save persistent statistics to cache."""
        try:
            if self.json_cache:
                stats = {
                    "total_posts": self.total_posts,
                    "error_count": self.error_count,
                    "last_error": self.last_error,
                    "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
                    "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
                
                await self.json_cache.set("bot_statistics", stats)
                await self.json_cache.save()
                
                logger.debug(f"📊 Saved statistics to cache")
                
        except Exception as e:
            logger.warning(f"⚠️ Could not save statistics to cache: {e}")

    async def _initialize_vps_optimizations(self) -> None:
        """
        Initialize VPS-specific optimizations for better performance and resource usage.
        """
        try:
            from src.utils.vps_optimizer import start_vps_optimizations
            await start_vps_optimizations(self)
            logger.info("🔧 VPS optimizations initialized")
        except ImportError:
            logger.debug("⚠️ VPS optimizer not available")
        except Exception as e:
            logger.warning(f"⚠️ VPS optimization failed: {e}")
            # Continue without VPS optimizations - not critical

