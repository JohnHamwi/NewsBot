# =============================================================================
# NewsBot Posting Service Module
# =============================================================================
# This service handles all Discord posting functionality including
# thread creation, message formatting, media attachment, and intelligent
# news role pinging based on AI analysis and urgency detection.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import asyncio
import datetime
import os
import re
from typing import Any, List, Optional

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import discord
import pytz

# =============================================================================
# Local Application Imports
# =============================================================================
from src.utils import error_handler
from src.utils.base_logger import base_logger as logger
from src.core.unified_config import unified_config as config

# =============================================================================
# Configuration Constants
# =============================================================================
try:
    NEWS_ROLE_ID = config.get("bot.news_role_id")
except Exception:
    NEWS_ROLE_ID = None

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

# AI Category to Forum Tag mapping
AI_CATEGORY_TO_FORUM_TAG = {
    "politics": "🏛️ Politics",
    "military": "⚔️ Military", 
    "economy": "💰 Economy",
    "health": "🏥 Health",
    "international": "🌍 International",
    "breaking": "🔴 Breaking News",
    "social": "👥 Social",
    "sports": "👥 Social",  # Map sports to social for now
    "technology": "📰 General News",  # Map technology to general news
    "culture": "👥 Social",  # Map culture to social
}


# =============================================================================
# Posting Service Class
# =============================================================================
class PostingService:
    """
    Enhanced Discord posting service with intelligent news processing.
    
    Features:
    - Intelligent thread creation with urgency-based titles
    - Smart news role pinging for all posts with appropriate styling
    - Forum tag assignment based on AI content categorization
    - Comprehensive media handling and attachment processing
    - Quality score integration and metadata display
    - Robust error handling with retry mechanisms
    """

    def __init__(self, bot):
        """Initialize the posting service with bot instance."""
        self.bot = bot
        self.logger = logger

    # =========================================================================
    # Main Posting Method
    # =========================================================================
    async def post_to_news_channel(
        self,
        arabic_text: str,
        english_translation: Optional[str],
        ai_title: Optional[str],
        channelname: str,
        message_id: int,
        media_files: Optional[List[str]] = None,
        ai_location: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 2,
        # Intelligence parameters for enhanced posting
        should_ping_news: bool = False,
        urgency_level: str = "normal",
        content_category: str = "social",
        quality_score: float = 0.7,
    ) -> bool:
        """
        Post content to the news channel with comprehensive intelligence integration.

        Args:
            arabic_text: The original Arabic text content
            english_translation: AI-generated English translation
            ai_title: AI-generated title for the thread
            channelname: Source Telegram channel name
            message_id: Telegram message ID for tracking
            media_files: List of media file paths to attach
            ai_location: AI-detected location of the news event
            timeout: Posting timeout in seconds
            max_retries: Maximum number of retry attempts
            should_ping_news: Whether to ping the news role (always True for all posts)
            urgency_level: Urgency level from news intelligence analysis
            content_category: Content category from AI analysis
            quality_score: Content quality score from AI analysis

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
                        ai_location,
                        should_ping_news,
                        urgency_level,
                        content_category,
                        quality_score,
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
        ai_location: Optional[str] = None,
        should_ping_news: bool = False,
        urgency_level: str = "normal",
        content_category: str = "social",
        quality_score: float = 0.7,
    ) -> bool:
        """Internal news posting logic."""
        try:
            # Get the news channel using config manager
            news_channel_id = config.get("discord.channels.news") or config.get("channels.news")
            if not news_channel_id:
                self.logger.error("[POSTING] News channel ID not configured")
                return False
                
            news_channel = self.bot.get_channel(news_channel_id)
            if not news_channel:
                self.logger.error(f"[POSTING] News channel not found with ID {news_channel_id}")
                return False

            # Generate thread title and determine category for consistency
            thread_title = self._generate_thread_title(
                arabic_text, ai_title, channelname, urgency_level
            )
            
            # Determine category once for consistent use in both forum tags and message content
            if content_category != "social":
                final_category = self._map_ai_category_to_forum_tag(content_category)
                self.logger.info(f"[POSTING] Using AI category mapping: '{content_category}' -> '{final_category}'")
            else:
                final_category = self._categorize_content(arabic_text, english_translation)
                self.logger.info(f"[POSTING] Using fallback categorization: '{final_category}'")
            
            message_content = self._generate_message_content(
                arabic_text, english_translation, channelname, message_id, ai_location, urgency_level, quality_score, final_category
            )
            
            # 🔔 Prepare news role ping for all posts
            ping_content = ""
            if should_ping_news and NEWS_ROLE_ID:
                if urgency_level == "breaking":
                    ping_content = f"<@&{NEWS_ROLE_ID}> 🚨 **Breaking News Alert!**\n\n"
                    self.logger.info(f"🔔 [BREAKING-NEWS] Preparing to ping news role {NEWS_ROLE_ID} for breaking news")
                elif urgency_level == "important":
                    ping_content = f"<@&{NEWS_ROLE_ID}> 📢 **Important News Update!**\n\n"
                    self.logger.info(f"🔔 [IMPORTANT-NEWS] Preparing to ping news role {NEWS_ROLE_ID} for important news")
                else:
                    ping_content = f"📰 <@&{NEWS_ROLE_ID}> **Update**\n\n"
                    self.logger.info(f"🔔 [NEWS-PING] Preparing to ping news role {NEWS_ROLE_ID} for regular news")

            # Prepare media attachments
            discord_files = []
            if media_files:
                discord_files = self._prepare_media_files(media_files)

            # Create the thread and post - different approach for forum vs regular channels
            if isinstance(news_channel, discord.ForumChannel):
                # Use the already determined category for forum tags
                applied_tags = self._get_forum_tags(news_channel, final_category)
                self.logger.info(f"[POSTING] Final forum tags applied: {[tag.name for tag in applied_tags] if applied_tags else 'None'}")

                # For forum channels, create thread with actual content directly
                final_content = ping_content + message_content
                
                # Ensure parameters are properly formatted for Discord API
                create_kwargs = {
                    "name": thread_title,
                    "content": final_content,
                    "applied_tags": applied_tags or [],
                }
                
                # Only add files parameter if we have files to attach
                if discord_files:
                    create_kwargs["files"] = discord_files
                
                thread, message = await news_channel.create_thread(**create_kwargs)
                
                if should_ping_news and ping_content:
                    if urgency_level == "breaking":
                        self.logger.info(f"🔔 [BREAKING-NEWS] Successfully posted with news role ping in forum thread: {thread_title}")
                    else:
                        self.logger.info(f"🔔 [NEWS-PING] Successfully posted with news role ping in forum thread: {thread_title}")
                
                self.logger.debug(
                    f"[POSTING] Created forum thread with content: {thread_title}, tags: {[tag.name for tag in applied_tags]}"
                )
            else:
                # For regular text channels, create thread then send message
                thread = await self._create_news_thread(news_channel, thread_title)
                if not thread:
                    return False
                
                # Send the message with media (include ping if needed)
                final_content = ping_content + message_content
                await self._send_message_to_thread(
                    thread, final_content, discord_files
                )
                
                if should_ping_news and ping_content:
                    if urgency_level == "breaking":
                        self.logger.info(f"🔔 [BREAKING-NEWS] Successfully posted with news role ping in thread: {thread_title}")
                    else:
                        self.logger.info(f"🔔 [NEWS-PING] Successfully posted with news role ping in thread: {thread_title}")

            # Send confirmation embed to logs channel
            await self._send_confirmation_embed(
                thread, thread_title, channelname, message_id, len(discord_files)
            )

            # Mark that content was posted for rich presence
            from src.core.rich_presence import mark_content_posted
            await mark_content_posted(self.bot)

            self.logger.info(
                f"[POSTING] Successfully posted to news channel: {thread_title}"
            )
            return True

        except Exception as e:
            self.logger.error(f"[POSTING] Error in news posting: {str(e)}")
            raise

    def _generate_thread_title(
        self, arabic_text: str, ai_title: Optional[str], channelname: str, urgency_level: str = "normal"
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
        
        # Add urgency indicator for breaking news
        if urgency_level == "breaking":
            urgency_emoji = "🚨"
        elif urgency_level == "important":
            urgency_emoji = "📢"
        else:
            urgency_emoji = "📅"

        # Build the thread title with appropriate emoji
        return f"{urgency_emoji} {current_date} | {title_text}"

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
        ai_location: Optional[str] = None,
        urgency_level: str = "normal",
        quality_score: float = 0.7,
        category_override: Optional[str] = None,
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
            from src.utils.ai_utils import clean_translation

            cleaned_translation = clean_translation(english_translation)
            content_parts.append("**Translation (EN):**")
            content_parts.append(cleaned_translation)
            content_parts.append("")  # Empty line

        # Add vertical info format (location, category, time)
        # Use AI-detected location if available, otherwise fall back to old detection method
        if ai_location and ai_location != "Unknown":
            location = ai_location
        else:
            location = self._detect_location(arabic_text, english_translation)
        
        # Use category override if provided (for consistency with forum tags), otherwise categorize content
        if category_override:
            category = category_override
        else:
            category = self._categorize_content(arabic_text, english_translation)
        
        damascus_tz = pytz.timezone("Asia/Damascus")
        current_time = datetime.datetime.now(damascus_tz).strftime(
            "%I:%M %p Damascus Time"
        )

        content_parts.append(f"📍 **Location:** {location}")
        content_parts.append(f"🏷️ **Category:** {category}")
        content_parts.append(f"🕒 **Posted:** {current_time}")
        
        # Add intelligence indicators
        if urgency_level != "normal":
            urgency_display = urgency_level.title()
            if urgency_level == "breaking":
                content_parts.append(f"🚨 **Urgency:** {urgency_display}")
            elif urgency_level == "important":
                content_parts.append(f"📢 **Urgency:** {urgency_display}")
        
        # Quality score removed - users don't need to see this information
        
        content_parts.append("")  # Empty line

        # Add improved beta warning with admin mention
        content_parts.append("---")
        content_parts.append("⚠️ **Beta Testing Notice**")
        content_parts.append(
            "This bot is currently in major development. News content and location accuracy may not be 100% accurate. "
            "Location detection includes accuracy percentages to help gauge reliability. "
            "If you notice any issues, translation errors, or unexpected content, please contact <@259725211664908288>."
        )
        content_parts.append("")  # Empty line

        # Note: News role ping is added at the top of the post, not here
        # to avoid duplicate pings

        return "\n".join(content_parts)

    def _detect_location(
        self, arabic_text: str, english_translation: Optional[str] = None
    ) -> str:
        """
        Detect location from Arabic text and English translation using AI and regex.

        Args:
            arabic_text: The original Arabic text
            english_translation: Optional English translation

        Returns:
            str: Detected location or "Syria" as fallback
        """
        try:
            # Import Syrian location detection utilities
            from src.utils.syrian_locations import detect_location_smart, detect_syrian_location

            # Try AI-powered detection first with the Arabic text
            if arabic_text:
                ai_location = detect_location_smart(arabic_text, self.bot)
                if ai_location and ai_location != "Unknown":
                    self.logger.debug(f"[POSTING] AI detected location: {ai_location}")
                    return ai_location

            # Try AI-powered detection with English translation
            if english_translation:
                ai_location = detect_location_smart(english_translation, self.bot)
                if ai_location and ai_location != "Unknown":
                    self.logger.debug(f"[POSTING] AI detected location from translation: {ai_location}")
                    return ai_location

            # Fallback to regex-based detection
            if arabic_text:
                location = detect_syrian_location(arabic_text)
                if location and location != "Syria":
                    return f"{location}, Syria"

            if english_translation:
                location = detect_syrian_location(english_translation)
                if location and location != "Syria":
                    return f"{location}, Syria"

            # Final fallback - only return "Syria" if we can't detect anything
            return "Unknown"

        except Exception as e:
            self.logger.debug(f"[POSTING] Error detecting location: {str(e)}")
            return "Unknown"

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
            logs_channel_id = config.get("discord.channels.logs") or config.get("channels.logs")
            logs_channel = self.bot.get_channel(logs_channel_id) if logs_channel_id else None
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

    def _map_ai_category_to_forum_tag(self, ai_category: str) -> str:
        """
        Map AI category to forum tag.

        Args:
            ai_category: The AI-generated category string

        Returns:
            str: Corresponding forum tag string
        """
        try:
            # Map AI category to forum tag
            ai_category_lower = ai_category.lower()
            mapped_tag = AI_CATEGORY_TO_FORUM_TAG.get(ai_category_lower, "📰 General News")
            
            self.logger.info(f"[POSTING] AI Category Mapping: '{ai_category}' -> '{ai_category_lower}' -> '{mapped_tag}'")
            self.logger.info(f"[POSTING] Available AI categories: {list(AI_CATEGORY_TO_FORUM_TAG.keys())}")
            
            return mapped_tag

        except Exception as e:
            self.logger.error(f"[POSTING] Error mapping AI category to forum tag: {str(e)}")
            return "📰 General News"

    async def post_news_content(self, content_data: dict, content_category: str = "social", is_manual: bool = False) -> bool:
        """
        Enhanced posting with comprehensive debugging.
        """
        try:
            self.logger.debug(f"📤 [POST-DEBUG] Starting post_news_content")
            self.logger.debug(f"📤 [POST-DEBUG] Content category: {content_category}")
            self.logger.debug(f"📤 [POST-DEBUG] Is manual: {is_manual}")
            self.logger.debug(f"📤 [POST-DEBUG] Content keys: {list(content_data.keys())}")
            
            # Extract content data
            arabic_text = content_data.get("text", "")
            english_translation = content_data.get("translation", "")
            ai_title = content_data.get("title", "أخبار سورية")
            location = content_data.get("location", "Unknown")
            media_urls = content_data.get("media_urls", [])
            source_channel = content_data.get("source_channel", "Unknown")
            
            self.logger.debug(f"📤 [POST-DEBUG] Arabic text length: {len(arabic_text)}")
            self.logger.debug(f"📤 [POST-DEBUG] English translation length: {len(english_translation)}")
            self.logger.debug(f"📤 [POST-DEBUG] AI title: {ai_title}")
            self.logger.debug(f"📤 [POST-DEBUG] Location: {location}")
            self.logger.debug(f"📤 [POST-DEBUG] Media URLs count: {len(media_urls)}")
            self.logger.debug(f"📤 [POST-DEBUG] Source channel: {source_channel}")

            # Validate required content
            if not arabic_text or not english_translation:
                self.logger.debug("📤 [POST-DEBUG] Missing required text content")
                self.logger.warning("[POSTING] Missing required text content")
                return False

            # Get Discord objects
            self.logger.debug("📤 [POST-DEBUG] Getting Discord guild and channels...")
            guild = self.bot.get_guild(self.guild_id)
            if not guild:
                self.logger.debug(f"📤 [POST-DEBUG] Guild not found: {self.guild_id}")
                self.logger.error(f"[POSTING] Guild not found: {self.guild_id}")
                return False

            news_channel = guild.get_channel(self.news_channel_id)
            log_channel = guild.get_channel(self.log_channel_id)
            
            self.logger.debug(f"📤 [POST-DEBUG] News channel found: {news_channel is not None}")
            self.logger.debug(f"📤 [POST-DEBUG] Log channel found: {log_channel is not None}")

            if not news_channel:
                self.logger.debug(f"📤 [POST-DEBUG] News channel not found: {self.news_channel_id}")
                self.logger.error(f"[POSTING] News channel not found: {self.news_channel_id}")
                return False

            # Create content parts
            self.logger.debug("📤 [POST-DEBUG] Building content parts...")
            content_parts = []
            
            # Add title
            content_parts.append(f"# {ai_title}")
            self.logger.debug(f"📤 [POST-DEBUG] Added title: {ai_title}")
            
            # Add original Arabic text
            content_parts.append("## النص الأصلي (Arabic)")
            content_parts.append(arabic_text)
            self.logger.debug("📤 [POST-DEBUG] Added Arabic text")
            
            # Add English translation
            content_parts.append("## Translation (English)")
            content_parts.append(english_translation)
            self.logger.debug("📤 [POST-DEBUG] Added English translation")
            
            # Add location with accuracy
            if location and location != "Unknown":
                content_parts.append(f"📍 **Location:** {location}")
                self.logger.debug(f"📤 [POST-DEBUG] Added location: {location}")
            
            # Add source
            content_parts.append(f"📺 **Source:** {source_channel}")
            self.logger.debug(f"📤 [POST-DEBUG] Added source: {source_channel}")
            
            # Add news role ping
            news_role = guild.get_role(self.news_role_id)
            if news_role:
                content_parts.append(f"📰 {news_role.mention} Update")
                self.logger.debug(f"📤 [POST-DEBUG] Added role mention: {news_role.name}")
            else:
                self.logger.debug(f"📤 [POST-DEBUG] News role not found: {self.news_role_id}")

            # Create the thread and post - different approach for forum vs regular channels
            if isinstance(news_channel, discord.ForumChannel):
                self.logger.debug("📤 [POST-DEBUG] Posting to forum channel")
                
                # Get the appropriate forum tag based on content category (use AI category if available)
                self.logger.debug(f"📤 [POST-DEBUG] Original AI content_category: '{content_category}'")
                
                if content_category != "social":
                    category = self._map_ai_category_to_forum_tag(content_category)
                    self.logger.debug(f"📤 [POST-DEBUG] Mapped AI category '{content_category}' to '{category}'")
                else:
                    category = self._categorize_content(arabic_text, english_translation)
                    self.logger.debug(f"📤 [POST-DEBUG] Used content categorization for 'social': '{category}'")
                
                applied_tags = self._get_forum_tags(news_channel, category)
                self.logger.debug(f"📤 [POST-DEBUG] Applied forum tags: {[tag.name for tag in applied_tags]}")
                
                # Create forum thread
                thread, message = await news_channel.create_thread(
                    name=ai_title[:100],  # Discord limits thread names to 100 chars
                    content="\n".join(content_parts),
                    applied_tags=applied_tags
                )
                self.logger.debug(f"📤 [POST-DEBUG] Created forum thread: {thread.name}")
            else:
                self.logger.debug("📤 [POST-DEBUG] Posting to regular channel")
                message = await news_channel.send("\n".join(content_parts))
                thread = None
                self.logger.debug(f"📤 [POST-DEBUG] Sent message to regular channel")

            # Handle media attachments
            if media_urls:
                self.logger.debug(f"📤 [POST-DEBUG] Processing {len(media_urls)} media attachments...")
                await self._handle_media_attachments(media_urls, thread or news_channel)
                self.logger.debug("📤 [POST-DEBUG] Media attachments processed")

            # Log successful post
            if log_channel:
                self.logger.debug("📤 [POST-DEBUG] Sending log notification...")
                log_embed = discord.Embed(
                    title="📰 News Posted Successfully",
                    description=f"**Title:** {ai_title}\n**Source:** {source_channel}\n**Category:** {content_category}",
                    color=0x00ff00,
                    timestamp=datetime.utcnow()
                )
                if thread:
                    log_embed.add_field(name="Thread", value=thread.mention, inline=False)
                else:
                    log_embed.add_field(name="Message", value=f"[Jump to message]({message.jump_url})", inline=False)
                
                await log_channel.send(embed=log_embed)
                self.logger.debug("📤 [POST-DEBUG] Log notification sent")

            self.logger.debug("📤 [POST-DEBUG] Post completed successfully")
            self.logger.info(f"[POSTING] Successfully posted news: {ai_title[:50]}...")
            return True

        except Exception as e:
            self.logger.debug(f"📤 [POST-DEBUG] Exception in posting: {str(e)}")
            self.logger.error(f"[POSTING] Error posting news content: {str(e)}")
            return False
