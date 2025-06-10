"""
FetchView UI Components

This module contains the Discord UI components for the fetch functionality.
Uses service classes for media, AI, and posting operations.
"""

import discord
from discord import ui
from typing import Optional, Any
import os
import asyncio

from src.utils.config import Config
from src.utils import error_handler
from src.utils.base_logger import base_logger as logger
from src.services.media_service import MediaService
from src.services.ai_service import AIService
from src.services.posting_service import PostingService

# Configuration constants
GUILD_ID = Config.GUILD_ID or 0
ADMIN_USER_ID = Config.ADMIN_USER_ID or 0


class FetchView(ui.View):
    """
    View for fetching and posting content from Telegram channels.
    Handles user interaction with the Telegram message display,
    including translation and posting to Discord channels.
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
        auto_mode=False
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
            auto_mode: Whether the view is operating in automatic mode
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
        elif hasattr(post, 'id'):
            self.message_id = getattr(post, 'id', 0)
        else:
            self.message_id = 0
            
        # Media handling
        if media is not None:
            self.media = media
        elif hasattr(post, 'media'):
            self.media = getattr(post, 'media', None)
        else:
            self.media = None
            
        self.media_bytes = media_bytes
        
        # Text content
        self.arabic_text_clean = arabic_text_clean
        self.ai_english = ai_english
        self.ai_title = ai_title
        
        # Initialize services
        self.media_service = MediaService(bot)
        self.ai_service = AIService(bot)
        self.posting_service = PostingService(bot)
        
        # If auto_mode is True, buttons should be disabled
        if auto_mode:
            for item in self.children:
                item.disabled = True
        
        self.logger.debug("[FETCH] FetchView loaded and initialized. Auto mode: %s", auto_mode)

    async def do_post_to_news(self, interaction: Optional[discord.Interaction] = None) -> bool:
        """
        Post the content to the news channel using service classes.
        
        Args:
            interaction: Optional Discord interaction. Required in interactive mode, 
                         but can be None in auto_mode.
                         
        Returns:
            bool: True if posting was successful, False otherwise
        """
        # Initialize context for logging
        user_id = getattr(interaction, 'user', None)
        user_id = getattr(user_id, 'id', 'auto_mode') if user_id else 'auto_mode'
        channel_id = getattr(interaction, 'channel', None)
        channel_id = getattr(channel_id, 'id', 0) if channel_id else 0
        
        self.logger.info(
            f"[FETCH][BTN][post_to_news] START post_id={self.message_id} | user={user_id} channel={channel_id}"
        )
        
        # Track overall success
        success = False
        media_files = []
        temp_path = None
        
        try:
            # Skip authorization check in auto mode
            if not self.auto_mode and interaction:
                if interaction.user.id != ADMIN_USER_ID:
                    if not interaction.response.is_done():
                        await interaction.response.send_message("You are not authorized.")
                    self.logger.error(
                        f"[FETCH][BTN][post_to_news] ERROR Unauthorized | user={user_id} channel={channel_id}"
                    )
                    await error_handler.send_error_embed(
                        "Unauthorized Access",
                        Exception("User is not authorized."),
                        context=f"User: {getattr(interaction, 'user', None)} ({user_id}) | Channel: {getattr(interaction, 'channel', None)} | Command: post_to_news",
                        bot=self.bot,
                        channel=getattr(self.bot, 'log_channel', None)
                    )
                    return False
            
            # Process AI translation if not already done
            if not self.ai_english or not self.ai_title:
                if self.arabic_text_clean:
                    self.logger.info("[FETCH] Processing text with AI services")
                    ai_english, ai_title = await self.ai_service.process_text_with_ai(self.arabic_text_clean)
                    if ai_english:
                        self.ai_english = ai_english
                    if ai_title:
                        self.ai_title = ai_title
            
            # Download media if present
            if self.media:
                self.logger.info("[FETCH] Downloading media using media service")
                media_files, temp_path = await self.media_service.download_media_with_timeout(
                    self.post, self.media
                )
                if media_files:
                    media_files = self.media_service.validate_media_files(media_files)
            
            # Post to news channel using posting service
            success = await self.posting_service.post_to_news_channel(
                arabic_text=self.arabic_text_clean or "",
                english_translation=self.ai_english,
                ai_title=self.ai_title,
                channelname=self.channelname,
                message_id=self.message_id,
                media_files=media_files
            )
            
            # Cleanup media files
            if media_files and temp_path:
                self.media_service.cleanup_media_files(media_files, temp_path)
            
            if success:
                self.logger.info(f"[FETCH] Successfully posted to news channel: post_id={self.message_id}")
                
                # Send success response in interactive mode
                if not self.auto_mode and interaction:
                    if not interaction.response.is_done():
                        await interaction.response.send_message("✅ Successfully posted to news channel!")
                    else:
                        await interaction.followup.send("✅ Successfully posted to news channel!")
            else:
                self.logger.error(f"[FETCH] Failed to post to news channel: post_id={self.message_id}")
                
                # Send error response in interactive mode
                if not self.auto_mode and interaction:
                    if not interaction.response.is_done():
                        await interaction.response.send_message("❌ Failed to post to news channel.")
                    else:
                        await interaction.followup.send("❌ Failed to post to news channel.")
            
            return success
            
        except Exception as e:
            self.logger.error(f"[FETCH] Error in do_post_to_news: {str(e)}", exc_info=True)
            
            # Cleanup on error
            if media_files and temp_path:
                self.media_service.cleanup_media_files(media_files, temp_path)
            
            await error_handler.send_error_embed(
                "Post to News Error",
                e,
                context=f"Post ID: {self.message_id}, Channel: {self.channelname}",
                bot=self.bot
            )
            
            # Send error response in interactive mode
            if not self.auto_mode and interaction:
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(f"❌ Error posting to news: {str(e)}")
                    else:
                        await interaction.followup.send(f"❌ Error posting to news: {str(e)}")
                except Exception:
                    pass
            
            return False

    @ui.button(label="Post to News", style=discord.ButtonStyle.success)
    async def post_to_news(self, interaction: discord.Interaction, button: ui.Button) -> None:
        """
        Handle the Post to News button click.
        
        Args:
            interaction: The Discord interaction from the button click
            button: The button that was clicked
        """
        try:
            self.logger.info(f"[FETCH][BTN] Post to News button clicked by user {interaction.user.id}")
            
            # Defer the response to give us more time
            await interaction.response.defer(thinking=True)
            
            # Call the main posting function
            success = await self.do_post_to_news(interaction)
            
            if success:
                self.logger.info("[FETCH][BTN] Post to News completed successfully")
            else:
                self.logger.error("[FETCH][BTN] Post to News failed")
                
        except Exception as e:
            self.logger.error(f"[FETCH][BTN] Error in post_to_news button: {str(e)}", exc_info=True)
            
            try:
                await interaction.followup.send(f"❌ An error occurred: {str(e)}")
            except Exception:
                pass

    @ui.button(label="Download Media", style=discord.ButtonStyle.primary)
    async def download_media(self, interaction: discord.Interaction, button: ui.Button) -> None:
        """
        Handle the Download Media button click.
        
        Args:
            interaction: The Discord interaction from the button click
            button: The button that was clicked
        """
        try:
            self.logger.info(f"[FETCH][BTN] Download Media button clicked by user {interaction.user.id}")
            
            # Check authorization
            if interaction.user.id != ADMIN_USER_ID:
                await interaction.response.send_message("You are not authorized.")
                return
            
            # Defer the response
            await interaction.response.defer(thinking=True)
            
            if not self.media:
                await interaction.followup.send("❌ No media found in this message.")
                return
            
            # Download media using media service
            media_files, temp_path = await self.media_service.download_media_with_timeout(
                self.post, self.media
            )
            
            if media_files:
                # Send the media files to Discord
                discord_files = []
                for file_path, filename in media_files:
                    if os.path.exists(file_path):
                        discord_files.append(discord.File(file_path, filename=filename))
                
                if discord_files:
                    await interaction.followup.send(
                        f"✅ Downloaded {len(discord_files)} media file(s):",
                        files=discord_files
                    )
                else:
                    await interaction.followup.send("❌ No valid media files to send.")
                
                # Cleanup
                self.media_service.cleanup_media_files(media_files, temp_path)
            else:
                await interaction.followup.send("❌ Failed to download media.")
                
        except Exception as e:
            self.logger.error(f"[FETCH][BTN] Error in download_media button: {str(e)}", exc_info=True)
            
            try:
                await interaction.followup.send(f"❌ Error downloading media: {str(e)}")
            except Exception:
                pass

    @ui.button(label="Blacklist", style=discord.ButtonStyle.danger)
    async def blacklist(self, interaction: discord.Interaction, button: ui.Button) -> None:
        """
        Handle the Blacklist button click.
        
        Args:
            interaction: The Discord interaction from the button click
            button: The button that was clicked
        """
        try:
            self.logger.info(f"[FETCH][BTN] Blacklist button clicked by user {interaction.user.id}")
            
            # Check authorization
            if interaction.user.id != ADMIN_USER_ID:
                await interaction.response.send_message("You are not authorized.")
                return
            
            # Add to blacklist (this would need to be implemented in a blacklist service)
            # For now, just acknowledge the action
            await interaction.response.send_message(
                f"⚠️ Message {self.message_id} from {self.channelname} has been blacklisted."
            )
            
            self.logger.info(f"[FETCH][BTN] Message {self.message_id} blacklisted by user {interaction.user.id}")
            
        except Exception as e:
            self.logger.error(f"[FETCH][BTN] Error in blacklist button: {str(e)}", exc_info=True)
            
            try:
                await interaction.response.send_message(f"❌ Error blacklisting: {str(e)}")
            except Exception:
                pass

    async def process_message(self) -> None:
        """
        Process the message for AI translation and title generation.
        This method is called during initialization to prepare the content.
        """
        try:
            if self.arabic_text_clean and (not self.ai_english or not self.ai_title):
                self.logger.info("[FETCH] Processing message with AI services")
                
                # Use AI service to process the text
                ai_english, ai_title = await self.ai_service.process_text_with_ai(self.arabic_text_clean)
                
                if ai_english:
                    self.ai_english = ai_english
                if ai_title:
                    self.ai_title = ai_title
                    
                self.logger.info("[FETCH] AI processing completed")
            
        except Exception as e:
            self.logger.error(f"[FETCH] Error processing message: {str(e)}", exc_info=True)

# --- END FetchView class --- 