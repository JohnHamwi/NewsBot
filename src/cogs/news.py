"""
News Channel Management Cog

This module provides commands for managing Telegram news channels.
"""

from typing import List

import discord
from discord import app_commands, ui
from discord.ext import commands

from src.components.decorators.admin_required import admin_required
from src.components.embeds.base_embed import BaseEmbed
from src.core.config_manager import config
from src.utils import error_handler
from src.utils.base_logger import base_logger as logger
from src.utils.config import Config
from src.utils.timezone_utils import now_eastern

# Configuration constants
GUILD_ID = Config.GUILD_ID or 0
ADMIN_USER_ID = Config.ADMIN_USER_ID or 0

# Embed color scheme
EMBED_COLOR_INFO = discord.Color.blue()
EMBED_COLOR_SUCCESS = discord.Color.green()
EMBED_COLOR_ERROR = discord.Color.red()
EMBED_COLOR_WARNING = discord.Color.orange()


class NewsCog(commands.Cog):
    """
    Cog for managing Telegram channel operations.

    Handles activation, deactivation, and listing of Telegram channels
    for news aggregation. Provides admin-only commands with proper
    validation and error handling.
    """

    def __init__(self, bot: commands.Bot) -> None:
        """Initialize the NewsCog with bot reference."""
        self.bot = bot
        logger.debug("🔧 NewsCog initialized")

    @app_commands.command(
        name="channel", description="Manage Telegram channels (admin only)"
    )
    @app_commands.describe(
        action="What channel action to perform",
        filter="Filter for list action (activated/deactivated/all)",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="📋 List Channels", value="list"),
            app_commands.Choice(name="➕ Add Channel", value="add"),
            app_commands.Choice(name="🟢 Activate Channel", value="activate"),
            app_commands.Choice(name="🔴 Deactivate Channel", value="deactivate"),
        ]
    )
    @app_commands.choices(
        filter=[
            app_commands.Choice(name="🟢 Activated", value="activated"),
            app_commands.Choice(name="🔴 Deactivated", value="deactivated"),
            app_commands.Choice(name="📋 All", value="all"),
        ]
    )
    async def channel_command(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        filter: app_commands.Choice[str] = None,
    ) -> None:
        """
        Consolidated channel management command (admin only).

        Args:
            interaction: The Discord interaction
            action: The action to perform (list/activate/deactivate)
            filter: Filter for list action
        """
        action_value = action.value
        filter_value = filter.value if filter else "all"

        logger.info(
            f"[NEWS][CMD][channel] Command invoked by user {interaction.user.id}, action={action_value}"
        )

        try:
            # Check authorization
            if not await self._check_admin_authorization(interaction):
                return

            # Handle add action differently since it needs to send a modal immediately
            if action_value == "add":
                await self._handle_channel_add(interaction)
                return

            # Defer response for other actions
            await interaction.response.defer(thinking=True)

            if action_value == "list":
                await self._handle_channel_list(interaction, filter_value)
            elif action_value == "activate":
                await self._handle_channel_activate_selection(interaction)
            elif action_value == "deactivate":
                await self._handle_channel_deactivate_selection(interaction)
            else:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ Invalid Action",
                        description="Invalid action specified.",
                        color=EMBED_COLOR_ERROR,
                    )
                )

        except Exception as e:
            logger.error(f"[NEWS][CMD][channel] Error: {str(e)}", exc_info=True)

            await self._send_error_response(
                interaction, "Channel Command Error", e, f"channel_{action_value}"
            )

    async def _check_admin_authorization(self, interaction: discord.Interaction) -> bool:
        """Check if user has admin authorization."""
        # Admin authorization is handled by decorators
        return True

    async def _get_channels_by_filter(self, filter_value: str) -> List[str]:
        """
        Get channels based on filter criteria.

        Args:
            filter_value: The filter to apply (activated/deactivated/all)

        Returns:
            List of channel names
        """
        if filter_value == "activated":
            return await self.bot.json_cache.list_telegram_channels("activated")
        elif filter_value == "deactivated":
            return await self.bot.json_cache.list_telegram_channels("deactivated")
        else:
            return await self.bot.json_cache.list_telegram_channels("all")

    def _create_channel_list_embed(
        self, channels: List[str], filter_value: str
    ) -> discord.Embed:
        """
        Create embed for channel list display.

        Args:
            channels: List of channel names
            filter_value: The filter that was applied

        Returns:
            Discord embed with channel list
        """
        # Determine emoji and title based on filter
        if filter_value == "activated":
            emoji = "🟢"
            title = "Activated Channels"
        elif filter_value == "deactivated":
            emoji = "🔴"
            title = "Deactivated Channels"
        else:
            emoji = "📋"
            title = "All Channels"

        if channels:
            # Limit display to prevent embed size issues
            display_channels = channels[:25]  # Discord embed field limit
            channel_text = "\n".join(f"@{c}" for c in display_channels)

            if len(channels) > 25:
                channel_text += f"\n... and {len(channels) - 25} more"

            embed = discord.Embed(
                title=f"{emoji} {title}",
                description=f"```{channel_text}```",
                color=EMBED_COLOR_INFO,
                timestamp=now_eastern(),
            )
            embed.set_footer(text=f"Total: {len(channels)} channels")
        else:
            embed = discord.Embed(
                title=f"{emoji} {title}",
                description="```No channels found for this category.```",
                color=EMBED_COLOR_WARNING,
                timestamp=now_eastern(),
            )

        return embed

    async def _send_error_response(
        self,
        interaction: discord.Interaction,
        title: str,
        error: Exception,
        context: str,
    ) -> None:
        """
        Send a standardized error response to the user.

        Args:
            interaction: The Discord interaction
            title: Error title
            error: The exception that occurred
            context: Context information for logging
        """
        # Create error embed
        embed = discord.Embed(
            title=f"❌ {title}",
            description=f"```{str(error)}```",
            color=EMBED_COLOR_ERROR,
            timestamp=now_eastern(),
        )

        try:
            # Try to send followup first (if response was deferred)
            await interaction.followup.send(embed=embed)
        except Exception:
            try:
                # Fallback to response if followup fails
                await interaction.response.send_message(embed=embed)
            except Exception as e:
                logger.error(f"[NEWS][CMD] Failed to send error response: {str(e)}")

        # Send error to error handler for logging
        await error_handler.send_error_embed(
            title,
            error,
            context=context,
            bot=self.bot,
            channel=getattr(self.bot, "log_channel", None),
        )

    async def _handle_channel_list(
        self, interaction: discord.Interaction, filter_value: str
    ):
        """Handle channel list action."""
        # Fetch channels based on filter
        channels = await self._get_channels_by_filter(filter_value)

        # Create and send response embed
        embed = self._create_channel_list_embed(channels, filter_value)
        await interaction.followup.send(embed=embed)

        logger.info(
            f"[NEWS][CMD][channel_list] Successfully listed {len(channels)} channels"
        )

    async def _handle_channel_add(self, interaction: discord.Interaction):
        """Handle adding a new channel."""
        try:
            # Create modal for channel input
            modal = ChannelAddModal(self.bot)

            # Send the modal
            await interaction.response.send_modal(modal)

        except Exception as e:
            logger.error(f"[NEWS][CMD] Error sending modal: {str(e)}", exc_info=True)

            # Fallback error response
            embed = discord.Embed(
                title="❌ Modal Error",
                description=f"Failed to open input dialog: {str(e)}",
                color=EMBED_COLOR_ERROR,
                timestamp=now_eastern(),
            )

            try:
                await interaction.response.send_message(embed=embed, ephemeral=False)
            except Exception:
                # If response fails, try followup
                try:
                    await interaction.followup.send(embed=embed, ephemeral=False)
                except Exception as followup_error:
                    logger.error(
                        f"[NEWS][CMD] Failed to send error response: {followup_error}"
                    )

    async def _handle_channel_activate_selection(
        self, interaction: discord.Interaction
    ):
        """Handle channel activate selection."""
        # Get deactivated channels for activation
        deactivated_channels = await self.bot.json_cache.list_telegram_channels(
            "deactivated"
        )

        if not deactivated_channels:
            embed = discord.Embed(
                title="ℹ️ No Channels Available",
                description="No deactivated channels available to activate.",
                color=EMBED_COLOR_INFO,
                timestamp=now_eastern(),
            )
            await interaction.followup.send(embed=embed)
            return

        # Create dropdown with deactivated channels
        view = ChannelActivateDropdown(self.bot, deactivated_channels)

        embed = discord.Embed(
            title="🟢 Activate Channel",
            description="Select channels to activate from the dropdown below:",
            color=EMBED_COLOR_INFO,
            timestamp=now_eastern(),
        )
        await interaction.followup.send(embed=embed, view=view)

    async def _handle_channel_deactivate_selection(
        self, interaction: discord.Interaction
    ):
        """Handle channel deactivate selection."""
        # Get activated channels for deactivation
        activated_channels = await self.bot.json_cache.list_telegram_channels(
            "activated"
        )

        if not activated_channels:
            embed = discord.Embed(
                title="ℹ️ No Channels Available",
                description="No activated channels available to deactivate.",
                color=EMBED_COLOR_INFO,
                timestamp=now_eastern(),
            )
            await interaction.followup.send(embed=embed)
            return

        # Create dropdown with activated channels
        view = ChannelDeactivateDropdown(self.bot, activated_channels)

        embed = discord.Embed(
            title="🔴 Deactivate Channel",
            description="Select channels to deactivate from the dropdown below:",
            color=EMBED_COLOR_WARNING,
            timestamp=now_eastern(),
        )
        await interaction.followup.send(embed=embed, view=view)


