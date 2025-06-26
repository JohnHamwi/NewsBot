# =============================================================================
# NewsBot FetchView UI Components Module
# =============================================================================
# This module contains the Discord UI components for the fetch functionality,
# using service classes for media, AI, and posting operations with comprehensive
# intelligence integration and user interaction handling.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import asyncio
import os
import traceback
from typing import Any, List, Optional

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import discord
from discord import ui

# =============================================================================
# Local Application Imports
# =============================================================================
from src.components.embeds.base_embed import BaseEmbed
from src.services.ai_service import AIService
from src.services.media_service import MediaService
from src.services.posting_service import PostingService
from src.utils import error_handler
from src.utils.base_logger import base_logger as logger

from src.utils.content_cleaner import clean_news_content
from src.utils.structured_logger import structured_logger

# =============================================================================
# Configuration Constants
# =============================================================================
# GUILD_ID and ADMIN_USER_ID will be set dynamically when needed


# =============================================================================
# FetchView Main Class
# =============================================================================
class FetchView(ui.View):
    """
    View for fetching and posting content from Telegram channels.

    Features:
    - Interactive Telegram message display
    - AI-powered translation and analysis
    - Media downloading and processing
    - Content posting to Discord channels
    - Intelligence integration with urgency levels
    - Automatic and manual operation modes
    """

    def __init__(
        self,
        bot,
        post,
        channelname,
        message_id=None,
        media=None,
        media_bytes=None,
        arabic_text_clean=None,
        ai_english=None,
        ai_title=None,
        ai_location=None,
        auto_mode=False,
        # 🧠 Intelligence parameters
        urgency_level="normal",
        should_ping_news=False,
        content_category="social",
        quality_score=0.7,
    ):
        """
        Initialize the FetchView with message data.

        Args:
            bot: The Discord bot instance
            post: The Telegram message object
            channelname: The Telegram channel name
            message_id: Optional ID of the message (will be extracted from post if not provided)
            media: Optional media object attached to the post
            media_bytes: Optional raw media bytes
            arabic_text_clean: Optional cleaned Arabic text
            ai_english: Optional AI-generated English translation
            ai_title: Optional AI-generated title
            ai_location: Optional AI-detected location
            auto_mode: Whether the view is operating in automatic mode
            urgency_level: Urgency level from news intelligence (breaking, important, normal, low)
            should_ping_news: Whether to ping the news role for breaking news
            content_category: Content category from AI analysis (politics, military, etc.)
            quality_score: Content quality score from AI analysis (0.0-1.0)
        """
        super().__init__(timeout=None)

        # Core attributes
        self.bot = bot
        self.post = post
        self.channelname = channelname
        self.auto_mode = auto_mode
        self.logger = logger

        # Message ID handling
        if message_id is not None:
            self.message_id = message_id
        elif hasattr(post, "id"):
            self.message_id = getattr(post, "id", 0)
        else:
            self.message_id = 0

        # Media handling
        if media is not None:
            self.media = media
        elif hasattr(post, "media"):
            self.media = getattr(post, "media", None)
        else:
            self.media = None

        self.media_bytes = media_bytes

        # Text content
        self.arabic_text_clean = arabic_text_clean
        self.ai_english = ai_english
        self.ai_title = ai_title
        self.ai_location = ai_location

        # 🧠 Intelligence data
        self.urgency_level = urgency_level
        self.should_ping_news = should_ping_news
        self.content_category = content_category
        self.quality_score = quality_score

        # Initialize services
        self.media_service = MediaService(bot)
        self.ai_service = AIService(bot)
        self.posting_service = PostingService(bot)

        # If auto_mode is True, buttons should be disabled
        if auto_mode:
            for item in self.children:
                item.disabled = True

        self.logger.debug(
            "[FETCH] FetchView loaded and initialized. Auto mode: %s", auto_mode
        )

    # =========================================================================
    # Content Posting Methods
    # =========================================================================
    async def do_post_to_news(
        self, interaction: Optional[discord.Interaction] = None
    ) -> bool:
        """
        Post the content to the news channel using service classes.

        Args:
            interaction: Optional Discord interaction. Required in interactive mode,
                         but can be None in auto_mode.

        Returns:
            bool: True if posting was successful, False otherwise
        """
        # Initialize context for logging
        user_id = getattr(interaction, "user", None)
        user_id = getattr(user_id, "id", "auto_mode") if user_id else "auto_mode"
        channel_id = getattr(interaction, "channel", None)
        channel_id = getattr(channel_id, "id", 0) if channel_id else 0

        self.logger.info(
            f"[FETCH][BTN][post_to_news] START post_id={self.message_id} | user={user_id} channel={channel_id}"
        )

        # Track overall success
        success = False
        media_files = []
        temp_path = None

        try:
            # Skip authorization check in auto mode (temporarily disabled for testing)
            if False:  # Temporarily disable all permission checks
                if interaction.user.id != ADMIN_USER_ID:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            "You are not authorized."
                        )
                    self.logger.error(
                        f"[FETCH][BTN][post_to_news] ERROR Unauthorized | user={user_id} channel={channel_id}"
                    )
                    await error_handler.send_error_embed(
                        "Unauthorized Access",
                        Exception("User is not authorized."),
                        context=(
                            f"User: {getattr(interaction, 'user', None)} ({user_id}) | "
                            f"Channel: {getattr(interaction, 'channel', None)} | Command: post_to_news"
                        ),
                        bot=self.bot,
                        channel=getattr(self.bot, "log_channel", None),
                    )
                    return False

            # Process AI translation if not already done
            if not self.ai_english or not self.ai_title:
                if self.arabic_text_clean:
                    self.logger.info("[FETCH] Processing text with AI services")
                    ai_english, ai_title, ai_location = await self.ai_service.process_text_with_ai(
                        self.arabic_text_clean
                    )
                    if ai_english:
                        self.ai_english = ai_english
                    if ai_title:
                        self.ai_title = ai_title
                    if ai_location:
                        self.ai_location = ai_location
                        self.logger.info(f"[FETCH] AI detected location: {ai_location}")

            # Download media if present - OPTIONAL based on configuration
            if self.media:
                self.logger.info("[FETCH] Downloading media using media service")
                media_files, temp_path = (
                    await self.media_service.download_media_with_timeout(
                        self.post, self.media
                    )
                )
                if media_files:
                    media_files = self.media_service.validate_media_files(media_files)

                    # If media download failed but we have media, check if media is required
                    if not media_files:
                        # Get require_media setting from config
                        from src.core.unified_config import unified_config
                        require_media = unified_config.get('automation.require_media', False)
                        
                        if require_media:
                            self.logger.error(
                                "[FETCH] Media download failed and media is required - aborting post"
                            )
                            return False
                        else:
                            self.logger.warning(
                                "[FETCH] Media download failed but media is not required - proceeding without media"
                            )
                else:
                    # No media present - check if media is required
                    from src.core.unified_config import unified_config
                    require_media = unified_config.get('automation.require_media', False)
                    
                    if require_media:
                        self.logger.error(
                            "[FETCH] No media present and media is required - aborting post"
                        )
                        return False
                    else:
                        self.logger.info(
                            "[FETCH] No media present but media is not required - proceeding with text-only post"
                        )

            # Post to news channel using posting service with intelligence parameters
            success = await self.posting_service.post_to_news_channel(
                arabic_text=self.arabic_text_clean or "",
                english_translation=self.ai_english,
                ai_title=self.ai_title,
                channelname=self.channelname,
                message_id=self.message_id,
                media_files=media_files,
                ai_location=getattr(self, 'ai_location', None),
                # 🧠 Pass intelligence parameters
                should_ping_news=self.should_ping_news,
                urgency_level=self.urgency_level,
                content_category=self.content_category,
                quality_score=self.quality_score,
            )

            # Cleanup media files
            if media_files and temp_path:
                self.media_service.cleanup_media_files(media_files, temp_path)

            if success:
                self.logger.info(
                    f"[FETCH] Successfully posted to news channel: post_id={self.message_id}"
                )

                # Send success response in interactive mode
                if not self.auto_mode and interaction:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            "✅ Successfully posted to news channel!"
                        )
                    else:
                        await interaction.followup.send(
                            "✅ Successfully posted to news channel!"
                        )
            else:
                self.logger.error(
                    f"[FETCH] Failed to post to news channel: post_id={self.message_id}"
                )

                # Send error response in interactive mode
                if not self.auto_mode and interaction:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            "❌ Failed to post to news channel."
                        )
                    else:
                        await interaction.followup.send(
                            "❌ Failed to post to news channel."
                        )

            return success

        except Exception as e:
            self.logger.error(
                f"[FETCH] Error in do_post_to_news: {str(e)}", exc_info=True
            )

            # Cleanup on error
            if media_files and temp_path:
                self.media_service.cleanup_media_files(media_files, temp_path)

            await error_handler.send_error_embed(
                "Post to News Error",
                e,
                context=f"Post ID: {self.message_id}, Channel: {self.channelname}",
                bot=self.bot,
            )

            # Send error response in interactive mode
            if not self.auto_mode and interaction:
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            f"❌ Error posting to news: {str(e)}"
                        )
                    else:
                        await interaction.followup.send(
                            f"❌ Error posting to news: {str(e)}"
                        )
                except Exception:
                    pass

            return False

    @ui.button(label="Post to News", style=discord.ButtonStyle.success)
    async def post_to_news(
        self, interaction: discord.Interaction, button: ui.Button
    ) -> None:
        """
        Handle the Post to News button click.

        Args:
            interaction: The Discord interaction from the button click
            button: The button that was clicked
        """
        try:
            self.logger.info(
                f"[FETCH][BTN] Post to News button clicked by user {interaction.user.id}"
            )

            # Defer the response to give us more time
            await interaction.response.defer(thinking=True)

            # Call the main posting function
            success = await self.do_post_to_news(interaction)

            if success:
                self.logger.info("[FETCH][BTN] Post to News completed successfully")
            else:
                self.logger.error("[FETCH][BTN] Post to News failed")

        except Exception as e:
            self.logger.error(
                f"[FETCH][BTN] Error in post_to_news button: {str(e)}", exc_info=True
            )

            try:
                await interaction.followup.send(f"❌ An error occurred: {str(e)}")
            except Exception:
                pass

    @ui.button(label="Download Media", style=discord.ButtonStyle.primary)
    async def download_media(
        self, interaction: discord.Interaction, button: ui.Button
    ) -> None:
        """
        Handle the Download Media button click.

        Args:
            interaction: The Discord interaction from the button click
            button: The button that was clicked
        """
        try:
            self.logger.info(
                f"[FETCH][BTN] Download Media button clicked by user {interaction.user.id}"
            )

            # Check authorization (temporarily disabled for testing)
            if False:  # Temporarily disable permission check
                if interaction.user.id != ADMIN_USER_ID:
                    await interaction.response.send_message("You are not authorized.")
                    return

            # Defer the response
            await interaction.response.defer(thinking=True)

            if not self.media:
                await interaction.followup.send("❌ No media found in this message.")
                return

            # Download media using media service
            media_files, temp_path = (
                await self.media_service.download_media_with_timeout(
                    self.post, self.media
                )
            )

            if media_files:
                # Send the media files to Discord
                discord_files = []
                for file_path in media_files:
                    if os.path.exists(file_path):
                        filename = os.path.basename(file_path)
                        discord_files.append(discord.File(file_path, filename=filename))

                if discord_files:
                    await interaction.followup.send(
                        f"✅ Downloaded {len(discord_files)} media file(s):",
                        files=discord_files,
                    )
                else:
                    await interaction.followup.send("❌ No valid media files to send.")

                # Cleanup
                self.media_service.cleanup_media_files(media_files, temp_path)
            else:
                await interaction.followup.send("❌ Failed to download media.")

        except Exception as e:
            self.logger.error(
                f"[FETCH][BTN] Error in download_media button: {str(e)}", exc_info=True
            )

            try:
                await interaction.followup.send(f"❌ Error downloading media: {str(e)}")
            except Exception:
                pass

    @ui.button(label="🚫 Blacklist Post", style=discord.ButtonStyle.danger)
    async def blacklist(
        self, interaction: discord.Interaction, button: ui.Button
    ) -> None:
        """
        Handle the Blacklist Post button click.

        Args:
            interaction: The Discord interaction from the button click
            button: The button that was clicked
        """
        try:
            self.logger.info(
                f"[FETCH][BTN] Blacklist Post button clicked by user {interaction.user.id}"
            )

            # Check if user is admin
            def get_config():
                """Get config manager instance."""
                from src.core.unified_config import unified_config as unified_config
                return unified_config
            
            admin_user_id = get_config().get("bot.admin_user_id")
            if not admin_user_id or interaction.user.id != int(admin_user_id):
                await interaction.response.send_message("❌ Only admins can blacklist posts.", ephemeral=True)
                return

            await interaction.response.defer()

            # Add message ID to blacklist
            if hasattr(self.bot, 'json_cache') and self.bot.json_cache:
                blacklisted_posts = await self.bot.json_cache.get("blacklisted_posts") or []
                if self.message_id not in blacklisted_posts:
                    blacklisted_posts.append(self.message_id)
                    await self.bot.json_cache.set("blacklisted_posts", blacklisted_posts)
                    await self.bot.json_cache.save()

                    # Create blacklist confirmation
                    embed = discord.Embed(
                        title="🚫 Post Blacklisted",
                        description=f"Message **{self.message_id}** from **{self.channelname}** has been blacklisted.",
                        color=0xFF0000
                    )
                    embed.add_field(name="Message ID", value=str(self.message_id), inline=True)
                    embed.add_field(name="Channel", value=self.channelname, inline=True)
                    embed.add_field(name="Blacklisted by", value=f"<@{interaction.user.id}>", inline=True)

                    # Disable all buttons
                    for item in self.children:
                        item.disabled = True

                    await interaction.followup.edit_message(interaction.message.id, view=self)
                    await interaction.followup.send(embed=embed)

                    self.logger.info(f"🚫 [BLACKLIST] Post {self.message_id} from {self.channelname} blacklisted by {interaction.user.id}")
                else:
                    await interaction.followup.send(f"⚠️ Message **{self.message_id}** is already blacklisted.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Cache not available for blacklisting.", ephemeral=True)

        except Exception as e:
            self.logger.error(
                f"[FETCH][BTN] Error in blacklist button: {str(e)}", exc_info=True
            )

            try:
                await interaction.followup.send(f"❌ Error blacklisting post: {str(e)}", ephemeral=True)
            except Exception:
                pass

    async def process_message(self) -> None:
        """
        Process the message for AI translation and title generation.
        This method is called during initialization to prepare the content.
        """
        try:
            # Extract text from the message if not already provided
            if (
                not self.arabic_text_clean
                and hasattr(self.post, "message")
                and self.post.message
            ):
                # Clean the text from the Telegram message
                self.arabic_text_clean = clean_news_content(self.post.message)
                self.logger.info(
                    f"[FETCH] Extracted and cleaned text: {len(self.arabic_text_clean)} characters"
                )

            if self.arabic_text_clean and (not self.ai_english or not self.ai_title):
                self.logger.info("[FETCH] Processing message with AI services")

                # Use AI service to process the text
                ai_english, ai_title, ai_location = await self.ai_service.process_text_with_ai(
                    self.arabic_text_clean
                )

                if ai_english:
                    self.ai_english = ai_english
                    self.logger.info(
                        f"[FETCH] AI translation completed: {len(ai_english)} characters"
                    )
                else:
                    self.logger.warning(
                        "[FETCH] AI translation failed or returned empty"
                    )

                if ai_title:
                    self.ai_title = ai_title
                    self.logger.info(f"[FETCH] AI title generated: {ai_title}")
                else:
                    self.logger.warning("[FETCH] AI title generation failed")

                if ai_location:
                    self.ai_location = ai_location
                    self.logger.info(f"[FETCH] AI detected location: {ai_location}")
                else:
                    self.ai_location = "Unknown"
                    self.logger.warning("[FETCH] AI location detection failed, using 'Unknown'")

                self.logger.info("[FETCH] AI processing completed")
            else:
                if not self.arabic_text_clean:
                    self.logger.warning("[FETCH] No text available for processing")

        except Exception as e:
            self.logger.error(
                f"[FETCH] Error processing message: {str(e)}", exc_info=True
            )


# --- END FetchView class ---
