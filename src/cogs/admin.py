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


async def setup(bot: commands.Bot) -> None:
    """Set up the AdminCommands cog."""
    await bot.add_cog(AdminCommands(bot))
    logger.info("✅ AdminCommands cog loaded") 