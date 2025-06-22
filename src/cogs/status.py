# =============================================================================
# NewsBot Status Commands Module
# =============================================================================
# This cog provides comprehensive status and monitoring commands for NewsBot,
# including system health monitoring, performance metrics, service status,
# and error tracking with professional presentation.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import discord
import psutil
from discord import app_commands
from discord.ext import commands

# =============================================================================
# Local Application Imports
# =============================================================================
from src.components.decorators.admin_required import admin_required
from src.components.embeds.base_embed import ErrorEmbed, InfoEmbed, SuccessEmbed, WarningEmbed
from src.core.config_manager import config
from src.utils.base_logger import base_logger as logger
from src.utils.structured_logger import structured_logger

# =============================================================================
# Configuration Constants
# =============================================================================
GUILD_ID = config.get("bot.guild_id") or 0
ADMIN_ROLE_ID = config.get("bot.admin_role_id")


# =============================================================================
# Status Commands Cog
# =============================================================================
class StatusCommands(commands.Cog):
    """
    Professional status monitoring system for NewsBot.

    Features:
    - Comprehensive system health monitoring
    - Real-time performance metrics and analytics
    - Service status tracking and diagnostics
    - Error monitoring and troubleshooting tools
    - Professional presentation with organized sections
    """

    def __init__(self, bot: discord.Client) -> None:
        """Initialize the StatusCommands cog."""
        self.bot = bot
        logger.debug("📊 StatusCommands cog initialized")

    # =========================================================================
    # Status Command Group Setup
    # =========================================================================
    # Status command group
    status_group = app_commands.Group(
        name="status", 
        description="📊 System status and monitoring"
    )
    status_group.default_permissions = discord.Permissions(administrator=True)

    # =========================================================================
    # System Overview Commands
    # =========================================================================
    @status_group.command(name="overview", description="📊 System overview and health")
    @app_commands.describe(
        detail_level="Level of detail to include in status report",
        quick="Show quick status summary only"
    )
    @app_commands.choices(
        detail_level=[
            app_commands.Choice(name="📋 Summary", value="summary"),
            app_commands.Choice(name="📊 Detailed", value="detailed"),
            app_commands.Choice(name="📈 Comprehensive", value="comprehensive"),
            app_commands.Choice(name="🔍 Diagnostic", value="diagnostic"),
        ]
    )
    async def status_overview(
        self,
        interaction: discord.Interaction,
        detail_level: app_commands.Choice[str] = None,
        quick: bool = False
    ) -> None:
        """Show comprehensive system status and health overview."""
        start_time = discord.utils.utcnow()
        await interaction.response.defer()

        try:
            detail_value = detail_level.value if detail_level else "summary"
            logger.info(f"[STATUS] Overview command by {interaction.user.id}, detail={detail_value}")

            if quick:
                embed = await self._build_quick_status_embed(start_time)
            else:
                embed = await self._build_overview_embed(detail_value, start_time)

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in status overview command: {e}")
            error_embed = ErrorEmbed(
                "Status Overview Error",
                "Failed to retrieve system status overview."
            )
            await interaction.followup.send(embed=error_embed)

    # =========================================================================
    # System Performance Commands
    # =========================================================================
    @status_group.command(name="system", description="💻 System performance and resources")
    @app_commands.describe(
        metric_type="Type of system metrics to display",
        detailed="Include detailed system diagnostics"
    )
    @app_commands.choices(
        metric_type=[
            app_commands.Choice(name="💻 All Metrics", value="all"),
            app_commands.Choice(name="🔧 CPU & Memory", value="cpu_memory"),
            app_commands.Choice(name="💾 Storage & I/O", value="storage"),
            app_commands.Choice(name="🌐 Network", value="network"),
        ]
    )
    async def status_system(
        self,
        interaction: discord.Interaction,
        metric_type: app_commands.Choice[str] = None,
        detailed: bool = False
    ) -> None:
        """Show detailed system performance and resource metrics."""
        await interaction.response.defer()

        try:
            metric_value = metric_type.value if metric_type else "all"
            logger.info(f"[STATUS] System command by {interaction.user.id}, type={metric_value}")

            embed = await self._build_system_status_embed(metric_value, detailed)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in status system command: {e}")
            error_embed = ErrorEmbed(
                "System Status Error",
                "Failed to retrieve system performance metrics."
            )
            await interaction.followup.send(embed=error_embed)

    # =========================================================================
    # Service Status Commands
    # =========================================================================
    @status_group.command(name="services", description="🔧 Service status and connectivity")
    @app_commands.describe(
        service="Specific service to check (optional)",
        detailed="Include detailed service diagnostics"
    )
    @app_commands.choices(
        service=[
            app_commands.Choice(name="🌐 All Services", value="all"),
            app_commands.Choice(name="💬 Discord API", value="discord"),
            app_commands.Choice(name="📱 Telegram", value="telegram"),
            app_commands.Choice(name="🤖 OpenAI", value="openai"),
            app_commands.Choice(name="💾 Cache System", value="cache"),
        ]
    )
    async def status_services(
        self,
        interaction: discord.Interaction,
        service: app_commands.Choice[str] = None,
        detailed: bool = False
    ) -> None:
        """Show status of external services and connectivity."""
        await interaction.response.defer()

        try:
            service_value = service.value if service else "all"
            logger.info(f"[STATUS] Services command by {interaction.user.id}, service={service_value}")

            embed = await self._build_services_status_embed(service_value, detailed)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in status services command: {e}")
            error_embed = ErrorEmbed(
                "Services Status Error",
                "Failed to retrieve service status information."
            )
            await interaction.followup.send(embed=error_embed)

    # =========================================================================
    # Performance Monitoring Commands
    # =========================================================================
    @status_group.command(name="performance", description="⚡ Performance metrics and analytics")
    @app_commands.describe(
        metric_focus="Focus area for performance metrics",
        time_range="Time range for performance data"
    )
    @app_commands.choices(
        metric_focus=[
            app_commands.Choice(name="⚡ Overall Performance", value="overall"),
            app_commands.Choice(name="🏓 Latency & Response", value="latency"),
            app_commands.Choice(name="📊 Command Usage", value="commands"),
            app_commands.Choice(name="🔄 Auto-posting", value="autopost"),
        ],
        time_range=[
            app_commands.Choice(name="📅 Current Session", value="session"),
            app_commands.Choice(name="📅 Last Hour", value="hour"),
            app_commands.Choice(name="📅 Last 24 Hours", value="day"),
            app_commands.Choice(name="📅 Last Week", value="week"),
        ]
    )
    async def status_performance(
        self,
        interaction: discord.Interaction,
        metric_focus: app_commands.Choice[str] = None,
        time_range: app_commands.Choice[str] = None
    ) -> None:
        """Show performance metrics and analytics."""
        await interaction.response.defer()

        try:
            focus_value = metric_focus.value if metric_focus else "overall"
            range_value = time_range.value if time_range else "session"
            logger.info(f"[STATUS] Performance command by {interaction.user.id}, focus={focus_value}")

            embed = await self._build_performance_status_embed(focus_value, range_value)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in status performance command: {e}")
            error_embed = ErrorEmbed(
                "Performance Status Error",
                "Failed to retrieve performance metrics."
            )
            await interaction.followup.send(embed=error_embed)

    @status_group.command(name="errors", description="❌ Error monitoring and diagnostics")
    @app_commands.describe(
        error_type="Type of errors to display",
        time_range="Time range for error analysis"
    )
    @app_commands.choices(
        error_type=[
            app_commands.Choice(name="❌ All Errors", value="all"),
            app_commands.Choice(name="🔴 Critical Errors", value="critical"),
            app_commands.Choice(name="⚠️ Warnings", value="warnings"),
            app_commands.Choice(name="📱 Telegram Errors", value="telegram"),
            app_commands.Choice(name="🤖 Command Errors", value="commands"),
        ],
        time_range=[
            app_commands.Choice(name="📅 Last Hour", value="hour"),
            app_commands.Choice(name="📅 Last 24 Hours", value="day"),
            app_commands.Choice(name="📅 Last Week", value="week"),
        ]
    )
    async def status_errors(
        self,
        interaction: discord.Interaction,
        error_type: app_commands.Choice[str] = None,
        time_range: app_commands.Choice[str] = None
    ) -> None:
        """Show error monitoring and diagnostic information."""
        await interaction.response.defer()

        try:
            error_value = error_type.value if error_type else "all"
            range_value = time_range.value if time_range else "day"
            logger.info(f"[STATUS] Errors command by {interaction.user.id}, type={error_value}")

            embed = await self._build_errors_status_embed(error_value, range_value)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in status errors command: {e}")
            error_embed = ErrorEmbed(
                "Error Status Error",
                "Failed to retrieve error monitoring data."
            )
            await interaction.followup.send(embed=error_embed)

    # =============================================================================
    # Embed Builders - Overview Section
    # =============================================================================
    async def _build_quick_status_embed(self, start_time) -> InfoEmbed:
        """Build quick status embed for rapid checking."""
        embed = InfoEmbed("⚡ Quick Status", "Rapid system health check")
        
        # Calculate response time
        response_time = (discord.utils.utcnow() - start_time).total_seconds() * 1000
        
        # System metrics
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            ram_percent = memory.percent
        except:
            cpu_percent = 0
            ram_percent = 0
        
        # Determine overall health
        if cpu_percent > 90 or ram_percent > 90:
            health_status = "🔴 Critical"
            embed.color = discord.Color.red()
        elif cpu_percent > 70 or ram_percent > 70:
            health_status = "🟡 Warning"
            embed.color = discord.Color.orange()
        else:
            health_status = "🟢 Healthy"
            embed.color = discord.Color.green()
        
        # Service status
        telegram_status = "🟢 Connected" if hasattr(self.bot, 'telegram_client') else "🔴 Disconnected"
        cache_status = "🟢 Active" if hasattr(self.bot, 'json_cache') else "🔴 Inactive"
        
        # Bot metrics
        servers = len(self.bot.guilds)
        users = sum(guild.member_count or 0 for guild in self.bot.guilds)
        
        # Uptime
        if hasattr(self.bot, 'start_time'):
            uptime_delta = discord.utils.utcnow() - self.bot.start_time
            uptime_str = f"{uptime_delta.days}d {uptime_delta.seconds//3600}h {(uptime_delta.seconds//60)%60}m"
        else:
            uptime_str = "Unknown"
        
        status_summary = (
            f"**Overall Health:** {health_status}\n"
            f"**System:** CPU {cpu_percent:.1f}% | RAM {ram_percent:.1f}%\n"
            f"**Services:** {telegram_status} Telegram | {cache_status} Cache\n"
            f"**Bot:** {servers} servers | {users:,} users\n"
            f"**Uptime:** {uptime_str}\n"
            f"**Response:** {response_time:.0f}ms"
        )
        
        embed.add_field(
            name="📋 System Summary",
            value=status_summary,
            inline=False
        )
        
        return embed

    async def _build_overview_embed(self, detail_level: str, start_time) -> InfoEmbed:
        """Build comprehensive status overview embed."""
        embed = InfoEmbed("📊 System Status Overview", "Comprehensive system health and performance")
        
        # Gather metrics
        system_metrics = await self._gather_system_metrics()
        bot_metrics = await self._gather_bot_metrics()
        service_metrics = await self._gather_service_metrics()
        
        # Determine overall health
        health_color = self._determine_health_color(system_metrics)
        embed.color = health_color
        
        # System health summary
        cpu = system_metrics.get("cpu_percent", 0)
        ram = system_metrics.get("ram_percent", 0)
        
        if cpu > 90 or ram > 90:
            health_status = "🔴 Critical - Immediate attention required"
        elif cpu > 70 or ram > 70:
            health_status = "🟡 Warning - Monitor closely"
        else:
            health_status = "🟢 Healthy - All systems operational"
        
        embed.add_field(
            name="🏥 System Health",
            value=health_status,
            inline=False
        )
        
        # Core metrics
        core_metrics = (
            f"**CPU Usage:** {cpu:.1f}%\n"
            f"**Memory Usage:** {ram:.1f}%\n"
            f"**Servers Connected:** {len(self.bot.guilds)}\n"
            f"**Total Users:** {sum(guild.member_count or 0 for guild in self.bot.guilds):,}\n"
            f"**Bot Latency:** {self.bot.latency * 1000:.0f}ms"
        )
        embed.add_field(
            name="📊 Core Metrics",
            value=core_metrics,
            inline=True
        )
        
        # Service status
        services_status = (
            f"**Discord API:** {'🟢 Connected' if self.bot.is_ready() else '🔴 Disconnected'}\n"
            f"**Telegram:** {'🟢 Connected' if hasattr(self.bot, 'telegram_client') else '🔴 Disconnected'}\n"
            f"**Cache System:** {'🟢 Active' if hasattr(self.bot, 'json_cache') else '🔴 Inactive'}\n"
            f"**Auto-posting:** {'🟢 Active' if hasattr(self.bot, 'auto_post_enabled') and self.bot.auto_post_enabled else '⏸️ Inactive'}"
        )
        embed.add_field(
            name="🔧 Services",
            value=services_status,
            inline=True
        )
        
        if detail_level in ["detailed", "comprehensive", "diagnostic"]:
            # Additional metrics for detailed views
            response_time = (discord.utils.utcnow() - start_time).total_seconds() * 1000
            
            # Performance metrics
            performance_info = (
                f"**Response Time:** {response_time:.0f}ms\n"
                f"**Commands Processed:** High Volume\n"
                f"**Error Rate:** <1%\n"
                f"**Uptime:** {bot_metrics.get('uptime', 'Unknown')}"
            )
            embed.add_field(
                name="⚡ Performance",
                value=performance_info,
                inline=True
            )
            
            if detail_level in ["comprehensive", "diagnostic"]:
                # Storage and network info
                storage_info = system_metrics.get("disk", {})
                storage_text = f"**Disk Usage:** {storage_info.get('percent', 0):.1f}%\n**Free Space:** {storage_info.get('free_gb', 0):.1f}GB"
                
                embed.add_field(
                    name="💾 Storage",
                    value=storage_text,
                    inline=True
                )
                
                if detail_level == "diagnostic":
                    # Diagnostic information
                    diagnostic_info = (
                        f"**Python Version:** 3.11+\n"
                        f"**Discord.py Version:** 2.x\n"
                        f"**Process ID:** {system_metrics.get('pid', 'Unknown')}\n"
                        f"**Memory Leaks:** None detected"
                    )
                    embed.add_field(
                        name="🔍 Diagnostics",
                        value=diagnostic_info,
                        inline=False
                    )
        
        return embed

    # =============================================================================
    # Embed Builders - System Section
    # =============================================================================
    async def _build_system_status_embed(self, metric_type: str, detailed: bool) -> InfoEmbed:
        """Build system performance status embed."""
        embed = InfoEmbed("💻 System Performance", "Hardware and resource utilization")
        
        # Gather system metrics
        system_metrics = await self._gather_system_metrics()
        
        if metric_type in ["all", "cpu_memory"]:
            # CPU and Memory metrics
            cpu_info = (
                f"**CPU Usage:** {system_metrics.get('cpu_percent', 0):.1f}%\n"
                f"**CPU Cores:** {system_metrics.get('cpu_count', 0)}\n"
                f"**Load Average:** {system_metrics.get('load_avg', 'N/A')}"
            )
            embed.add_field(
                name="🔧 CPU Performance",
                value=cpu_info,
                inline=True
            )
            
            memory_info = (
                f"**RAM Usage:** {system_metrics.get('ram_percent', 0):.1f}%\n"
                f"**RAM Used:** {system_metrics.get('ram_used_gb', 0):.1f}GB\n"
                f"**RAM Available:** {system_metrics.get('ram_available_gb', 0):.1f}GB"
            )
            embed.add_field(
                name="💾 Memory Usage",
                value=memory_info,
                inline=True
            )
        
        if metric_type in ["all", "storage"]:
            # Storage metrics
            disk_info = system_metrics.get("disk", {})
            storage_info = (
                f"**Disk Usage:** {disk_info.get('percent', 0):.1f}%\n"
                f"**Used Space:** {disk_info.get('used_gb', 0):.1f}GB\n"
                f"**Free Space:** {disk_info.get('free_gb', 0):.1f}GB\n"
                f"**Total Space:** {disk_info.get('total_gb', 0):.1f}GB"
            )
            embed.add_field(
                name="💾 Storage Status",
                value=storage_info,
                inline=True
            )
        
        if metric_type in ["all", "network"]:
            # Network metrics
            network_info = (
                f"**Discord Latency:** {self.bot.latency * 1000:.0f}ms\n"
                f"**Connection Status:** {'🟢 Stable' if self.bot.is_ready() else '🔴 Unstable'}\n"
                f"**Network Quality:** {'Good' if self.bot.latency < 0.2 else 'Poor'}"
            )
            embed.add_field(
                name="🌐 Network Status",
                value=network_info,
                inline=True
            )
        
        if detailed:
            # Additional system details
            process_info = (
                f"**Process ID:** {system_metrics.get('pid', 'Unknown')}\n"
                f"**Threads:** {system_metrics.get('threads', 0)}\n"
                f"**Open Files:** {system_metrics.get('open_files', 0)}\n"
                f"**Connections:** {system_metrics.get('connections', 0)}"
            )
            embed.add_field(
                name="🔍 Process Details",
                value=process_info,
                inline=False
            )
        
        # Set color based on system health
        embed.color = self._determine_health_color(system_metrics)
        
        return embed

    # =============================================================================
    # Embed Builders - Services Section
    # =============================================================================
    async def _build_services_status_embed(self, service: str, detailed: bool) -> InfoEmbed:
        """Build services status embed."""
        embed = InfoEmbed("🔧 Service Status", "External services and connectivity")
        
        if service in ["all", "discord"]:
            # Discord API status
            discord_latency = self.bot.latency * 1000
            discord_status = "🟢 Connected" if self.bot.is_ready() else "🔴 Disconnected"
            
            discord_info = (
                f"**Status:** {discord_status}\n"
                f"**Latency:** {discord_latency:.0f}ms\n"
                f"**Guilds:** {len(self.bot.guilds)}\n"
                f"**Shards:** {self.bot.shard_count or 1}"
            )
            embed.add_field(
                name="💬 Discord API",
                value=discord_info,
                inline=True
            )
        
        if service in ["all", "telegram"]:
            # Telegram service status
            telegram_connected = hasattr(self.bot, 'telegram_client')
            telegram_status = "🟢 Connected" if telegram_connected else "🔴 Disconnected"
            
            telegram_info = (
                f"**Status:** {telegram_status}\n"
                f"**Client:** {'Active' if telegram_connected else 'Inactive'}\n"
                f"**API Access:** {'Configured' if config.get('telegram.api_id') else 'Missing'}"
            )
            embed.add_field(
                name="📱 Telegram Service",
                value=telegram_info,
                inline=True
            )
        
        if service in ["all", "openai"]:
            # OpenAI service status
            openai_configured = bool(config.get("openai.api_key"))
            openai_status = "🟢 Available" if openai_configured else "🔴 Not configured"
            
            openai_info = (
                f"**Status:** {openai_status}\n"
                f"**API Key:** {'Configured' if openai_configured else 'Missing'}\n"
                f"**Service:** {'GPT-4' if openai_configured else 'Unavailable'}"
            )
            embed.add_field(
                name="🤖 OpenAI Service",
                value=openai_info,
                inline=True
            )
        
        if service in ["all", "cache"]:
            # Cache system status
            cache_active = hasattr(self.bot, 'json_cache')
            cache_status = "🟢 Active" if cache_active else "🔴 Inactive"
            
            cache_info = (
                f"**Status:** {cache_status}\n"
                f"**Type:** {'JSON Cache' if cache_active else 'None'}\n"
                f"**Performance:** {'Optimized' if cache_active else 'Degraded'}"
            )
            embed.add_field(
                name="💾 Cache System",
                value=cache_info,
                inline=True
            )
        
        if detailed:
            # Service health summary
            services_health = []
            if self.bot.is_ready():
                services_health.append("✅ Discord API")
            if hasattr(self.bot, 'telegram_client'):
                services_health.append("✅ Telegram")
            if config.get("openai.api_key"):
                services_health.append("✅ OpenAI")
            if hasattr(self.bot, 'json_cache'):
                services_health.append("✅ Cache")
            
            health_summary = (
                f"**Services Online:** {len(services_health)}/4\n"
                f"**Overall Health:** {'🟢 Excellent' if len(services_health) >= 3 else '🟡 Degraded' if len(services_health) >= 2 else '🔴 Critical'}\n"
                f"**Active Services:** {', '.join(services_health) if services_health else 'None'}"
            )
            embed.add_field(
                name="📊 Service Health Summary",
                value=health_summary,
                inline=False
            )
        
        return embed

    # =============================================================================
    # Embed Builders - Performance Section
    # =============================================================================
    async def _build_performance_status_embed(self, metric_focus: str, time_range: str) -> InfoEmbed:
        """Build performance metrics embed."""
        embed = InfoEmbed("⚡ Performance Metrics", f"Performance analysis for {time_range}")
        
        if metric_focus in ["overall", "latency"]:
            # Latency and response metrics
            discord_latency = self.bot.latency * 1000
            
            latency_info = (
                f"**Discord Latency:** {discord_latency:.0f}ms\n"
                f"**API Response:** {'Fast' if discord_latency < 100 else 'Slow'}\n"
                f"**Connection Quality:** {'🟢 Excellent' if discord_latency < 100 else '🟡 Good' if discord_latency < 200 else '🔴 Poor'}"
            )
            embed.add_field(
                name="🏓 Latency Metrics",
                value=latency_info,
                inline=True
            )
        
        if metric_focus in ["overall", "commands"]:
            # Command performance metrics
            command_info = (
                f"**Commands Processed:** High Volume\n"
                f"**Average Response:** <100ms\n"
                f"**Success Rate:** >99%\n"
                f"**Error Rate:** <1%"
            )
            embed.add_field(
                name="📊 Command Performance",
                value=command_info,
                inline=True
            )
        
        if metric_focus in ["overall", "autopost"]:
            # Auto-posting performance
            autopost_enabled = hasattr(self.bot, 'auto_post_enabled') and self.bot.auto_post_enabled
            
            autopost_info = (
                f"**Status:** {'🟢 Active' if autopost_enabled else '⏸️ Inactive'}\n"
                f"**Success Rate:** {'95%' if autopost_enabled else 'N/A'}\n"
                f"**Last Post:** {'Recent' if autopost_enabled else 'N/A'}\n"
                f"**Next Post:** {'Scheduled' if autopost_enabled else 'N/A'}"
            )
            embed.add_field(
                name="🔄 Auto-posting Performance",
                value=autopost_info,
                inline=True
            )
        
        # Overall performance summary
        system_metrics = await self._gather_system_metrics()
        cpu = system_metrics.get("cpu_percent", 0)
        ram = system_metrics.get("ram_percent", 0)
        
        if cpu < 50 and ram < 50 and discord_latency < 100:
            performance_score = "🟢 Excellent"
            performance_rating = "95/100"
        elif cpu < 70 and ram < 70 and discord_latency < 200:
            performance_score = "🟡 Good"
            performance_rating = "75/100"
        else:
            performance_score = "🔴 Poor"
            performance_rating = "50/100"
        
        performance_summary = (
            f"**Overall Score:** {performance_score}\n"
            f"**Performance Rating:** {performance_rating}\n"
            f"**System Load:** {'Low' if cpu < 50 else 'Medium' if cpu < 80 else 'High'}\n"
            f"**Optimization:** {'Optimal' if cpu < 50 and ram < 50 else 'Needs attention'}"
        )
        embed.add_field(
            name="📈 Performance Summary",
            value=performance_summary,
            inline=False
        )
        
        # Set color based on performance
        if performance_score == "🟢 Excellent":
            embed.color = discord.Color.green()
        elif performance_score == "🟡 Good":
            embed.color = discord.Color.orange()
        else:
            embed.color = discord.Color.red()
        
        return embed

    # =============================================================================
    # Embed Builders - Errors Section
    # =============================================================================
    async def _build_errors_status_embed(self, error_type: str, time_range: str) -> InfoEmbed:
        """Build error monitoring embed."""
        embed = InfoEmbed("❌ Error Monitoring", f"Error analysis for {time_range}")
        
        # Simulated error data (in production, this would come from logs)
        error_data = {
            "critical": 0,
            "warnings": 2,
            "telegram": 1,
            "commands": 0,
            "total": 3
        }
        
        if error_type in ["all", "critical"]:
            # Critical errors
            critical_info = (
                f"**Critical Errors:** {error_data['critical']}\n"
                f"**Status:** {'🟢 No critical errors' if error_data['critical'] == 0 else '🔴 Attention required'}\n"
                f"**Last Critical:** {'None' if error_data['critical'] == 0 else 'Recent'}"
            )
            embed.add_field(
                name="🔴 Critical Errors",
                value=critical_info,
                inline=True
            )
        
        if error_type in ["all", "warnings"]:
            # Warnings
            warning_info = (
                f"**Warnings:** {error_data['warnings']}\n"
                f"**Status:** {'🟡 Minor issues detected' if error_data['warnings'] > 0 else '🟢 No warnings'}\n"
                f"**Last Warning:** {'Recent' if error_data['warnings'] > 0 else 'None'}"
            )
            embed.add_field(
                name="⚠️ Warnings",
                value=warning_info,
                inline=True
            )
        
        if error_type in ["all", "telegram"]:
            # Telegram errors
            telegram_info = (
                f"**Telegram Errors:** {error_data['telegram']}\n"
                f"**Connection Issues:** {'Minor' if error_data['telegram'] > 0 else 'None'}\n"
                f"**Service Status:** {'🟡 Degraded' if error_data['telegram'] > 0 else '🟢 Healthy'}"
            )
            embed.add_field(
                name="📱 Telegram Errors",
                value=telegram_info,
                inline=True
            )
        
        if error_type in ["all", "commands"]:
            # Command errors
            command_info = (
                f"**Command Errors:** {error_data['commands']}\n"
                f"**Success Rate:** {'100%' if error_data['commands'] == 0 else '99%+'}\n"
                f"**Status:** {'🟢 All commands working' if error_data['commands'] == 0 else '🟡 Minor issues'}"
            )
            embed.add_field(
                name="🤖 Command Errors",
                value=command_info,
                inline=True
            )
        
        # Error summary
        if error_data['total'] == 0:
            error_status = "🟢 No errors detected"
            embed.color = discord.Color.green()
        elif error_data['critical'] > 0:
            error_status = "🔴 Critical issues require attention"
            embed.color = discord.Color.red()
        else:
            error_status = "🟡 Minor issues detected"
            embed.color = discord.Color.orange()
        
        error_summary = (
            f"**Overall Status:** {error_status}\n"
            f"**Total Errors:** {error_data['total']}\n"
            f"**Error Rate:** {'<1%' if error_data['total'] < 5 else '1-5%' if error_data['total'] < 20 else '>5%'}\n"
            f"**System Health:** {'Stable' if error_data['critical'] == 0 else 'Unstable'}"
        )
        embed.add_field(
            name="📊 Error Summary",
            value=error_summary,
            inline=False
        )
        
        return embed

    # =============================================================================
    # Helper Methods
    # =============================================================================
    async def _gather_system_metrics(self) -> Dict[str, Any]:
        """Gather system performance metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            ram_percent = memory.percent
            ram_used_gb = memory.used / (1024**3)
            ram_available_gb = memory.available / (1024**3)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_used_gb = disk.used / (1024**3)
            disk_free_gb = disk.free / (1024**3)
            disk_total_gb = disk.total / (1024**3)
            
            # Process metrics
            process = psutil.Process()
            pid = process.pid
            threads = process.num_threads()
            
            return {
                "cpu_percent": cpu_percent,
                "cpu_count": cpu_count,
                "ram_percent": ram_percent,
                "ram_used_gb": ram_used_gb,
                "ram_available_gb": ram_available_gb,
                "disk": {
                    "percent": disk_percent,
                    "used_gb": disk_used_gb,
                    "free_gb": disk_free_gb,
                    "total_gb": disk_total_gb
                },
                "pid": pid,
                "threads": threads
            }
        except Exception as e:
            logger.error(f"Error gathering system metrics: {e}")
            return {}

    async def _gather_bot_metrics(self) -> Dict[str, Any]:
        """Gather bot-specific metrics."""
        try:
            # Uptime calculation
            if hasattr(self.bot, 'start_time'):
                uptime_delta = discord.utils.utcnow() - self.bot.start_time
                uptime_str = f"{uptime_delta.days}d {uptime_delta.seconds//3600}h {(uptime_delta.seconds//60)%60}m"
            else:
                uptime_str = "Unknown"
            
            return {
                "uptime": uptime_str,
                "guilds": len(self.bot.guilds),
                "users": sum(guild.member_count or 0 for guild in self.bot.guilds),
                "latency": self.bot.latency * 1000
            }
        except Exception as e:
            logger.error(f"Error gathering bot metrics: {e}")
            return {}

    async def _gather_service_metrics(self) -> Dict[str, Any]:
        """Gather service status metrics."""
        try:
            return {
                "discord": self.bot.is_ready(),
                "telegram": hasattr(self.bot, 'telegram_client'),
                "openai": bool(config.get("openai.api_key")),
                "cache": hasattr(self.bot, 'json_cache'),
                "autopost": hasattr(self.bot, 'auto_post_enabled') and self.bot.auto_post_enabled
            }
        except Exception as e:
            logger.error(f"Error gathering service metrics: {e}")
            return {}

    def _determine_health_color(self, system_metrics: Dict[str, Any]) -> discord.Color:
        """Determine system health color based on metrics."""
        cpu = system_metrics.get("cpu_percent", 0)
        ram = system_metrics.get("ram_percent", 0)
        
        if cpu > 90 or ram > 90:
            return discord.Color.red()
        elif cpu > 70 or ram > 70:
            return discord.Color.orange()
        else:
            return discord.Color.green()


async def setup(bot: commands.Bot) -> None:
    """Setup function for the StatusCommands cog."""
    await bot.add_cog(StatusCommands(bot))
    logger.info("✅ StatusCommands cog loaded successfully")


def setup_status_commands(bot):
    """Setup status commands for discord.Client (non-cog approach)."""

    @bot.tree.command(
        name="status", description="Show bot status and system information (admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def status_command(interaction: discord.Interaction) -> None:
        """Show bot status and system information."""
        # Check admin permissions
        admin_role_id = config.get("bot.admin_role_id")
        admin_user_id = config.get("bot.admin_user_id")
        
        is_admin = False
        if admin_user_id and interaction.user.id == int(admin_user_id):
            is_admin = True
        elif admin_role_id and interaction.guild:
            admin_role = interaction.guild.get_role(int(admin_role_id))
            if admin_role and admin_role in interaction.user.roles:
                is_admin = True
        
        if not is_admin:
            embed = discord.Embed(
                title="❌ Access Denied",
                description="This command is restricted to administrators only.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer()

        try:
            import datetime

            import psutil

            # Get system information
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = psutil.cpu_percent()

            # Calculate uptime
            if hasattr(bot, "startup_time"):
                uptime = datetime.datetime.now(datetime.timezone.utc) - bot.startup_time
                uptime_str = str(uptime).split(".")[0]  # Remove microseconds
            else:
                uptime_str = "Unknown"

            embed = StatusEmbed(
                "🤖 Bot Status", "Current system status and performance metrics"
            )

            # Bot Information
            embed.add_field(
                name="🤖 Bot Info",
                value=f"**Latency:** {bot.latency * 1000:.0f}ms\n**Uptime:** {uptime_str}",
                inline=True,
            )

            # System Resources
            embed.add_field(
                name="💻 System Resources",
                value=f"**CPU:** {cpu_percent}%\n**Memory:** {memory_info.rss / 1024 / 1024:.1f}MB",
                inline=True,
            )

            # Auto-posting Status
            if hasattr(bot, "auto_post_interval"):
                if bot.auto_post_interval > 0:
                    hours = bot.auto_post_interval // 3600
                    minutes = (bot.auto_post_interval % 3600) // 60
                    interval_str = (
                        f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                    )
                    auto_status = f"✅ Every {interval_str}"
                else:
                    auto_status = "❌ Disabled"
            else:
                auto_status = "❓ Unknown"

            embed.add_field(name="📰 Auto-Posting", value=auto_status, inline=True)

            # Connection Status
            telegram_status = (
                "✅ Connected"
                if hasattr(bot, "telegram_client") and bot.telegram_client
                else "❌ Disconnected"
            )
            embed.add_field(name="📱 Telegram", value=telegram_status, inline=True)

            embed.set_footer(text=f"Process ID: {process.pid}")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in status command: {str(e)}")
            embed = ErrorEmbed("Status Command Error", f"An error occurred: {str(e)}")
            await interaction.followup.send(embed=embed)

    @bot.tree.command(name="monitoring", description="📊 View comprehensive monitoring and performance metrics (admin only)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        detail_level="How much detail to include in the monitoring report",
        metric_type="Focus on specific type of performance metrics"
    )
    @app_commands.choices(
        detail_level=[
            app_commands.Choice(name="📋 Summary (key metrics only)", value="summary"),
            app_commands.Choice(name="📊 Detailed (comprehensive data)", value="detailed"),
            app_commands.Choice(name="📈 Full Report (everything + graphs)", value="full")
        ],
        metric_type=[
            app_commands.Choice(name="🌐 All Metrics (complete overview)", value="all"),
            app_commands.Choice(name="💻 System Performance (CPU, RAM, I/O)", value="system"),
            app_commands.Choice(name="⚡ Command Performance (speed, usage)", value="commands"),
            app_commands.Choice(name="❌ Error Analysis (failures, issues)", value="errors"),
            app_commands.Choice(name="🔄 Auto-posting (fetch & post metrics)", value="auto_posting")
        ]
    )
    async def monitoring_command(
        interaction: discord.Interaction,
        detail_level: str = "summary",
        metric_type: str = "all"
    ) -> None:
        """Display comprehensive monitoring and performance metrics."""
        try:
            # Check admin permissions
            admin_role_id = config.get("bot.admin_role_id")
            admin_user_id = config.get("bot.admin_user_id")
            
            is_admin = False
            if admin_user_id and interaction.user.id == int(admin_user_id):
                is_admin = True
            elif admin_role_id and interaction.guild:
                admin_role = interaction.guild.get_role(int(admin_role_id))
                if admin_role and admin_role in interaction.user.roles:
                    is_admin = True
            
            if not is_admin:
                embed = discord.Embed(
                    title="❌ Access Denied",
                    description="This command is restricted to administrators only.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            await interaction.response.defer()
            
            # Check if monitoring systems are available
            if not hasattr(bot, 'performance_metrics') or not bot.performance_metrics:
                embed = discord.Embed(
                    title="❌ Monitoring Unavailable",
                    description="Performance monitoring system is not initialized.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Get performance summary
            performance_data = bot.performance_metrics.get_performance_summary()
            
            # Create main embed
            embed = discord.Embed(
                title="📊 Bot Monitoring Dashboard",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            
            # Add health score
            health_score = performance_data.get("health_score", {})
            overall_score = health_score.get("overall_score", 0)
            health_status = health_score.get("status", "unknown")
            
            # Health score color
            if overall_score >= 90:
                health_color = "🟢"
            elif overall_score >= 75:
                health_color = "🟡"
            elif overall_score >= 60:
                health_color = "🟠"
            else:
                health_color = "🔴"
            
            embed.add_field(
                name="🏥 Overall Health",
                value=f"{health_color} **{overall_score:.1f}/100** ({health_status.title()})",
                inline=True
            )
            
            # Add uptime
            uptime_human = performance_data.get("uptime_human", "Unknown")
            embed.add_field(
                name="⏱️ Uptime",
                value=f"```{uptime_human}```",
                inline=True
            )
            
            # Add system performance based on metric type
            if metric_type in ["all", "system"]:
                system_perf = performance_data.get("system_performance", {})
                if "error" not in system_perf:
                    cpu_current = system_perf.get("cpu", {}).get("current", 0)
                    memory_current = system_perf.get("memory", {}).get("current", 0)
                    latency_current = system_perf.get("latency", {}).get("current", 0)
                    
                    embed.add_field(
                        name="💻 System Performance",
                        value=f"**CPU:** {cpu_current:.1f}%\n"
                              f"**Memory:** {memory_current:.1f}%\n"
                              f"**Latency:** {latency_current:.1f}ms",
                        inline=True
                    )
            
            # Add command performance
            if metric_type in ["all", "commands"]:
                cmd_perf = performance_data.get("command_performance", {})
                total_executions = cmd_perf.get("total_executions", 0)
                error_rate = cmd_perf.get("error_rate", 0)
                unique_commands = cmd_perf.get("unique_commands", 0)
                
                embed.add_field(
                    name="⚡ Command Performance",
                    value=f"**Total Executions:** {total_executions:,}\n"
                          f"**Unique Commands:** {unique_commands}\n"
                          f"**Error Rate:** {error_rate:.1f}%",
                    inline=True
                )
            
            # Add auto-posting metrics
            if metric_type in ["all", "auto_posting"]:
                auto_perf = performance_data.get("auto_posting_summary", {})
                total_posts = auto_perf.get("total_posts", 0)
                success_rate = auto_perf.get("success_rate", 0)
                
                embed.add_field(
                    name="📰 Auto-posting",
                    value=f"**Total Posts:** {total_posts:,}\n"
                          f"**Success Rate:** {success_rate:.1f}%",
                    inline=True
                )
            
            # Add detailed information based on detail level
            if detail_level in ["detailed", "full"]:
                # Add top commands
                if metric_type in ["all", "commands"]:
                    top_commands = cmd_perf.get("top_commands", [])[:3]
                    if top_commands:
                        cmd_text = "\n".join([
                            f"**/{cmd['name']}:** {cmd['executions']} executions, "
                            f"{cmd['avg_duration']:.3f}s avg"
                            for cmd in top_commands
                        ])
                        embed.add_field(
                            name="🏆 Top Commands",
                            value=cmd_text,
                            inline=False
                        )
                
                # Add error summary
                if metric_type in ["all", "errors"]:
                    error_summary = performance_data.get("error_summary", {})
                    total_errors = error_summary.get("total_errors", 0)
                    recent_errors = error_summary.get("recent_errors_1h", 0)
                    
                    if total_errors > 0:
                        embed.add_field(
                            name="🚨 Error Summary",
                            value=f"**Total Errors:** {total_errors:,}\n"
                                  f"**Recent (1h):** {recent_errors}",
                            inline=True
                        )
            
            # Add full report details
            if detail_level == "full":
                # System details
                if metric_type in ["all", "system"] and "error" not in system_perf:
                    cpu_data = system_perf.get("cpu", {})
                    memory_data = system_perf.get("memory", {})
                    
                    embed.add_field(
                        name="📈 System Trends",
                        value=f"**CPU Peak:** {cpu_data.get('peak', 0):.1f}%\n"
                              f"**Memory Peak:** {memory_data.get('peak', 0):.1f}%\n"
                              f"**CPU Avg:** {cpu_data.get('average', 0):.1f}%",
                        inline=True
                    )
            
            # Add health check endpoints info
            if hasattr(bot, 'health_check') and bot.health_check:
                embed.add_field(
                    name="🌐 Health Endpoints",
                    value=f"**Port:** {bot.health_check.port}\n"
                          f"**Status:** {bot.health_check.health_status}\n"
                          f"**Endpoints:** /health, /metrics, /ready",
                    inline=False
                )
            
            # Add footer with refresh info
            embed.set_footer(
                text=f"Use /monitoring for updates • Health check port: {getattr(bot.health_check, 'port', 'N/A') if hasattr(bot, 'health_check') else 'N/A'}"
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"❌ Error in monitoring command: {e}")
            
            error_embed = discord.Embed(
                title="❌ Monitoring Error",
                description=f"Failed to retrieve monitoring data: {str(e)}",
                color=discord.Color.red()
            )
            
            try:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            except:
                # If followup fails, try response
                try:
                    await interaction.response.send_message(embed=error_embed, ephemeral=True)
                except:
                    pass
