"""
Configuration Command Module for NewsBot

This module provides Discord slash commands for managing the bot's configuration.
"""

import json
import os
from typing import List, Optional

import discord
import yaml
from discord import app_commands
from discord.ext import commands

from src.core.simple_config import config
from src.utils.base_logger import base_logger as logger


class ConfigCommands(commands.Cog):
    """Commands for managing the bot's configuration."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="config", description="Manage bot configuration (admin only)"
    )
    @app_commands.describe(
        action="What configuration action to perform",
        key="Configuration key (for get/set actions, e.g. 'bot.debug_mode')",
        value="Value to set (for set action)",
        profile="Profile to switch to (for profile action)",
        filename="Filename for save action (without extension)",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="📄 Get Value", value="get"),
            app_commands.Choice(name="✏️ Set Override", value="set"),
            app_commands.Choice(name="🗑️ Clear Overrides", value="clear"),
            app_commands.Choice(name="🔄 Reload Config", value="reload"),
            app_commands.Choice(name="💾 Save Config", value="save"),
            app_commands.Choice(name="🔧 Switch Profile", value="profile"),
            app_commands.Choice(name="📋 Show Profile", value="show_profile"),
        ]
    )
    @app_commands.choices(
        profile=[
            app_commands.Choice(name="Default", value="default"),
            app_commands.Choice(name="Development", value="dev"),
            app_commands.Choice(name="Testing", value="test"),
            app_commands.Choice(name="Production", value="prod"),
        ]
    )
    async def config_command(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        key: str = None,
        value: str = None,
        profile: app_commands.Choice[str] = None,
        filename: str = None,
    ):
        """
        Consolidated configuration management command (admin only).

        Args:
            interaction: Discord interaction
            action: The action to perform
            key: Configuration key (for get/set)
            value: Value to set (for set action)
            profile: Profile to switch to (for profile action)
            filename: Filename for save action
        """
        # Check if user has admin permissions
        if not self._is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.", ephemeral=False
            )
            return

        action_value = action.value
        logger.info(
            f"[CONFIG][CMD] Config command invoked by user {interaction.user.id}, action={action_value}"
        )

        try:
            if action_value == "get":
                await self._handle_config_get(interaction, key)
            elif action_value == "set":
                await self._handle_config_set(interaction, key, value)
            elif action_value == "clear":
                await self._handle_config_clear(interaction)
            elif action_value == "reload":
                await self._handle_config_reload(interaction)
            elif action_value == "save":
                await self._handle_config_save(interaction, filename)
            elif action_value == "profile":
                await self._handle_config_profile(interaction, profile)
            elif action_value == "show_profile":
                await self._handle_show_profile(interaction)
            else:
                await interaction.response.send_message(
                    "❌ Invalid action specified.", ephemeral=False
                )

        except Exception as e:
            logger.error(
                f"[CONFIG][CMD] Error in config command: {str(e)}", exc_info=True
            )

            error_embed = discord.Embed(
                title="❌ Configuration Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow(),
            )

            try:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=error_embed)
                else:
                    await interaction.response.send_message(embed=error_embed)
            except discord.errors.NotFound:
                logger.warning("[CONFIG][CMD] Could not send error response")

    async def _handle_config_get(self, interaction: discord.Interaction, key: str):
        """Handle config get action."""
        if not key:
            await interaction.response.send_message(
                "❌ Please specify a configuration key to get.", ephemeral=False
            )
            return

        value = config.get(key)

        embed = discord.Embed(
            title="🔧 Configuration Value", color=discord.Color.blue()
        )
        embed.add_field(name="Key", value=f"`{key}`", inline=False)
        embed.add_field(name="Value", value=f"`{value}`", inline=False)
        embed.add_field(name="Type", value=f"`{type(value).__name__}`", inline=False)

        await interaction.response.send_message(embed=embed)

    async def _handle_config_set(
        self, interaction: discord.Interaction, key: str, value: str
    ):
        """Handle config set action."""
        if not key or value is None:
            await interaction.response.send_message(
                "❌ Please specify both a key and value for set action.",
                ephemeral=False,
            )
            return

        # Convert value to appropriate type
        converted_value = self._convert_value(value)

        # Set override
        config.set_override(key, converted_value)

        embed = discord.Embed(
            title="🔧 Configuration Override Set",
            description=f"Set override for **{key}** to **{converted_value}**",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="⚠️ Note",
            value="This override is temporary and will be reset when the bot restarts.",
            inline=False,
        )
        await interaction.response.send_message(embed=embed)

    async def _handle_config_clear(self, interaction: discord.Interaction):
        """Handle config clear action."""
        config.clear_overrides()

        embed = discord.Embed(
            title="🔧 Configuration Overrides Cleared",
            description="All configuration overrides have been cleared.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    async def _handle_config_reload(self, interaction: discord.Interaction):
        """Handle config reload action."""
        success = config.load_config()

        if success:
            embed = discord.Embed(
                title="🔧 Configuration Reloaded",
                description="Configuration reloaded successfully from file.",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="❌ Configuration Reload Failed",
                description="Failed to reload configuration from file.",
                color=discord.Color.red(),
            )

        await interaction.response.send_message(embed=embed)

    async def _handle_config_save(
        self, interaction: discord.Interaction, filename: str
    ):
        """Handle config save action."""
        if not filename:
            await interaction.response.send_message(
                "❌ Please specify a filename for save action.", ephemeral=False
            )
            return

        # Ensure filename has no path components or extension
        safe_filename = os.path.basename(filename).split(".")[0]

        # Create path in configs directory
        os.makedirs("configs", exist_ok=True)
        filepath = f"configs/{safe_filename}.yaml"

        # Save configuration
        success = config.save_to_file(filepath)

        if success:
            embed = discord.Embed(
                title="🔧 Configuration Saved",
                description=f"Configuration saved to **{filepath}**",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="❌ Configuration Save Failed",
                description=f"Failed to save configuration to **{filepath}**",
                color=discord.Color.red(),
            )

        await interaction.response.send_message(embed=embed)

    async def _handle_config_profile(
        self, interaction: discord.Interaction, profile: app_commands.Choice[str]
    ):
        """Handle config profile switch action."""
        if not profile:
            await interaction.response.send_message(
                "❌ Please specify a profile to switch to.", ephemeral=False
            )
            return

        profile_value = profile.value
        success = config.set_profile(profile_value)

        if success:
            embed = discord.Embed(
                title="🔧 Configuration Profile",
                description=f"Switched to profile: **{profile_value}**",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="❌ Profile Switch Failed",
                description=f"Failed to switch to profile: **{profile_value}**",
                color=discord.Color.red(),
            )

        await interaction.response.send_message(embed=embed)

    async def _handle_show_profile(self, interaction: discord.Interaction):
        """Handle show current profile action."""
        current_profile = config.get_current_profile()

        embed = discord.Embed(
            title="🔧 Current Configuration Profile",
            description=f"Active profile: **{current_profile}**",
            color=discord.Color.blue(),
        )

        # Add available profiles
        available_profiles = ["default", "dev", "test", "prod"]
        embed.add_field(
            name="Available Profiles",
            value="\n".join(
                f"{'✅' if p == current_profile else '⚪'} {p}"
                for p in available_profiles
            ),
            inline=False,
        )

        await interaction.response.send_message(embed=embed)

    def _is_admin(self, user: discord.User) -> bool:
        """
        Check if user is an admin.

        Args:
            user: Discord user

        Returns:
            bool: True if user is an admin
        """
        # Check if user ID matches admin user ID
        admin_user_id = config.get("bot.admin_user_id")
        if admin_user_id and str(user.id) == str(admin_user_id):
            return True

        # Check if user has admin role
        if hasattr(user, "roles"):
            admin_role_id = config.get("bot.admin_role_id")
            if admin_role_id:
                return any(role.id == admin_role_id for role in user.roles)

        return False

    def _convert_value(self, value: str) -> any:
        """
        Convert string value to appropriate type.

        Args:
            value: String value to convert

        Returns:
            any: Converted value
        """
        # Try to convert to int
        if value.isdigit():
            return int(value)

        # Try to convert to float
        try:
            return float(value)
        except ValueError:
            pass

        # Try to convert to bool
        if value.lower() in ["true", "false"]:
            return value.lower() == "true"

        # Try to convert to None
        if value.lower() in ["none", "null"]:
            return None

        # Try to convert to JSON
        try:
            return json.loads(value)
        except ValueError:
            pass

        # Return as string
        return value


async def setup(bot):
    """Add the configuration commands cog to the bot."""
    await bot.add_cog(ConfigCommands(bot))
