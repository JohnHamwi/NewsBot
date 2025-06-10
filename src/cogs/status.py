"""
Status Commands Cog

This cog provides status and monitoring commands for NewsBot.
"""

import traceback
from typing import Dict, Any

import psutil
import discord
from discord import app_commands
from discord.ext import commands

from src.core.config_manager import config
from src.utils.base_logger import base_logger as logger
from src.utils.structured_logger import structured_logger
from src.components.decorators.admin_required import admin_required
from src.components.embeds.base_embed import StatusEmbed, ErrorEmbed

# Configuration constants
GUILD_ID = config.get('bot.guild_id') or 0
ADMIN_ROLE_ID = config.get('bot.admin_role_id')


class StatusCommands(commands.Cog):
    """
    Cog for status and monitoring commands.

    Provides comprehensive system monitoring, bot status information,
    and performance metrics for the NewsBot.
    """

    def __init__(self, bot: discord.Client) -> None:
        """Initialize the StatusCommands cog."""
        self.bot = bot
        logger.debug("🔧 StatusCommands cog initialized")

    @app_commands.command(name="status", description="Show detailed bot status (admin only)")
    @app_commands.describe(
        view="Choose what information to display",
        details="Show additional technical details",
        compact="Use a more compact display format"
    )
    @app_commands.choices(view=[
        app_commands.Choice(name="All", value="all"),
        app_commands.Choice(name="System", value="system"),
        app_commands.Choice(name="Bot", value="bot"),
        app_commands.Choice(name="Cache", value="cache"),
        app_commands.Choice(name="Performance", value="performance"),
        app_commands.Choice(name="Errors", value="errors"),
        app_commands.Choice(name="Services", value="services"),
    ])
    @admin_required
    async def status_command(
        self,
        interaction: discord.Interaction,
        view: app_commands.Choice[str] = None,
        details: bool = False,
        compact: bool = False
    ) -> None:
        """
        Show detailed bot status and system information (admin only).

        Args:
            interaction: The Discord interaction
            view: Choose what information to display
            details: Show additional technical details
            compact: Use a more compact display format
        """
        try:
            view_value = view.value if view else "all"

            logger.info(
                f"[STATUS][CMD] Status command invoked by user {interaction.user.id}, "
                f"view={view_value}, details={details}, compact={compact}"
            )

            # Gather metrics based on selected view
            metric_data = await self._gather_metrics(view_value)

            # Determine health status and create embed
            color = self._determine_health_color(metric_data)
            embed = await self._build_status_embed(metric_data, view_value, details, compact, color)

            # Send response
            try:
                await interaction.followup.send(embed=embed)
            except discord.errors.NotFound:
                structured_logger.warning("Could not send response, interaction expired")

            logger.info(f"[STATUS][CMD] Status command completed successfully for user {interaction.user.id}")

        except Exception as e:
            structured_logger.error(
                "Error executing status command",
                extra_data={"error": str(e), "traceback": traceback.format_exc()}
            )

            error_embed = ErrorEmbed(
                "Status Command Error",
                f"An error occurred: {str(e)}"
            )

            try:
                await interaction.followup.send(embed=error_embed)
            except discord.errors.NotFound:
                structured_logger.warning("Could not send error response")

    async def _gather_metrics(self, view: str) -> Dict[str, Any]:
        """Gather metrics based on the requested view."""
        metric_data = {}

        # Always gather basic metrics
        metric_data['system'] = await self._gather_system_metrics()
        metric_data['bot'] = await self._gather_bot_metrics()

        # Gather additional metrics based on view
        if view in ["all", "cache"]:
            metric_data['cache'] = await self._gather_cache_metrics()

        if view in ["all", "services"]:
            metric_data['circuit_breakers'] = await self._gather_circuit_breaker_metrics()
            metric_data['presence'] = await self._gather_presence_metrics()
            metric_data['telegram'] = await self._gather_telegram_metrics()

        if view in ["all", "errors"]:
            metric_data['errors'] = await self._gather_error_metrics()

        if view in ["all", "performance"]:
            metric_data['performance'] = await self._gather_performance_metrics()

        return metric_data

    def _determine_health_color(self, metric_data: Dict[str, Any]) -> discord.Color:
        """Determine the health status color based on metrics."""
        color = discord.Color.green()

        # Check system metrics
        if "system" in metric_data:
            system_metrics = metric_data["system"]
            cpu = system_metrics.get('cpu', 0)
            ram_percent = system_metrics.get('ram_percent', 0)

            if cpu > 90 or ram_percent > 90:
                color = discord.Color.red()
            elif cpu > 70 or ram_percent > 70:
                color = discord.Color.orange()

        # Check for Telegram auth issues
        if "telegram" in metric_data and not metric_data["telegram"].get('connected', True):
            color = discord.Color.orange()

        return color

    async def _build_status_embed(
        self,
        metric_data: dict,
        view: str,
        details: bool,
        compact: bool,
        color: discord.Color
    ) -> StatusEmbed:
        """Build the status embed using the new StatusEmbed class."""

        # Create status embed
        embed = StatusEmbed("📊 NewsBot Status")
        embed.color = color

        # Telegram status directly at the top
        telegram_status = "Connected" if hasattr(
            self.bot, "telegram_client") and self.bot.telegram_client.is_connected() else "Disconnected"
        status_emoji = "✅" if telegram_status == "Connected" else "❌"
        embed.add_field(
            name="📱 Telegram Connection Status",
            value=f"{status_emoji} {telegram_status}",
            inline=False
        )

        # Add metrics based on view
        if view in ["all", "system"] and "system" in metric_data:
            system_data = metric_data["system"]
            embed.add_metric("💻 CPU Usage", f"{system_data.get('cpu', 0):.1f}", "%")
            embed.add_metric("🧠 RAM Usage", f"{system_data.get('ram_percent', 0):.1f}", "%")
            embed.add_metric("💾 RAM Used", f"{system_data.get('ram_used_gb', 0):.1f}", " GB")

            if details:
                embed.add_metric("🔧 Threads", system_data.get('threads', 0))
                embed.add_metric("📁 Open Files", system_data.get('open_files', 0))

        if view in ["all", "bot"] and "bot" in metric_data:
            bot_data = metric_data["bot"]
            embed.add_metric("⏱️ Uptime", bot_data.get('uptime', 'Unknown'))
            embed.add_metric("📡 Latency", f"{bot_data.get('latency_ms', 0):.0f}", " ms")
            embed.add_metric("🏰 Guilds", bot_data.get('guild_count', 0))
            embed.add_metric("👥 Users", bot_data.get('user_count', 0))

        if view in ["all", "cache"] and "cache" in metric_data:
            cache_data = metric_data["cache"]
            embed.add_metric("📰 Active Channels", cache_data.get('active_channels', 0))
            embed.add_metric("🚫 Deactivated Channels", cache_data.get('deactivated_channels', 0))
            embed.add_metric("📝 Recent Posts", cache_data.get('recent_posts', 0))

        if view in ["all", "performance"] and "performance" in metric_data:
            perf_data = metric_data["performance"]
            embed.add_metric("⚡ Commands/min", f"{perf_data.get('commands_per_minute', 0):.1f}")
            embed.add_metric("📊 Success Rate", f"{perf_data.get('success_rate', 0):.1f}", "%")

        if view in ["all", "errors"] and "errors" in metric_data:
            error_data = metric_data["errors"]
            embed.add_metric("❌ Errors (24h)", error_data.get('error_count_24h', 0))
            embed.add_metric("⚠️ Warnings (24h)", error_data.get('warning_count_24h', 0))

        # Add description based on view
        embed.description = self._get_status_description(view, compact)

        return embed

    def _get_status_description(self, view: str, compact: bool) -> str:
        """Get status description based on view and format."""
        if compact:
            return f"Showing {view} metrics in compact format."

        descriptions = {
            "all": "Complete system overview with all available metrics.",
            "system": "System resource usage and performance metrics.",
            "bot": "Discord bot connection and activity metrics.",
            "cache": "Data cache status and channel information.",
            "performance": "Command execution and success rate metrics.",
            "errors": "Error tracking and system health indicators.",
            "services": "External service connections and circuit breaker status."
        }

        return descriptions.get(view, "System status information.")

    async def _gather_system_metrics(self):
        """Gather system performance metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            process = psutil.Process()

            return {
                'cpu': cpu_percent,
                'ram_percent': memory.percent,
                'ram_used_gb': memory.used / (1024**3),
                'ram_total_gb': memory.total / (1024**3),
                'threads': process.num_threads(),
                'open_files': len(process.open_files()) if hasattr(process, 'open_files') else 0,
            }
        except Exception as e:
            logger.error(f"Error gathering system metrics: {e}")
            return {}

    async def _gather_bot_metrics(self):
        """Gather Discord bot metrics."""
        try:
            uptime = discord.utils.utcnow() - self.bot.startup_time if hasattr(self.bot, 'startup_time') else None
            uptime_str = str(uptime).split('.')[0] if uptime else "Unknown"

            return {
                'uptime': uptime_str,
                'latency_ms': self.bot.latency * 1000,
                'guild_count': len(self.bot.guilds),
                'user_count': sum(guild.member_count or 0 for guild in self.bot.guilds),
            }
        except Exception as e:
            logger.error(f"Error gathering bot metrics: {e}")
            return {}

    async def _gather_cache_metrics(self):
        """Gather cache and data metrics."""
        try:
            cache = self.bot.json_cache
            active_channels = await cache.list_telegram_channels("activated")
            deactivated_channels = await cache.list_telegram_channels("deactivated")

            return {
                'active_channels': len(active_channels),
                'deactivated_channels': len(deactivated_channels),
                'recent_posts': 0,  # Could be enhanced to track recent posts
            }
        except Exception as e:
            logger.error(f"Error gathering cache metrics: {e}")
            return {}

    async def _gather_circuit_breaker_metrics(self):
        """Gather circuit breaker status."""
        try:
            if hasattr(self.bot, 'circuit_breakers'):
                return {name: cb.state for name, cb in self.bot.circuit_breakers.items()}
            return {}
        except Exception as e:
            logger.error(f"Error gathering circuit breaker metrics: {e}")
            return {}

    async def _gather_presence_metrics(self):
        """Gather rich presence metrics."""
        try:
            return {
                'mode': getattr(self.bot, 'rich_presence_mode', 'unknown'),
                'status': str(self.bot.status) if hasattr(self.bot, 'status') else 'unknown',
            }
        except Exception as e:
            logger.error(f"Error gathering presence metrics: {e}")
            return {}

    async def _gather_error_metrics(self):
        """Gather error tracking metrics."""
        try:
            # This could be enhanced with actual error tracking
            return {
                'error_count_24h': 0,
                'warning_count_24h': 0,
                'last_error': None,
            }
        except Exception as e:
            logger.error(f"Error gathering error metrics: {e}")
            return {}

    async def _gather_telegram_metrics(self):
        """Gather Telegram connection metrics."""
        try:
            connected = hasattr(self.bot, 'telegram_client') and self.bot.telegram_client.is_connected()
            auth_failed = getattr(self.bot, 'telegram_auth_failed', False)

            return {
                'connected': connected,
                'auth_failed': auth_failed,
            }
        except Exception as e:
            logger.error(f"Error gathering Telegram metrics: {e}")
            return {}

    async def _gather_performance_metrics(self):
        """Gather performance metrics."""
        try:
            # This could be enhanced with actual performance tracking
            return {
                'commands_per_minute': 0.0,
                'success_rate': 100.0,
                'avg_response_time': 0.0,
            }
        except Exception as e:
            logger.error(f"Error gathering performance metrics: {e}")
            return {}


async def setup(bot: commands.Bot) -> None:
    """Set up the StatusCommands cog."""
    await bot.add_cog(StatusCommands(bot))
    logger.info("✅ StatusCommands cog loaded")