class ChannelActivateDropdown(ui.View):
    """View for selecting a channel to activate."""

    def __init__(self, bot: commands.Bot, deactivated_channels: List[str]) -> None:
        """Initialize the view for selecting a channel to activate."""
        super().__init__(timeout=60)
        self.bot = bot

        # Create select options from deactivated channels
        options = [
            discord.SelectOption(
                label=f"@{channel}", value=channel, description=f"Activate @{channel}"
            )
            for channel in deactivated_channels[:25]  # Discord limit is 25 options
        ]

        # Create the select dropdown
        self.channel_select = ui.Select(
            placeholder="Choose channels to activate...",
            min_values=1,
            max_values=min(len(options), 25),
            options=options,
        )
        self.channel_select.callback = self.channel_callback
        self.add_item(self.channel_select)

    async def channel_callback(self, interaction: discord.Interaction):
        """Handle selection of channels to activate."""
        selected_channels = self.channel_select.values
        logger.info(f"[NEWS][VIEW] Channels to activate: {selected_channels}")

        try:
            success_count = 0
            failed_channels = []

            for channel in selected_channels:
                try:
                    success = await self.bot.json_cache.add_telegram_channel(channel)
                    if success:
                        success_count += 1
                    else:
                        failed_channels.append(channel)
                except Exception as e:
                    logger.error(
                        f"[NEWS][VIEW] Error activating channel {channel}: {str(e)}"
                    )
                    failed_channels.append(channel)

            # Create response embed
            if success_count > 0 and not failed_channels:
                embed = discord.Embed(
                    title="✅ Channels Activated",
                    description=(
                        f"Successfully activated {success_count} channel(s): "
                        f"{', '.join(f'@{c}' for c in selected_channels)}"
                    ),
                    color=EMBED_COLOR_SUCCESS,
                    timestamp=now_eastern(),
                )
            elif success_count > 0 and failed_channels:
                embed = discord.Embed(
                    title="⚠️ Partial Success",
                    description=(
                        f"Activated {success_count} channel(s), but failed to activate: "
                        f"{', '.join(f'@{c}' for c in failed_channels)}"
                    ),
                    color=EMBED_COLOR_WARNING,
                    timestamp=now_eastern(),
                )
            else:
                embed = discord.Embed(
                    title="❌ Activation Failed",
                    description=f"Failed to activate any channels: {', '.join(f'@{c}' for c in failed_channels)}",
                    color=EMBED_COLOR_ERROR,
                    timestamp=now_eastern(),
                )

            await interaction.response.edit_message(embed=embed, view=None)

        except Exception as e:
            logger.error(
                f"[NEWS][VIEW] Error in channel activation: {str(e)}", exc_info=True
            )

            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=EMBED_COLOR_ERROR,
                timestamp=now_eastern(),
            )
            await interaction.response.edit_message(embed=embed, view=None)


