"""
Posting Service

This service handles all Discord posting functionality including
thread creation, message formatting, and media attachment.
Extracted from fetch_view.py for better separation of concerns.
"""

import asyncio
import datetime
import os
import re
from typing import Optional, List, Any

import discord

from src.utils.base_logger import base_logger as logger
from src.utils import error_handler

# Configuration constants
try:
    from src.utils.config import Config
    NEWS_ROLE_ID = getattr(Config, 'NEWS_ROLE_ID', None) or os.getenv("NEWS_ROLE_ID")
except Exception:
    NEWS_ROLE_ID = os.getenv("NEWS_ROLE_ID")


class PostingService:
    """Service for handling Discord posting operations."""
    
    def __init__(self, bot):
        """Initialize the posting service with bot instance."""
        self.bot = bot
        self.logger = logger
    
    async def post_to_news_channel(
        self,
        arabic_text: str,
        english_translation: Optional[str],
        ai_title: Optional[str],
        channelname: str,
        message_id: int,
        media_files: Optional[List[str]] = None,
        timeout: int = 30
    ) -> bool:
        """
        Post content to the news channel with timeout.
        
        Args:
            arabic_text: The original Arabic text
            english_translation: AI-generated English translation
            ai_title: AI-generated title
            channelname: Source Telegram channel name
            message_id: Telegram message ID
            media_files: List of media file paths to attach
            timeout: Posting timeout in seconds
            
        Returns:
            bool: True if posting was successful, False otherwise
        """
        try:
            return await asyncio.wait_for(
                self._post_to_news_internal(
                    arabic_text, english_translation, ai_title, 
                    channelname, message_id, media_files
                ),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            self.logger.error(f"[POSTING] News posting timed out after {timeout} seconds")
            return False
        except Exception as e:
            self.logger.error(f"[POSTING] News posting failed: {str(e)}")
            await error_handler.send_error_embed(
                "News Posting Error",
                e,
                context=f"Message ID: {message_id}, Channel: {channelname}",
                bot=self.bot
            )
            return False
    
    async def _post_to_news_internal(
        self,
        arabic_text: str,
        english_translation: Optional[str],
        ai_title: Optional[str],
        channelname: str,
        message_id: int,
        media_files: Optional[List[str]] = None
    ) -> bool:
        """Internal news posting logic."""
        try:
            # Get the news channel
            news_channel = self.bot.get_channel(self.bot.news_channel.id)
            if not news_channel:
                self.logger.error("[POSTING] News channel not found")
                return False
            
            # Generate thread title and message content
            thread_title = self._generate_thread_title(arabic_text, ai_title, channelname)
            message_content = self._generate_message_content(
                arabic_text, english_translation, channelname, message_id
            )
            
            # Prepare media attachments
            discord_files = []
            if media_files:
                discord_files = self._prepare_media_files(media_files)
            
            # Create the thread and post
            thread = await self._create_news_thread(news_channel, thread_title)
            if not thread:
                return False
            
            # Send the message with media
            await self._send_message_to_thread(thread, message_content, discord_files)
            
            self.logger.info(f"[POSTING] Successfully posted to news channel: {thread_title}")
            return True
            
        except Exception as e:
            self.logger.error(f"[POSTING] Error in news posting: {str(e)}")
            raise
    
    def _generate_thread_title(
        self, 
        arabic_text: str, 
        ai_title: Optional[str], 
        channelname: str
    ) -> str:
        """Generate a thread title for the news post."""
        # Get current date
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Determine the title to use
        if ai_title:
            title_text = ai_title
        else:
            # Extract Arabic title as fallback
            title_text = self._extract_arabic_title(arabic_text, channelname)
        
        # Build the thread title with calendar emoji
        return f"📅 {current_date} | {title_text}"
    
    def _extract_arabic_title(self, arabic_text: str, channelname: str) -> str:
        """Extract a short Arabic title from the text."""
        if not arabic_text:
            return channelname
        
        # Clean the text aggressively
        cleaned = self._clean_arabic_for_title(arabic_text)
        
        if not cleaned:
            return channelname
        
        # Get 3-5 words for the title
        words = cleaned.split()
        title_length = min(5, max(3, len(words)))
        
        if title_length > 0:
            return " ".join(words[:title_length])
        
        return channelname
    
    def _clean_arabic_for_title(self, text: str) -> str:
        """Clean Arabic text specifically for title extraction."""
        if not text:
            return ""
        
        # Remove hashtags, links, and network signatures
        cleaned = re.sub(r'#\w+', '', text)
        cleaned = re.sub(r'https?://\S+', '', cleaned)
        cleaned = re.sub(r'\.?شبكة.?اخبار.?سوريا.?_?الحرة', '', cleaned)
        
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def _generate_message_content(
        self,
        arabic_text: str,
        english_translation: Optional[str],
        channelname: str,
        message_id: int
    ) -> str:
        """Generate the message content for the news post."""
        # Clean up the Arabic text for display
        cleaned_arabic = self._clean_arabic_for_display(arabic_text)
        
        # Start with news role ping if available
        content_parts = []
        
        if NEWS_ROLE_ID:
            content_parts.append(f"<@&{NEWS_ROLE_ID}>")
            content_parts.append("")  # Empty line
        
        # Add the Arabic text
        content_parts.append(cleaned_arabic)
        content_parts.append("")  # Empty line
        
        # Add English translation if available
        if english_translation:
            from src.cogs.ai_utils import clean_translation
            cleaned_translation = clean_translation(english_translation)
            content_parts.append("**Translation (EN):**")
            content_parts.append(cleaned_translation)
            content_parts.append("")  # Empty line
        
        # Add source information
        content_parts.append(f"**Source:** {channelname} | **ID:** {message_id}")
        
        return "\n".join(content_parts)
    
    def _clean_arabic_for_display(self, text: str) -> str:
        """Clean Arabic text for display in Discord."""
        if not text:
            return 'No content available'
        
        # Remove hashtags, links, and network signatures
        cleaned = re.sub(r'#\w+', '', text)
        cleaned = re.sub(r'https?://\S+', '', cleaned)
        cleaned = re.sub(r'\.?شبكة.?اخبار.?سوريا.?_?الحرة', '', cleaned)
        
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned or 'No content available'
    
    def _prepare_media_files(self, media_files: List[str]) -> List[discord.File]:
        """Prepare media files for Discord upload."""
        discord_files = []
        
        for file_path in media_files:
            try:
                if os.path.exists(file_path):
                    discord_file = discord.File(file_path)
                    discord_files.append(discord_file)
                    self.logger.debug(f"[POSTING] Prepared media file: {os.path.basename(file_path)}")
                else:
                    self.logger.warning(f"[POSTING] Media file not found: {file_path}")
            except Exception as e:
                self.logger.error(f"[POSTING] Failed to prepare media file {file_path}: {str(e)}")
        
        self.logger.debug(f"[POSTING] Prepared {len(discord_files)} media files for upload")
        return discord_files
    
    async def _create_news_thread(
        self, 
        news_channel: discord.TextChannel, 
        thread_title: str
    ) -> Optional[discord.Thread]:
        """Create a new thread in the news channel."""
        try:
            thread = await news_channel.create_thread(
                name=thread_title,
                type=discord.ChannelType.public_thread,
                auto_archive_duration=1440  # 24 hours
            )
            
            self.logger.debug(f"[POSTING] Created thread: {thread_title}")
            return thread
            
        except Exception as e:
            self.logger.error(f"[POSTING] Failed to create thread '{thread_title}': {str(e)}")
            return None
    
    async def _send_message_to_thread(
        self,
        thread: discord.Thread,
        content: str,
        discord_files: List[discord.File]
    ) -> None:
        """Send a message with content and media to the thread."""
        try:
            if discord_files:
                # Send message with files
                await thread.send(content=content, files=discord_files)
                self.logger.debug(f"[POSTING] Sent message with {len(discord_files)} media files")
            else:
                # Send text-only message
                await thread.send(content=content)
                self.logger.debug("[POSTING] Sent text-only message")
                
        except Exception as e:
            self.logger.error(f"[POSTING] Failed to send message to thread: {str(e)}")
            raise 