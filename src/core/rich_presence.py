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
# Maintenance Presence Functions
# =============================================================================
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
        
    if seconds_until_next_post > 0:
        hours = seconds_until_next_post // 3600
        minutes = (seconds_until_next_post % 3600) // 60

        if hours > 0:
            activity_name = f"⏰ Next post in {hours}h {minutes}m"
        else:
            activity_name = f"⏰ Next post in {minutes}m"
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
        
    activity = discord.Activity(
        type=discord.ActivityType.watching, name="📰 Just posted news!"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)
