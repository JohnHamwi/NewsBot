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
from typing import Any, List, Optional

import discord
import pytz

from src.utils import error_handler
from src.utils.base_logger import base_logger as logger
from src.utils.config import Config

# Configuration constants
try:
    from src.utils.config import Config

    NEWS_ROLE_ID = getattr(Config, "NEWS_ROLE_ID", None) or os.getenv("NEWS_ROLE_ID")
except Exception:
    NEWS_ROLE_ID = os.getenv("NEWS_ROLE_ID")

# Forum tag mapping - maps category names to Discord forum tag IDs
FORUM_TAG_MAPPING = {
    "🔴 Breaking News": 1382114954165092565,
    "⚔️ Military": 1382114547996954664,
    "🏛️ Politics": 1382115092077871174,
    "💰 Economy": 1382115132317892619,
    "🏥 Health": 1382115182184235088,
    "🌍 International": 1382115248814690354,
    "👥 Social": 1382115306842882118,
    "🚨 Security": 1382115376715927602,
    "📰 General News": 1382115427743826050,
}


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
        timeout: int = 30,
        max_retries: int = 2,
    ) -> bool:
        """
        Post content to the news channel with timeout and retry logic.

        Args:
            arabic_text: The original Arabic text
            english_translation: AI-generated English translation
            ai_title: AI-generated title
            channelname: Source Telegram channel name
            message_id: Telegram message ID
            media_files: List of media file paths to attach
            timeout: Posting timeout in seconds
            max_retries: Maximum number of retry attempts

        Returns:
            bool: True if posting was successful, False otherwise
        """
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.info(
                        f"[POSTING] Retry attempt {attempt}/{max_retries} for message {message_id}"
                    )
                    # Wait a bit before retrying
                    await asyncio.sleep(2 * attempt)

                result = await asyncio.wait_for(
                    self._post_to_news_internal(
                        arabic_text,
                        english_translation,
                        ai_title,
                        channelname,
                        message_id,
                        media_files,
                    ),
                    timeout=timeout,
                )

                if result:
                    if attempt > 0:
                        self.logger.info(
                            f"[POSTING] Successfully posted on retry attempt {attempt}"
                        )
                    return True

            except asyncio.TimeoutError:
                self.logger.error(
                    f"[POSTING] News posting timed out after {timeout} seconds (attempt {attempt + 1})"
                )
                if attempt == max_retries:
                    return False
                continue

            except Exception as e:
                self.logger.error(
                    f"[POSTING] News posting failed on attempt {attempt + 1}: {str(e)}"
                )
                if attempt == max_retries:
                    await error_handler.send_error_embed(
                        "News Posting Error",
                        e,
                        context=f"Message ID: {message_id}, Channel: {channelname}, Final attempt failed",
                        bot=self.bot,
                    )
                    return False
                continue

        return False

    async def _post_to_news_internal(
        self,
        arabic_text: str,
        english_translation: Optional[str],
        ai_title: Optional[str],
        channelname: str,
        message_id: int,
        media_files: Optional[List[str]] = None,
    ) -> bool:
        """Internal news posting logic."""
        try:
            # Get the news channel using Config
            from src.utils.config import Config
            news_channel = self.bot.get_channel(Config.NEWS_CHANNEL_ID)
            if not news_channel:
                self.logger.error(f"[POSTING] News channel not found with ID {Config.NEWS_CHANNEL_ID}")
                return False

            # Generate thread title and message content
            thread_title = self._generate_thread_title(
                arabic_text, ai_title, channelname
            )
            message_content = self._generate_message_content(
                arabic_text, english_translation, channelname, message_id
            )

            # Prepare media attachments
            discord_files = []
            if media_files:
                discord_files = self._prepare_media_files(media_files)

            # Create the thread and post - different approach for forum vs regular channels
            if isinstance(news_channel, discord.ForumChannel):
                # Get the appropriate forum tag based on content category
                category = self._categorize_content(arabic_text, english_translation)
                applied_tags = self._get_forum_tags(news_channel, category)

                # For forum channels, create thread with actual content directly
                thread, message = await news_channel.create_thread(
                    name=thread_title,
                    content=message_content,
                    files=discord_files if discord_files else None,
                    applied_tags=applied_tags,
                )
                self.logger.debug(
                    f"[POSTING] Created forum thread with content: {thread_title}, tags: {[tag.name for tag in applied_tags]}"
                )
            else:
                # For regular text channels, create thread then send message
                thread = await self._create_news_thread(news_channel, thread_title)
                if not thread:
                    return False
                # Send the message with media
                await self._send_message_to_thread(
                    thread, message_content, discord_files
                )

            # Send confirmation embed to logs channel
            await self._send_confirmation_embed(
                thread, thread_title, channelname, message_id, len(discord_files)
            )

            self.logger.info(
                f"[POSTING] Successfully posted to news channel: {thread_title}"
            )
            return True

        except Exception as e:
            self.logger.error(f"[POSTING] Error in news posting: {str(e)}")
            raise

    def _generate_thread_title(
        self, arabic_text: str, ai_title: Optional[str], channelname: str
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
        cleaned = re.sub(r"#\w+", "", text)
        cleaned = re.sub(r"https?://\S+", "", cleaned)
        cleaned = re.sub(r"\.?شبكة.?اخبار.?سوريا.?_?الحرة", "", cleaned)

        # Normalize whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned

    def _generate_message_content(
        self,
        arabic_text: str,
        english_translation: Optional[str],
        channelname: str,
        message_id: int,
    ) -> str:
        """Generate the message content for the news post."""
        # Clean up the Arabic text for display
        cleaned_arabic = self._clean_arabic_for_display(arabic_text)

        # Start building content
        content_parts = []

        # Add the Arabic text with title
        content_parts.append("**Original (AR):**")
        content_parts.append(cleaned_arabic)
        content_parts.append("")  # Empty line

        # Add English translation if available
        if english_translation:
            from src.cogs.ai_utils import clean_translation

            cleaned_translation = clean_translation(english_translation)
            content_parts.append("**Translation (EN):**")
            content_parts.append(cleaned_translation)
            content_parts.append("")  # Empty line

        # Add vertical info format (location, category, time)
        location = self._detect_location(arabic_text, english_translation)
        category = self._categorize_content(arabic_text, english_translation)
        damascus_tz = pytz.timezone("Asia/Damascus")
        current_time = datetime.datetime.now(damascus_tz).strftime(
            "%I:%M %p Damascus Time"
        )

        content_parts.append(f"📍 **Location:** {location}")
        content_parts.append(f"🏷️ **Category:** {category}")
        content_parts.append(f"🕒 **Posted:** {current_time}")
        content_parts.append("")  # Empty line

        # Add improved beta warning with admin mention
        content_parts.append("---")
        content_parts.append("⚠️ **Beta Testing Notice**")
        content_parts.append(
            "This bot is currently in beta testing. If you notice any issues, translation errors, or unexpected content, please contact <@259725211664908288>."
        )
        content_parts.append("")  # Empty line

        # Add news role ping at the bottom
        if NEWS_ROLE_ID:
            content_parts.append(f"<@&{NEWS_ROLE_ID}>")

        return "\n".join(content_parts)

    def _detect_location(
        self, arabic_text: str, english_translation: Optional[str] = None
    ) -> str:
        """
        Detect location from Arabic text and English translation.

        Args:
            arabic_text: The original Arabic text
            english_translation: Optional English translation

        Returns:
            str: Detected location or "Syria" as fallback
        """
        try:
            # Import Syrian location detection utility
            from src.utils.syrian_locations import detect_syrian_location

            # Try to detect location from Arabic text first
            if arabic_text:
                location = detect_syrian_location(arabic_text)
                if location and location != "Syria":
                    return location

            # Try to detect from English translation if available
            if english_translation:
                location = detect_syrian_location(english_translation)
                if location and location != "Syria":
                    return location

            # Fallback to Syria if no specific city detected
            return "Syria"

        except Exception as e:
            self.logger.debug(f"[POSTING] Error detecting location: {str(e)}")
            return "Syria"

    def _clean_arabic_for_display(self, text: str) -> str:
        """Clean Arabic text for display in Discord."""
        if not text:
            return "No content available"

        # Use the enhanced content cleaner
        from src.utils.content_cleaner import clean_news_content

        cleaned = clean_news_content(text, preserve_structure=True)

        return cleaned or "No content available"

    def _prepare_media_files(self, media_files: List[str]) -> List[discord.File]:
        """Prepare media files for Discord upload."""
        discord_files = []

        for file_path in media_files:
            try:
                if os.path.exists(file_path):
                    discord_file = discord.File(file_path)
                    discord_files.append(discord_file)
                    self.logger.debug(
                        f"[POSTING] Prepared media file: {os.path.basename(file_path)}"
                    )
                else:
                    self.logger.warning(f"[POSTING] Media file not found: {file_path}")
            except Exception as e:
                self.logger.error(
                    f"[POSTING] Failed to prepare media file {file_path}: {str(e)}"
                )

        self.logger.debug(
            f"[POSTING] Prepared {len(discord_files)} media files for upload"
        )
        return discord_files

    async def _create_news_thread(
        self, news_channel: discord.TextChannel, thread_title: str
    ) -> Optional[discord.Thread]:
        """Create a new thread in the news channel."""
        try:
            # Check if it's a forum channel or regular text channel
            if isinstance(news_channel, discord.ForumChannel):
                # For forum channels, create a thread with placeholder initial message
                thread, message = await news_channel.create_thread(
                    name=thread_title,
                    content="📰 Loading news content...",  # Placeholder content that will be replaced
                )
            else:
                # For regular text channels, create a thread without type parameter
                thread = await news_channel.create_thread(
                    name=thread_title, auto_archive_duration=1440  # 24 hours
                )

            self.logger.debug(f"[POSTING] Created thread: {thread_title}")
            return thread

        except Exception as e:
            self.logger.error(
                f"[POSTING] Failed to create thread '{thread_title}': {str(e)}"
            )
            return None

    async def _send_message_to_thread(
        self, thread: discord.Thread, content: str, discord_files: List[discord.File]
    ) -> None:
        """Send a message with content and media to the thread."""
        try:
            if discord_files:
                # Send message with files
                await thread.send(content=content, files=discord_files)
                self.logger.debug(
                    f"[POSTING] Sent message with {len(discord_files)} media files"
                )
            else:
                # Send text-only message
                await thread.send(content=content)
                self.logger.debug("[POSTING] Sent text-only message")

        except Exception as e:
            self.logger.error(f"[POSTING] Failed to send message to thread: {str(e)}")
            raise

    async def _send_confirmation_embed(
        self,
        thread: discord.Thread,
        thread_title: str,
        channelname: str,
        message_id: int,
        media_count: int,
    ) -> None:
        """Send a confirmation embed to the logs channel after successful posting."""
        try:
            # Get the logs channel
            logs_channel = self.bot.get_channel(Config.LOG_CHANNEL_ID)
            if not logs_channel:
                self.logger.warning(
                    "[POSTING] Logs channel not found, skipping confirmation embed"
                )
                return

            # Create the confirmation embed
            embed = discord.Embed(
                title="📰 News Post Published",
                description=f"Successfully posted news to {thread.parent.mention}",
                color=0x00FF00,  # Green color
                timestamp=datetime.datetime.now(),
            )

            # Add fields with post information
            embed.add_field(name="📅 Thread Title", value=thread_title, inline=False)

            embed.add_field(
                name="🔗 Thread Link",
                value=f"[Click here to view the post]({thread.jump_url})",
                inline=True,
            )

            embed.add_field(name="📺 Source Channel", value=channelname, inline=True)

            embed.add_field(name="🆔 Message ID", value=str(message_id), inline=True)

            if media_count > 0:
                embed.add_field(
                    name="📎 Media Files",
                    value=f"{media_count} file(s) attached",
                    inline=True,
                )

            # Add footer
            embed.set_footer(
                text="Syrian News Bot",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None,
            )

            # Send the embed
            await logs_channel.send(embed=embed)
            self.logger.debug(f"[POSTING] Sent confirmation embed to logs channel")

        except Exception as e:
            self.logger.error(f"[POSTING] Failed to send confirmation embed: {str(e)}")
            # Don't raise the exception as this is not critical for the main posting functionality

    def _categorize_content(
        self, arabic_text: str, english_translation: Optional[str] = None
    ) -> str:
        """
        Categorize content using AI analysis.

        Args:
            arabic_text: The original Arabic text
            english_translation: Optional English translation

        Returns:
            str: Content category with emoji
        """
        try:
            # Use English translation for better AI analysis if available
            text_to_analyze = (
                english_translation if english_translation else arabic_text
            )

            if not text_to_analyze:
                return "📰 General News"

            # Convert to lowercase for keyword matching
            text_lower = text_to_analyze.lower()

            # Define category keywords
            categories = {
                "🔴 Breaking News": [
                    "breaking",
                    "urgent",
                    "emergency",
                    "alert",
                    "immediate",
                    "just in",
                    "عاجل",
                    "طارئ",
                    "فوري",
                ],
                "⚔️ Military": [
                    "military",
                    "army",
                    "forces",
                    "attack",
                    "strike",
                    "combat",
                    "war",
                    "battle",
                    "soldier",
                    "weapon",
                    "defense",
                    "offensive",
                    "operation",
                    "عسكري",
                    "جيش",
                    "قوات",
                    "هجوم",
                    "ضربة",
                    "معركة",
                    "حرب",
                    "جندي",
                ],
                "🏛️ Politics": [
                    "government",
                    "minister",
                    "president",
                    "parliament",
                    "political",
                    "policy",
                    "election",
                    "vote",
                    "diplomatic",
                    "embassy",
                    "official",
                    "statement",
                    "حكومة",
                    "وزير",
                    "رئيس",
                    "برلمان",
                    "سياسي",
                    "انتخابات",
                    "دبلوماسي",
                ],
                "💰 Economy": [
                    "economy",
                    "economic",
                    "trade",
                    "business",
                    "market",
                    "price",
                    "inflation",
                    "currency",
                    "bank",
                    "investment",
                    "finance",
                    "budget",
                    "اقتصاد",
                    "تجارة",
                    "أعمال",
                    "سوق",
                    "سعر",
                    "تضخم",
                    "عملة",
                    "بنك",
                ],
                "🏥 Health": [
                    "health",
                    "medical",
                    "hospital",
                    "doctor",
                    "patient",
                    "treatment",
                    "medicine",
                    "disease",
                    "virus",
                    "vaccine",
                    "clinic",
                    "صحة",
                    "طبي",
                    "مستشفى",
                    "طبيب",
                    "مريض",
                    "علاج",
                    "دواء",
                    "مرض",
                ],
                "🌍 International": [
                    "international",
                    "global",
                    "world",
                    "foreign",
                    "abroad",
                    "embassy",
                    "united nations",
                    "european",
                    "american",
                    "russian",
                    "turkish",
                    "دولي",
                    "عالمي",
                    "خارجي",
                    "أمريكي",
                    "روسي",
                    "تركي",
                    "أوروبي",
                ],
                "👥 Social": [
                    "social",
                    "community",
                    "people",
                    "citizen",
                    "family",
                    "education",
                    "school",
                    "university",
                    "student",
                    "culture",
                    "religion",
                    "اجتماعي",
                    "مجتمع",
                    "شعب",
                    "مواطن",
                    "عائلة",
                    "تعليم",
                    "مدرسة",
                    "جامعة",
                ],
                "🚨 Security": [
                    "security",
                    "police",
                    "arrest",
                    "crime",
                    "investigation",
                    "terrorist",
                    "explosion",
                    "bomb",
                    "incident",
                    "violence",
                    "أمن",
                    "شرطة",
                    "اعتقال",
                    "جريمة",
                    "تحقيق",
                    "إرهابي",
                    "انفجار",
                    "قنبلة",
                ],
            }

            # Check for category matches
            for category, keywords in categories.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        return category

            # Default category
            return "📰 General News"

        except Exception as e:
            self.logger.debug(f"[POSTING] Error categorizing content: {str(e)}")
            return "📰 General News"

    def _get_forum_tags(
        self, forum_channel: discord.ForumChannel, category: str
    ) -> List[discord.ForumTag]:
        """
        Get the appropriate forum tags for a given category.

        Args:
            forum_channel: The Discord forum channel
            category: The content category string

        Returns:
            List[discord.ForumTag]: List of forum tags to apply (usually just one)
        """
        try:
            # Get the tag ID for this category
            tag_id = FORUM_TAG_MAPPING.get(category)
            if not tag_id:
                # Fallback to General News if category not found
                tag_id = FORUM_TAG_MAPPING.get("📰 General News")

            if not tag_id:
                self.logger.warning(
                    f"[POSTING] No forum tag mapping found for category: {category}"
                )
                return []

            # Find the actual forum tag object by ID
            for tag in forum_channel.available_tags:
                if tag.id == tag_id:
                    self.logger.debug(
                        f"[POSTING] Selected forum tag: {tag.name} for category: {category}"
                    )
                    return [tag]

            # If tag not found, log warning and return empty list
            self.logger.warning(
                f"[POSTING] Forum tag with ID {tag_id} not found in channel {forum_channel.name}"
            )
            return []

        except Exception as e:
            self.logger.error(f"[POSTING] Error getting forum tags: {str(e)}")
            return []
