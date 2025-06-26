# =============================================================================
# NewsBot Streamlined Fetch Module - Automation Only
# =============================================================================
# This module handles automated fetching and posting of content from Telegram 
# channels, focusing only on background automation without manual commands.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import asyncio
import re
from typing import Optional
from datetime import datetime, timezone, timedelta

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import discord
from discord.ext import commands

# =============================================================================
# Local Application Imports
# =============================================================================
from src.components.embeds.base_embed import ErrorEmbed, SuccessEmbed
from src.utils.base_logger import base_logger as logger
from src.utils.structured_logger import structured_logger

# Import intelligence services
from src.services.news_intelligence import NewsIntelligenceService, UrgencyLevel
from src.services.ai_content_analyzer import AIContentAnalyzer

from .fetch_view import FetchView

# =============================================================================
# Text Processing Utility Functions
# =============================================================================
def remove_emojis(text):
    """Remove emojis from text using regex patterns."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub(r"", text)


def remove_links(text):
    """Remove URLs from text using regex patterns."""
    url_pattern = re.compile(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
    return url_pattern.sub("", text)


def remove_source_phrases(text):
    """Remove common source attribution phrases from Arabic text."""
    source_patterns = [
        r"المصدر:.*$",
        r"المصدر :.*$",
        r"المصدر\s*:.*$",
        r"مصدر:.*$",
        r"مصدر :.*$",
        r"مصدر\s*:.*$",
        r"من:.*$",
        r"من :.*$",
        r"من\s*:.*$",
        r"عن:.*$",
        r"عن :.*$",
        r"عن\s*:.*$",
        r"نقلاً عن:.*$",
        r"نقلاً عن :.*$",
        r"نقلاً عن\s*:.*$",
        r"نقلا عن:.*$",
        r"نقلا عن :.*$",
        r"نقلا عن\s*:.*$",
    ]
    for pattern in source_patterns:
        text = re.sub(pattern, "", text, flags=re.MULTILINE)
    return text.strip()


# =============================================================================
# Blacklist Management Functions
# =============================================================================
async def _atomic_blacklist_add(bot, message_id: int, max_retries: int = 3) -> bool:
    """
    Atomically add a message ID to the blacklist with retry logic to prevent race conditions.
    
    Args:
        bot: The bot instance
        message_id: The message ID to add to blacklist
        max_retries: Maximum number of retry attempts
        
    Returns:
        bool: True if successfully added, False otherwise
    """
    logger.info(f"🔒 [BLACKLIST] Attempting to add message {message_id} to blacklist")
    
    for attempt in range(max_retries):
        try:
            # Get current blacklist
            blacklist = await bot.json_cache.get("blacklisted_posts") or []
            current_count = len(blacklist)
            
            # Check if already exists (avoid duplicates)
            if message_id in blacklist:
                logger.info(f"✅ [BLACKLIST] Message {message_id} already in blacklist (size: {current_count})")
                return True
            
            # Add the new message ID
            blacklist.append(message_id)
            
            # Try to save - this is where race conditions can occur
            await bot.json_cache.set("blacklisted_posts", blacklist)
            
            logger.info(f"✅ [BLACKLIST] Successfully added message {message_id} to blacklist (attempt {attempt + 1}, new size: {len(blacklist)})")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ [BLACKLIST] Failed to update blacklist (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                # Wait a bit before retrying to reduce race condition probability
                await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
            else:
                logger.error(f"❌ [BLACKLIST] Failed to add message {message_id} to blacklist after {max_retries} attempts")
                return False
    
    return False


# =============================================================================
# Streamlined Fetch Commands Cog Class
# =============================================================================
class StreamlinedFetchCommands(commands.Cog):
    """
    Streamlined fetch and content management for automated operation.

    Features:
    - Intelligent news fetching with urgency detection (automation only)
    - Advanced content analysis and quality assessment
    - Smart posting decisions with timing logic
    - Multi-language support and filtering
    - No manual commands - fully automated
    """

    def __init__(self, bot: discord.Client) -> None:
        """Initialize the StreamlinedFetchCommands cog."""
        self.bot = bot
        self.posting_locks = set()  # Track locked channels to prevent spam posting
        
        # DUPLICATE PREVENTION: In-memory tracking for messages being processed
        self._processing_messages = set()  # Track messages currently being processed
        self._processing_lock = asyncio.Lock()  # Lock for processing set operations
        
        # Initialize AI services for intelligent analysis
        try:
            self.news_intelligence = NewsIntelligenceService()
            self.ai_analyzer = AIContentAnalyzer(bot)
            logger.info("🧠 AI services initialized for StreamlinedFetchCommands")
        except Exception as e:
            logger.error(f"❌ Failed to initialize AI services: {e}")
            self.news_intelligence = None
            self.ai_analyzer = None
        
        logger.info("🔧 StreamlinedFetchCommands cog initialized (automation only)")

    async def _cleanup_processing_message(self, message_id: int, reason: str = "completed"):
        """Remove a message from the processing set with logging."""
        async with self._processing_lock:
            self._processing_messages.discard(message_id)
            logger.debug(f"🔓 [DUPLICATE-PREVENTION] Removed message {message_id} from processing set ({reason})")

    async def should_skip_post(self, content: str) -> bool:
        """
        Check if a post should be skipped based on content filters.
        
        Args:
            content: The content to check
            
        Returns:
            bool: True if the post should be skipped, False otherwise
        """
        try:
            if not content:
                return True
                
            # Check content length
            if len(content.strip()) < 10:
                logger.debug("[CONTENT-FILTER] Skipping short content")
                return True
                
            # Basic spam detection
            spam_patterns = [
                r'http[s]?://[^\s]+',  # URLs
                r'@\w+',               # Mentions
                r'#\w+',               # Hashtags (excessive)
            ]
            
            for pattern in spam_patterns:
                if len(re.findall(pattern, content)) > 3:
                    logger.debug(f"[CONTENT-FILTER] Skipping content with excessive {pattern}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"[FETCH] Error checking blacklist: {e}")
            # On error, skip the post to be safe
            return True

    # =========================================================================
    # Core Automation Methods
    # =========================================================================
    async def fetch_and_post_auto(self, channel_name: str) -> bool:
        """
        Enhanced intelligent auto-fetch with comprehensive AI analysis.
        
        This method fetches the latest messages from a Telegram channel,
        processes them with advanced AI intelligence, and posts suitable content to Discord.
        
        Features:
        - Breaking news detection with urgency scoring and confidence assessment
        - Advanced sentiment analysis and intelligent content categorization
        - Duplicate detection using similarity algorithms to prevent reposts
        - Content quality assessment with detailed metrics
        - News role pinging for ALL posts with appropriate styling based on urgency
        - Comprehensive logging and fallback mechanisms for reliability
        
        Args:
            channel_name: Name of the Telegram channel to fetch from
            
        Returns:
            bool: True if posting was successful, False otherwise
        """
        # SPAM PREVENTION: Global posting lock
        if not hasattr(self.bot, '_posting_lock'):
            self.bot._posting_lock = asyncio.Lock()
        
        async with self.bot._posting_lock:
            logger.info(f"🔒 [SPAM-PREVENTION] Acquired posting lock for {channel_name}")
            try:
                logger.info(f"🧠 [INTELLIGENT-FETCH] Starting enhanced auto-post for channel: {channel_name}")
                
                # Check if Telegram client is available
                if not hasattr(self.bot, 'telegram_client') or not self.bot.telegram_client:
                    logger.warning("[INTELLIGENT-FETCH] Telegram client not available")
                    return False

                if not await self.bot.telegram_client.is_connected():
                    logger.warning("[INTELLIGENT-FETCH] Telegram client not connected")
                    return False

                # Get blacklisted message IDs
                blacklisted_ids = await self.bot.json_cache.get("blacklisted_posts") or []
                logger.debug(f"[INTELLIGENT-FETCH] Loaded {len(blacklisted_ids)} blacklisted message IDs")

                # Fetch messages from the channel (SPAM PREVENTION: Only 1 message at a time)
                messages = await self.bot.telegram_client.get_messages(channel_name, limit=1)
                messages_processed = len(messages)
                logger.debug(f"[INTELLIGENT-FETCH] Fetched {messages_processed} messages from {channel_name}")

                for message in messages:
                    # CRITICAL DUPLICATE PREVENTION: Check both persistent blacklist and in-memory processing
                    async with self._processing_lock:
                        # Check if message is currently being processed
                        if message.id in self._processing_messages:
                            logger.warning(f"🚫 [DUPLICATE-PREVENTION] Message {message.id} already being processed, skipping to prevent duplicate")
                            continue
                        
                        # Check persistent blacklist
                        if message.id in blacklisted_ids:
                            logger.debug(f"[INTELLIGENT-FETCH] Skipping blacklisted message {message.id}")
                            continue
                        
                        # Mark message as being processed to prevent duplicate processing
                        self._processing_messages.add(message.id)
                        logger.debug(f"🔒 [DUPLICATE-PREVENTION] Marked message {message.id} as being processed")

                    # Get automation config to check requirements
                    automation_config = getattr(self.bot, 'automation_config', {})
                    require_media = automation_config.get('require_media', True)
                    require_text = automation_config.get('require_text', True)

                    # Check if message has text (if required)
                    if require_text and not message.message:
                        logger.debug(f"[INTELLIGENT-FETCH] Skipping message {message.id} - missing text (text required)")
                        await self._cleanup_processing_message(message.id, "missing text")
                        continue

                    # Check for media requirement (only if required by config)
                    if require_media and not message.media:
                        logger.debug(f"[INTELLIGENT-FETCH] Skipping message {message.id} - text-only post (media required by config)")
                        await self._cleanup_processing_message(message.id, "no media")
                        continue

                    # Clean the message text
                    cleaned_text = message.message
                    if cleaned_text:
                        cleaned_text = remove_emojis(cleaned_text)
                        cleaned_text = remove_links(cleaned_text)
                        cleaned_text = remove_source_phrases(cleaned_text)
                        cleaned_text = cleaned_text.strip()

                    # Check if content should be skipped (basic blacklist)
                    if await self.should_skip_post(cleaned_text):
                        logger.info(f"[INTELLIGENT-FETCH] Skipping message {message.id} - basic content filter")
                        continue

                    # 🧠 AI ANALYSIS
                    try:
                        if hasattr(self, 'ai_analyzer') and self.ai_analyzer is not None:
                            ai_processed = await self.ai_analyzer.process_content_intelligently(
                                raw_content=cleaned_text,
                                channel=channel_name,
                                media=[message.media] if message.media else [],
                                telegram_message=message,
                                message_id=message.id
                            )

                            logger.info(f"🤖 [AI-ANALYSIS] Message {message.id}: {ai_processed.sentiment.sentiment.value} "
                                      f"| {ai_processed.categories.primary_category.value} "
                                      f"| Quality: {ai_processed.quality.overall_score:.2f} "
                                      f"| Safety: {ai_processed.safety.safety_level.value} "
                                      f"| Should post: {ai_processed.should_post}")

                            # Safety filtering
                            if ai_processed.safety.should_filter:
                                logger.warning(f"🛡️ [SAFETY-FILTER] Skipping message {message.id} - content filtered for safety")
                                await _atomic_blacklist_add(self.bot, message.id)
                                continue

                            # AI posting recommendation
                            if not ai_processed.should_post:
                                logger.info(f"[INTELLIGENT-FETCH] Skipping message {message.id} - AI analysis recommends skip")
                                logger.info(f"[DEBUG] AI rejection reason - Quality: {ai_processed.quality.overall_score:.2f}, Similarity: {ai_processed.similarity_score:.2f}, Safety: {ai_processed.safety.safety_level.value}")
                                continue

                            # Duplicate check
                            if ai_processed.similarity_score > 0.8:
                                logger.info(f"[INTELLIGENT-FETCH] Skipping message {message.id} - too similar to recent content")
                                continue

                    except Exception as e:
                        logger.error(f"❌ [AI-ANALYSIS] Analysis failed for message {message.id}: {e}")

                    # Schedule posting with delay
                    try:
                        fetch_view = FetchView(self.bot, auto_mode=True)
                        await self._schedule_delayed_post(fetch_view, message.id, 30, channel_name)
                        logger.info(f"⏱️ [INTELLIGENT-FETCH] Scheduled delayed post for message {message.id} in 30 seconds")
                        
                        # Add to blacklist immediately to prevent duplicate scheduling
                        await _atomic_blacklist_add(self.bot, message.id)
                        await self._cleanup_processing_message(message.id, "scheduled")
                        
                        return True
                        
                    except Exception as e:
                        logger.error(f"❌ [INTELLIGENT-FETCH] Failed to schedule post for message {message.id}: {e}")
                        await self._cleanup_processing_message(message.id, "schedule failed")
                        continue

                logger.info(f"📊 [INTELLIGENT-FETCH] Processed {messages_processed} messages from {channel_name}, no suitable content found")
                return False

            except Exception as e:
                logger.error(f"❌ [INTELLIGENT-FETCH] Error in auto-fetch for {channel_name}: {e}")
                return False

    async def _schedule_delayed_post(self, fetch_view, message_id, delay, channel_name):
        """Schedule a delayed post with proper error handling."""
        async def delayed_post():
            try:
                await asyncio.sleep(delay)
                logger.info(f"🚀 [DELAYED-POST] Attempting to post delayed message {message_id} from {channel_name}")
                
                # Verify message is still blacklisted (should be)
                blacklisted_ids = await self.bot.json_cache.get("blacklisted_posts") or []
                if message_id not in blacklisted_ids:
                    logger.warning(f"⚠️ [DELAYED-POST] Message {message_id} not in blacklist, may be duplicate")
                else:
                    logger.debug(f"✅ [DELAYED-POST] Message {message_id} is properly blacklisted")
                
                # Post the message
                try:
                    await fetch_view.post_to_news(None, message_id, "auto_mode")
                    logger.info(f"✅ [DELAYED-POST] Successfully posted message {message_id} from {channel_name}")
                except Exception as e:
                    logger.error(f"❌ [DELAYED-POST] Failed to post message {message_id}: {e}")
                    
            except Exception as e:
                logger.error(f"❌ [DELAYED-POST] Error in delayed post task for message {message_id}: {e}")
        
        # Create and start the delayed post task
        asyncio.create_task(delayed_post())

    async def auto_post_from_channel(self, channel_name: str) -> bool:
        """
        Auto-post from a specific channel using intelligent fetch.
        
        Args:
            channel_name: Name of the channel to fetch from
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            return await self.fetch_and_post_auto(channel_name)
        except Exception as e:
            logger.error(f"❌ [AUTO-POST] Error in auto_post_from_channel for {channel_name}: {e}")
            return False


async def setup(bot: commands.Bot) -> None:
    """Setup function for the cog."""
    await bot.add_cog(StreamlinedFetchCommands(bot))


def setup_fetch_commands(bot):
    """Setup fetch commands for the bot (automation only)."""
    try:
        # Create streamlined fetch commands instance
        fetch_cog = StreamlinedFetchCommands(bot)
        
        # Store reference to fetch commands for auto-posting
        bot.fetch_commands = fetch_cog
        
        logger.info("✅ Streamlined fetch commands setup completed (automation only)")
        
    except Exception as e:
        logger.error(f"❌ Failed to setup streamlined fetch commands: {e}")
        raise 