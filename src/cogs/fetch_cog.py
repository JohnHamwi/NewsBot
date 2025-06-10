"""
Telegram Fetch Module for NewsBot

This module handles fetching and posting of content from Telegram channels,
including translation, formatting, and media handling.
"""

import asyncio
import os
import re
from typing import List

import discord
from discord.ext import commands
from discord import app_commands

from src.utils import error_handler
from src.utils.config import Config
from .fetch_view import FetchView
from src.components.decorators.admin_required import admin_required
from src.utils.base_logger import base_logger as logger
from src.core.config_manager import config

GUILD_ID = Config.GUILD_ID or 0
ADMIN_USER_ID = Config.ADMIN_USER_ID or 0


def remove_emojis(text):
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text)


def remove_links(text):
    """Remove URLs from text."""
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    return url_pattern.sub('', text)


def remove_source_phrases(text):
    """Remove common source attribution phrases."""
    source_patterns = [
        r'المصدر:.*$',
        r'المصدر :.*$',
        r'المصدر\s*:.*$',
        r'مصدر:.*$',
        r'مصدر :.*$',
        r'مصدر\s*:.*$',
        r'من:.*$',
        r'من :.*$',
        r'من\s*:.*$',
        r'عن:.*$',
        r'عن :.*$',
        r'عن\s*:.*$',
        r'نقلاً عن:.*$',
        r'نقلاً عن :.*$',
        r'نقلاً عن\s*:.*$',
        r'نقلا عن:.*$',
        r'نقلا عن :.*$',
        r'نقلا عن\s*:.*$',
    ]
    for pattern in source_patterns:
        text = re.sub(pattern, '', text, flags=re.MULTILINE)
    return text.strip()


