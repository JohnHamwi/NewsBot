"""
Admin Commands Cog

This cog provides administrative commands for NewsBot.
Handles bot management, logging, presence settings, and system control.
"""

import os
import traceback
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from src.core.config_manager import config
from src.utils.base_logger import base_logger as logger
from src.utils.structured_logger import structured_logger
from src.components.decorators.admin_required import admin_required, admin_required_with_defer
from src.components.embeds.base_embed import SuccessEmbed, ErrorEmbed, WarningEmbed, CommandEmbed

# Configuration constants
GUILD_ID = config.get('bot.guild_id') or 0


class AdminCommands(commands.Cog):
    """
    Cog for administrative commands.
    
    Provides bot management, logging, and system control commands.
    """

    def __init__(self, bot: discord.Client) -> None:
        """Initialize the AdminCommands cog."""
        self.bot = bot
        logger.debug("🔧 AdminCommands cog initialized")

    @app_commands.command(name="log", description="Show the last N lines of the bot log (admin only)")
    @app_commands.describe(count="Number of log lines to show")
    @app_commands.choices(count=[
        app_commands.Choice(name="10", value=10),
        app_commands.Choice(name="20", value=20),
        app_commands.Choice(name="30", value=30),
        app_commands.Choice(name="40", value=40),
        app_commands.Choice(name="50", value=50),
    ])
    @admin_required_with_defer
    async def log_command(self, interaction: discord.Interaction, count: app_commands.Choice[int] = None) -> None:
        """
        Show the last N lines of the bot log (admin only).
        
        Args:
            interaction: The Discord interaction
            count: Number of log lines to show
        """
        try:
            logger.info(f"[ADMIN][CMD] Log command invoked by user {interaction.user.id}, count={count.value if count else 20}")
            
            # Get the number of lines to show
            lines_to_show = count.value if count else 20
            
            # Read the log file
            log_file_path = "logs/newsbot.log"
            
            if not os.path.exists(log_file_path):
                embed = WarningEmbed(
                    "Log File Not Found",
                    f"The log file `{log_file_path}` does not exist."
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Read the last N lines
            try:
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    last_lines = lines[-lines_to_show:] if len(lines) > lines_to_show else lines
                    
                    if not last_lines:
                        embed = WarningEmbed(
                            "Empty Log File",
                            "The log file is empty."
                        )
                        await interaction.followup.send(embed=embed)
                        return
                    
                    # Format the log content
                    log_content = ''.join(last_lines)
                    
                    # Truncate if too long for Discord
                    if len(log_content) > 1900:  # Leave room for embed formatting
                        log_content = log_content[-1900:]
                        log_content = "...\n" + log_content[log_content.find('\n') + 1:]
                    
                    embed = CommandEmbed(
                        f"📋 Last {len(last_lines)} Log Lines",
                        f"```\n{log_content}\n```"
                    )
                    embed.set_footer(text=f"Log file: {log_file_path}")
                    
                    await interaction.followup.send(embed=embed)
                    logger.info(f"[ADMIN][CMD] Log command completed successfully for user {interaction.user.id}")
                    
            except Exception as e:
                embed = ErrorEmbed(
                    "Error Reading Log File",
                    f"Failed to read log file: {str(e)}"
                )
                await interaction.followup.send(embed=embed)
            
        except Exception as e:
            structured_logger.error(
                "Error executing log command",
                extra_data={"error": str(e), "traceback": traceback.format_exc()}
            )
            
            error_embed = ErrorEmbed(
                "Log Command Error",
                f"An error occurred: {str(e)}"
            )
            
            try:
                await interaction.followup.send(embed=error_embed)
            except discord.errors.NotFound:
                structured_logger.warning("Could not send error response")

    @app_commands.command(name="start", description="Trigger immediate news post (admin only)")
    @admin_required_with_defer
    async def start_command(self, interaction: discord.Interaction) -> None:
        """
        Trigger an immediate news post without waiting for the interval.
        
        Args:
            interaction: The Discord interaction
        """
        try:
            logger.info(f"[ADMIN][CMD] Start command invoked by user {interaction.user.id}")
            
            # Check if auto-posting is configured
            if not hasattr(self.bot, 'auto_post_interval') or self.bot.auto_post_interval <= 0:
                embed = WarningEmbed(
                    "Auto-Posting Disabled",
                    "Auto-posting is not configured. Use `/set_interval` to set up automatic posting first."
                )
                embed.add_field(
                    name="💡 Quick Setup", 
                    value="Try `/set_interval interval:360` (6 hours) to enable auto-posting, then use `/start` again.", 
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Set the force auto post flag
            self.bot.force_auto_post = True
            
            embed = SuccessEmbed(
                "🚀 Immediate Post Triggered",
                "The bot will attempt to post news immediately on the next auto-post cycle (within 1 minute)."
            )
            embed.add_field(
                name="ℹ️ Note", 
                value="This bypasses the normal posting interval and will post from the next available channel.", 
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            logger.info(f"[ADMIN][CMD] Start command completed successfully for user {interaction.user.id}")
            
        except Exception as e:
            structured_logger.error(
                "Error executing start command",
                extra_data={"error": str(e), "traceback": traceback.format_exc()}
            )
            
            error_embed = ErrorEmbed(
                "Start Command Error",
                f"An error occurred: {str(e)}"
            )
            
            try:
                await interaction.followup.send(embed=error_embed)
            except discord.errors.NotFound:
                structured_logger.warning("Could not send error response")

    @app_commands.command(name="set_interval", description="Set auto-posting interval (admin only)")
    @app_commands.describe(interval="Time between posts")
    @app_commands.choices(interval=[
        app_commands.Choice(name="Disabled", value=0),
        app_commands.Choice(name="5 minutes", value=5),
        app_commands.Choice(name="15 minutes", value=15),
        app_commands.Choice(name="30 minutes", value=30),
        app_commands.Choice(name="1 hour", value=60),
        app_commands.Choice(name="2 hours", value=120),
        app_commands.Choice(name="3 hours", value=180),
        app_commands.Choice(name="6 hours", value=360),
        app_commands.Choice(name="12 hours", value=720),
        app_commands.Choice(name="24 hours", value=1440),
    ])
    @admin_required_with_defer
    async def set_interval_command(self, interaction: discord.Interaction, interval: app_commands.Choice[int]) -> None:
        """
        Set the auto-posting interval.
        
        Args:
            interaction: The Discord interaction
            interval: Number of minutes between posts
        """
        try:
            logger.info(f"[ADMIN][CMD] Set interval command invoked by user {interaction.user.id}, interval={interval.value} minutes")
            
            # Validate input
            if interval.value < 0 or interval.value > 1440:
                embed = ErrorEmbed(
                    "Invalid Interval",
                    "Interval must be between 0 (disabled) and 24 hours (1440 minutes)."
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Convert minutes to seconds and set the interval
            seconds = interval.value * 60
            if hasattr(self.bot, 'set_auto_post_interval'):
                # Use hours for the existing method
                hours = interval.value / 60
                self.bot.set_auto_post_interval(hours)
            else:
                self.bot.auto_post_interval = seconds
            
            # Create response embed
            if interval.value == 0:
                embed = SuccessEmbed(
                    "⏹️ Auto-Posting Disabled",
                    "Automatic news posting has been disabled."
                )
            else:
                # Format the interval nicely
                if interval.value < 60:
                    interval_text = f"{interval.value} minute{'s' if interval.value != 1 else ''}"
                elif interval.value == 60:
                    interval_text = "1 hour"
                elif interval.value % 60 == 0:
                    hours = interval.value // 60
                    interval_text = f"{hours} hour{'s' if hours != 1 else ''}"
                else:
                    hours = interval.value // 60
                    minutes = interval.value % 60
                    interval_text = f"{hours}h {minutes}m"
                
                embed = SuccessEmbed(
                    "⏰ Auto-Posting Interval Updated",
                    f"Automatic posting interval set to **{interval_text}**."
                )
                embed.add_field(
                    name="ℹ️ Next Post", 
                    value="Use `/start` to trigger an immediate post or wait for the next scheduled interval.", 
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            logger.info(f"[ADMIN][CMD] Set interval command completed successfully for user {interaction.user.id}")
            
        except Exception as e:
            structured_logger.error(
                "Error executing set_interval command",
                extra_data={"error": str(e), "traceback": traceback.format_exc()}
            )
            
            error_embed = ErrorEmbed(
                "Set Interval Command Error",
                f"An error occurred: {str(e)}"
            )
            
            try:
                await interaction.followup.send(embed=error_embed)
            except discord.errors.NotFound:
                structured_logger.warning("Could not send error response")

    @app_commands.command(name="set_rich_presence", description="Set bot's Discord presence mode (admin only)")
    @app_commands.describe(mode="Presence mode to set")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Automatic", value="automatic"),
        app_commands.Choice(name="Maintenance", value="maintenance"),
    ])
    @admin_required_with_defer
    async def set_rich_presence_command(self, interaction: discord.Interaction, mode: app_commands.Choice[str]) -> None:
        """
        Set the bot's Discord rich presence mode.
        
        Args:
            interaction: The Discord interaction
            mode: The presence mode to set
        """
        try:
            logger.info(f"[ADMIN][CMD] Set rich presence command invoked by user {interaction.user.id}, mode={mode.value}")
            
            # Set the presence mode
            if hasattr(self.bot, 'set_rich_presence_mode'):
                self.bot.set_rich_presence_mode(mode.value)
            else:
                self.bot.rich_presence_mode = mode.value
            
            # Create response embed
            if mode.value == "automatic":
                embed = SuccessEmbed(
                    "🤖 Automatic Presence Enabled",
                    "Bot presence will automatically show news monitoring status and countdown to next post."
                )
            else:
                embed = SuccessEmbed(
                    "🔧 Maintenance Mode Enabled",
                    "Bot presence set to maintenance mode."
                )
            
            await interaction.followup.send(embed=embed)
            logger.info(f"[ADMIN][CMD] Set rich presence command completed successfully for user {interaction.user.id}")
            
        except Exception as e:
            structured_logger.error(
                "Error executing set_rich_presence command",
                extra_data={"error": str(e), "traceback": traceback.format_exc()}
            )
            
            error_embed = ErrorEmbed(
                "Set Rich Presence Command Error",
                f"An error occurred: {str(e)}"
            )
            
            try:
                await interaction.followup.send(embed=embed)
            except discord.errors.NotFound:
                structured_logger.warning("Could not send error response")


async def setup(bot: commands.Bot) -> None:
    """Set up the AdminCommands cog."""
    await bot.add_cog(AdminCommands(bot))
    logger.info("✅ AdminCommands cog loaded") 