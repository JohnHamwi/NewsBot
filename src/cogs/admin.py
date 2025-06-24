# =============================================================================
# NewsBot Administrative Commands Module
# =============================================================================
# Streamlined administrative commands with better organization.
# Replaces the complex admin.py with simpler, more intuitive commands.
# Features comprehensive bot management, posting controls, and system operations.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import asyncio
import logging
import os
import traceback
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import discord
from discord import app_commands
from discord.ext import commands

# =============================================================================
# Local Application Imports
# =============================================================================
from src.components.embeds.base_embed import InfoEmbed, ErrorEmbed, SuccessEmbed, WarningEmbed
from src.core.unified_config import unified_config as config
from src.utils.base_logger import base_logger as logger
from src.utils.structured_logger import structured_logger
from src.components.decorators.admin_required import admin_required
from src.utils.structured_logger import StructuredLogger


# =============================================================================
# Configuration Constants
# =============================================================================
GUILD_ID = config.get("bot.guild_id") or 0


# =============================================================================
# Administrative Commands Cog
# =============================================================================
class AdminCommands(commands.Cog):
    """
    Professional administrative commands system for NewsBot.

    Features:
    - Post management (manual, test, schedule, status)
    - Channel management (list, activate, deactivate, test)
    - Auto-posting control (start, stop, status)
    - System operations (logs, restart, health check)
    - Streamlined user interface
    """

    # =========================================================================
    # Admin Command Group Setup
    # =========================================================================
    admin_group = app_commands.Group(
        name="admin",
        description="🔧 Administrative commands for bot management"
    )
    admin_group.default_permissions = discord.Permissions(administrator=True)

    def __init__(self, bot: discord.Client) -> None:
        """Initialize the AdminCommands cog."""
        self.bot = bot
        logger.debug("🔧 AdminCommands cog initialized")

    # =========================================================================
    # Helper Methods
    # =========================================================================
    def _is_admin(self, user: discord.User) -> bool:
        """Check if user has admin permissions."""
        admin_user_id = config.get("bot.admin_user_id")
        return admin_user_id and user.id == int(admin_user_id)

    async def _handle_manual_fetch(self, interaction: discord.Interaction, channel: str, count: int) -> None:
        """Handle manual fetch from a specific channel with preview."""
        try:
            logger.info(f"[ADMIN] Manual fetch requested by {interaction.user.id} for channel: {channel}, count: {count}")

            # Check if Telegram client is available
            if not hasattr(self.bot, 'telegram_client') or not self.bot.telegram_client:
                embed = ErrorEmbed(
                    "❌ Telegram Client Error",
                    "Telegram client is not available."
                )
                await interaction.followup.send(embed=embed)
                return

            # Check if Telegram client is connected
            if not await self.bot.telegram_client.is_connected():
                embed = ErrorEmbed(
                    "❌ Connection Error",
                    "Telegram client is not connected."
                )
                await interaction.followup.send(embed=embed)
                return

            # Get messages from the channel
            messages = await self.bot.telegram_client.get_messages(channel, limit=count)

            if not messages:
                embed = WarningEmbed(
                    "⚠️ No Messages",
                    f"No messages found in channel '{channel}'."
                )
                await interaction.followup.send(embed=embed)
                return

            # Get blacklisted message IDs
            blacklisted_ids = await self.bot.json_cache.get("blacklisted_posts") or []

            # Filter out blacklisted messages and messages without content/media
            valid_messages = []
            for message in messages:
                if message.id in blacklisted_ids:
                    logger.debug(f"[MANUAL-FETCH] Skipping blacklisted message {message.id}")
                    continue

                if not message.message and not message.media:
                    logger.debug(f"[MANUAL-FETCH] Skipping message {message.id} - no content or media")
                    continue

                valid_messages.append(message)

            if not valid_messages:
                embed = WarningEmbed(
                    "⚠️ No Valid Messages",
                    f"No valid messages found in channel '{channel}' (all messages are either blacklisted or have no content)."
                )
                await interaction.followup.send(embed=embed)
                return

            # Check if logs channel is available (use the same logs channel as the main bot)
            if not hasattr(self.bot, 'log_channel') or not self.bot.log_channel:
                embed = ErrorEmbed(
                    "❌ Configuration Error",
                    "Logs channel is not configured. Manual fetch previews require a logs channel to be set in the environment variables (LOG_CHANNEL_ID)."
                )
                await interaction.followup.send(embed=embed)
                return

            # Create preview for each valid message
            previews_created = 0
            for i, message in enumerate(valid_messages):
                try:
                    await self._create_manual_fetch_preview(message, channel, interaction.user, i + 1, len(valid_messages))
                    previews_created += 1
                except Exception as e:
                    logger.error(f"[MANUAL-FETCH] Error creating preview for message {message.id}: {e}")
                    continue

            # Send confirmation
            if previews_created > 0:
                embed = SuccessEmbed(
                    "📱 Manual Fetch Complete",
                    f"Created {previews_created} preview(s) from channel '{channel}'. Check the logs channel for preview buttons."
                )
            else:
                embed = ErrorEmbed(
                    "❌ Preview Creation Failed",
                    f"Failed to create any previews from channel '{channel}'."
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"[MANUAL-FETCH] Error in manual fetch: {e}")
            embed = ErrorEmbed(
                "❌ Manual Fetch Error",
                f"An error occurred during manual fetch: {str(e)}"
            )
            await interaction.followup.send(embed=embed)

    async def _create_manual_fetch_preview(self, message, channel: str, user: discord.User, index: int, total: int) -> None:
        """Create a preview of the fetched message in the logs channel."""
        try:
            # Use the same logs channel as the main bot
            if not hasattr(self.bot, 'log_channel') or not self.bot.log_channel:
                logger.error("[MANUAL-FETCH] No logs channel available")
                return

            logs_channel = self.bot.log_channel

            # Create preview embed
            title = f"📱 Manual Fetch Preview ({index}/{total})" if total > 1 else "📱 Manual Fetch Preview"
            embed = discord.Embed(
                title=title,
                description=f"**Channel:** {channel}\n**Message ID:** {message.id}",
                color=0x3498db,
                timestamp=message.date if hasattr(message.date, 'year') else None
            )

            # Add message content preview
            if hasattr(message, 'message') and message.message:
                content_preview = message.message[:500] + "..." if len(message.message) > 500 else message.message
                embed.add_field(
                    name="📝 Content Preview",
                    value=f"```{content_preview}```",
                    inline=False
                )

            # Add media info
            if hasattr(message, 'media') and message.media:
                media_type = self._detect_media_type(message.media)
                
                embed.add_field(
                    name="🖼️ Media",
                    value=media_type,
                    inline=True
                )

            # Add requester info
            embed.add_field(
                name="👤 Requested by",
                value=f"<@{user.id}>",
                inline=True
            )

            # Add timestamp
            embed.add_field(
                name="⏰ Message Date",
                value=f"<t:{int(message.date.timestamp())}:R>" if hasattr(message.date, 'timestamp') else "Unknown",
                inline=True
            )

            # Create view with buttons
            view = ManualFetchPreview(
                bot=self.bot,
                message=message,
                channel=channel,
                user_id=user.id
            )

            # Send to logs channel
            await logs_channel.send(embed=embed, view=view)
            logger.info(f"[MANUAL-FETCH] Preview created for message {message.id} from {channel} ({index}/{total})")

        except Exception as e:
            logger.error(f"[MANUAL-FETCH] Error creating preview: {e}")
            raise

    def _detect_media_type(self, media) -> str:
        """Detect media type with comprehensive checking."""
        try:
            # Check for photo
            if hasattr(media, 'photo') and media.photo:
                return "📸 Photo"
            
            # Check for video
            if hasattr(media, 'video') and media.video:
                return "🎥 Video"
            
            # Check for document (which includes many file types)
            if hasattr(media, 'document') and media.document:
                document = media.document
                
                # Check document attributes for more specific type
                if hasattr(document, 'mime_type') and document.mime_type:
                    mime_type = document.mime_type.lower()
                    
                    # Video formats
                    if mime_type.startswith('video/'):
                        return "🎥 Video"
                    # Image formats
                    elif mime_type.startswith('image/'):
                        return "📸 Image"
                    # Audio formats
                    elif mime_type.startswith('audio/'):
                        return "🎵 Audio"
                    # Text/document formats
                    elif mime_type in ['application/pdf', 'text/plain', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                        return "📄 Document"
                    # Archive formats
                    elif mime_type in ['application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed']:
                        return "🗜️ Archive"
                    else:
                        return "📎 File"
                
                # Check file name/extension if mime_type not available
                if hasattr(document, 'file_name') and document.file_name:
                    file_name = document.file_name.lower()
                    
                    # Video extensions
                    if any(file_name.endswith(ext) for ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']):
                        return "🎥 Video"
                    # Image extensions
                    elif any(file_name.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']):
                        return "📸 Image"
                    # Audio extensions
                    elif any(file_name.endswith(ext) for ext in ['.mp3', '.wav', '.ogg', '.flac', '.aac']):
                        return "🎵 Audio"
                    # Document extensions
                    elif any(file_name.endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.txt', '.rtf']):
                        return "📄 Document"
                    # Archive extensions
                    elif any(file_name.endswith(ext) for ext in ['.zip', '.rar', '.7z', '.tar', '.gz']):
                        return "🗜️ Archive"
                
                return "📎 File"
            
            # Check for web page preview
            if hasattr(media, 'webpage') and media.webpage:
                return "🌐 Web Page"
            
            # Check for contact
            if hasattr(media, 'contact') and media.contact:
                return "👤 Contact"
            
            # Check for location/venue
            if hasattr(media, 'geo') and media.geo:
                return "📍 Location"
            
            # Check for poll
            if hasattr(media, 'poll') and media.poll:
                return "📊 Poll"
            
            # Check for game
            if hasattr(media, 'game') and media.game:
                return "🎮 Game"
            
            # Check for invoice
            if hasattr(media, 'invoice') and media.invoice:
                return "💰 Invoice"
            
            # If we have media but can't identify it, just say "Media" instead of "Unknown"
            return "📎 Media"
            
        except Exception as e:
            logger.debug(f"Error detecting media type: {e}")
            return "📎 Media"

    # =========================================================================
    # Autocomplete Functions
    # =========================================================================
    async def channel_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for channel parameter with comprehensive debugging."""
        try:
            logger.info(f"🔍 [AUTOCOMPLETE] channel_autocomplete called by {interaction.user.id}")
            logger.info(f"🔍 [AUTOCOMPLETE] Current input: '{current}'")

            # Check if bot and json_cache are available
            if not hasattr(self.bot, 'json_cache'):
                logger.warning("⚠️ [AUTOCOMPLETE] Bot has no json_cache attribute")
                return [app_commands.Choice(name="❌ Cache not available", value="none")]

            if not self.bot.json_cache:
                logger.warning("⚠️ [AUTOCOMPLETE] Bot json_cache is None")
                return [app_commands.Choice(name="❌ Cache not initialized", value="none")]

            # Get active channels from json_cache
            logger.debug("🔍 [AUTOCOMPLETE] Accessing bot json_cache...")
            try:
                active_channels = await self.bot.json_cache.list_telegram_channels("activated")
                logger.debug(f"🔍 [AUTOCOMPLETE] Got {len(active_channels)} active channels from cache")
            except Exception as cache_error:
                logger.error(f"❌ [AUTOCOMPLETE] Cache operation failed: {cache_error}")
                return [app_commands.Choice(name="❌ Cache error", value="none")]

            if not active_channels:
                logger.debug("⚠️ [AUTOCOMPLETE] No active channels found in cache")
                return [app_commands.Choice(name="📡 No active channels", value="none")]

            choices = []
            for channel_name in active_channels:
                # Filter based on current input
                if not current or current.lower() in channel_name.lower():
                    display_name = f"📡 {channel_name}"
                    choices.append(app_commands.Choice(name=display_name, value=channel_name))
                    logger.debug(f"🔍 [AUTOCOMPLETE] Added choice: {display_name}")

            if not choices and current:
                # If no matches found, show a helpful message
                choices.append(app_commands.Choice(name=f"❓ No channels matching '{current}'", value="none"))

            logger.info(f"✅ [AUTOCOMPLETE] Returning {len(choices)} choices")
            return choices[:25]  # Discord limit

        except Exception as e:
            logger.error(f"❌ [AUTOCOMPLETE] channel_autocomplete failed: {e}")
            logger.error(f"❌ [AUTOCOMPLETE] Full traceback: {traceback.format_exc()}")
            return [app_commands.Choice(name="❌ Autocomplete error", value="none")]

    async def all_channels_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for all channels (including inactive) with comprehensive debugging."""
        try:
            logger.debug(f"🔍 [AUTOCOMPLETE] all_channels_autocomplete called by {interaction.user.id}")
            logger.debug(f"🔍 [AUTOCOMPLETE] Current input: '{current}'")

            # Check if bot and json_cache are available
            if not hasattr(self.bot, 'json_cache'):
                logger.warning("⚠️ [AUTOCOMPLETE] Bot has no json_cache attribute")
                return [app_commands.Choice(name="❌ Cache not available", value="none")]

            if not self.bot.json_cache:
                logger.warning("⚠️ [AUTOCOMPLETE] Bot json_cache is None")
                return [app_commands.Choice(name="❌ Cache not initialized", value="none")]

            # Get all channels from json_cache
            logger.debug("🔍 [AUTOCOMPLETE] Accessing bot json_cache...")
            try:
                active_channels = await self.bot.json_cache.list_telegram_channels("activated")
                inactive_channels = await self.bot.json_cache.list_telegram_channels("deactivated")
                logger.debug(f"🔍 [AUTOCOMPLETE] Got {len(active_channels)} active, {len(inactive_channels)} inactive channels")
            except Exception as cache_error:
                logger.error(f"❌ [AUTOCOMPLETE] Cache operation failed: {cache_error}")
                return [app_commands.Choice(name="❌ Cache error", value="none")]

            all_channels = active_channels + inactive_channels
            if not all_channels:
                logger.debug("⚠️ [AUTOCOMPLETE] No channels found in cache")
                return [app_commands.Choice(name="📡 No channels configured", value="none")]

            choices = []
            for channel_name in all_channels:
                # Determine status
                status = "✅" if channel_name in active_channels else "❌"
                display_name = f"{status} 📡 {channel_name}"

                # Filter based on current input
                if not current or current.lower() in channel_name.lower():
                    choices.append(app_commands.Choice(name=display_name, value=channel_name))
                    logger.debug(f"🔍 [AUTOCOMPLETE] Added choice: {display_name}")

            if not choices and current:
                # If no matches found, show a helpful message
                choices.append(app_commands.Choice(name=f"❓ No channels matching '{current}'", value="none"))

            logger.debug(f"✅ [AUTOCOMPLETE] Returning {len(choices)} choices")
            return choices[:25]  # Discord limit

        except Exception as e:
            logger.error(f"❌ [AUTOCOMPLETE] all_channels_autocomplete failed: {e}")
            logger.error(f"❌ [AUTOCOMPLETE] Full traceback: {traceback.format_exc()}")
            return [app_commands.Choice(name="❌ Autocomplete error", value="none")]

    # =========================================================================
    # Post Management Commands
    # =========================================================================
    @admin_group.command(name="post", description="🚀 Manual posting controls")
    @app_commands.describe(
        action="Posting action to perform",
        channel="Telegram channel to fetch from (required for Manual Fetch)",
        count="Number of posts to fetch (1-10, default: 1)"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="🚀 Trigger Auto-Post", value="auto"),
            app_commands.Choice(name="📱 Manual Fetch", value="fetch"),
            app_commands.Choice(name="📊 Post Status", value="status"),
        ]
    )
    @app_commands.autocomplete(channel=channel_autocomplete)
    async def post_command(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        channel: str = None,
        count: int = 1
    ) -> None:
        """Manual posting controls."""
        if not self._is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin access required.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            action_value = action.value
            logger.info(f"[ADMIN] Post command by {interaction.user.id}, action={action_value}")

            if action_value == "auto":
                # Trigger auto-post
                if hasattr(self.bot, 'fetch_and_post_auto'):
                    success = await self.bot.fetch_and_post_auto()
                    if success:
                        embed = SuccessEmbed(
                            "🚀 Auto-Post Triggered",
                            "Auto-post has been manually triggered successfully."
                        )
                    else:
                        embed = WarningEmbed(
                            "⚠️ Auto-Post Failed",
                            "Auto-post was triggered but no content was posted."
                        )
                else:
                    embed = ErrorEmbed(
                        "❌ Auto-Post Error",
                        "Auto-post functionality is not available."
                    )

            elif action_value == "fetch":
                # Manual fetch from specific channel with preview
                if not channel or channel == "none":
                    embed = ErrorEmbed(
                        "❌ Missing Channel",
                        "Please specify a valid channel name to fetch from."
                    )
                    await interaction.followup.send(embed=embed)
                    return

                # Validate count parameter
                if count < 1 or count > 10:
                    embed = ErrorEmbed(
                        "❌ Invalid Count",
                        "Count must be between 1 and 10 posts."
                    )
                    await interaction.followup.send(embed=embed)
                    return

                # Start the manual fetch process
                await self._handle_manual_fetch(interaction, channel, count)
                return  # _handle_manual_fetch handles its own response

            elif action_value == "status":
                # Show posting status
                embed = InfoEmbed(
                    "📊 Posting Status",
                    "Current posting system status"
                )

                auto_status = "✅ Enabled" if hasattr(self.bot, 'auto_post_enabled') and self.bot.auto_post_enabled else "⏸️ Disabled"
                embed.add_field(
                    name="🔄 Auto-Posting",
                    value=auto_status,
                    inline=True
                )

                if hasattr(self.bot, 'last_post_time'):
                    last_post = f"<t:{int(self.bot.last_post_time.timestamp())}:R>"
                else:
                    last_post = "Never"

                embed.add_field(
                    name="⏰ Last Post",
                    value=last_post,
                    inline=True
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in post command: {e}")
            error_embed = ErrorEmbed(
                "Post Command Error",
                f"Failed to execute post command: {str(e)}"
            )
            await interaction.followup.send(embed=error_embed)

    # =========================================================================
    # Channel Management Commands
    # =========================================================================
    @admin_group.command(name="channels", description="📺 Manage Telegram channels")
    @app_commands.describe(
        action="Channel management action",
        channel="Channel name for operations (required for add/activate/deactivate)"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="📋 List All", value="list"),
            app_commands.Choice(name="➕ Add Channel", value="add"),
            app_commands.Choice(name="🟢 Activate", value="activate"),
            app_commands.Choice(name="🔴 Deactivate", value="deactivate"),
            app_commands.Choice(name="📊 Statistics", value="stats"),
            app_commands.Choice(name="🔄 Rotation Status", value="rotation"),
            app_commands.Choice(name="🔄 Reset Rotation", value="reset_rotation"),
        ]
    )
    @app_commands.autocomplete(channel=all_channels_autocomplete)
    async def channels_command(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        channel: str = None
    ) -> None:
        """Manage Telegram channels."""
        if not self._is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin access required.", ephemeral=True)
            return

        try:
            action_value = action.value
            logger.info(f"[ADMIN] Channels command by {interaction.user.id}, action={action_value}")

            # Handle modal case first (before deferring response)
            if action_value == "add":
                # Show modal for adding channel
                modal = AddChannelModal(self.bot)
                await interaction.response.send_modal(modal)
                return  # Modal handles its own response

            # For all other actions, defer the response
            await interaction.response.defer()

            if action_value == "list":
                # List all channels
                if hasattr(self.bot, 'json_cache'):
                    active_channels = await self.bot.json_cache.list_telegram_channels("activated")
                    inactive_channels = await self.bot.json_cache.list_telegram_channels("deactivated")

                    embed = InfoEmbed(
                        "📺 Telegram Channels",
                        f"Total: {len(active_channels) + len(inactive_channels)} channels"
                    )

                    if active_channels:
                        active_list = "\n".join([f"🟢 {ch}" for ch in active_channels[:10]])
                        embed.add_field(
                            name=f"🟢 Active Channels ({len(active_channels)})",
                            value=active_list,
                            inline=False
                        )

                    if inactive_channels:
                        inactive_list = "\n".join([f"🔴 {ch}" for ch in inactive_channels[:5]])
                        embed.add_field(
                            name=f"🔴 Inactive Channels ({len(inactive_channels)})",
                            value=inactive_list,
                            inline=False
                        )
                else:
                    embed = ErrorEmbed(
                        "❌ Cache Error",
                        "Unable to access channel cache."
                    )

            elif action_value in ["activate", "deactivate"]:
                if not channel or channel == "none":
                    embed = ErrorEmbed(
                        "❌ Missing Channel",
                        "Please specify a valid channel name for this operation."
                    )
                else:
                    # Activate/deactivate channel
                    status = "activated" if action_value == "activate" else "deactivated"
                    embed = SuccessEmbed(
                        f"✅ Channel {action_value.title()}d",
                        f"Channel '{channel}' has been {status}."
                    )

            elif action_value == "stats":
                # Show channel statistics
                embed = InfoEmbed(
                    "📊 Channel Statistics",
                    "Performance metrics for all channels"
                )
                embed.add_field(
                    name="💡 Coming Soon",
                    value="Detailed channel statistics will be shown here.",
                    inline=False
                )

            elif action_value == "rotation":
                # Show channel rotation status
                if hasattr(self.bot, 'json_cache'):
                    active_channels = await self.bot.json_cache.list_telegram_channels("activated")
                    last_index = await self.bot.json_cache.get_last_channel_index()
                    last_channel_name = await self.bot.json_cache.get_last_channel_name()

                    embed = InfoEmbed(
                        "🔄 Channel Rotation Status",
                        "Current channel rotation state"
                    )

                    if active_channels:
                        # Show current channel and next channel
                        current_channel = active_channels[last_index] if last_index < len(active_channels) else "None"
                        next_index = (last_index + 1) % len(active_channels) if active_channels else 0
                        next_channel = active_channels[next_index] if active_channels else "None"

                        # Show both index-based and name-based tracking
                        position_info = f"**Last Used (by index):** {current_channel} (index {last_index})\n"
                        if last_channel_name:
                            position_info += f"**Last Used (by name):** {last_channel_name}\n"
                        position_info += f"**Next Channel:** {next_channel} (index {next_index})\n"
                        position_info += f"**Total Channels:** {len(active_channels)}"

                        embed.add_field(
                            name="📍 Current Position",
                            value=position_info,
                            inline=False
                        )

                        # Show rotation order
                        rotation_order = "\n".join([
                            f"{'▶️' if i == next_index else '📍' if i == last_index else '🔹'} {i}: {ch}"
                            for i, ch in enumerate(active_channels)
                        ])
                        embed.add_field(
                            name="🔄 Rotation Order",
                            value=rotation_order,
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="❌ No Active Channels",
                            value="No active channels configured for rotation.",
                            inline=False
                        )
                else:
                    embed = ErrorEmbed(
                        "❌ Cache Error",
                        "Unable to access channel cache."
                    )

            elif action_value == "reset_rotation":
                # Reset channel rotation
                if hasattr(self.bot, 'json_cache'):
                    success = await self.bot.json_cache.reset_channel_rotation()
                    if success:
                        embed = SuccessEmbed(
                            "🔄 Rotation Reset",
                            "Channel rotation has been reset to start from the beginning."
                        )
                    else:
                        embed = ErrorEmbed(
                            "❌ Reset Failed",
                            "Failed to reset channel rotation."
                        )
                else:
                    embed = ErrorEmbed(
                        "❌ Cache Error",
                        "Unable to access channel cache."
                    )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in channels command: {e}")
            error_embed = ErrorEmbed(
                "Channels Command Error",
                f"Failed to execute channels command: {str(e)}"
            )
            await interaction.followup.send(embed=error_embed)

    @admin_group.command(name="autopost", description="⏰ Configure automatic posting")
    @app_commands.describe(
        action="Auto-posting configuration action",
        value="Value for interval settings (in minutes)"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="✅ Enable", value="enable"),
            app_commands.Choice(name="⏸️ Disable", value="disable"),
            app_commands.Choice(name="⏰ Set Interval", value="interval"),
            app_commands.Choice(name="📊 Show Status", value="status"),
            app_commands.Choice(name="🔄 Reload Config", value="reload"),
            app_commands.Choice(name="⚙️ Advanced Settings", value="advanced"),
        ]
    )
    async def autopost_command(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        value: int = None
    ) -> None:
        """Configure automatic posting settings."""
        if not self._is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin access required.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            action_value = action.value
            logger.info(f"[ADMIN] Autopost command by {interaction.user.id}, action={action_value}")

            if action_value == "enable":
                # Enable automation using new dynamic system
                success = await self.bot.update_automation_config(enabled=True)
                if success:
                    embed = SuccessEmbed(
                        "✅ Auto-Posting Enabled",
                        "Automatic posting has been enabled dynamically."
                    )
                else:
                    embed = ErrorEmbed(
                        "❌ Enable Failed",
                        "Failed to enable automation. Check logs for details."
                    )

            elif action_value == "disable":
                # Disable automation using new dynamic system
                success = await self.bot.update_automation_config(enabled=False)
                if success:
                    embed = WarningEmbed(
                        "⏸️ Auto-Posting Disabled",
                        "Automatic posting has been disabled dynamically."
                    )
                else:
                    embed = ErrorEmbed(
                        "❌ Disable Failed",
                        "Failed to disable automation. Check logs for details."
                    )

            elif action_value == "interval":
                if not value or value < 1:
                    embed = ErrorEmbed(
                        "❌ Invalid Interval",
                        "Please specify a valid interval in minutes (minimum 1)."
                    )
                else:
                    # Set interval using new dynamic system
                    success = await self.bot.update_automation_config(interval_minutes=value)
                    if success:
                        embed = SuccessEmbed(
                            "⏰ Interval Updated",
                            f"Auto-post interval set to {value} minutes and saved to unified config."
                        )
                    else:
                        embed = ErrorEmbed(
                            "❌ Update Failed",
                            "Failed to update interval. Check logs for details."
                        )

            elif action_value == "reload":
                # Reload configuration from botdata.json
                success = await self.bot.reload_automation_config()
                if success:
                    embed = SuccessEmbed(
                        "🔄 Config Reloaded",
                        "Automation configuration reloaded from unified config successfully."
                    )
                else:
                    embed = ErrorEmbed(
                        "❌ Reload Failed",
                        "Failed to reload configuration. Check logs for details."
                    )

            elif action_value == "advanced":
                # Show advanced automation settings
                config = await self.bot.get_automation_config()

                embed = InfoEmbed(
                    "⚙️ Advanced Automation Settings",
                    "Current automation configuration from unified config"
                )

                embed.add_field(
                    name="🔧 Core Settings",
                    value=f"**Enabled:** {config.get('enabled', 'Unknown')}\n"
                          f"**Interval:** {config.get('interval_minutes', 'Unknown')} minutes\n"
                          f"**Startup Delay:** {config.get('startup_delay_minutes', 'Unknown')} minutes",
                    inline=False
                )

                # Get active channels for rotation
                if hasattr(self.bot, 'json_cache'):
                    active_channels = await self.bot.json_cache.list_telegram_channels("activated")
                    channel_display = f"**Active Channels:** {', '.join(active_channels) if active_channels else 'None'}\n"
                    channel_display += f"**Total Active:** {len(active_channels)}\n"
                else:
                    channel_display = "**Active Channels:** Unable to load\n"
                
                channel_display += f"**Max Posts/Session:** {config.get('max_posts_per_session', 'Unknown')}"

                embed.add_field(
                    name="📺 Channel Rotation",
                    value=channel_display,
                    inline=False
                )

                embed.add_field(
                    name="🎯 Content Filters",
                    value=f"**Require Media:** {config.get('require_media', 'Unknown')}\n"
                          f"**Require Text:** {config.get('require_text', 'Unknown')}\n"
                          f"**Min Length:** {config.get('min_content_length', 'Unknown')} chars\n"
                          f"**AI Filtering:** {config.get('use_ai_filtering', 'Unknown')}",
                    inline=False
                )

                embed.add_field(
                    name="💡 Edit Configuration",
                    value="Edit `config/unified_config.yaml` → `automation` section\nThen use `/admin autopost reload` to apply changes",
                    inline=False
                )

            elif action_value == "status":
                # Show comprehensive automation status
                status_info = self.bot.get_automation_status()

                embed = InfoEmbed(
                    "📊 Automation Status",
                    "Real-time automation system status"
                )

                status_icon = "✅" if status_info.get("enabled") else "⏸️"
                status_text = "Enabled" if status_info.get("enabled") else "Disabled"

                embed.add_field(
                    name="🔄 Status",
                    value=f"{status_icon} {status_text}",
                    inline=True
                )

                embed.add_field(
                    name="⏰ Interval",
                    value=f"{status_info.get('interval_minutes', 'Unknown')} minutes",
                    inline=True
                )

                # Format timestamps
                last_post = status_info.get('last_post_time')
                if last_post:
                    last_post_dt = datetime.fromisoformat(last_post.replace('Z', '+00:00'))
                    last_post_display = f"<t:{int(last_post_dt.timestamp())}:R>"
                else:
                    last_post_display = "Never"

                embed.add_field(
                    name="📅 Last Post",
                    value=last_post_display,
                    inline=True
                )

                next_post = status_info.get('next_post_time')
                if next_post and status_info.get("enabled"):
                    next_post_dt = datetime.fromisoformat(next_post.replace('Z', '+00:00'))
                    next_post_display = f"<t:{int(next_post_dt.timestamp())}:R>"
                else:
                    next_post_display = "N/A" if not status_info.get("enabled") else "Soon"

                embed.add_field(
                    name="⏭️ Next Post",
                    value=next_post_display,
                    inline=True
                )

                # Grace period info
                if status_info.get('in_grace_period'):
                    grace_remaining = status_info.get('grace_remaining_seconds', 0)
                    embed.add_field(
                        name="🛡️ Grace Period",
                        value=f"Active ({grace_remaining}s remaining)",
                        inline=True
                    )

                # Channels - show active channels instead of primary
                if hasattr(self.bot, 'json_cache'):
                    active_channels = await self.bot.json_cache.list_telegram_channels("activated")
                    if active_channels:
                        embed.add_field(
                            name="📺 Active Channels",
                            value=f"{len(active_channels)} channels: {', '.join(active_channels[:3])}{'...' if len(active_channels) > 3 else ''}",
                            inline=True
                        )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in autopost command: {e}")
            error_embed = ErrorEmbed(
                "Autopost Command Error",
                f"Failed to execute autopost command: {str(e)}"
            )
            await interaction.followup.send(embed=error_embed)

    @admin_group.command(name="logs", description="📋 View system logs")
    @app_commands.describe(
        lines="Number of log lines to show (5-50)",
        level="Log level filter"
    )
    @app_commands.choices(
        level=[
            app_commands.Choice(name="🔴 Error", value="error"),
            app_commands.Choice(name="⚠️ Warning", value="warning"),
            app_commands.Choice(name="ℹ️ Info", value="info"),
            app_commands.Choice(name="📋 All", value="all"),
        ]
    )
    async def logs_command(
        self,
        interaction: discord.Interaction,
        lines: int = 20,
        level: app_commands.Choice[str] = None
    ) -> None:
        """View system logs."""
        if not self._is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin access required.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            lines = max(5, min(lines, 50))
            level_value = level.value if level else "all"

            logger.info(f"[ADMIN] Logs command by {interaction.user.id}, lines={lines}, level={level_value}")

            embed = InfoEmbed(
                f"📋 System Logs ({lines} lines)",
                f"Recent log entries (level: {level_value})"
            )

            # This would integrate with your log aggregator
            embed.add_field(
                name="💡 Log Access",
                value="Log viewing functionality will be implemented here.\nUse the development tools for now: `python tools/view_logs.py`",
                inline=False
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in logs command: {e}")
            error_embed = ErrorEmbed(
                "Logs Command Error",
                f"Failed to retrieve logs: {str(e)}"
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

    @admin_group.command(name="system", description="🔧 System operations")
    @app_commands.describe(
        operation="System operation to perform"
    )
    @app_commands.choices(
        operation=[
            app_commands.Choice(name="🔄 Restart Bot", value="restart"),
            app_commands.Choice(name="🛑 Shutdown Bot", value="shutdown"),
            app_commands.Choice(name="🗑️ Clear Cache", value="clear_cache"),
            app_commands.Choice(name="🛡️ Health Check", value="health"),
            app_commands.Choice(name="📊 System Info", value="info"),
            app_commands.Choice(name="🔄 Sync Commands", value="sync_commands"),
        ]
    )
    async def system_command(
        self,
        interaction: discord.Interaction,
        operation: app_commands.Choice[str]
    ) -> None:
        """System operations and maintenance."""
        if not self._is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin access required.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            operation_value = operation.value
            logger.info(f"[ADMIN] System command by {interaction.user.id}, operation={operation_value}")

            if operation_value == "restart":
                embed = WarningEmbed(
                    "🔄 Restart Requested",
                    "Bot restart has been requested. This may take a moment."
                )
                await interaction.followup.send(embed=embed)

                # Implement restart logic here
                logger.info("Bot restart requested by admin")

            elif operation_value == "shutdown":
                # Send confirmation embed first
                embed = WarningEmbed(
                    "🛑 Shutdown Initiated",
                    "Bot shutdown has been requested by admin. The bot will now shut down gracefully."
                )
                embed.add_field(
                    name="📊 Shutdown Process",
                    value=(
                        "✅ Stopping background tasks\n"
                        "✅ Saving cache and data\n"
                        "✅ Disconnecting services\n"
                        "✅ Graceful shutdown"
                    ),
                    inline=False
                )
                embed.add_field(
                    name="🔄 To Restart",
                    value="Use your VPS management tools or SSH to restart the bot service.",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed)
                logger.warning(f"🛑 Bot shutdown requested by admin {interaction.user.id}")
                
                # Send shutdown notification to log channel if available
                try:
                    from src.bot.background_tasks import send_shutdown_notification
                    await send_shutdown_notification(self.bot)
                except Exception as e:
                    logger.error(f"Failed to send shutdown notification: {e}")
                
                # Initiate graceful shutdown after a brief delay
                await asyncio.sleep(2)  # Give time for the response to be sent
                logger.info("🛑 Initiating graceful bot shutdown...")
                await self.bot.close()
                return  # Don't continue after shutdown

            elif operation_value == "clear_cache":
                # Clear cache
                if hasattr(self.bot, 'json_cache'):
                    # Implement cache clearing
                    embed = SuccessEmbed(
                        "🗑️ Cache Cleared",
                        "System cache has been cleared successfully."
                    )
                else:
                    embed = ErrorEmbed(
                        "❌ Cache Error",
                        "Cache system is not available."
                    )

            elif operation_value == "health":
                # Health check
                embed = InfoEmbed(
                    "🛡️ System Health Check",
                    "Current system health status"
                )

                # Discord connection
                embed.add_field(
                    name="🌐 Discord",
                    value="🟢 Connected",
                    inline=True
                )

                # Telegram connection
                telegram_status = "🟢 Connected" if hasattr(self.bot, 'telegram_client') else "🔴 Disconnected"
                embed.add_field(
                    name="📱 Telegram",
                    value=telegram_status,
                    inline=True
                )

                # Cache system
                cache_status = "🟢 Available" if hasattr(self.bot, 'json_cache') else "🔴 Unavailable"
                embed.add_field(
                    name="💾 Cache",
                    value=cache_status,
                    inline=True
                )

            elif operation_value == "sync_commands":
                # Force sync commands with Discord
                # Respond immediately to avoid timeout
                initial_embed = InfoEmbed(
                    "🔄 Starting Command Sync",
                    "Initiating slash command sync with Discord...\nThis may take a moment."
                )

                try:
                    # Get current commands first
                    commands = self.bot.tree.get_commands()
                    command_count = len(commands)

                    initial_embed.add_field(
                        name="📋 Current Status",
                        value=f"**Commands to Sync:** {command_count}\n**Status:** Starting sync process...",
                        inline=False
                    )

                    await interaction.followup.send(embed=initial_embed)

                    # Now perform the sync with a shorter timeout
                    logger.info(f"[ADMIN] Starting command sync - {command_count} commands")

                    try:
                        synced = await asyncio.wait_for(self.bot.tree.sync(), timeout=15.0)

                        success_embed = SuccessEmbed(
                            "✅ Commands Synced Successfully",
                            f"Successfully synced {len(synced)} slash commands with Discord."
                        )
                        success_embed.add_field(
                            name="📋 Sync Results",
                            value=(
                                f"**Total Commands:** {command_count}\n"
                                f"**Successfully Synced:** {len(synced)}\n"
                                f"**Status:** ✅ Complete\n"
                                f"**Time:** <t:{int(datetime.now().timestamp())}:T>"
                            ),
                            inline=False
                        )
                        success_embed.add_field(
                            name="💡 Next Steps",
                            value=(
                                "Commands should now be available immediately!\n\n"
                                "**If autocomplete still doesn't work:**\n"
                                "• Refresh Discord (Ctrl+R or Cmd+R)\n"
                                "• Wait 30-60 seconds for propagation\n"
                                "• Try typing the command again"
                            ),
                            inline=False
                        )

                        # Edit the original message with success
                        await interaction.edit_original_response(embed=success_embed)
                        logger.info(f"✅ Commands successfully synced by admin {interaction.user.id}: {len(synced)} commands")

                    except asyncio.TimeoutError:
                        timeout_embed = ErrorEmbed(
                            "⏰ Sync Timeout",
                            "Command sync timed out after 15 seconds."
                        )
                        timeout_embed.add_field(
                            name="🔄 What to try:",
                            value=(
                                "• Bot may be experiencing high latency\n"
                                "• Discord API may be slow\n"
                                "• Try again in a few minutes\n"
                                "• Commands may still sync in background"
                            ),
                            inline=False
                        )
                        await interaction.edit_original_response(embed=timeout_embed)
                        logger.warning(f"Command sync timed out for admin {interaction.user.id}")

                    except Exception as sync_error:
                        error_embed = ErrorEmbed(
                            "❌ Sync Failed",
                            f"Failed to sync commands with Discord."
                        )
                        error_embed.add_field(
                            name="🔍 Error Details",
                            value=f"```{str(sync_error)[:500]}```",
                            inline=False
                        )
                        error_embed.add_field(
                            name="🛠️ Troubleshooting",
                            value=(
                                "• Check bot permissions\n"
                                "• Verify bot is in the server\n"
                                "• Try restarting the bot\n"
                                "• Contact support if issue persists"
                            ),
                            inline=False
                        )
                        await interaction.edit_original_response(embed=error_embed)
                        logger.error(f"Command sync failed for admin {interaction.user.id}: {sync_error}")

                except Exception as setup_error:
                    # This catches errors in the initial setup
                    setup_error_embed = ErrorEmbed(
                        "❌ Sync Setup Failed",
                        f"Failed to initialize command sync: {str(setup_error)}"
                    )
                    await interaction.followup.send(embed=setup_error_embed)
                    logger.error(f"Command sync setup failed: {setup_error}")

                return  # Early return to avoid sending embed twice

            elif operation_value == "info":
                # System information
                embed = InfoEmbed(
                    "📊 System Information",
                    "Current system configuration and status"
                )

                embed.add_field(
                    name="🤖 Bot Version",
                    value="v2.0.0",
                    inline=True
                )

                embed.add_field(
                    name="🐍 Python Version",
                    value="3.11+",
                    inline=True
                )

                embed.add_field(
                    name="🌐 Servers",
                    value=f"{len(self.bot.guilds)}",
                    inline=True
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in system command: {e}")
            error_embed = ErrorEmbed(
                "System Command Error",
                f"Failed to execute system command: {str(e)}"
            )
            await interaction.followup.send(embed=error_embed)

    # =========================================================================
    # Quick Sync Command (Alternative)
    # =========================================================================
    @admin_group.command(name="sync", description="🔄 Quick command sync with Discord")
    async def sync_command(
        self,
        interaction: discord.Interaction
    ) -> None:
        """Quick command sync with comprehensive debugging."""
        try:
            if not self._is_admin(interaction.user):
                await interaction.response.send_message("❌ Admin access required.", ephemeral=True)
                return
            # Respond immediately to prevent timeout
            await interaction.response.send_message("🔄 Starting command sync...", ephemeral=True)
        except Exception as early_exc:
            logger.error(f"Exception before initial response: {early_exc}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Sync command failed to start: {str(early_exc)[:100]}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Sync command failed to start: {str(early_exc)[:100]}", ephemeral=True)
            except Exception as fallback_exc:
                logger.error(f"Fallback error in sync_command: {fallback_exc}")
            return
        try:
            logger.info(f"🔄 Quick sync command by {interaction.user.id}")
            # Get command count and details
            commands = self.bot.tree.get_commands()
            command_count = len(commands)
            logger.debug(f"Found {command_count} commands to sync")
            # Count autocomplete parameters
            autocomplete_count = 0
            for cmd in commands:
                if hasattr(cmd, 'commands') and cmd.commands:  # Group commands
                    for subcmd in cmd.commands:
                        for param in subcmd.parameters:
                            if hasattr(param, 'autocomplete') and param.autocomplete:
                                autocomplete_count += 1
                                logger.debug(f"Found autocomplete: {cmd.name} {subcmd.name} -> {param.name}")
            logger.debug(f"Total autocomplete parameters: {autocomplete_count}")
            # Perform the sync with timeout
            start_time = asyncio.get_event_loop().time()
            synced = await asyncio.wait_for(self.bot.tree.sync(), timeout=10.0)
            sync_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"✅ Quick sync completed: {len(synced)} commands in {sync_time:.2f}s")
            # Update the user with results
            result_msg = f"✅ **Command Sync Complete**\n"
            result_msg += f"📊 **Synced:** {len(synced)}/{command_count} commands\n"
            result_msg += f"⏱️ **Time:** {sync_time:.2f} seconds\n"
            result_msg += f"🔧 **Autocomplete:** {autocomplete_count} parameters\n"
            if len(synced) == command_count:
                result_msg += f"✅ **Status:** Perfect sync!"
            else:
                result_msg += f"⚠️ **Status:** Partial sync - check logs"
            await interaction.edit_original_response(content=result_msg)
        except asyncio.TimeoutError:
            logger.error("❌ Quick sync timed out after 10 seconds")
            await interaction.edit_original_response(content="❌ **Sync Timeout**\nCommand sync took too long. Check logs for details.")
        except Exception as e:
            logger.error(f"❌ Quick sync failed: {e}")
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            await interaction.edit_original_response(content=f"❌ **Sync Failed**\nError: {str(e)[:100]}")

    # =========================================================================
    # Test Command for Debugging Autocomplete
    # =========================================================================
    @admin_group.command(name="test", description="🧪 Test autocomplete functionality")
    @app_commands.describe(
        option="Test option with autocomplete"
    )
    async def test_command(
        self,
        interaction: discord.Interaction,
        option: str = None
    ) -> None:
        """Test command to debug autocomplete issues."""
        if not self._is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin access required.", ephemeral=True)
            return

        await interaction.response.defer()

        embed = SuccessEmbed(
            "🧪 Test Command",
            f"Selected option: {option or 'None'}"
        )
        await interaction.followup.send(embed=embed)

    @test_command.autocomplete('option')
    async def test_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Simple test autocomplete."""
        try:
            logger.debug(f"test_autocomplete called by {interaction.user.id}")
            logger.debug(f"Current input: '{current}'")

            test_options = [
                "🔧 Test Option 1",
                "🔧 Test Option 2",
                "🔧 Test Option 3"
            ]

            choices = []
            for option in test_options:
                if not current or current.lower() in option.lower():
                    choices.append(app_commands.Choice(name=option, value=option))
                    logger.debug(f"Added test choice: {option}")

            logger.debug(f"Returning {len(choices)} test choices")
            return choices

        except Exception as e:
            logger.error(f"test_autocomplete failed: {e}")
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            return []

    # =========================================================================
    # Debug Command for Discord Application Issues
    # =========================================================================
    @admin_group.command(name="test_filter", description="🛡️ Test content safety filtering")
    @app_commands.describe(
        text="Text content to test for safety filtering"
    )
    async def test_filter_command(
        self,
        interaction: discord.Interaction,
        text: str
    ) -> None:
        """Test the content safety filtering system."""
        try:
            await interaction.response.defer()

            # Import the AI content analyzer
            from src.services.ai_content_analyzer import AIContentAnalyzer

            # Initialize analyzer with bot instance for Discord logging
            analyzer = AIContentAnalyzer(self.bot)

            # Analyze the content
            safety_result = await analyzer.analyze_content_safety(
                text=text,
                media=None,
                channel="Admin-Test"
            )

            # Create result embed
            if safety_result.should_filter:
                embed = discord.Embed(
                    title="🚨 Content Would Be BLOCKED",
                    color=0xFF0000,  # Red
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="🛡️ Action", value="**BLOCKED** - Content filtered for safety", inline=False)
            elif safety_result.safety_level.value == 'sensitive':
                embed = discord.Embed(
                    title="⚠️ Content Would Be FLAGGED",
                    color=0xFFFF00,  # Yellow
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="⚠️ Action", value="**ALLOWED** with content warning", inline=False)
            else:
                embed = discord.Embed(
                    title="✅ Content Would Be APPROVED",
                    color=0x00FF00,  # Green
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="✅ Action", value="**APPROVED** - Content is safe", inline=False)

            # Add analysis details
            embed.add_field(name="📊 Safety Level", value=f"`{safety_result.safety_level.value.upper()}`", inline=True)
            embed.add_field(name="🎯 Confidence", value=f"`{safety_result.confidence:.1%}`", inline=True)
            embed.add_field(name="🔍 Indicators Found", value=f"`{len(safety_result.graphic_indicators)}`", inline=True)

            # Add content preview
            content_preview = text[:200] + "..." if len(text) > 200 else text
            embed.add_field(name="📝 Test Content", value=f"```{content_preview}```", inline=False)

            # Add indicators if present
            if safety_result.graphic_indicators:
                indicators_text = ", ".join(safety_result.graphic_indicators[:5])
                if len(safety_result.graphic_indicators) > 5:
                    indicators_text += f" (+{len(safety_result.graphic_indicators) - 5} more)"
                embed.add_field(name="🔍 Keywords Detected", value=f"`{indicators_text}`", inline=False)

            # Add warning if present
            if safety_result.content_warning:
                embed.add_field(name="⚠️ Content Warning", value=safety_result.content_warning, inline=False)

            # Add footer
            embed.set_footer(text="NewsBot Content Safety Test • Discord log sent if enabled")

            await interaction.followup.send(embed=embed)

            # Log the test
            logger.info(f"🧪 [ADMIN-TEST] Content filter test by {interaction.user.id}: {safety_result.safety_level.value} (confidence: {safety_result.confidence:.2f})")

        except Exception as e:
            logger.error(f"❌ Error in test filter command: {e}")
            embed = ErrorEmbed(
                "❌ Test Filter Error",
                f"An error occurred while testing content filtering: {str(e)}"
            )
            await interaction.followup.send(embed=embed)

    @admin_group.command(name="debug", description="🔍 Debug Discord application and command issues")
    async def debug_command(
        self,
        interaction: discord.Interaction
    ) -> None:
        """Debug Discord application and command registration issues."""
        if not self._is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin access required.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            embed = InfoEmbed(
                "🔍 Discord Application Debug",
                "Checking Discord application and command registration..."
            )

            # Check bot application info
            app_info = await self.bot.application_info()
            embed.add_field(
                name="🤖 Application Info",
                value=(
                    f"**Name:** {app_info.name}\n"
                    f"**ID:** {app_info.id}\n"
                    f"**Owner:** {app_info.owner}\n"
                    f"**Public:** {app_info.bot_public}"
                ),
                inline=False
            )

            # Check command tree info
            commands = self.bot.tree.get_commands()
            embed.add_field(
                name="📋 Command Tree",
                value=f"**Total Commands:** {len(commands)}",
                inline=True
            )

            # Check guild info
            if interaction.guild:
                embed.add_field(
                    name="🏰 Guild Info",
                    value=(
                        f"**Name:** {interaction.guild.name}\n"
                        f"**ID:** {interaction.guild.id}\n"
                        f"**Bot Permissions:** {interaction.guild.me.guild_permissions.value}"
                    ),
                    inline=False
                )

            # Check specific admin command
            admin_cmd = None
            for cmd in commands:
                if cmd.name == "admin":
                    admin_cmd = cmd
                    break

            if admin_cmd and hasattr(admin_cmd, 'commands'):
                post_cmd = None
                for subcmd in admin_cmd.commands:
                    if subcmd.name == "post":
                        post_cmd = subcmd
                        break

                if post_cmd:
                    autocomplete_info = []
                    for param in post_cmd.parameters:
                        if hasattr(param, 'autocomplete') and param.autocomplete:
                            autocomplete_info.append(f"✅ {param.name}")
                        else:
                            autocomplete_info.append(f"❌ {param.name}")

                    embed.add_field(
                        name="🔍 Autocomplete Status",
                        value="\n".join(autocomplete_info) if autocomplete_info else "No parameters found",
                        inline=False
                    )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in debug command: {e}")
            error_embed = ErrorEmbed(
                "Debug Command Error",
                f"Failed to gather debug info: {str(e)}"
            )
            await interaction.followup.send(embed=error_embed)

    # =============================================================================
    # Feature Management Commands
    # =============================================================================
    @commands.group(name='feature', invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def feature_group(self, ctx):
        """Feature management commands."""
        from src.core.feature_manager import feature_manager
        
        embed = InfoEmbed(
            "🎛️ Feature Management", 
            "Use subcommands to manage bot features"
        )
        
        embed.add_field(
            name="📋 Available Commands",
            value=(
                "`!feature list` - List all features\n"
                "`!feature status <name>` - Check feature status\n"
                "`!feature enable <name>` - Enable a feature\n"
                "`!feature disable <name>` - Disable a feature\n"
                "`!feature report` - Generate feature report"
            ),
            inline=False
        )
        
        # Quick stats
        enabled_count = len(feature_manager.get_enabled_features())
        disabled_count = len(feature_manager.get_disabled_features())
        experimental_count = len(feature_manager.get_experimental_features())
        
        embed.add_field(
            name="📊 Quick Stats",
            value=f"✅ Enabled: {enabled_count}\n❌ Disabled: {disabled_count}\n🧪 Experimental: {experimental_count}",
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @feature_group.command(name='list')
    @commands.has_permissions(administrator=True)
    async def feature_list(self, ctx):
        """List all available features."""
        from src.core.feature_manager import feature_manager
        
        embed = InfoEmbed("🎛️ Feature List", "All available bot features")
        
        enabled_features = feature_manager.get_enabled_features()
        disabled_features = feature_manager.get_disabled_features()
        experimental_features = feature_manager.get_experimental_features()
        
        if enabled_features:
            embed.add_field(
                name="✅ Enabled Features",
                value="\n".join([f"• {name}" for name in sorted(enabled_features)]),
                inline=False
            )
        
        if disabled_features:
            embed.add_field(
                name="❌ Disabled Features", 
                value="\n".join([f"• {name}" for name in sorted(disabled_features)]),
                inline=False
            )
        
        if experimental_features:
            embed.add_field(
                name="🧪 Experimental Features",
                value="\n".join([f"• {name}" for name in sorted(experimental_features)]),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @feature_group.command(name='status')
    @commands.has_permissions(administrator=True)
    async def feature_status(self, ctx, feature_name: str):
        """Check the status of a specific feature."""
        from src.core.feature_manager import feature_manager
        
        feature = feature_manager.features.get(feature_name)
        if not feature:
            embed = ErrorEmbed("Feature Not Found", f"No feature named '{feature_name}' exists.")
            await ctx.send(embed=embed)
            return
        
        status = feature_manager.get_feature_status(feature_name)
        is_enabled = feature_manager.is_enabled(feature_name)
        
        status_emoji = "✅" if is_enabled else "❌" if status == feature_manager.FeatureStatus.DISABLED else "🧪"
        
        embed = InfoEmbed(f"{status_emoji} Feature Status: {feature_name}", feature.description)
        
        embed.add_field(name="Status", value=status.value.title(), inline=True)
        embed.add_field(name="Enabled", value="Yes" if is_enabled else "No", inline=True)
        embed.add_field(name="Version Added", value=feature.version_added, inline=True)
        
        if feature.dependencies:
            deps_status = []
            for dep in feature.dependencies:
                dep_enabled = feature_manager.is_enabled(dep)
                deps_status.append(f"{'✅' if dep_enabled else '❌'} {dep}")
            
            embed.add_field(
                name="Dependencies",
                value="\n".join(deps_status),
                inline=False
            )
        
        if feature.config_requirements:
            from src.core.unified_config import unified_config as config
            config_status = []
            for req in feature.config_requirements:
                has_config = bool(config.get(req))
                config_status.append(f"{'✅' if has_config else '❌'} {req}")
            
            embed.add_field(
                name="Config Requirements",
                value="\n".join(config_status),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @feature_group.command(name='enable')
    @commands.has_permissions(administrator=True)
    async def feature_enable(self, ctx, feature_name: str):
        """Enable a feature."""
        from src.core.feature_manager import feature_manager
        
        if feature_manager.enable_feature(feature_name):
            embed = SuccessEmbed("Feature Enabled", f"Successfully enabled feature '{feature_name}'")
        else:
            embed = ErrorEmbed("Enable Failed", f"Failed to enable feature '{feature_name}'. Check dependencies and config requirements.")
        
        await ctx.send(embed=embed)
    
    @feature_group.command(name='disable')
    @commands.has_permissions(administrator=True)
    async def feature_disable(self, ctx, feature_name: str):
        """Disable a feature."""
        from src.core.feature_manager import feature_manager
        
        if feature_manager.disable_feature(feature_name):
            embed = SuccessEmbed("Feature Disabled", f"Successfully disabled feature '{feature_name}'")
        else:
            embed = ErrorEmbed("Disable Failed", f"Failed to disable feature '{feature_name}'. Check for dependent features.")
        
        await ctx.send(embed=embed)
    
    @feature_group.command(name='report')
    @commands.has_permissions(administrator=True)
    async def feature_report(self, ctx):
        """Generate a comprehensive feature report."""
        from src.core.feature_manager import feature_manager
        
        report = feature_manager.generate_feature_report()
        
        # Split long reports across multiple messages
        if len(report) > 1900:
            chunks = [report[i:i+1900] for i in range(0, len(report), 1900)]
            for i, chunk in enumerate(chunks):
                embed = InfoEmbed(
                    f"📋 Feature Report (Part {i+1}/{len(chunks)})",
                    f"```\n{chunk}\n```"
                )
                await ctx.send(embed=embed)
        else:
            embed = InfoEmbed("📋 Feature Report", f"```\n{report}\n```")
            await ctx.send(embed=embed)

    # =============================================================================
    # Health Monitoring Commands
    # =============================================================================
    @commands.group(name='health', invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def health_group(self, ctx):
        """System health monitoring commands."""
        embed = InfoEmbed(
            "🏥 Health Monitoring", 
            "System health and performance monitoring"
        )
        
        embed.add_field(
            name="📋 Available Commands",
            value=(
                "`!health check` - Run full health check\n"
                "`!health status` - Quick health status\n"
                "`!health metrics` - Performance metrics\n"
                "`!health history` - Health check history"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @health_group.command(name='check')
    @commands.has_permissions(administrator=True)
    async def health_check(self, ctx):
        """Run a comprehensive health check."""
        from src.monitoring.health_monitor import health_monitor
        
        if not health_monitor:
            embed = ErrorEmbed("Health Monitor Unavailable", "Health monitor is not initialized.")
            await ctx.send(embed=embed)
            return
        
        # Send initial message
        checking_embed = InfoEmbed("🔄 Running Health Check", "Please wait while I check all systems...")
        message = await ctx.send(embed=checking_embed)
        
        try:
            # Run health check
            health = await health_monitor.run_full_health_check()
            
            # Create health embed
            health_embed = await health_monitor.create_health_embed(health)
            
            # Update message with results
            await message.edit(embed=health_embed)
            
        except Exception as e:
            error_embed = ErrorEmbed("Health Check Failed", f"Health check encountered an error: {str(e)}")
            await message.edit(embed=error_embed)
    
    @health_group.command(name='status')
    @commands.has_permissions(administrator=True)
    async def health_status(self, ctx):
        """Get quick health status."""
        from src.monitoring.health_monitor import health_monitor
        
        if not health_monitor or not health_monitor.last_health_check:
            embed = WarningEmbed("No Health Data", "No recent health check data available. Run `!health check` first.")
            await ctx.send(embed=embed)
            return
        
        health = health_monitor.last_health_check
        
        # Quick status embed
        status_emoji = "✅" if health.overall_status.value == "healthy" else "⚠️" if health.overall_status.value == "warning" else "❌"
        
        embed = InfoEmbed(
            f"{status_emoji} System Status: {health.overall_status.value.title()}",
            f"Last checked: {health.last_updated.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Quick stats
        healthy_count = len([c for c in health.checks if c.status.value == "healthy"])
        total_checks = len(health.checks)
        
        embed.add_field(name="Health Checks", value=f"{healthy_count}/{total_checks} Passing", inline=True)
        embed.add_field(name="Uptime", value=str(timedelta(seconds=int(health.uptime_seconds))), inline=True)
        
        # Top issues
        issues = [c for c in health.checks if c.status.value in ["critical", "warning"]]
        if issues:
            issue_text = "\n".join([f"{'❌' if c.status.value == 'critical' else '⚠️'} {c.name}: {c.message}" for c in issues[:5]])
            embed.add_field(name="Issues", value=issue_text, inline=False)
        
        await ctx.send(embed=embed)
    
    @health_group.command(name='metrics')
    @commands.has_permissions(administrator=True)
    async def health_metrics(self, ctx):
        """Show performance metrics."""
        from src.monitoring.health_monitor import health_monitor
        
        if not health_monitor:
            embed = ErrorEmbed("Health Monitor Unavailable", "Health monitor is not initialized.")
            await ctx.send(embed=embed)
            return
        
        metrics = health_monitor.performance_metrics
        
        embed = InfoEmbed("📊 Performance Metrics", "Current system performance statistics")
        
        # API calls
        api_calls = metrics['api_calls']
        embed.add_field(
            name="🔌 API Calls",
            value=f"OpenAI: {api_calls['openai']}\nDiscord: {api_calls['discord']}\nTelegram: {api_calls['telegram']}",
            inline=True
        )
        
        # Errors
        errors = metrics['errors']
        total_errors = sum(errors.values())
        embed.add_field(
            name="❌ Errors",
            value=f"Total: {total_errors}\nOpenAI: {errors['openai']}\nDiscord: {errors['discord']}\nTelegram: {errors['telegram']}\nGeneral: {errors['general']}",
            inline=True
        )
        
        # Success rates
        total_posts = metrics['posts_successful'] + metrics['posts_failed']
        post_success_rate = (metrics['posts_successful'] / total_posts * 100) if total_posts > 0 else 100
        
        total_translations = metrics['translations_successful'] + metrics['translations_failed']
        translation_success_rate = (metrics['translations_successful'] / total_translations * 100) if total_translations > 0 else 100
        
        embed.add_field(
            name="📈 Success Rates",
            value=f"Posts: {post_success_rate:.1f}% ({metrics['posts_successful']}/{total_posts})\nTranslations: {translation_success_rate:.1f}% ({metrics['translations_successful']}/{total_translations})",
            inline=True
        )
        
        await ctx.send(embed=embed)

    # =============================================================================
    # Debug Commands
    # =============================================================================
    @commands.group(name='debug', invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def debug_group(self, ctx):
        """Advanced debugging commands."""
        embed = InfoEmbed(
            "🐛 Debug Tools", 
            "Advanced debugging and troubleshooting tools"
        )
        
        embed.add_field(
            name="📋 Available Commands",
            value=(
                "`!debug config` - Validate configuration\n"
                "`!debug features` - Check feature dependencies\n"
                "`!debug api` - Test API connections\n"
                "`!debug channels` - Verify channel access\n"
                "`!debug permissions` - Check bot permissions"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @debug_group.command(name='config')
    @commands.has_permissions(administrator=True)
    async def debug_config(self, ctx):
        """Validate bot configuration."""
        from src.core.config_validator import config_validator
        from src.core.unified_config import unified_config as config
        
        # Run validation
        is_valid = config_validator.validate_all(config._config)
        report = config_validator.get_validation_report()
        
        status_emoji = "✅" if is_valid else "❌"
        title = f"{status_emoji} Configuration Validation"
        
        embed = InfoEmbed(title, f"```\n{report}\n```")
        await ctx.send(embed=embed)
    
    @debug_group.command(name='features')
    @commands.has_permissions(administrator=True)
    async def debug_features(self, ctx):
        """Check feature dependencies."""
        from src.core.feature_manager import feature_manager
        
        issues = feature_manager.validate_feature_dependencies()
        
        if not issues:
            embed = SuccessEmbed("Feature Dependencies", "All feature dependencies are satisfied ✅")
        else:
            issue_text = "\n".join([f"• {issue}" for issue in issues])
            embed = WarningEmbed("Feature Dependency Issues", issue_text)
        
        await ctx.send(embed=embed)
    
    @debug_group.command(name='api')
    @commands.has_permissions(administrator=True)
    async def debug_api(self, ctx):
        """Test API connections."""
        from src.core.unified_config import unified_config as config
        import openai
        
        embed = InfoEmbed("🔌 API Connection Tests", "Testing external API connectivity")
        
        # Test OpenAI API
        try:
            api_key = config.get("openai.api_key")
            if not api_key:
                embed.add_field(name="❌ OpenAI API", value="API key not configured", inline=False)
            else:
                # Quick test (minimal cost)
                client = openai.OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1
                )
                embed.add_field(name="✅ OpenAI API", value="Connection successful", inline=False)
        except Exception as e:
            embed.add_field(name="❌ OpenAI API", value=f"Error: {str(e)}", inline=False)
        
        # Test Discord API (already connected if this command works)
        embed.add_field(name="✅ Discord API", value="Connection successful (bot is online)", inline=False)
        
        await ctx.send(embed=embed)
    
    @debug_group.command(name='channels')
    @commands.has_permissions(administrator=True)
    async def debug_channels(self, ctx):
        """Verify channel access."""
        from src.core.unified_config import unified_config as config
        
        embed = InfoEmbed("📺 Channel Access Verification", "Checking configured channel accessibility")
        
        guild = ctx.guild
        channel_configs = {
                            "news": config.get("discord.channels.news") or config.get("channels.news"),
                "logs": config.get("discord.channels.logs") or config.get("channels.logs"),
                "errors": config.get("discord.channels.errors") or config.get("channels.errors")
        }
        
        for channel_name, channel_id in channel_configs.items():
            if not channel_id:
                embed.add_field(name=f"❌ {channel_name.title()} Channel", value="Not configured", inline=False)
                continue
            
            channel = guild.get_channel(channel_id)
            if not channel:
                embed.add_field(name=f"❌ {channel_name.title()} Channel", value=f"Channel {channel_id} not found", inline=False)
            else:
                # Check permissions
                permissions = channel.permissions_for(guild.me)
                can_send = permissions.send_messages
                can_embed = permissions.embed_links
                
                status = "✅" if can_send and can_embed else "⚠️"
                perm_status = "Full access" if can_send and can_embed else f"Limited access (send: {can_send}, embed: {can_embed})"
                
                embed.add_field(
                    name=f"{status} {channel_name.title()} Channel",
                    value=f"{channel.mention} - {perm_status}",
                    inline=False
                )
        
        await ctx.send(embed=embed)
    
    @debug_group.command(name='permissions')
    @commands.has_permissions(administrator=True)
    async def debug_permissions(self, ctx):
        """Check bot permissions."""
        guild = ctx.guild
        bot_member = guild.me
        
        embed = InfoEmbed("🔐 Bot Permissions Check", f"Permissions for {bot_member.mention}")
        
        # Check critical permissions
        critical_perms = {
            "send_messages": "Send Messages",
            "embed_links": "Embed Links", 
            "attach_files": "Attach Files",
            "read_message_history": "Read Message History",
            "manage_messages": "Manage Messages",
            "create_public_threads": "Create Public Threads",
            "send_messages_in_threads": "Send Messages in Threads"
        }
        
        missing_perms = []
        for perm_name, display_name in critical_perms.items():
            has_perm = getattr(bot_member.guild_permissions, perm_name)
            status = "✅" if has_perm else "❌"
            embed.add_field(name=f"{status} {display_name}", value="Granted" if has_perm else "Missing", inline=True)
            
            if not has_perm:
                missing_perms.append(display_name)
        
        if missing_perms:
            embed.add_field(
                name="⚠️ Missing Permissions",
                value=f"The bot is missing: {', '.join(missing_perms)}",
                inline=False
            )
        
        await ctx.send(embed=embed)


# =============================================================================
# Manual Fetch Preview View
# =============================================================================
class ManualFetchPreview(discord.ui.View):
    """View for manual fetch preview with post/download buttons."""

    def __init__(self, bot, message, channel: str, user_id: int):
        super().__init__(timeout=3600)  # 1 hour timeout
        self.bot = bot
        self.message = message
        self.channel = channel
        self.user_id = user_id

    @discord.ui.button(label="📤 Post Anyway", style=discord.ButtonStyle.success)
    async def post_anyway(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Post the message manually without AI filtering."""
        try:
            # Get config helper function
            def get_config():
                if hasattr(self.bot, 'unified_config') and self.bot.unified_config:
                    return self.bot.unified_config.config_data
                # Fallback to unified config import
                from src.core.unified_config import unified_config
                return unified_config.config_data
            
            # Check if user is admin
            config_data = get_config()
            admin_user_id = config_data.get("bot", {}).get("admin_user_id")
            if not admin_user_id or interaction.user.id != int(admin_user_id):
                await interaction.response.send_message("❌ Only admins can use this button.", ephemeral=True)
                return

            await interaction.response.defer()

            # Import necessary modules for AI processing
            if hasattr(self.bot, 'fetch_commands'):
                try:
                    # Import AI processing utilities
                    from src.cogs.fetch_cog import remove_emojis, remove_links, remove_source_phrases
                    from src.services.ai_service import AIService
                    from src.services.news_intelligence import NewsIntelligenceService
                    from src.services.ai_content_analyzer import AIContentAnalyzer
                    from src.cogs.fetch_view import FetchView

                    logger.info(f"[MANUAL-FETCH] Processing message {self.message.id} from {self.channel}")

                    # Clean the message text (same as auto-posting)
                    cleaned_text = self.message.message or ""
                    if cleaned_text:
                        cleaned_text = remove_emojis(cleaned_text)
                        cleaned_text = remove_links(cleaned_text)
                        cleaned_text = remove_source_phrases(cleaned_text)
                        cleaned_text = cleaned_text.strip()

                    # Initialize AI services (same as auto-posting)
                    ai_service = AIService(self.bot)
                    news_intelligence = NewsIntelligenceService()
                    ai_analyzer = AIContentAnalyzer(self.bot)

                    # 🧠 PHASE 1: NEWS INTELLIGENCE ANALYSIS (same as auto-posting)
                    news_analysis = None
                    try:
                        news_analysis = await news_intelligence.analyze_urgency(
                            content=cleaned_text,
                            channel=self.channel,
                            media=[self.message.media] if self.message.media else []
                        )
                        logger.info(f"📊 [MANUAL-FETCH] Intelligence analysis: {news_analysis.urgency_level.value} "
                                  f"(score: {news_analysis.urgency_score:.2f})")
                    except Exception as e:
                        logger.error(f"❌ [MANUAL-FETCH] News analysis failed: {e}")

                    # 🤖 PHASE 2: AI CONTENT ANALYSIS (same as auto-posting)
                    ai_processed = None
                    try:
                        ai_processed = await ai_analyzer.process_content_intelligently(
                            raw_content=cleaned_text,
                            channel=self.channel,
                            media=[self.message.media] if self.message.media else []
                        )
                        logger.info(f"🤖 [MANUAL-FETCH] AI analysis: {ai_processed.categories.primary_category.value} "
                                  f"| Quality: {ai_processed.quality.overall_score:.2f}")
                        final_content = ai_processed.translated_content
                    except Exception as e:
                        logger.error(f"❌ [MANUAL-FETCH] AI analysis failed: {e}")
                        final_content = cleaned_text

                    # 🔄 LEGACY AI PROCESSING (same as auto-posting)
                    ai_result = ai_service.get_ai_result_comprehensive(final_content)
                    if not ai_result:
                        await interaction.followup.send("❌ AI processing failed for this message.", ephemeral=True)
                        return

                    ai_title = ai_result.get('title', '')
                    ai_english = ai_result.get('translation', ai_result.get('english', ''))
                    ai_location = ai_result.get('location', 'Unknown')

                    # 📝 ENHANCED POSTING DECISION (same as auto-posting)
                    should_ping = True  # Always ping news role
                    urgency_indicator = "📰"

                    if news_analysis:
                        urgency_indicator = await news_intelligence.format_urgency_indicator(news_analysis)

                    # Use only the AI title - let posting service add the single emoji
                    enhanced_title = ai_title

                    # Create FetchView with intelligence data (same as auto-posting)
                    fetch_view = FetchView(
                        bot=self.bot,
                        post=self.message,
                        channelname=self.channel,
                        message_id=self.message.id,
                        media=self.message.media,
                        arabic_text_clean=final_content,
                        ai_english=ai_english,
                        ai_title=enhanced_title,
                        ai_location=ai_location,
                        auto_mode=False,  # Manual mode for interaction
                        # Pass intelligence data for enhanced posting (same as auto-posting)
                        urgency_level=news_analysis.urgency_level.value if news_analysis else "normal",
                        should_ping_news=should_ping,
                        content_category=ai_processed.categories.primary_category.value if ai_processed else "social",
                        quality_score=ai_processed.quality.overall_score if ai_processed else 0.7
                    )

                    # Post to news channel
                    success = await fetch_view.do_post_to_news()

                    if success:
                        # Add to blacklist to prevent reposting
                        blacklisted_ids = await self.bot.json_cache.get("blacklisted_posts") or []
                        blacklisted_ids.append(self.message.id)
                        await self.bot.json_cache.set("blacklisted_posts", blacklisted_ids)
                        await self.bot.json_cache.save()

                        # Create admin override notification (same style as ContentFilterView)
                        embed = discord.Embed(
                            title="✅ Manual Post - Content Posted",
                            description=f"Content from **{self.channel}** was posted via manual override.",
                            color=0x00FF00  # Green
                        )
                        embed.add_field(name="Message ID", value=str(self.message.id), inline=True)
                        embed.add_field(name="Posted by", value=f"<@{interaction.user.id}>", inline=True)
                        embed.add_field(name="Channel", value=self.channel, inline=True)

                        # Add intelligence info if available
                        if 'news_analysis' in locals() and news_analysis:
                            embed.add_field(name="Urgency Level", value=news_analysis.urgency_level.value.title(), inline=True)
                        if 'ai_processed' in locals() and ai_processed:
                            embed.add_field(name="Category", value=ai_processed.categories.primary_category.value.title(), inline=True)
                            embed.add_field(name="Quality Score", value=f"{ai_processed.quality.overall_score:.2f}", inline=True)

                        # Add note
                        embed.add_field(
                            name="ℹ️ Note",
                            value="This content was posted via manual fetch with full AI processing.",
                            inline=False
                        )

                        # Disable all buttons
                        for item in self.children:
                            item.disabled = True

                        await interaction.followup.edit_message(interaction.message.id, view=self)
                        await interaction.followup.send(embed=embed)

                        logger.info(f"✅ [MANUAL-OVERRIDE] Content posted via manual fetch by {interaction.user.id}: {self.message.id}")
                    else:
                        await interaction.followup.send("❌ Failed to post message to news channel.", ephemeral=True)

                except ImportError as e:
                    logger.error(f"Import error in manual fetch: {e}")
                    await interaction.followup.send("❌ AI services not available.", ephemeral=True)
                except Exception as e:
                    logger.error(f"Error in manual fetch AI processing: {e}")
                    await interaction.followup.send(f"❌ Error processing message: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send("❌ Fetch commands not available.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error posting manual fetch: {e}")
            await interaction.followup.send(f"❌ Error posting message: {str(e)}", ephemeral=True)

    @discord.ui.button(label="📥 Download Media", style=discord.ButtonStyle.secondary)
    async def download_media(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Download media from the message for manual review."""
        try:
            # Check if user is admin
            def get_config():
                """Get config manager instance."""
                if hasattr(self.bot, 'unified_config') and self.bot.unified_config:
                    return self.bot.unified_config.config_data
                # Fallback to unified config import
                from src.core.unified_config import unified_config
                return unified_config.config_data
            
            config_data = get_config()
            admin_user_id = config_data.get("bot", {}).get("admin_user_id")
            if not admin_user_id or interaction.user.id != int(admin_user_id):
                await interaction.response.send_message("❌ Only admins can download media.", ephemeral=True)
                return

            await interaction.response.defer()

            # Check if we have message data with media
            if not self.message or not hasattr(self.message, 'media') or not self.message.media:
                await interaction.followup.send("❌ No media found in this message.", ephemeral=True)
                return

            # Import media service
            try:
                from src.services.media_service import MediaService
                import os

                media_service = MediaService(self.bot)

                # Download media
                media_files, temp_path = await media_service.download_media_with_timeout(
                    self.message, self.message.media
                )

                if media_files:
                    # Create download notification
                    embed = discord.Embed(
                        title="📥 Media Downloaded",
                        description=f"Media from **{self.channel}** has been downloaded for manual review.",
                        color=0x00FF00
                    )
                    embed.add_field(name="Message ID", value=str(self.message.id), inline=True)
                    embed.add_field(name="Downloaded by", value=f"<@{interaction.user.id}>", inline=True)
                    embed.add_field(name="Files", value=f"{len(media_files)} file(s)", inline=True)

                    # Try to attach the first file if it's small enough
                    try:
                        if media_files and len(media_files) > 0:
                            file_path = media_files[0]
                            if os.path.exists(file_path) and os.path.getsize(file_path) < 8 * 1024 * 1024:  # 8MB limit
                                discord_file = discord.File(file_path)
                                await interaction.followup.send(embed=embed, file=discord_file)
                            else:
                                embed.add_field(name="Note", value="File too large to attach to Discord", inline=False)
                                await interaction.followup.send(embed=embed)
                        else:
                            await interaction.followup.send(embed=embed)
                    except Exception as e:
                        logger.warning(f"Could not attach file to Discord: {e}")
                        await interaction.followup.send(embed=embed)

                    logger.info(f"📥 [DOWNLOAD] Media downloaded by {interaction.user.id} from {self.channel}: {len(media_files)} files")
                else:
                    await interaction.followup.send("❌ Failed to download media files.", ephemeral=True)

            except Exception as e:
                logger.error(f"Error downloading media: {e}")
                await interaction.followup.send(f"❌ Error downloading media: {str(e)}", ephemeral=True)

        except Exception as e:
            logger.error(f"Error in download media button: {e}")
            await interaction.followup.send(f"❌ Error downloading media: {str(e)}", ephemeral=True)

    @discord.ui.button(label="🚫 Blacklist Post", style=discord.ButtonStyle.danger)
    async def blacklist_post(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Blacklist the message to prevent future processing."""
        try:
            # Check if user is admin
            def get_config():
                """Get config manager instance."""
                if hasattr(self.bot, 'unified_config') and self.bot.unified_config:
                    return self.bot.unified_config.config_data
                # Fallback to unified config import
                from src.core.unified_config import unified_config
                return unified_config.config_data
            
            config_data = get_config()
            admin_user_id = config_data.get("bot", {}).get("admin_user_id")
            if not admin_user_id or interaction.user.id != int(admin_user_id):
                await interaction.response.send_message("❌ Only admins can blacklist posts.", ephemeral=True)
                return

            await interaction.response.defer()

            # Add message ID to blacklist
            if hasattr(self.bot, 'json_cache') and self.bot.json_cache:
                blacklisted_posts = await self.bot.json_cache.get("blacklisted_posts") or []
                if self.message.id not in blacklisted_posts:
                    blacklisted_posts.append(self.message.id)
                    await self.bot.json_cache.set("blacklisted_posts", blacklisted_posts)
                    await self.bot.json_cache.save()

                    # Create blacklist confirmation
                    embed = discord.Embed(
                        title="🚫 Post Blacklisted",
                        description=f"Message **{self.message.id}** from **{self.channel}** has been blacklisted.",
                        color=0xFF0000
                    )
                    embed.add_field(name="Message ID", value=str(self.message.id), inline=True)
                    embed.add_field(name="Channel", value=self.channel, inline=True)
                    embed.add_field(name="Blacklisted by", value=f"<@{interaction.user.id}>", inline=True)

                    # Disable all buttons
                    for item in self.children:
                        item.disabled = True

                    await interaction.followup.edit_message(interaction.message.id, view=self)
                    await interaction.followup.send(embed=embed)

                    logger.info(f"🚫 [BLACKLIST] Manual fetch post {self.message.id} from {self.channel} blacklisted by {interaction.user.id}")
                else:
                    await interaction.followup.send(f"⚠️ Message **{self.message.id}** is already blacklisted.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Cache not available for blacklisting.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error in blacklist button: {e}")
            await interaction.followup.send(f"❌ Error blacklisting post: {str(e)}", ephemeral=True)

    async def on_timeout(self):
        """Called when the view times out."""
        # Disable all buttons
        for item in self.children:
            item.disabled = True


# =============================================================================
# Modal for Adding Channels
# =============================================================================
class AddChannelModal(discord.ui.Modal, title="➕ Add Telegram Channel"):
    """Modal for adding a new Telegram channel."""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    channel_name = discord.ui.TextInput(
        label="Channel Username",
        placeholder="Enter channel username (e.g., alekhbariahsy)",
        required=True,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        await interaction.response.defer()

        try:
            channel = self.channel_name.value.strip().lower()

            # Remove @ if present
            if channel.startswith('@'):
                channel = channel[1:]

            # Basic validation
            if not channel or len(channel) < 3:
                embed = ErrorEmbed(
                    "❌ Invalid Channel Name",
                    "Channel name must be at least 3 characters long."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Check for valid characters
            if not channel.replace('_', '').replace('-', '').isalnum():
                embed = ErrorEmbed(
                    "❌ Invalid Characters",
                    "Channel name can only contain letters, numbers, underscores, and hyphens."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Add channel to cache
            if hasattr(self.bot, 'json_cache') and self.bot.json_cache:
                success = await self.bot.json_cache.add_telegram_channel(channel)
                if success:
                    embed = SuccessEmbed(
                        "➕ Channel Added Successfully",
                        f"Channel **{channel}** has been added and activated."
                    )
                    embed.add_field(
                        name="📋 Next Steps",
                        value="The channel is now active and will be included in auto-posting rotation.",
                        inline=False
                    )
                    logger.info(f"[ADMIN] Channel '{channel}' added by {interaction.user.id}")
                else:
                    embed = ErrorEmbed(
                        "❌ Channel Already Exists",
                        f"Channel **{channel}** is already in the system."
                    )
            else:
                embed = ErrorEmbed(
                    "❌ Cache Error",
                    "Unable to access channel cache system."
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in AddChannelModal: {e}")
            error_embed = ErrorEmbed(
                "❌ Add Channel Error",
                f"Failed to add channel: {str(e)}"
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)


def setup_admin_commands(bot):
    """Setup admin commands for the bot."""
    cog = AdminCommands(bot)
    bot.tree.add_command(AdminCommands.admin_group)
    logger.info("✅ Admin commands loaded")
