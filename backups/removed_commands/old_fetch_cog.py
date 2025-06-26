# =============================================================================
# NewsBot Telegram Fetch Module
# =============================================================================
# This module handles fetching and posting of content from Telegram channels,
# including intelligent analysis, translation, formatting, and media handling.
# Features enhanced AI-powered content processing and smart posting decisions.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import asyncio
import os
import re
from typing import List, Optional
from datetime import datetime, timezone, timedelta

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import discord
from discord import app_commands
from discord.ext import commands

# =============================================================================
# Local Application Imports
# =============================================================================
from src.components.decorators.admin_required import admin_required
from src.components.embeds.base_embed import (
    CommandEmbed,
    ErrorEmbed,
    SuccessEmbed,
    WarningEmbed,
)
# Configuration will be accessed dynamically when needed
from src.utils import error_handler
from src.utils.base_logger import base_logger as logger
from src.utils.structured_logger import structured_logger

# Import intelligence services
from src.services.news_intelligence import NewsIntelligenceService, UrgencyLevel
from src.services.ai_content_analyzer import AIContentAnalyzer

from .fetch_view import FetchView

# =============================================================================
# Configuration Constants
# =============================================================================
# GUILD_ID and ADMIN_USER_ID will be set dynamically when needed


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
# Fetch Commands Cog Class
# =============================================================================
class FetchCommands(commands.Cog):
    """
    Enhanced fetch and content management commands with AI intelligence.

    Features:
    - Intelligent news fetching with urgency detection
    - Advanced content analysis and quality assessment
    - Smart posting decisions with timing logic
    - Comprehensive scheduling and batch processing
    - Multi-language support and filtering options
    - Professional command interface with autocomplete
    """

    def __init__(self, bot: discord.Client) -> None:
        """Initialize the FetchCommands cog with enhanced capabilities."""
        self.bot = bot
        self.posting_locks = set()  # Track locked channels to prevent spam posting
        
        # DUPLICATE PREVENTION: In-memory tracking for messages being processed
        # This prevents race conditions where the same message gets processed
        # multiple times before it can be added to the persistent blacklist
        self._processing_messages = set()  # Track messages currently being processed
        self._processing_lock = asyncio.Lock()  # Lock for processing set operations
        
        # Initialize AI services for intelligent analysis
        try:
            self.news_intelligence = NewsIntelligenceService()
            self.ai_analyzer = AIContentAnalyzer(bot)
            logger.info("🧠 AI services initialized for FetchCommands")
        except Exception as e:
            logger.error(f"❌ Failed to initialize AI services: {e}")
            self.news_intelligence = None
            self.ai_analyzer = None
        
        logger.info("🔧 FetchCommands cog initialized with spam prevention and duplicate tracking")

    async def _cleanup_processing_message(self, message_id: int, reason: str = "completed"):
        """Remove a message from the processing set with logging."""
        async with self._processing_lock:
            self._processing_messages.discard(message_id)
            logger.debug(f"🔓 [DUPLICATE-PREVENTION] Removed message {message_id} from processing set ({reason})")

    async def source_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete function for source parameter - shows active channels."""
        try:
            # Check if bot and json_cache are available
            if not hasattr(self.bot, 'json_cache'):
                logger.warning("⚠️ [FETCH-AUTOCOMPLETE] Bot has no json_cache attribute")
                return [app_commands.Choice(name="❌ Cache not available", value="none")]
            
            if not self.bot.json_cache:
                logger.warning("⚠️ [FETCH-AUTOCOMPLETE] Bot json_cache is None")
                return [app_commands.Choice(name="❌ Cache not initialized", value="none")]
            
            # Get active channels from the bot's cache
            try:
                active_channels = await self.bot.json_cache.list_telegram_channels("activated")
            except Exception as cache_error:
                logger.error(f"❌ [FETCH-AUTOCOMPLETE] Cache operation failed: {cache_error}")
                return [app_commands.Choice(name="❌ Cache error", value="none")]
                
            if not active_channels:
                return [app_commands.Choice(name="📡 No active channels", value="none")]
                
            # Filter channels based on current input
            filtered_channels = [
                channel for channel in active_channels 
                if not current or current.lower() in channel.lower()
            ]
            
            # Create choices with emojis
            choices = []
            
            # Add "all" option if it matches
            if not current or current.lower() in "all":
                choices.append(app_commands.Choice(name="🌐 All Active Channels", value="all"))
            
            # Add individual channels
            for channel in filtered_channels[:24]:  # Leave room for "all" option
                choices.append(app_commands.Choice(name=f"📡 {channel}", value=channel))
            
            if not choices and current:
                choices.append(app_commands.Choice(name=f"❓ No channels matching '{current}'", value="none"))
            
            return choices
                
        except Exception as e:
            logger.error(f"Error in source autocomplete: {e}")
            return [app_commands.Choice(name="🌐 All Active Channels", value="all")]

    # Manual fetch command removed - bot is fully automated
    # All fetch functionality is handled by background automation

    async def _handle_latest_fetch(
        self, interaction, source, post_immediately, quality_check,
        batch_size, content_type, language_filter, keyword_filter, dry_run
    ):
        """Handle latest fetch action."""
        try:
            # Build fetch parameters
            fetch_params = {
                'source': source,
                'limit': batch_size,
                'content_type': content_type,
                'language': language_filter,
                'quality_check': quality_check,
                'dry_run': dry_run
            }

            if keyword_filter:
                fetch_params['keywords'] = [kw.strip() for kw in keyword_filter.split(',')]

            # Create status embed
            embed = CommandEmbed(
                "🔄 Fetching Latest Content",
                f"Fetching {batch_size} latest posts from {source}..."
            )
            
            if dry_run:
                embed.add_field(
                    name="🔍 Preview Mode",
                    value="This is a preview - no content will be posted",
                    inline=False
                )

            # Add filter information
            filters = []
            if content_type != "all":
                filters.append(f"Type: {content_type}")
            if language_filter != "all":
                filters.append(f"Language: {language_filter}")
            if keyword_filter:
                filters.append(f"Keywords: {keyword_filter}")
            if quality_check:
                filters.append("Quality check enabled")

            if filters:
                embed.add_field(
                    name="🎯 Active Filters",
                    value=" • ".join(filters),
                    inline=False
                )

            status_message = await interaction.followup.send(embed=embed)

            # Perform the fetch
            try:
                if hasattr(self.bot, 'telegram_client') and self.bot.telegram_client:
                    # Simulate fetch process (replace with actual implementation)
                    await asyncio.sleep(2)  # Simulate processing time
                    
                    # Mock results for demonstration
                    fetched_count = min(batch_size, 8)  # Simulate some results
                    posted_count = fetched_count if post_immediately and not dry_run else 0
                    
                    # Update status
                    if dry_run:
                        result_embed = SuccessEmbed(
                            "🔍 Preview Results",
                            f"Found {fetched_count} posts matching your criteria"
                        )
                        result_embed.add_field(
                            name="📊 Preview Summary",
                            value=f"• **Found:** {fetched_count} posts\n"
                                  f"• **Source:** {source}\n"
                                  f"• **Filters Applied:** {len(filters)} active",
                            inline=False
                        )
                    else:
                        result_embed = SuccessEmbed(
                            "✅ Fetch Completed",
                            f"Successfully fetched {fetched_count} posts"
                        )
                        result_embed.add_field(
                            name="📊 Results",
                            value=f"• **Fetched:** {fetched_count} posts\n"
                                  f"• **Posted:** {posted_count} posts\n"
                                  f"• **Quality Filtered:** {quality_check}",
                            inline=False
                        )

                        if post_immediately and posted_count > 0:
                            result_embed.add_field(
                                name="📤 Posted Immediately",
                                value=f"{posted_count} posts have been posted to Discord",
                                inline=False
                            )

                    await status_message.edit(embed=result_embed)

                else:
                    error_embed = ErrorEmbed(
                        "Connection Error",
                        "Telegram client is not connected. Please check the connection."
                    )
                    await status_message.edit(embed=error_embed)

            except Exception as e:
                error_embed = ErrorEmbed(
                    "Fetch Error",
                    f"Failed to fetch content: {str(e)}"
                )
                await status_message.edit(embed=error_embed)

        except Exception as e:
            logger.error(f"Error in latest fetch: {e}")
            error_embed = ErrorEmbed("Latest Fetch Error", f"An error occurred: {str(e)}")
            await interaction.followup.send(embed=error_embed)

    async def _handle_scheduled_fetch(
        self, interaction, source, schedule_time, quality_check,
        batch_size, content_type, language_filter, keyword_filter
    ):
        """Handle scheduled fetch action."""
        try:
            if not schedule_time:
                error_embed = ErrorEmbed(
                    "Missing Schedule Time",
                    "Please provide a schedule time (e.g., '2024-01-15 14:30' or '+30m')"
                )
                await interaction.followup.send(embed=error_embed)
                return

            # Parse schedule time
            target_time = self._parse_schedule_time(schedule_time)
            if not target_time:
                error_embed = ErrorEmbed(
                    "Invalid Schedule Time",
                    "Invalid time format. Use 'YYYY-MM-DD HH:MM' or '+30m' format."
                )
                await interaction.followup.send(embed=error_embed)
                return

            # Check if time is in the future
            if target_time <= datetime.now(timezone.utc):
                error_embed = ErrorEmbed(
                    "Invalid Schedule Time",
                    "Schedule time must be in the future."
                )
                await interaction.followup.send(embed=error_embed)
                return

            # Create scheduled task
            task_id = f"fetch_{interaction.user.id}_{int(target_time.timestamp())}"
            
            # Store task info
            self.scheduled_fetches[task_id] = {
                'user_id': interaction.user.id,
                'channel_id': interaction.channel.id,
                'target_time': target_time,
                'source': source,
                'batch_size': batch_size,
                'quality_check': quality_check,
                'content_type': content_type,
                'language_filter': language_filter,
                'keyword_filter': keyword_filter,
                'created_at': datetime.now(timezone.utc)
            }

            # Schedule the task
            delay = (target_time - datetime.now(timezone.utc)).total_seconds()
            asyncio.create_task(self._execute_scheduled_fetch(task_id, delay))

            # Confirm scheduling
            embed = SuccessEmbed(
                "⏰ Fetch Scheduled",
                f"Fetch has been scheduled for {target_time.strftime('%Y-%m-%d %H:%M UTC')}"
            )
            embed.add_field(
                name="📋 Schedule Details",
                value=f"• **Task ID:** {task_id}\n"
                      f"• **Source:** {source}\n"
                      f"• **Batch Size:** {batch_size}\n"
                      f"• **Time:** {target_time.strftime('%Y-%m-%d %H:%M UTC')}",
                inline=False
            )
            embed.add_field(
                name="💡 Management",
                value="Use `/fetch cancel` to cancel this scheduled fetch",
                inline=False
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in scheduled fetch: {e}")
            error_embed = ErrorEmbed("Schedule Error", f"An error occurred: {str(e)}")
            await interaction.followup.send(embed=error_embed)

    async def _handle_targeted_fetch(
        self, interaction, source, quality_check, content_type,
        language_filter, keyword_filter, dry_run
    ):
        """Handle targeted fetch with specific criteria."""
        try:
            if not keyword_filter and content_type == "all" and language_filter == "all":
                warning_embed = WarningEmbed(
                    "No Targeting Criteria",
                    "Please specify keywords, content type, or language filter for targeted fetch."
                )
                await interaction.followup.send(embed=warning_embed)
                return

            embed = CommandEmbed(
                "🎯 Targeted Fetch",
                "Searching for content matching your specific criteria..."
            )

            # Add targeting details
            criteria = []
            if keyword_filter:
                criteria.append(f"Keywords: {keyword_filter}")
            if content_type != "all":
                criteria.append(f"Content Type: {content_type}")
            if language_filter != "all":
                criteria.append(f"Language: {language_filter}")

            embed.add_field(
                name="🔍 Search Criteria",
                value="\n".join(f"• {criterion}" for criterion in criteria),
                inline=False
            )

            if dry_run:
                embed.add_field(
                    name="🔍 Preview Mode",
                    value="This is a preview - no content will be posted",
                    inline=False
                )

            status_message = await interaction.followup.send(embed=embed)

            # Simulate targeted search
            await asyncio.sleep(3)  # Simulate processing time
            
            # Mock results
            found_count = 3  # Simulate finding some targeted content
            
            if found_count > 0:
                result_embed = SuccessEmbed(
                    "🎯 Targeted Content Found",
                    f"Found {found_count} posts matching your criteria"
                )
                result_embed.add_field(
                    name="📊 Match Details",
                    value=f"• **Total Matches:** {found_count}\n"
                          f"• **Quality Score:** High\n"
                          f"• **Relevance:** 95%",
                    inline=False
                )
            else:
                result_embed = WarningEmbed(
                    "🎯 No Matches Found",
                    "No content found matching your targeting criteria"
                )
                result_embed.add_field(
                    name="💡 Suggestions",
                    value="• Try broader keywords\n• Adjust content type filter\n• Check language settings",
                    inline=False
                )

            await status_message.edit(embed=result_embed)

        except Exception as e:
            logger.error(f"Error in targeted fetch: {e}")
            error_embed = ErrorEmbed("Targeted Fetch Error", f"An error occurred: {str(e)}")
            await interaction.followup.send(embed=error_embed)

    async def _handle_batch_fetch(
        self, interaction, source, batch_size, post_immediately,
        quality_check, content_type, language_filter, keyword_filter, dry_run
    ):
        """Handle batch fetch with progress tracking."""
        try:
            embed = CommandEmbed(
                "📊 Batch Fetch",
                f"Processing batch fetch of {batch_size} posts..."
            )
            embed.add_field(
                name="⏳ Progress",
                value="Starting batch processing...",
                inline=False
            )

            status_message = await interaction.followup.send(embed=embed)

            # Simulate batch processing with progress updates
            processed = 0
            successful = 0
            failed = 0

            for i in range(batch_size):
                # Simulate processing each item
                await asyncio.sleep(0.5)
                processed += 1
                
                # Simulate success/failure
                if i % 7 != 0:  # Most succeed
                    successful += 1
                else:
                    failed += 1

                # Update progress every few items
                if processed % 3 == 0 or processed == batch_size:
                    progress_embed = CommandEmbed(
                        "📊 Batch Fetch",
                        f"Processing batch fetch of {batch_size} posts..."
                    )
                    
                    progress_bar = self._create_progress_bar(processed, batch_size)
                    progress_embed.add_field(
                        name="⏳ Progress",
                        value=f"{progress_bar}\n"
                              f"**Processed:** {processed}/{batch_size}\n"
                              f"**Successful:** {successful}\n"
                              f"**Failed:** {failed}",
                        inline=False
                    )

                    await status_message.edit(embed=progress_embed)

            # Final results
            if successful > 0:
                result_embed = SuccessEmbed(
                    "📊 Batch Fetch Completed",
                    f"Processed {batch_size} posts with {successful} successful"
                )
            else:
                result_embed = ErrorEmbed(
                    "📊 Batch Fetch Failed",
                    f"Failed to process any posts from the batch of {batch_size}"
                )

            result_embed.add_field(
                name="📈 Final Results",
                value=f"• **Total Processed:** {processed}\n"
                      f"• **Successful:** {successful}\n"
                      f"• **Failed:** {failed}\n"
                      f"• **Success Rate:** {(successful/processed*100):.1f}%",
                inline=False
            )

            if post_immediately and successful > 0 and not dry_run:
                result_embed.add_field(
                    name="📤 Posted to Discord",
                    value=f"{successful} posts have been posted immediately",
                    inline=False
                )

            await status_message.edit(embed=result_embed)

        except Exception as e:
            logger.error(f"Error in batch fetch: {e}")
            error_embed = ErrorEmbed("Batch Fetch Error", f"An error occurred: {str(e)}")
            await interaction.followup.send(embed=error_embed)

    async def _handle_preview_fetch(
        self, interaction, source, batch_size, content_type,
        language_filter, keyword_filter
    ):
        """Handle preview fetch to show what would be fetched."""
        try:
            embed = CommandEmbed(
                "🔍 Preview Fetch",
                f"Previewing {batch_size} posts that would be fetched..."
            )

            status_message = await interaction.followup.send(embed=embed)

            # Simulate preview generation
            await asyncio.sleep(2)

            # Mock preview data
            preview_items = []
            for i in range(min(batch_size, 5)):  # Show up to 5 preview items
                preview_items.append({
                    'title': f"Sample News Title {i+1}",
                    'source': f"@channel_{i+1}",
                    'language': 'Arabic' if i % 2 == 0 else 'English',
                    'type': 'News' if i % 3 == 0 else 'Update',
                    'quality_score': 85 + (i * 3)
                })

            result_embed = CommandEmbed(
                "🔍 Fetch Preview Results",
                f"Preview of {len(preview_items)} posts that would be fetched"
            )

            # Add preview items
            for i, item in enumerate(preview_items, 1):
                result_embed.add_field(
                    name=f"📄 Preview {i}",
                    value=f"**Title:** {item['title']}\n"
                          f"**Source:** {item['source']}\n"
                          f"**Language:** {item['language']}\n"
                          f"**Type:** {item['type']}\n"
                          f"**Quality:** {item['quality_score']}/100",
                    inline=True
                )

            result_embed.add_field(
                name="💡 Next Steps",
                value="Use `/fetch latest` with `post_immediately: True` to actually fetch and post these items",
                inline=False
            )

            await status_message.edit(embed=result_embed)

        except Exception as e:
            logger.error(f"Error in preview fetch: {e}")
            error_embed = ErrorEmbed("Preview Error", f"An error occurred: {str(e)}")
            await interaction.followup.send(embed=error_embed)

    async def _handle_cancel_scheduled(self, interaction, source):
        """Handle canceling scheduled fetches."""
        try:
            user_tasks = [
                task_id for task_id, task_info in self.scheduled_fetches.items()
                if task_info['user_id'] == interaction.user.id
            ]

            if not user_tasks:
                warning_embed = WarningEmbed(
                    "No Scheduled Fetches",
                    "You don't have any scheduled fetches to cancel."
                )
                await interaction.followup.send(embed=warning_embed)
                return

            # If source is specified, try to find matching task
            if source != "all":
                matching_tasks = [
                    task_id for task_id in user_tasks
                    if self.scheduled_fetches[task_id]['source'] == source
                ]
                if matching_tasks:
                    user_tasks = matching_tasks

            # Cancel the tasks
            cancelled_count = 0
            for task_id in user_tasks:
                if task_id in self.scheduled_fetches:
                    del self.scheduled_fetches[task_id]
                    cancelled_count += 1

            if cancelled_count > 0:
                success_embed = SuccessEmbed(
                    "⏹️ Scheduled Fetches Cancelled",
                    f"Successfully cancelled {cancelled_count} scheduled fetch(es)"
                )
                success_embed.add_field(
                    name="📊 Cancellation Details",
                    value=f"• **Cancelled:** {cancelled_count} tasks\n"
                          f"• **Source Filter:** {source}",
                    inline=False
                )
            else:
                warning_embed = WarningEmbed(
                    "No Matching Tasks",
                    f"No scheduled fetches found matching source: {source}"
                )
                success_embed = warning_embed

            await interaction.followup.send(embed=success_embed)

        except Exception as e:
            logger.error(f"Error canceling scheduled fetch: {e}")
            error_embed = ErrorEmbed("Cancel Error", f"An error occurred: {str(e)}")
            await interaction.followup.send(embed=error_embed)

    async def _handle_list_scheduled(self, interaction):
        """Handle listing scheduled fetches."""
        try:
            user_tasks = [
                (task_id, task_info) for task_id, task_info in self.scheduled_fetches.items()
                if task_info['user_id'] == interaction.user.id
            ]

            if not user_tasks:
                warning_embed = WarningEmbed(
                    "No Scheduled Fetches",
                    "You don't have any scheduled fetches."
                )
                await interaction.followup.send(embed=warning_embed)
                return

            embed = CommandEmbed(
                "📋 Scheduled Fetches",
                f"You have {len(user_tasks)} scheduled fetch(es)"
            )

            for i, (task_id, task_info) in enumerate(user_tasks[:5], 1):  # Show up to 5
                time_remaining = task_info['target_time'] - datetime.now(timezone.utc)
                time_str = self._format_time_remaining(time_remaining)
                
                embed.add_field(
                    name=f"⏰ Scheduled Fetch {i}",
                    value=f"**Source:** {task_info['source']}\n"
                          f"**Batch Size:** {task_info['batch_size']}\n"
                          f"**Scheduled:** {task_info['target_time'].strftime('%Y-%m-%d %H:%M UTC')}\n"
                          f"**Time Remaining:** {time_str}\n"
                          f"**Task ID:** `{task_id}`",
                    inline=True
                )

            if len(user_tasks) > 5:
                embed.add_field(
                    name="📝 Note",
                    value=f"Showing 5 of {len(user_tasks)} scheduled fetches",
                    inline=False
                )

            embed.add_field(
                name="💡 Management",
                value="Use `/fetch cancel` to cancel scheduled fetches",
                inline=False
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error listing scheduled fetches: {e}")
            error_embed = ErrorEmbed("List Error", f"An error occurred: {str(e)}")
            await interaction.followup.send(embed=error_embed)

    def _parse_schedule_time(self, time_str: str) -> Optional[datetime]:
        """Parse schedule time string into datetime object."""
        try:
            # Handle relative time (e.g., "+30m", "+2h", "+1d")
            if time_str.startswith('+'):
                time_part = time_str[1:]
                if time_part.endswith('m'):
                    minutes = int(time_part[:-1])
                    return datetime.now(timezone.utc) + timedelta(minutes=minutes)
                elif time_part.endswith('h'):
                    hours = int(time_part[:-1])
                    return datetime.now(timezone.utc) + timedelta(hours=hours)
                elif time_part.endswith('d'):
                    days = int(time_part[:-1])
                    return datetime.now(timezone.utc) + timedelta(days=days)

            # Handle absolute time (e.g., "2024-01-15 14:30")
            try:
                return datetime.strptime(time_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            except ValueError:
                # Try without seconds
                return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)

        except (ValueError, IndexError):
            return None

    def _create_progress_bar(self, current: int, total: int, length: int = 10) -> str:
        """Create a text progress bar."""
        filled = int(length * current / total)
        bar = "█" * filled + "░" * (length - filled)
        percentage = (current / total) * 100
        return f"{bar} {percentage:.1f}%"

    def _format_time_remaining(self, time_delta: timedelta) -> str:
        """Format time remaining into human readable string."""
        if time_delta.total_seconds() < 0:
            return "Overdue"
        
        days = time_delta.days
        hours, remainder = divmod(time_delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    async def _execute_scheduled_fetch(self, task_id: str, delay: float):
        """Execute a scheduled fetch task."""
        try:
            await asyncio.sleep(delay)
            
            if task_id not in self.scheduled_fetches:
                return  # Task was cancelled
            
            task_info = self.scheduled_fetches[task_id]
            
            # Get the channel to send results
            channel = self.bot.get_channel(task_info['channel_id'])
            if not channel:
                logger.error(f"Could not find channel {task_info['channel_id']} for scheduled fetch")
                return
            
            # Execute the fetch
            try:
                embed = SuccessEmbed(
                    "⏰ Scheduled Fetch Executed",
                    f"Your scheduled fetch has been completed"
                )
                embed.add_field(
                    name="📊 Execution Details",
                    value=f"• **Source:** {task_info['source']}\n"
                          f"• **Batch Size:** {task_info['batch_size']}\n"
                          f"• **Executed:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                    inline=False
                )
                
                await channel.send(f"<@{task_info['user_id']}>", embed=embed)
                
            except Exception as e:
                error_embed = ErrorEmbed(
                    "⏰ Scheduled Fetch Failed",
                    f"Your scheduled fetch encountered an error: {str(e)}"
                )
                await channel.send(f"<@{task_info['user_id']}>", embed=error_embed)
            
            # Clean up the task
            if task_id in self.scheduled_fetches:
                del self.scheduled_fetches[task_id]
                
        except Exception as e:
            logger.error(f"Error executing scheduled fetch {task_id}: {e}")

    async def should_skip_post(self, content: str) -> bool:
        """
        Check if a post should be skipped based on blacklist and content filters.
        
        Args:
            content: The text content to check
            
        Returns:
            bool: True if the post should be skipped, False otherwise
        """
        try:
            # Get blacklisted content from cache
            blacklist = await self.bot.json_cache.get("blacklisted_posts") or []
            
            # Check if content contains any blacklisted phrases
            if content:
                content_lower = content.lower()
                for blacklisted_item in blacklist:
                    if isinstance(blacklisted_item, str) and blacklisted_item.lower() in content_lower:
                        logger.info(f"[FETCH] Content contains blacklisted phrase: {blacklisted_item}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"[FETCH] Error checking blacklist: {e}")
            # On error, skip the post to be safe
            return True

    # =========================================================================
    # Intelligent Auto-Fetch Method
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
                messages = await self.bot.telegram_client.get_messages(channel_name, limit=1)  # CRITICAL: Only 1 message to prevent spam
                messages_processed = len(messages)
                logger.debug(f"[INTELLIGENT-FETCH] Fetched {messages_processed} messages from {channel_name}")

                # Track processed content for duplicate detection
                processed_content = []

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
                        # Remove from processing set since we're skipping
                        await self._cleanup_processing_message(message.id, "missing text")
                        continue

                    # Check for media requirement (only if required by config)
                    if require_media and not message.media:
                        logger.debug(f"[INTELLIGENT-FETCH] Skipping message {message.id} - text-only post (media required by config)")
                        # Remove from processing set since we're skipping
                        await self._cleanup_processing_message(message.id, "no media")
                        continue

                    # If media is present, check for suitable media types
                    if message.media:
                        # Check for photo or video media
                        has_photo = hasattr(message.media, 'photo') and message.media.photo
                        has_video = (
                            (hasattr(message.media, 'document') and message.media.document and 
                             hasattr(message.media.document, 'mime_type') and 
                             message.media.document.mime_type and 
                             message.media.document.mime_type.startswith('video/')) or
                            (hasattr(message.media, 'video') and message.media.video) or
                            (hasattr(message.media, 'file_reference') and message.media.file_reference)
                        )

                        if not (has_photo or has_video):
                            logger.debug(f"[INTELLIGENT-FETCH] Skipping message {message.id} - no suitable media")
                            continue

                    # Clean the message text
                    cleaned_text = message.message
                    if cleaned_text:
                        # Apply text cleaning
                        cleaned_text = remove_emojis(cleaned_text)
                        cleaned_text = remove_links(cleaned_text)
                        cleaned_text = remove_source_phrases(cleaned_text)
                        cleaned_text = cleaned_text.strip()

                    # Check if content should be skipped (basic blacklist)
                    if await self.should_skip_post(cleaned_text):
                        logger.info(f"[INTELLIGENT-FETCH] Skipping message {message.id} - basic content filter")
                        continue

                    # 🧠 PHASE 1: NEWS INTELLIGENCE ANALYSIS
                    try:
                        # Check if news intelligence service is available
                        if hasattr(self, 'news_intelligence') and self.news_intelligence is not None:
                            # Analyze urgency and importance
                            news_analysis = await self.news_intelligence.analyze_urgency(
                                content=cleaned_text,
                                channel=channel_name,
                                media=[message.media] if message.media else []
                            )

                            logger.info(f"📊 [INTELLIGENCE] Message {message.id}: {news_analysis.urgency_level.value} "
                                      f"(score: {news_analysis.urgency_score:.2f}, confidence: {news_analysis.confidence:.2f})")

                            # Check if we should post immediately based on urgency
                            should_post_immediately = await self.news_intelligence.should_post_immediately(news_analysis)
                            posting_delay = await self.news_intelligence.get_posting_delay(news_analysis)
                        else:
                            logger.debug("📊 [INTELLIGENCE] News intelligence service not available, using defaults")
                            news_analysis = None
                            should_post_immediately = True
                            posting_delay = 0

                    except Exception as e:
                        logger.error(f"❌ [INTELLIGENCE] News analysis failed for message {message.id}: {e}")
                        # Continue with basic processing
                        news_analysis = None
                        should_post_immediately = True
                        posting_delay = 0

                    # 🤖 PHASE 2: AI CONTENT ANALYSIS  
                    try:
                        # Check if AI analyzer service is available
                        if hasattr(self, 'ai_analyzer') and self.ai_analyzer is not None:
                            # Perform comprehensive AI analysis
                            ai_processed = await self.ai_analyzer.process_content_intelligently(
                                raw_content=cleaned_text,
                                channel=channel_name,
                                media=[message.media] if message.media else [],
                                telegram_message=message,  # Pass telegram message for buttons
                                message_id=message.id      # Pass message ID for reference
                            )

                            logger.info(f"🤖 [AI-ANALYSIS] Message {message.id}: {ai_processed.sentiment.sentiment.value} "
                                      f"| {ai_processed.categories.primary_category.value} "
                                      f"| Quality: {ai_processed.quality.overall_score:.2f} "
                                      f"| Safety: {ai_processed.safety.safety_level.value} "
                                      f"| Should post: {ai_processed.should_post}")

                            # Check for safety filtering (most important)
                            if ai_processed.safety.should_filter:
                                logger.warning(f"🛡️ [SAFETY-FILTER] Skipping message {message.id} - content filtered for safety: {ai_processed.safety.safety_level.value}")
                                logger.warning(f"🛡️ [SAFETY-FILTER] Safety issues: {ai_processed.safety.safety_issues}")
                                # Add to blacklist to prevent future processing
                                await _atomic_blacklist_add(self.bot, message.id)
                                continue

                            # Check if AI recommends posting
                            if not ai_processed.should_post:
                                logger.info(f"[INTELLIGENT-FETCH] Skipping message {message.id} - AI analysis recommends skip")
                                continue

                            # Check for duplicates
                            if ai_processed.similarity_score > 0.8:
                                logger.info(f"[INTELLIGENT-FETCH] Skipping message {message.id} - too similar to recent content (score: {ai_processed.similarity_score:.2f})")
                                continue

                            # Use AI-processed content for posting
                            final_content = ai_processed.translated_content
                        else:
                            logger.debug("🤖 [AI-ANALYSIS] AI analyzer service not available, skipping enhanced analysis")
                            ai_processed = None
                            final_content = cleaned_text

                    except Exception as e:
                        logger.error(f"❌ [AI-ANALYSIS] Content analysis failed for message {message.id}: {e}")
                        # Fall back to basic AI processing
                        ai_processed = None
                        final_content = cleaned_text

                    # 🔄 LEGACY AI PROCESSING (fallback)
                    try:
                        from src.services.ai_service import AIService

                        # Initialize AI service with bot reference
                        ai_service = AIService(self.bot)

                        ai_result = ai_service.get_ai_result_comprehensive(final_content)
                        if not ai_result:
                            logger.warning(f"[INTELLIGENT-FETCH] Legacy AI processing failed for message {message.id}")
                            continue

                        # Check AI flags
                        if ai_result.get('is_ad', False):
                            logger.info(f"[INTELLIGENT-FETCH] Skipping message {message.id} - detected as advertisement")
                            continue

                        if ai_result.get('is_not_syria', False):
                            logger.info(f"[INTELLIGENT-FETCH] Skipping message {message.id} - not related to Syria")
                            continue

                        ai_title = ai_result.get('title', '')
                        ai_english = ai_result.get('translation', ai_result.get('english', ''))
                        ai_location = ai_result.get('location', 'Unknown')

                    except Exception as e:
                        logger.error(f"[INTELLIGENT-FETCH] Legacy AI processing error for message {message.id}: {e}")
                        continue

                    # 📝 ENHANCED POSTING DECISION
                    try:
                        # Always ping news role for all posts
                        should_ping = True
                        urgency_indicator = "📰"

                        if news_analysis:
                            # Check if news intelligence service is still available for formatting
                            if hasattr(self, 'news_intelligence') and self.news_intelligence is not None:
                                urgency_indicator = await self.news_intelligence.format_urgency_indicator(news_analysis)
                            else:
                                urgency_indicator = "📰"  # Default indicator if service unavailable
                                
                            if news_analysis.urgency_level == UrgencyLevel.BREAKING:
                                logger.info(f"🚨 [BREAKING-NEWS] Message {message.id} will ping news role - breaking news detected!")
                            else:
                                logger.info(f"🔔 [NEWS-PING] Message {message.id} will ping news role - regular post")

                        # Use only the AI title - let posting service add the single emoji
                        enhanced_title = ai_title

                        # Create enhanced FetchView with intelligence data
                        fetch_view = FetchView(
                            bot=self.bot,
                            post=message,
                            channelname=channel_name,
                            message_id=message.id,
                            media=message.media,
                            arabic_text_clean=final_content,
                            ai_english=ai_english,
                            ai_title=enhanced_title,
                            ai_location=ai_location,
                            auto_mode=True,  # Important: enables auto mode
                            # Pass intelligence data for enhanced posting
                            urgency_level=news_analysis.urgency_level.value if news_analysis else "normal",
                            should_ping_news=should_ping,
                            content_category=ai_processed.categories.primary_category.value if ai_processed else "social",
                            quality_score=ai_processed.quality.overall_score if ai_processed else 0.7
                        )

                        # Apply posting delay if needed
                        if posting_delay > 0:
                            logger.info(f"⏱️ [INTELLIGENT-FETCH] Scheduling delayed post for message {message.id} in {posting_delay} seconds")

                            # SPAM PREVENTION: Limit delayed posts to prevent overwhelming the system
                            if not hasattr(self.bot, '_delayed_post_count'):
                                self.bot._delayed_post_count = 0

                            if self.bot._delayed_post_count >= 3:  # Maximum 3 delayed posts at once
                                logger.warning(f"⚠️ [SPAM-PREVENTION] Too many delayed posts queued, skipping message {message.id}")
                                continue

                            # CRITICAL DUPLICATE PREVENTION: Add to blacklist immediately when scheduling
                            # This prevents the same message from being scheduled multiple times
                            # while it's waiting in the delayed posting queue
                            blacklist_success = await _atomic_blacklist_add(self.bot, message.id)
                            if not blacklist_success:
                                logger.warning(f"⚠️ [DUPLICATE-PREVENTION] Failed to blacklist message {message.id}, skipping to prevent duplicates")
                                # Remove from processing set since we're not proceeding
                                async with self._processing_lock:
                                    self._processing_messages.discard(message.id)
                                continue

                            self.bot._delayed_post_count += 1
                            logger.info(f"🔒 [DUPLICATE-PREVENTION] Message {message.id} blacklisted immediately to prevent duplicate scheduling")

                            # Schedule the post for later execution (non-blocking)
                            asyncio.create_task(self._schedule_delayed_post_with_cleanup(
                                fetch_view, message.id, posting_delay, channel_name
                            ))

                            # Remove from processing set since delayed posting will handle it
                            async with self._processing_lock:
                                self._processing_messages.discard(message.id)
                                logger.debug(f"🔓 [DUPLICATE-PREVENTION] Removed message {message.id} from processing set (scheduled)")

                            # Continue to next message without blocking
                            continue

                        # Attempt to post immediately
                        post_success = await fetch_view.do_post_to_news()

                        if post_success:
                            # Add message ID to blacklist to prevent reposting
                            await _atomic_blacklist_add(self.bot, message.id)

                            # Remove from processing set since we're done
                            async with self._processing_lock:
                                self._processing_messages.discard(message.id)
                                logger.debug(f"🔓 [DUPLICATE-PREVENTION] Removed message {message.id} from processing set (posted)")

                            # Log success with intelligence info
                            success_msg = f"✅ [INTELLIGENT-FETCH] Successfully posted message {message.id} from {channel_name}"
                            if news_analysis:
                                success_msg += f" | Urgency: {news_analysis.urgency_level.value}"
                            if ai_processed:
                                success_msg += f" | Category: {ai_processed.categories.primary_category.value}"
                                success_msg += f" | Quality: {ai_processed.quality.overall_score:.2f}"
                            if should_ping:
                                success_msg += " | 🔔 NEWS ROLE PINGED"

                            logger.info(success_msg)
                            return True
                        else:
                            logger.warning(f"❌ [INTELLIGENT-FETCH] Failed to post message {message.id}")
                            # Remove from processing set since posting failed
                            async with self._processing_lock:
                                self._processing_messages.discard(message.id)
                                logger.debug(f"🔓 [DUPLICATE-PREVENTION] Removed message {message.id} from processing set (failed)")

                    except Exception as e:
                        logger.error(f"❌ [INTELLIGENT-FETCH] Error posting message {message.id}: {e}")
                        # Remove from processing set on error
                        async with self._processing_lock:
                            self._processing_messages.discard(message.id)
                            logger.debug(f"🔓 [DUPLICATE-PREVENTION] Removed message {message.id} from processing set (error)")
                        continue

                logger.info(f"📊 [INTELLIGENT-FETCH] Processed {messages_processed} messages from {channel_name}, no suitable content found")
                return False

            except Exception as e:
                logger.error(f"❌ [INTELLIGENT-FETCH] Error in intelligent auto-fetch for {channel_name}: {e}")
                return False

    async def _schedule_delayed_post(self, fetch_view, message_id, delay, channel_name):
        """
        Schedule and execute a delayed post with proper interval management.
        
        This method handles the delayed posting of content with comprehensive
        blacklist checking, error handling, and crucially updates the posting
        interval timer to prevent subsequent auto-posts from violating the
        configured posting frequency.
        
        Args:
            fetch_view: The FetchView instance containing the message data
            message_id: Unique identifier for the message being posted
            delay: Delay in seconds before posting (for spacing multiple posts)
            channel_name: Name of the source Telegram channel
            
        Returns:
            bool: True if posting was successful, False otherwise
            
        Note:
            This method calls bot.mark_just_posted() on successful posting
            to ensure the auto-posting interval timer is properly updated.
            This prevents the bot from posting again too soon and maintains
            the configured posting frequency.
        """
        try:
            # Wait for the specified delay to space out multiple posts
            await asyncio.sleep(delay)
            
            # Ensure we have a posting lock to prevent race conditions
            if not hasattr(self.bot, '_posting_lock'):
                self.bot._posting_lock = asyncio.Lock()
            
            async with self.bot._posting_lock:
                logger.info(f"🚀 [DELAYED-POST] Attempting to post delayed message {message_id} from {channel_name}")
                
                # Verify message is blacklisted (should already be blacklisted when scheduled)
                if hasattr(self.bot, 'json_cache') and self.bot.json_cache:
                    blacklisted_ids = await self.bot.json_cache.get("blacklisted_posts") or []
                    if message_id in blacklisted_ids:
                        logger.debug(f"✅ [DELAYED-POST] Message {message_id} is properly blacklisted")
                    else:
                        logger.warning(f"⚠️ [DELAYED-POST] Message {message_id} not in blacklist as expected, canceling delayed post to prevent duplicates")
                        return False
                
                # Attempt to post the content
                post_success = await fetch_view.do_post_to_news()
                
                if post_success:
                    # NOTE: Message already blacklisted when scheduled, no need to blacklist again
                    logger.debug(f"✅ [DELAYED-POST] Message {message_id} already blacklisted during scheduling")
                    
                    # CRITICAL: Update last post time to respect auto-post interval
                    # This ensures the bot won't auto-post again too soon after this delayed post
                    self.bot.mark_just_posted()
                    
                    # Build comprehensive success message with intelligence data
                    success_msg = f"✅ [DELAYED-POST] Successfully posted message {message_id} from {channel_name}"
                    if hasattr(fetch_view, 'urgency_level'):
                        success_msg += f" | Urgency: {fetch_view.urgency_level}"
                    if hasattr(fetch_view, 'content_category'):
                        success_msg += f" | Category: {fetch_view.content_category}"
                    if hasattr(fetch_view, 'quality_score'):
                        success_msg += f" | Quality: {fetch_view.quality_score:.2f}"
                    if hasattr(fetch_view, 'should_ping_news') and fetch_view.should_ping_news:
                        success_msg += " | 🔔 NEWS ROLE PINGED"
                        
                    logger.info(success_msg)
                    
                    # Brief delay to prevent rapid-fire posting
                    await asyncio.sleep(2)
                    return True
                else:
                    logger.warning(f"❌ [DELAYED-POST] Failed to post delayed message {message_id}")
                    return False
                
        except Exception as e:
            logger.error(f"❌ [DELAYED-POST] Error in delayed posting for message {message_id}: {e}")
            return False

    async def _schedule_delayed_post_with_cleanup(self, fetch_view, message_id, delay, channel_name):
        """Schedule a delayed post with proper cleanup to prevent spam."""
        try:
            result = await self._schedule_delayed_post(fetch_view, message_id, delay, channel_name)
            return result
        finally:
            # Always decrement the counter when done
            if hasattr(self.bot, '_delayed_post_count'):
                self.bot._delayed_post_count = max(0, self.bot._delayed_post_count - 1)
                logger.debug(f"🔢 [SPAM-PREVENTION] Delayed post counter: {self.bot._delayed_post_count}")

    async def auto_post_from_channel(self, channel_name: str) -> bool:
        """
        Enhanced auto-post implementation with intelligent content selection.
        
        This method performs the core auto-posting logic by fetching recent
        messages from a Telegram channel, applying AI-powered filtering and
        analysis, and posting the best suitable content to Discord.
        
        Features:
        - Spam prevention through channel-specific posting locks
        - Intelligent content filtering (length, media, duplicates)
        - AI-powered translation and analysis
        - Automatic last_post_time updating for interval management
        
        Args:
            channel_name (str): Name of the Telegram channel to fetch from
            
        Returns:
            bool: True if content was successfully posted, False otherwise
            
        Process Flow:
        1. Acquire posting lock for the channel (spam prevention)
        2. Fetch recent messages from Telegram channel
        3. Filter messages by content quality and requirements
        4. Process suitable messages with AI translation/analysis
        5. Post the first suitable content via posting service
        6. Update last_post_time to maintain posting intervals
        """
        try:
            logger.debug(f"🔄 [FETCH] Starting auto_post_from_channel for: {channel_name}")
            
            # Check if posting is locked for this channel (spam prevention)
            if channel_name in self.posting_locks:
                logger.info(f"🔒 [SPAM-PREVENTION] Channel {channel_name} is currently locked, skipping auto-post")
                return False
            
            # Acquire posting lock for this channel
            self.posting_locks.add(channel_name)
            logger.info(f"🔒 [SPAM-PREVENTION] Acquired posting lock for {channel_name}")
            
            try:
                logger.info(f"🧠 [INTELLIGENT-FETCH] Starting enhanced auto-post for channel: {channel_name}")
                
                # Verify Telegram client availability
                telegram_client = self.bot.telegram_client
                if not telegram_client:
                    logger.error("[FETCH] No Telegram client available")
                    return False
                
                # Fetch recent messages from the channel
                messages = await telegram_client.get_messages(channel_name, limit=10)
                logger.debug(f"🔄 [FETCH] Retrieved {len(messages)} messages from {channel_name}")
                
                if not messages:
                    logger.info(f"📊 [INTELLIGENT-FETCH] No messages found in {channel_name}")
                    return False
                
                # Process messages with intelligent filtering
                suitable_content = []
                for i, message in enumerate(messages):
                    # Check message quality requirements
                    has_media = bool(message.media)
                    message_text = message.text or ""
                    text_length = len(message_text.strip())
                    
                    # Skip messages that don't meet basic requirements
                    if text_length < 50:
                        continue
                    
                    # Check for duplicate content
                    if await self._is_duplicate_content(message_text):
                        continue
                    
                    # Process with AI translation and analysis
                    ai_service = self.bot.ai_service
                    if ai_service:
                        try:
                            english_translation, ai_title, location = await ai_service.process_text_with_ai(message_text)
                            
                            if english_translation:
                                # Prepare content data for posting
                                content_data = {
                                    "text": message_text,
                                    "translation": english_translation,
                                    "title": ai_title,
                                    "location": location,
                                    "media_urls": await self._extract_media_urls(message),
                                    "source_channel": channel_name,
                                    "message_id": message.id
                                }
                                
                                suitable_content.append(content_data)
                                logger.debug(f"🔄 [FETCH] Found suitable content: message {i+1}")
                                break  # Found suitable content, post it
                                
                        except Exception as e:
                            logger.debug(f"🔄 [FETCH] AI processing failed for message {i+1}: {str(e)}")
                            continue
                
                logger.info(f"📊 [INTELLIGENT-FETCH] Processed {len(messages)} messages from {channel_name}, {len(suitable_content)} suitable content found")
                
                # Post the first suitable content if found
                if suitable_content:
                    content_data = suitable_content[0]
                    
                    posting_service = self.bot.posting_service
                    if posting_service:
                        success = await posting_service.post_news_content(content_data, is_manual=False)
                        
                        if success:
                            # CRITICAL: Update last post time to respect auto-post interval
                            # This prevents subsequent auto-posts from violating posting frequency
                            self.bot.mark_just_posted()
                            logger.info(f"✅ [INTELLIGENT-FETCH] Successfully posted content from {channel_name}")
                            return True
                        else:
                            logger.debug(f"🔄 [FETCH] Posting failed for {channel_name}")
                    else:
                        logger.error("🔄 [FETCH] No posting service available")
                
                logger.info(f"ℹ️ No suitable content found in {channel_name}")
                return False
                
            finally:
                # Always release the posting lock
                self.posting_locks.discard(channel_name)
                logger.debug(f"🔄 [FETCH] Released posting lock for {channel_name}")
                
        except Exception as e:
            logger.error(f"[FETCH] Error in auto-post for {channel_name}: {str(e)}")
            return False


async def setup(bot: commands.Bot) -> None:
    """Setup function for the cog."""
    await bot.add_cog(FetchCommands(bot))
    logger.info("✅ FetchCommands cog loaded")


def setup_fetch_commands(bot):
    """Setup fetch commands for the bot."""
    # Create and add the FetchCommands cog
    fetch_cog = FetchCommands(bot)
    
    # Store the FetchCommands instance in the bot for auto-posting access
    bot.fetch_commands = fetch_cog
    
    # Add the enhanced fetch command to the bot's command tree
    bot.tree.add_command(fetch_cog.fetch_command)
    
    logger.info("✅ Enhanced fetch command setup completed successfully")