class ChannelDeactivateDropdown(ui.View):
    """View for selecting a channel to deactivate."""

    def __init__(self, bot: commands.Bot, activated_channels: List[str]) -> None:
        """Initialize the view for selecting a channel to deactivate."""
        super().__init__(timeout=60)
        self.bot = bot

        # Create select options from activated channels
        options = [
            discord.SelectOption(
                label=f"@{channel}", value=channel, description=f"Deactivate @{channel}"
            )
            for channel in activated_channels[:25]  # Discord limit is 25 options
        ]

        # Create the select dropdown
        self.channel_select = ui.Select(
            placeholder="Choose channels to deactivate...",
            min_values=1,
            max_values=min(len(options), 25),
            options=options,
        )
        self.channel_select.callback = self.channel_callback
        self.add_item(self.channel_select)

    async def channel_callback(self, interaction: discord.Interaction):
        """Handle selection of channels to deactivate."""
        selected_channels = self.channel_select.values
        logger.info(f"[NEWS][VIEW] Channels to deactivate: {selected_channels}")

        try:
            success_count = 0
            failed_channels = []

            for channel in selected_channels:
                try:
                    await self.bot.json_cache.set_channel_status(channel, "deactivated")
                    success_count += 1
                except Exception as e:
                    logger.error(
                        f"[NEWS][VIEW] Error deactivating channel {channel}: {str(e)}"
                    )
                    failed_channels.append(channel)

            # Create response embed
            if success_count > 0 and not failed_channels:
                embed = discord.Embed(
                    title="🚫 Channels Deactivated",
                    description=(
                        f"Successfully deactivated {success_count} channel(s): "
                        f"{', '.join(f'@{c}' for c in selected_channels)}"
                    ),
                    color=EMBED_COLOR_WARNING,
                    timestamp=now_eastern(),
                )
            elif success_count > 0 and failed_channels:
                embed = discord.Embed(
                    title="⚠️ Partial Success",
                    description=(
                        f"Deactivated {success_count} channel(s), but failed to deactivate: "
                        f"{', '.join(f'@{c}' for c in failed_channels)}"
                    ),
                    color=EMBED_COLOR_WARNING,
                    timestamp=now_eastern(),
                )
            else:
                embed = discord.Embed(
                    title="❌ Deactivation Failed",
                    description=f"Failed to deactivate any channels: {', '.join(f'@{c}' for c in failed_channels)}",
                    color=EMBED_COLOR_ERROR,
                    timestamp=now_eastern(),
                )

            await interaction.response.edit_message(embed=embed, view=None)

        except Exception as e:
            logger.error(
                f"[NEWS][VIEW] Error in channel deactivation: {str(e)}", exc_info=True
            )

            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=EMBED_COLOR_ERROR,
                timestamp=now_eastern(),
            )
            await interaction.response.edit_message(embed=embed, view=None)


