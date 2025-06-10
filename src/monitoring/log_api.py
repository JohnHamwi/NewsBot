"""
Log API Module

This module provides an API for accessing and querying logs through Discord bot commands.
It integrates with the log aggregator to fetch structured logs.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

import discord
from discord import app_commands
from discord.ext import commands

from src.monitoring.log_aggregator import log_aggregator
from src.utils.structured_logger import structured_logger


class LogAPICog(commands.Cog):
    """
    Discord cog providing commands for accessing logs and metrics through the bot.
    """

    def __init__(self, bot):
        """
        Initialize the LogAPI cog.

        Args:
            bot: The bot instance
        """
        self.bot = bot
        self._lock = asyncio.Lock()
        self._last_initialization = None

    async def ensure_aggregator_initialized(self):
        """
        Ensure the log aggregator is initialized.
        """
        async with self._lock:
            # Only initialize if not done in the last 5 minutes
            now = datetime.utcnow()
            if (self._last_initialization is None or
                    (now - self._last_initialization).total_seconds() > 300):
                try:
                    # Initialize log aggregator
                    from src.monitoring.log_aggregator import initialize_log_aggregator
                    await initialize_log_aggregator()
                    self._last_initialization = now
                except Exception as e:
                    structured_logger.error(f"Failed to initialize log aggregator: {e}")

    @app_commands.command(
        name="logs",
        description="View recent logs with filtering options"
    )
    @app_commands.describe(
        level="Log level filter (INFO, WARNING, ERROR, etc.)",
        component="Component filter (e.g., FetchCog, TaskManager)",
        hours="Hours to look back (default: 24)",
        limit="Maximum number of logs to return (default: 10)"
    )
    async def logs_command(
        self,
        interaction: discord.Interaction,
        level: Optional[str] = None,
        component: Optional[str] = None,
        hours: Optional[int] = 24,
        limit: Optional[int] = 10
    ):
        """
        Command to view recent logs with filtering options.
        """
        await interaction.response.defer(ephemeral=True)

        # Initialize log aggregator if needed
        await self.ensure_aggregator_initialized()

        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        # Fetch logs
        logs = log_aggregator.get_logs(
            level=level,
            component=component,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )

        if not logs:
            await interaction.followup.send("No logs found matching the criteria.", ephemeral=True)
            return

        # Format logs for display
        formatted_logs = []
        for log in logs:
            timestamp = datetime.fromisoformat(log['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            level_str = log['level']
            component_str = log.get('component', 'unknown')
            message = log['message']

            # Format with emoji based on level
            emoji = "ℹ️"
            if level_str == "WARNING":
                emoji = "⚠️"
            elif level_str == "ERROR":
                emoji = "❌"
            elif level_str == "CRITICAL":
                emoji = "🔥"
            elif level_str == "DEBUG":
                emoji = "🔍"

            formatted_logs.append(f"{timestamp} {emoji} **[{level_str}]** [{component_str}] {message}")

        # Create embeds (paginate if needed)
        embeds = []
        current_embed = discord.Embed(
            title="📋 Log Viewer",
            description="",
            color=discord.Color.blue()
        )

        # Add filters to embed
        filter_text = []
        if level:
            filter_text.append(f"Level: {level}")
        if component:
            filter_text.append(f"Component: {component}")
        filter_text.append(f"Last {hours} hours")

        current_embed.add_field(
            name="Filters",
            value=" | ".join(filter_text),
            inline=False
        )

        # Add logs to embeds
        for i, log in enumerate(formatted_logs):
            if len(current_embed.description) + len(log) > 4000 or i % 10 == 0 and i > 0:
                embeds.append(current_embed)
                current_embed = discord.Embed(
                    title="📋 Log Viewer (Continued)",
                    description="",
                    color=discord.Color.blue()
                )

            current_embed.description += log + "\n\n"

        embeds.append(current_embed)

        # Send the first embed
        if len(embeds) == 1:
            await interaction.followup.send(embed=embeds[0], ephemeral=True)
        else:
            current_page = 0

            # Add page indicator
            for i, embed in enumerate(embeds):
                embed.set_footer(text=f"Page {i + 1}/{len(embeds)}")

            message = await interaction.followup.send(embed=embeds[0], ephemeral=True)

            # Additional pages would need a custom view with pagination buttons
            # But due to ephemeral limitations, we'll just send the first page
            if len(embeds) > 1:
                await interaction.followup.send(
                    "There are more logs than can be displayed. Try filtering further or reducing the time range.",
                    ephemeral=True
                )

    @app_commands.command(
        name="error_summary",
        description="View a summary of recent errors"
    )
    @app_commands.describe(
        hours="Hours to look back (default: 24)"
    )
    async def error_summary_command(
        self,
        interaction: discord.Interaction,
        hours: Optional[int] = 24
    ):
        """
        Command to view a summary of recent errors.
        """
        await interaction.response.defer(ephemeral=True)

        # Initialize log aggregator if needed
        await self.ensure_aggregator_initialized()

        # Fetch error summary
        summary = log_aggregator.get_error_summary(hours=hours)

        # Create embed
        embed = discord.Embed(
            title="❌ Error Summary",
            description=f"Last {hours} hours",
            color=discord.Color.red()
        )

        # Add total count
        embed.add_field(
            name="Total Errors",
            value=str(summary['total_count']),
            inline=False
        )

        # Add breakdown by component
        components_text = ""
        for component, count in summary['by_component'].items():
            components_text += f"**{component}**: {count}\n"

        if components_text:
            embed.add_field(
                name="Errors by Component",
                value=components_text,
                inline=False
            )

        # Add recent errors
        if summary['recent']:
            recent_text = ""
            for error in summary['recent'][:5]:  # Show at most 5 recent errors
                timestamp = datetime.fromisoformat(error['timestamp']).strftime('%H:%M:%S')
                component = error.get('component', 'unknown')
                message = error['message']
                recent_text += f"[{timestamp}] **{component}**: {message}\n\n"

            embed.add_field(
                name="Recent Errors",
                value=recent_text or "None",
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="performance",
        description="View performance metrics for commands and operations"
    )
    async def performance_command(
        self,
        interaction: discord.Interaction
    ):
        """
        Command to view performance metrics.
        """
        await interaction.response.defer(ephemeral=True)

        # Initialize log aggregator if needed
        await self.ensure_aggregator_initialized()

        # Fetch performance metrics
        metrics = log_aggregator.get_performance_metrics()

        if not metrics:
            await interaction.followup.send("No performance metrics available yet.", ephemeral=True)
            return

        # Create embed
        embed = discord.Embed(
            title="⚡ Performance Metrics",
            description="Command execution times and counts",
            color=discord.Color.gold()
        )

        # Add command metrics
        for command, data in metrics.items():
            value = (
                f"**Count:** {data['count']}\n"
                f"**Avg Time:** {data['avg_duration']:.3f}s\n"
                f"**Min Time:** {data['min_duration']:.3f}s\n"
                f"**Max Time:** {data['max_duration']:.3f}s"
            )

            embed.add_field(
                name=command,
                value=value,
                inline=True
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="user_activity",
        description="View activity logs for a specific user"
    )
    @app_commands.describe(
        user="The user to view activity for",
        hours="Hours to look back (default: 24)"
    )
    async def user_activity_command(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        hours: Optional[int] = 24
    ):
        """
        Command to view activity logs for a specific user.
        """
        await interaction.response.defer(ephemeral=True)

        # Initialize log aggregator if needed
        await self.ensure_aggregator_initialized()

        # Fetch user activity
        activity = log_aggregator.get_user_activity(str(user.id), hours=hours)

        if not activity:
            await interaction.followup.send(f"No activity found for {user.display_name} in the last {hours} hours.", ephemeral=True)
            return

        # Create embed
        embed = discord.Embed(
            title=f"👤 User Activity: {user.display_name}",
            description=f"Last {hours} hours",
            color=discord.Color.blue()
        )

        # Add user info
        embed.set_thumbnail(url=user.display_avatar.url)

        # Group activity by command
        command_activity = {}
        for entry in activity:
            command = entry.get('command_name')
            if command:
                if command not in command_activity:
                    command_activity[command] = {
                        'count': 0,
                        'last_used': None
                    }
                command_activity[command]['count'] += 1

                timestamp = datetime.fromisoformat(entry['timestamp'])
                if (command_activity[command]['last_used'] is None or
                        timestamp > command_activity[command]['last_used']):
                    command_activity[command]['last_used'] = timestamp

        # Add command activity
        commands_text = ""
        for command, data in command_activity.items():
            last_used = data['last_used'].strftime('%Y-%m-%d %H:%M:%S') if data['last_used'] else 'Unknown'
            commands_text += f"**{command}**: {data['count']} times (Last: {last_used})\n"

        if commands_text:
            embed.add_field(
                name="Command Usage",
                value=commands_text,
                inline=False
            )

        # Add recent activity
        recent_text = ""
        for entry in activity[:5]:  # Show at most 5 recent activities
            timestamp = datetime.fromisoformat(entry['timestamp']).strftime('%H:%M:%S')
            component = entry.get('component', 'unknown')
            message = entry['message']
            recent_text += f"[{timestamp}] **{component}**: {message}\n\n"

        if recent_text:
            embed.add_field(
                name="Recent Activity",
                value=recent_text,
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    """
    Set up the LogAPI cog.
    """
    await bot.add_cog(LogAPICog(bot))