class FetchCog(commands.Cog):
    """
    Cog for fetching and posting content from Telegram channels.
    Includes translation, formatting, and media handling.
    """

    def __init__(self, bot):
        """Initialize the fetch cog with the bot instance."""
        self.bot = bot
        self.logger = logger
        self.logger.info("FetchCog initialized")

    @app_commands.command(
        name="fetch",
        description="Fetch posts from a Telegram channel"
    )
    @app_commands.describe(
        channel="The name of the Telegram channel to fetch from",
        number="Number of posts to fetch (1-5)"
    )
    async def fetch(self, interaction: discord.Interaction, channel: str, number: int = 1):
        """
        Slash command to fetch the latest posts from a Telegram channel (admin only).
        """
        self.logger.info(f"[FETCH][CMD][fetch] START channel={channel} number={number}")
        from .ai_utils import call_chatgpt_for_news
        try:
            # Change direct ID check to use the RBAC system when available
            is_authorized = False
            if hasattr(self.bot, 'rbac') and self.bot.rbac:
                # Check for the fetch permission using RBAC
                is_authorized = self.bot.rbac.has_permission(interaction.user.id, "fetch")
            else:
                # Fallback to direct ID check
                is_authorized = interaction.user.id == ADMIN_USER_ID

            if not is_authorized:
                await interaction.response.send_message("You are not authorized to use this command.", ephemeral=False)
                self.logger.warning(f"[UNAUTHORIZED] User {interaction.user.id} attempted to use /fetch")
                return

            # Parameter validation
            if number < 1 or number > 5:
                await interaction.response.send_message("Please specify a number between 1 and 5.", ephemeral=False)
                return

            # Send initial response
            await interaction.response.send_message(f"Fetching {number} posts from {channel}...", ephemeral=False)

            # Get Telegram client from bot
            if not hasattr(self.bot, 'telegram_client') or not self.bot.telegram_client:
                await interaction.followup.send("Telegram client is not connected. Please check the logs.", ephemeral=False)
                self.logger.error("Telegram client not connected for fetch command")
                return

            client = self.bot.telegram_client

            # Try to get the channel entity
            try:
                entity = await client.get_entity(channel)
                channel_display = entity.title if hasattr(entity, 'title') else channel
                await interaction.followup.send(f"Found channel: {channel_display}. Fetching posts...", ephemeral=False)
            except Exception as e:
                await interaction.followup.send(f"Error: Could not find channel '{channel}'. {str(e)}", ephemeral=False)
                self.logger.error(f"[ERROR] Failed to find channel '{channel}': {e}")
                return

            # Get the posts
            try:
                posts = await client.get_posts(channel, limit=number)
                if not posts:
                    await interaction.followup.send(f"No posts found in {channel_display}.", ephemeral=False)
                    return

                await interaction.followup.send(f"Found {len(posts)} posts. Processing...", ephemeral=False)

                # Get blacklisted posts to avoid duplicates
                blacklist = await self.bot.json_cache.get("blacklisted_posts") or []

                # Process each post
                for i, post in enumerate(posts):
                    if post.id in blacklist:
                        await interaction.followup.send(f"Post {i + 1} (ID {post.id}) was already processed before. Skipping.", ephemeral=False)
                        continue

                    self.logger.info(f"Processing post {i + 1}/{len(posts)} from {channel_display} (ID: {post.id})")

                    # Check if the post has text
                    if not post.message:
                        await interaction.followup.send(f"Post {i + 1} has no text content. Skipping.", ephemeral=False)
                        continue

                    # Remove emojis from text
                    cleaned_text = remove_emojis(post.message)

                    # Get news channel from config
                    news_channel_id = config.get("channels.news")
                    if not news_channel_id:
                        await interaction.followup.send("News channel not configured. Check config.yaml", ephemeral=False)
                        return

                    news_channel = self.bot.get_channel(int(news_channel_id))
                    if not news_channel:
                        await interaction.followup.send(f"Could not find news channel with ID {news_channel_id}", ephemeral=False)
                        return

                    # Create view for the post
                    view = FetchView(
                        self.bot,
                        post,
                        cleaned_text,
                        interaction.user,
                        news_channel
                    )

                    # Send the view to the user
                    await interaction.followup.send(
                        "Post preview (click 'Post to News' to publish):",
                        view=view,
                        ephemeral=False
                    )

                    # Add to blacklist (if not in debug mode)
                    debug_mode = getattr(self.bot, 'debug_mode', False)
                    if not debug_mode:
                        blacklist.append(post.id)
                        await self.bot.json_cache.set("blacklisted_posts", blacklist)

            except Exception as e:
                await interaction.followup.send(f"Failed to fetch posts: {e}")
                self.logger.error(
                    f"[ERROR] Failed to fetch posts: {e} | user={interaction.user.id} "
                    f"channel={interaction.channel.id}"
                )
                return

        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=False)
            self.logger.error(f"[ERROR] Fetch command failed: {e}")
            await error_handler.send_error_embed(
                "Fetch Error",
                e,
                context=f"fetch command for {channel}",
                user=interaction.user,
                bot=self.bot
            )

    async def fetch_and_post_auto(self, channel_name: str) -> bool:
        """
        Fetch and post from a channel in automatic mode.
        This is called by the auto_post_task.

        Args:
            channel_name: The Telegram channel name to fetch from

        Returns:
            bool: True if a post was made, False otherwise
        """
        logger.info(f"Auto fetch started for channel: {channel_name}")

        try:
            # Add timeout for channel fetch
            async def fetch_with_timeout():
                return await self.bot.telegram_client.get_entity(channel_name)

            try:
                logger.debug(f"Fetching channel entity for {channel_name}")
                channel = await asyncio.wait_for(fetch_with_timeout(), timeout=10.0)
                logger.debug(f"Successfully got channel entity: {getattr(channel, 'title', channel_name)}")
            except asyncio.TimeoutError:
                logger.error(f"Timeout fetching channel entity for {channel_name}")
                return False
            except Exception as e:
                logger.error(f"Error fetching channel entity for {channel_name}: {str(e)}")

                # Check for the specific Telegram authentication error
                error_str = str(e).lower()
                if "key is not registered" in error_str or "resolve" in error_str:
                    logger.critical(
                        "Telegram authentication issue detected. Need to run fix_telegram_auth.py")

                    # Try to notify an admin if possible
                    try:
                        admin_id = int(os.getenv("ADMIN_USER_ID", "0"))
                        if admin_id > 0:
                            admin_user = await self.bot.fetch_user(admin_id)
                            if admin_user:
                                await admin_user.send(
                                    "⚠️ **Telegram Authentication Error**\n\n"
                                    "The bot is unable to access Telegram channels due to an authentication issue.\n"
                                    "Please run the `fix_telegram_auth.py` script to fix this problem."
                                )
                    except Exception as dm_error:
                        logger.error(f"Failed to notify admin: {str(dm_error)}")

                return False

            # Add timeout for message fetch
            async def get_messages_with_timeout():
                return await self.bot.telegram_client.get_messages(channel, limit=5)

            try:
                logger.debug(f"Fetching messages from {channel_name}")
                messages = await asyncio.wait_for(get_messages_with_timeout(), timeout=10.0)
                logger.debug(f"Got {len(messages)} messages from {channel_name}")
            except asyncio.TimeoutError:
                logger.error(f"Timeout fetching messages from {channel_name}")
                return False
            except Exception as e:
                logger.error(f"Error fetching messages from {channel_name}: {str(e)}")
                return False

            # No messages found
            if not messages:
                logger.warning(f"No messages found in channel {channel_name}")
                return False

            # Find the most recent message with text and media
            found_post = False

            # Only process messages from newest to oldest
            messages.sort(key=lambda msg: msg.id, reverse=True)

            # Only process the most recent valid message
            for message in messages:
                # Skip messages with no text
                if not message.message or len(message.message.strip()) == 0:
                    logger.debug(f"Message {message.id} has no text, skipping")
                    continue
                # Debug log for media type
                if hasattr(message, 'media'):
                    logger.debug(
                        f"Message {message.id} media type: {type(message.media)}, "
                        f"media: {repr(message.media)}"
                    )
                else:
                    logger.debug(f"Message {message.id} has no media attribute")
                # Check for any type of media (more lenient)
                has_media = False
                if hasattr(message, 'media') and message.media is not None:
                    media = message.media
                    # Telegram photo
                    if hasattr(media, 'photo') and media.photo:
                        has_media = True
                    # Telegram video/document
                    elif hasattr(media, 'document') and media.document:
                        has_media = True
                    # Any other media type
                    else:
                        has_media = True
                        
                # ONLY allow posts with media - skip text-only posts completely
                if not has_media:
                    logger.debug(f"Message {message.id} has no media, skipping (media required)")
                    continue
                    
                logger.debug(f"Message {message.id} has media, processing")

                # Check if the message has been posted before
                if await self._check_already_posted(message.id, channel_name):
                    logger.debug(f"Message {message.id} already posted, skipping")
                    continue

                # For posts with media, require minimum text
                min_length = 50
                if len(message.message.strip()) < min_length:
                    logger.debug(
                        f"Message {message.id} too short ({len(message.message.strip())} chars, min: {min_length}), skipping")
                    continue

                # Log what media is being attached
                logger.info(f"Processing message {message.id} with media (type: {type(message.media)})")

                # Found a valid post - create a FetchView and post it
                try:
                    # Add timeout for AI translation
                    logger.debug(f"Creating FetchView for message {message.id}")
                    view = FetchView(self.bot, message, channel_name, auto_mode=True)

                    # Process message with timeout
                    async def process_message_with_timeout():
                        nonlocal view
                        await view.process_message()
                        return True

                    try:
                        logger.debug(f"Processing message with timeout")
                        await asyncio.wait_for(process_message_with_timeout(), timeout=20.0)
                    except asyncio.TimeoutError:
                        logger.error(f"Timeout processing message {message.id}")
                        continue

                    # Allow posts without translation (more lenient)
                    if not view.ai_english:
                        logger.debug(f"No translation available for message {message.id}, but proceeding anyway")
                        # Set a fallback translation
                        view.ai_english = "Translation not available"

                    # Post to news channel - but ONLY if media download succeeds
                    logger.debug(f"Posting message {message.id} to news channel")
                    success = await view.do_post_to_news()

                    if success:
                        logger.info(
                            f"Successfully posted message {message.id} from {channel_name}"
                        )
                        # Mark as posted
                        await self._mark_as_posted(message.id, channel_name)
                        found_post = True
                        # Exit after posting the first valid message
                        break
                    else:
                        logger.warning(f"Failed to post message {message.id} from {channel_name} (likely media download failed)")
                        # Skip to next message only if posting failed
                        continue

                except Exception as e:
                    logger.error(f"Error processing message {message.id}: {str(e)}")
                    # Skip to next message
                    continue

            return found_post

        except Exception as e:
            logger.error(f"Error in fetch_and_post_auto for {channel_name}: {str(e)}")
            return False

    async def _check_already_posted(self, message_id: int, channel_name: str) -> bool:
        """Check if a message has already been posted."""
        blacklist = await self.bot.json_cache.get("blacklisted_posts") or []
        return message_id in blacklist

    async def _mark_as_posted(self, message_id: int, channel_name: str) -> None:
        """Mark a message as posted."""
        blacklist = await self.bot.json_cache.get("blacklisted_posts") or []
        if message_id not in blacklist:
            blacklist.append(message_id)
            await self.bot.json_cache.set("blacklisted_posts", blacklist)


async def setup(bot):
    """Add the FetchCog to the bot."""
    await bot.add_cog(FetchCog(bot))
