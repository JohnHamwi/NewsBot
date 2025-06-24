# =============================================================================
# NewsBot Rich Presence Module
# =============================================================================
# This module handles Discord bot rich presence (status) updates including
# maintenance mode, automatic monitoring status, and post notifications
# with dynamic countdown timers and activity indicators.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import datetime

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import discord


# =============================================================================
# Post Status Tracking
# =============================================================================
async def mark_content_posted(bot: discord.Client) -> None:
    """
    Mark that content was just posted and should show posted status.
    
    Args:
        bot (discord.Client): The bot instance
    """
    bot._last_posted_time = datetime.datetime.now(datetime.timezone.utc)
    bot._show_posted_status = True


def should_show_posted_status(bot: discord.Client) -> bool:
    """
    Check if we should show the posted status (within 10 minutes of posting).
    
    Args:
        bot (discord.Client): The bot instance
        
    Returns:
        bool: True if we should show posted status
    """
    if not hasattr(bot, '_last_posted_time') or not hasattr(bot, '_show_posted_status'):
        return False
        
    if not bot._show_posted_status:
        return False
        
    now = datetime.datetime.now(datetime.timezone.utc)
    time_since_post = (now - bot._last_posted_time).total_seconds()
    
    # Show posted status for 10 minutes (600 seconds)
    if time_since_post > 600:
        bot._show_posted_status = False
        return False
        
    return True


def get_posted_status_time_remaining(bot: discord.Client) -> int:
    """
    Get the remaining time in seconds to show posted status.
    
    Args:
        bot (discord.Client): The bot instance
        
    Returns:
        int: Seconds remaining, or 0 if not showing posted status
    """
    if not should_show_posted_status(bot):
        return 0
        
    now = datetime.datetime.now(datetime.timezone.utc)
    time_since_post = (now - bot._last_posted_time).total_seconds()
    
    return max(0, 600 - int(time_since_post))


# =============================================================================
# Maintenance Presence Functions
# =============================================================================
async def set_startup_presence(bot: discord.Client) -> None:
    """
    Set the bot's presence to show startup status.

    Args:
        bot (discord.Client): The bot instance to update presence for
    """
    # Wait for bot to be ready before updating presence
    if not bot.is_ready():
        return
        
    activity = discord.Activity(
        type=discord.ActivityType.playing, name="🚀 Starting up..."
    )
    await bot.change_presence(status=discord.Status.idle, activity=activity)


async def set_maintenance_presence(bot: discord.Client) -> None:
    """
    Set the bot's presence to maintenance mode.

    Args:
        bot (discord.Client): The bot instance to update presence for
    """
    # Wait for bot to be ready before updating presence
    if not bot.is_ready():
        return
        
    activity = discord.Activity(
        type=discord.ActivityType.playing, name="🔧 Under Maintenance"
    )
    await bot.change_presence(status=discord.Status.idle, activity=activity)


# =============================================================================
# Automatic Monitoring Presence Functions
# =============================================================================
async def set_automatic_presence(
    bot: discord.Client, seconds_until_next_post: int = 0
) -> None:
    """
    Set the bot's presence to show automatic monitoring status.

    Args:
        bot (discord.Client): The bot instance to update presence for
        seconds_until_next_post (int): Seconds until the next scheduled post
    """
    # Wait for bot to be ready before updating presence
    if not bot.is_ready():
        return
        
    # Check if we should show posted status first
    if should_show_posted_status(bot):
        remaining_time = get_posted_status_time_remaining(bot)
        minutes_remaining = remaining_time // 60
        if minutes_remaining > 0:
            activity_name = f"✅ Posted! ({minutes_remaining}m)"
        else:
            activity_name = "✅ Posted!"
    elif seconds_until_next_post > 0:
        hours = seconds_until_next_post // 3600
        minutes = (seconds_until_next_post % 3600) // 60

        if hours > 0:
            activity_name = f"⏰ Next post in {hours}h {minutes}m"
        else:
            activity_name = f"⏰ Next post in {minutes}m"
    else:
        # Check if we have a last post time to determine if we're overdue
        if hasattr(bot, 'last_post_time') and bot.last_post_time:
            activity_name = "🚀 Ready to post!"
        else:
            activity_name = "📰 Monitoring news channels"

    activity = discord.Activity(type=discord.ActivityType.watching, name=activity_name)
    await bot.change_presence(status=discord.Status.online, activity=activity)


# =============================================================================
# Post Notification Presence Functions
# =============================================================================
async def set_posted_presence(bot: discord.Client) -> None:
    """
    Set the bot's presence to show that news was just posted.

    Args:
        bot (discord.Client): The bot instance to update presence for
    """
    # Wait for bot to be ready before updating presence
    if not bot.is_ready():
        return
        
    # Mark that content was posted
    await mark_content_posted(bot)
        
    activity = discord.Activity(
        type=discord.ActivityType.watching, name="✅ Posted!"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)