class ChannelAddModal(ui.Modal):
    """Modal for adding a new Telegram channel."""

    def __init__(self, bot: commands.Bot):
        super().__init__(title="➕ Add New Telegram Channel")
        self.bot = bot

        # Channel name input
        self.channel_input = ui.TextInput(
            label="Channel Username",
            placeholder="Enter channel username (without @)",
            required=True,
            max_length=100,
        )
        self.add_item(self.channel_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        channel_name = self.channel_input.value.strip()

        # Remove @ if user included it
        if channel_name.startswith("@"):
            channel_name = channel_name[1:]

        logger.info(f"[NEWS][MODAL] Adding new channel: {channel_name}")

        try:
            # Add channel to cache (this will add it as activated)
            success = await self.bot.json_cache.add_telegram_channel(channel_name)

            if success:
                embed = discord.Embed(
                    title="✅ Channel Added Successfully",
                    description=f"Channel `@{channel_name}` has been added and activated!",
                    color=EMBED_COLOR_SUCCESS,
                    timestamp=now_eastern(),
                )
                embed.add_field(
                    name="💡 Next Steps",
                    value="The channel is now active and will be used for auto-posting.",
                    inline=False,
                )
            else:
                embed = discord.Embed(
                    title="⚠️ Channel Already Exists",
                    description=f"Channel `@{channel_name}` is already in the system.",
                    color=EMBED_COLOR_WARNING,
                    timestamp=now_eastern(),
                )
                embed.add_field(
                    name="💡 Tip",
                    value="Use `/channel activate` to activate existing channels.",
                    inline=False,
                )

            await interaction.response.send_message(embed=embed, ephemeral=False)

        except Exception as e:
            logger.error(
                f"[NEWS][MODAL] Error adding channel {channel_name}: {str(e)}",
                exc_info=True,
            )

            embed = discord.Embed(
                title="❌ Error Adding Channel",
                description=f"Failed to add channel `@{channel_name}`: {str(e)}",
                color=EMBED_COLOR_ERROR,
                timestamp=now_eastern(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot):
    """
    Setup function to add the NewsCog to the bot instance.
    """
    await bot.add_cog(NewsCog(bot))
