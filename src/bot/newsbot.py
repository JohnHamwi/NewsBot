# =============================================================================
# NewsBot Core Module
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
# - Comprehensive admin controls and monitoring systems
# - Modern Discord.py 2.5+ slash commands and interactions
# - Advanced error handling, recovery, and performance metrics
#
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
# NewsBot Main Class
# =============================================================================
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

        # Startup protection - prevents auto-posting for first 5 minutes after launch
        self.startup_grace_period_minutes: int = 5
        self.disable_auto_post_on_startup: bool = True

        # Core systems initialization
        self.json_cache: Optional[JSONCache] = None
        self.rbac: Optional[RBACManager] = None
        self.telegram_client: Optional[Any] = None

        # Command cogs/handlers
        self.fetch_commands: Optional[Any] = None

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
        Async setup hook called when the bot is starting up.

        This method initializes all core systems, loads commands, and starts
        background tasks. It's called automatically by Discord.py.
        """
        try:
            logger.info("🚀 Starting NewsBot setup process...")

            # Record startup time for uptime tracking
            self.startup_time = datetime.datetime.now(datetime.timezone.utc)
            logger.info(f"🛡️ Auto-posting disabled for {self.startup_grace_period_minutes} minutes after startup (use /admin autopost operation:enable to override)")

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

            # Initialize VPS optimizations for better performance
            await self._initialize_vps_optimizations()

            # Initialize Telegram client if configured
            await self._initialize_telegram_client()
            
            # Initialize backup scheduler
            await self._initialize_backup_scheduler()

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

    async def _load_commands(self) -> None:
        """
        Load all slash commands from command modules.

        Uses the streamlined command structure with automation support:
        - /news - User-friendly news access commands
        - /info - General bot information and utilities
        - /admin - Administrative commands for management
        - Background automation runs independently
        """
        try:
            logger.info("📥 Loading command structure with automation support...")

            # Load news commands
            try:
                from src.cogs.news_commands import NewsCommands
                news_cog = NewsCommands(self)
                self.tree.add_command(news_cog.news_group)
                logger.info("✅ News commands loaded")
            except Exception as e:
                logger.warning(f"Could not load news commands: {e}")

            # Load bot info commands (general info & utilities)
            try:
                from src.cogs.bot_commands import BotCommands
                bot_cog = BotCommands(self)
                self.tree.add_command(bot_cog.info_group)
                logger.info("✅ Bot info commands loaded")
            except Exception as e:
                logger.warning(f"Could not load bot info commands: {e}")

            # Load utility commands
            try:
                from src.cogs.utility import UtilityCommands
                utility_cog = UtilityCommands(self)
                self.tree.add_command(utility_cog.utils_group)
                logger.info("✅ Utility commands loaded")
            except Exception as e:
                logger.warning(f"Could not load utility commands: {e}")

            # Load status commands
            try:
                from src.cogs.status import StatusCommands
                status_cog = StatusCommands(self)
                self.tree.add_command(status_cog.status_group)
                logger.info("✅ Status commands loaded")
            except Exception as e:
                logger.warning(f"Could not load status commands: {e}")

            # Load configuration commands
            try:
                from src.commands.config_commands import ConfigCommands
                config_cog = ConfigCommands(self)
                self.tree.add_command(config_cog.config_group)
                logger.info("✅ Configuration commands loaded")
            except Exception as e:
                logger.warning(f"Could not load configuration commands: {e}")

            # Load admin commands with automation controls
            try:
                from src.cogs.admin import AdminCommands
                admin_cog = AdminCommands(self)
                self.tree.add_command(admin_cog.admin_group)
                logger.info("✅ Admin commands loaded")
            except Exception as e:
                logger.warning(f"Could not load admin commands: {e}")

            # Load fetch commands (essential for automation)
            try:
                from src.cogs.fetch_cog import setup_fetch_commands
                setup_fetch_commands(self)
                logger.info("✅ Enhanced fetch command setup completed successfully")
            except Exception as e:
                logger.warning(f"Could not load fetch commands: {e}")

            logger.info("✅ Command structure with automation loaded successfully")
            logger.info("🎯 Available: /news, /info, /utils, /status, /config, /admin + background automation")

        except Exception as e:
            logger.error(f"❌ Error loading commands: {e}")
            raise

    async def _sync_commands(self) -> None:
        """
        Sync application commands with Discord.

        This method registers all slash commands with Discord's API,
        making them available for use globally.
        """
        try:
            logger.info("🔄 Syncing slash commands with Discord...")

            # Get all commands before sync
            commands = self.tree.get_commands()
            command_count = len(commands)
            command_names = [cmd.name for cmd in commands]

            logger.debug(f"📋 Found {command_count} commands to sync: {', '.join(command_names)}")

            # Log detailed command info only in debug mode
            for cmd in commands:
                if hasattr(cmd, 'commands') and cmd.commands:  # Group commands
                    subcommands = [subcmd.name for subcmd in cmd.commands]
                    logger.debug(f"📝 Group command '{cmd.name}' has subcommands: {subcommands}")

                    # Check for autocomplete in subcommands (debug only)
                    for subcmd in cmd.commands:
                        for param in subcmd.parameters:
                            if hasattr(param, 'autocomplete') and param.autocomplete:
                                logger.debug(f"✅ Command '{cmd.name} {subcmd.name}' parameter '{param.name}' has autocomplete")

            # Perform the sync
            import time
            sync_start = time.time()

            synced = await asyncio.wait_for(self.tree.sync(), timeout=30.0)

            sync_end = time.time()
            sync_duration = sync_end - sync_start

            # Log results
            synced_names = [cmd.name for cmd in synced]
            logger.info(f"✅ Command sync completed: {len(synced)} commands in {sync_duration:.2f} seconds")
            logger.debug(f"📋 Synced commands: {', '.join(synced_names)}")

            # Verify sync results
            if len(synced) != command_count:
                logger.warning(f"⚠️ Sync mismatch: Expected {command_count}, synced {len(synced)}")

            # Check if admin command was synced (debug only)
            admin_synced = any(cmd.name == "admin" for cmd in synced)
            if not admin_synced:
                logger.debug("⚠️ Admin command group was not synced")
            else:
                logger.debug("✅ Admin command group synced successfully")

        except asyncio.TimeoutError:
            logger.error("❌ Command sync timed out after 30 seconds")
            logger.warning("⚠️ Continuing without command sync - commands may not be updated")
            # Don't raise - let the bot continue
        except Exception as e:
            logger.error(f"❌ Failed to sync commands: {e}")
            logger.debug(f"Full sync error traceback: {traceback.format_exc()}")
            logger.warning("⚠️ Continuing without command sync - commands may not be updated")
            # Don't raise - let the bot continue

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
        Load auto-posting configuration from unified config.

        This uses the unified configuration system for consistent settings.
        """
        try:
            # Load automation settings from unified config
            automation_config = config.get_section("automation")

            if not automation_config:
                logger.warning("⚠️ No automation config found in unified config")
                # Use default values
                automation_config = {
                    "enabled": True,
                    "interval_minutes": 180,
                    "startup_delay_minutes": 5,
                    "max_posts_per_session": 1,
                    "require_media": True,
                    "require_text": True,
                    "min_content_length": 50,
                    "use_ai_filtering": True
                }

            # Apply automation settings
            self.automation_config = automation_config

            # Set auto-post interval from config
            interval_minutes = automation_config.get("interval_minutes", 180)
            self.set_auto_post_interval(interval_minutes)

            # Store startup delay
            self.startup_grace_period_minutes = automation_config.get("startup_delay_minutes", 5)

            logger.info(f"⚙️ Automation config loaded:")
            logger.info(f"   • Enabled: {automation_config.get('enabled', True)}")
            logger.info(f"   • Interval: {interval_minutes} minutes")
            logger.info(f"   • Startup delay: {self.startup_grace_period_minutes} minutes")
            
            # Get active channels for rotation instead of primary channels
            if self.json_cache:
                active_channels = await self.json_cache.list_telegram_channels("activated")
                logger.info(f"   • Active channels for rotation: {active_channels}")
                logger.info(f"   • Total active channels: {len(active_channels)}")
            else:
                logger.warning("   • Could not load active channels - cache not available")
            
            logger.info(f"   • Require media: {automation_config.get('require_media', True)}")
            logger.info(f"   • AI filtering: {automation_config.get('use_ai_filtering', True)}")

            # CRITICAL: Load last post time from cache (this ensures the bot remembers when it last posted)
            if self.json_cache:
                last_post_time_str = await self.json_cache.get("last_post_time")
                if last_post_time_str:
                    try:
                        self.last_post_time = datetime.datetime.fromisoformat(last_post_time_str)
                        logger.info(f"📅 Last post time loaded from cache: {self.last_post_time}")
                        
                        # Calculate time since last post
                        time_since_last = (now_eastern() - self.last_post_time).total_seconds()
                        interval_seconds = interval_minutes * 60
                        
                        if time_since_last < interval_seconds:
                            # Still within interval, show when next post will be
                            remaining_seconds = interval_seconds - time_since_last
                            remaining_minutes = remaining_seconds / 60
                            logger.info(f"⏰ Next post scheduled in {remaining_minutes:.1f} minutes")
                        else:
                            # Interval has passed, will post after grace period
                            logger.info(f"📝 Ready to post (last post was {time_since_last/60:.1f} minutes ago)")
                            
                    except Exception as e:
                        logger.error(f"❌ Failed to parse last post time: {e}")
                        self.last_post_time = None
                else:
                    logger.info("📅 No previous post time found - first run or cache cleared")
                    self.last_post_time = None
            else:
                logger.warning("⚠️ Cannot load last post time - JSON cache not available")
                self.last_post_time = None

        except Exception as e:
            logger.error(f"❌ Failed to load auto-post config: {e}")
            # Set safe defaults
            self.automation_config = {"enabled": True, "interval_minutes": 180}
            self.set_auto_post_interval(180)  # Default 3 hours

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
                    automation_config = await self.json_cache.get("automation_config")
                    if automation_config:
                        active_channels = automation_config.get("active_channels", [])
                        auto_post_interval = automation_config.get("intervals", {}).get("auto_post_minutes", 180)
                        
                        self.logger.info(f"Active channels for rotation: {len(active_channels)}")
                        for channel in active_channels:
                            self.logger.info(f"  • {channel}")
                        self.logger.info(f"Auto-post interval: {auto_post_interval} minutes")
                    else:
                        self.logger.info("No automation config found in cache")
                except Exception as e:
                    self.logger.warning(f"Failed to load automation config from cache: {e}")
            else:
                self.logger.warning("JSON cache not available")
            
            # Check feature status
            self._log_feature_status()
            
            # Run initial health check
            await self._run_initial_health_check()
            
            # Initialize rich presence
            await self._initialize_rich_presence()
            
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
        
    async def _initialize_rich_presence(self):
        """Initialize rich presence system."""
        try:
            from src.core.rich_presence import set_startup_presence
            await set_startup_presence(self)
            self.logger.info("✅ Rich presence initialized")
        except Exception as e:
            self.logger.error(f"Rich presence initialization failed: {e}")
            
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
        
        logger.info(f"📅 Post time marked: {self.last_post_time}")
        
        # Save to cache immediately to persist across restarts
        # This is crucial for interval respect after bot restarts
        asyncio.create_task(self.save_auto_post_config())

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
            if not self.fetch_commands:
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

            # Stop background tasks first
            try:
                await asyncio.wait_for(task_manager.stop_all_tasks(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("🛑 Background task shutdown timeout")
            except Exception as e:
                logger.error(f"❌ Error stopping background tasks: {e}")

            # Stop monitoring systems
            try:
                if self.performance_metrics:
                    await asyncio.wait_for(self.performance_metrics.stop_monitoring(), timeout=3.0)
                    logger.info("📊 Performance metrics stopped")
            except asyncio.TimeoutError:
                logger.warning("🛑 Performance metrics shutdown timeout")
            except Exception as e:
                logger.error(f"❌ Error stopping performance metrics: {e}")

            try:
                if self.health_check:
                    await asyncio.wait_for(self.health_check.stop(), timeout=3.0)
                    logger.info("🏥 Health check service stopped")
            except asyncio.TimeoutError:
                logger.warning("🛑 Health check shutdown timeout")
            except Exception as e:
                logger.error(f"❌ Error stopping health check: {e}")
            
            # Stop backup scheduler
            try:
                if self.backup_scheduler:
                    self.backup_scheduler.stop_scheduler()
                    logger.info("🗄️ Backup scheduler stopped")
            except Exception as e:
                logger.error(f"❌ Error stopping backup scheduler: {e}")

            # Disconnect Telegram client with timeout and error handling
            if self.telegram_client:
                try:
                    await asyncio.wait_for(self.telegram_client.disconnect(), timeout=5.0)
                    logger.info("📱 Telegram client disconnected")
                except asyncio.TimeoutError:
                    logger.warning("🛑 Telegram disconnect timeout - continuing shutdown")
                except Exception as e:
                    error_msg = str(e)
                    if "database is locked" in error_msg or "disk I/O error" in error_msg:
                        logger.warning(f"📱 Telegram session save error: {error_msg}")
                    else:
                        logger.error(f"❌ Error disconnecting Telegram: {error_msg}")

            # Save final cache state
            try:
                if self.json_cache:
                    await asyncio.wait_for(self.json_cache.save(), timeout=3.0)
                    logger.info("💾 Final cache save completed")
            except asyncio.TimeoutError:
                logger.warning("🛑 Cache save timeout")
            except Exception as e:
                logger.error(f"❌ Error saving cache: {e}")

            # Call parent close method with timeout
            try:
                await asyncio.wait_for(super().close(), timeout=5.0)
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
            await self._load_auto_post_config()
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
                "posts_today": 0,  # TODO: Implement post counting
                "total_posts": 0,  # TODO: Implement total post counting
                "last_error": None,  # TODO: Track last error
                "uptime_hours": 0  # TODO: Calculate uptime
            }

            return status

        except Exception as e:
            logger.error(f"❌ Failed to get automation status: {e}")
            return {"enabled": False, "error": str(e)}

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
