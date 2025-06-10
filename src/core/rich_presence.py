"""
Rich Presence Module for NewsBot

This module handles Discord rich presence status functions.
"""
import datetime
from discord.ext import commands
import discord

async def set_maintenance_presence(bot: commands.Bot) -> None:
    """
    Set the bot's rich presence to show it's in maintenance mode.

    Args:
        bot (commands.Bot): The bot instance to update presence for
    """
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="⚠️ Maintenance Mode"
        )
    )

async def set_automatic_presence(bot: commands.Bot, seconds_until_next_post: int = 0) -> None:
    """
    Set the bot's rich presence to show it's monitoring Telegram and when next post is due.

    Args:
        bot (commands.Bot): The bot instance to update presence for
        seconds_until_next_post (int): Seconds until the next scheduled post
    """
    if seconds_until_next_post <= 0 or bot.auto_post_interval <= 0:
        # If auto-posting is disabled or we can't calculate next post
        status = "📱 Monitoring Telegram..."
    else:
        # Calculate hours and minutes until next post
        hours = seconds_until_next_post // 3600
        minutes = (seconds_until_next_post % 3600) // 60
        
        if hours > 0:
            status = f"Next post in {hours}h {minutes}m"
        else:
            status = f"Next post in {minutes}m"
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=status
        )
    )

async def set_posted_presence(bot: commands.Bot) -> None:
    """
    Set the bot's rich presence to indicate a post was just made.

    Args:
        bot (commands.Bot): The bot instance to update presence for
    """
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="📰 Just posted news!"
        )
    )
