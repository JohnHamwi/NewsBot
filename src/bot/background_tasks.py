"""
Background Tasks Module

This module contains all background tasks for the NewsBot including
monitoring, auto-posting, rich presence updates, and notifications.
"""

import asyncio
import datetime
import os
import platform
from typing import TYPE_CHECKING

import discord
import psutil
from discord.ext import commands

from src.core.config_manager import config
from src.utils import error_handler
from src.utils.base_logger import base_logger as logger
from src.utils.task_manager import task_manager
from src.utils.timezone_utils import now_eastern

if TYPE_CHECKING:
    from .newsbot import NewsBot

# Configuration constants
__version__ = config.get("bot.version") or "2.0.0"


async def send_startup_notification(bot: "NewsBot") -> None:
    """Send startup notification to log channel."""
    try:
        # Gather system information
        process = psutil.Process()
        sys_info = (
            f"🐍 Python: {platform.python_version()}\n"
            f"🎮 Discord.py: {discord.__version__}\n"
            f"🖥️ Platform: {platform.system()} {platform.release()}\n"
            f"📊 Process ID: {process.pid}\n"
            f"🧵 Thread Count: {process.num_threads()}\n"
            f"📈 Memory Usage: {process.memory_info().rss / 1024 / 1024:.1f}MB"
        )

        conn_info = (
            f"⚡ Latency: {bot.latency * 1000:.0f}ms\n"
            f"🕒 Startup Time: {bot.startup_time.strftime('%Y-%m-%d | %I:%M:%S %p')}\n"
            f"🏰 Guild ID: {bot.get_guild(config.get('bot.guild_id')).id}"
        )

        # Create embed based on Telegram status
        if bot.telegram_auth_failed:
            embed = discord.Embed(
                title="🤖 NewsBot Online - Telegram Auth Failed",
                description="```✨ Bot connected but Telegram authentication failed!```",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(
                name="📱 Telegram Status",
                value="```❌ Authentication Failed```",
                inline=False,
            )
            embed.add_field(
                name="🔧 How to Fix",
                value="Run `python fix_telegram_auth.py` and restart the bot",
                inline=False,
            )
        else:
            embed = discord.Embed(
                title="🤖 NewsBot Online - All Systems Ready",
                description="```✨ Bot connected and ready to serve!```",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(
                name="📱 Telegram Status", value="```✅ Connected```", inline=False
            )

        embed.add_field(name="💻 System Info", value=f"```{sys_info}```", inline=False)
        embed.add_field(
            name="🌐 Connection Info", value=f"```{conn_info}```", inline=False
        )
        embed.set_footer(text=f"🤖 Bot ID: {bot.user.id} • Version: {__version__}")

        # Check if log channel is available before sending
        if not bot.log_channel:
            logger.warning("⚠️ Log channel not available for startup notification")
            return
            
        await bot.log_channel.send(embed=embed)
        logger.debug("✅ Sent startup notification")

    except Exception as e:
        logger.error(f"❌ Failed to send startup notification: {str(e)}")


async def send_shutdown_notification(bot: "NewsBot") -> None:
    """Send shutdown notification to log channel."""
    try:
        if not bot.log_channel:
            logger.warning("⚠️ Log channel not available for shutdown notification")
            return

        # Calculate uptime (handle timezone-aware vs naive datetime)
        current_time = discord.utils.utcnow()
        if bot.startup_time.tzinfo is None:
            # If startup_time is naive, make current_time naive too
            import datetime as dt

            current_time = dt.datetime.utcnow()
        uptime = current_time - bot.startup_time
        uptime_str = str(uptime).split(".")[0]  # Remove microseconds

        # Gather final system stats
        process = psutil.Process()
        final_stats = (
            f"⏱️ Uptime: {uptime_str}\n"
            f"📊 Final Memory: {process.memory_info().rss / 1024 / 1024:.1f}MB\n"
            f"🧵 Final Threads: {process.num_threads()}\n"
            f"🕒 Shutdown Time: {discord.utils.utcnow().strftime('%Y-%m-%d | %I:%M:%S %p')}"
        )

        embed = discord.Embed(
            title="🤖 NewsBot Shutdown",
            description="```🔄 Bot is shutting down gracefully...```",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name="📊 Final Statistics", value=f"```{final_stats}```", inline=False
        )
        embed.set_footer(text=f"🤖 Bot ID: {bot.user.id} • Version: {__version__}")

        await bot.log_channel.send(embed=embed)
        logger.debug("✅ Sent shutdown notification")

    except Exception as e:
        logger.error(f"❌ Failed to send shutdown notification: {str(e)}")


async def start_monitoring_tasks(bot: "NewsBot") -> None:
    """Start monitoring and background tasks."""
    try:
        logger.debug("🔄 Starting monitoring tasks")

        # Start resource monitor
        asyncio.create_task(resource_monitor(bot))

        # Create wrapper functions to avoid lambda issues
        async def auto_post_wrapper():
            await auto_post_task(bot)

        async def log_tail_wrapper():
            await log_tail_task(bot)

        async def rich_presence_wrapper():
            await rich_presence_task(bot)

        async def update_metrics_wrapper():
            await update_metrics(bot)

        # Start other background tasks via task manager
        await task_manager.start_task("auto_post", auto_post_wrapper)
        await task_manager.start_task("log_tail", log_tail_wrapper)
        await task_manager.start_task("rich_presence", rich_presence_wrapper)
        await task_manager.start_task("update_metrics", update_metrics_wrapper)

        logger.debug("✅ All monitoring tasks started")

    except Exception as e:
        logger.error(f"❌ Failed to start monitoring tasks: {str(e)}", exc_info=True)
        raise


async def resource_monitor(bot: "NewsBot") -> None:
    """Monitor CPU and RAM usage and alert if thresholds are exceeded."""
    admin_user_id = int(os.getenv("ADMIN_USER_ID", "0"))
    cpu_threshold = 80.0
    ram_threshold = 70.0
    process = psutil.Process()

    logger.debug("🛡️ Starting resource monitor")

    try:
        while True:
            try:
                cpu = psutil.cpu_percent()
                ram = process.memory_percent()

                if cpu > cpu_threshold or ram > ram_threshold:
                    await send_resource_alert(bot, cpu, ram, process.pid, admin_user_id)

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"❌ Error in resource monitor: {str(e)}")
                await asyncio.sleep(60)  # Continue monitoring even if there's an error

    except asyncio.CancelledError:
        logger.debug("🛡️ Resource monitor stopped")
        raise


async def send_resource_alert(
    bot: "NewsBot", cpu: float, ram: float, pid: int, admin_user_id: int
) -> None:
    """Send resource usage alert to admin."""
    try:
        if not bot.errors_channel:
            return

        embed = discord.Embed(
            title="⚠️ High Resource Usage Alert",
            description=f"The bot is experiencing high resource usage.",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(
            name="📊 Current Usage",
            value=f"**CPU:** {cpu:.1f}%\n**RAM:** {ram:.1f}%\n**PID:** {pid}",
            inline=False,
        )

        embed.add_field(
            name="🔧 Recommended Actions",
            value="• Check for memory leaks\n• Monitor background tasks\n• Consider restarting if usage remains high",
            inline=False,
        )

        await bot.errors_channel.send(f"<@{admin_user_id}>", embed=embed)
        logger.warning(f"⚠️ Sent resource alert - CPU: {cpu:.1f}%, RAM: {ram:.1f}%")

    except Exception as e:
        logger.error(f"❌ Failed to send resource alert: {str(e)}")


async def update_metrics(bot: "NewsBot") -> None:
    """Update bot metrics periodically."""
    logger.debug("📊 Starting metrics update task")

    try:
        while True:
            try:
                if hasattr(bot, "metrics") and bot.metrics:
                    # Update basic metrics
                    bot.metrics.update_metric("bot_latency", bot.latency * 1000)
                    bot.metrics.update_metric("guild_count", len(bot.guilds))
                    bot.metrics.update_metric(
                        "user_count",
                        sum(guild.member_count or 0 for guild in bot.guilds),
                    )

                    # Update system metrics
                    process = psutil.Process()
                    bot.metrics.update_metric("cpu_usage", psutil.cpu_percent())
                    bot.metrics.update_metric("memory_usage", process.memory_percent())
                    bot.metrics.update_metric("thread_count", process.num_threads())

                await asyncio.sleep(60)  # Update every minute

            except Exception as e:
                logger.error(f"❌ Error updating metrics: {str(e)}")
                await asyncio.sleep(60)

    except asyncio.CancelledError:
        logger.debug("📊 Metrics update task stopped")
        raise


async def log_tail_task(bot: "NewsBot"):
    """Background task to periodically send log summaries."""
    logger.debug("📝 Starting log tail task")

    try:
        while True:
            try:
                await asyncio.sleep(3600)  # Wait 1 hour

                # Read recent log entries
                log_file_path = "logs/newsbot.log"
                if os.path.exists(log_file_path):
                    try:
                        with open(log_file_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                            recent_lines = lines[-50:] if len(lines) > 50 else lines

                            if recent_lines:
                                # Count log levels
                                error_count = sum(
                                    1 for line in recent_lines if "ERROR" in line
                                )
                                warning_count = sum(
                                    1 for line in recent_lines if "WARNING" in line
                                )
                                info_count = sum(
                                    1 for line in recent_lines if "INFO" in line
                                )

                                if (
                                    error_count > 0 or warning_count > 5
                                ):  # Only send if there are issues
                                    embed = discord.Embed(
                                        title="📝 Hourly Log Summary",
                                        description=f"Recent activity from the last hour",
                                        color=(
                                            discord.Color.red()
                                            if error_count > 0
                                            else discord.Color.orange()
                                        ),
                                        timestamp=discord.utils.utcnow(),
                                    )

                                    embed.add_field(
                                        name="📊 Log Counts",
                                        value=f"❌ Errors: {error_count}\n⚠️ Warnings: {warning_count}\nℹ️ Info: {info_count}",
                                        inline=False,
                                    )

                                    if error_count > 0:
                                        # Show recent errors
                                        error_lines = [
                                            line.strip()
                                            for line in recent_lines
                                            if "ERROR" in line
                                        ][-3:]
                                        error_text = "\n".join(error_lines)
                                        if len(error_text) > 1000:
                                            error_text = error_text[-1000:]

                                        embed.add_field(
                                            name="🔴 Recent Errors",
                                            value=f"```\n{error_text}\n```",
                                            inline=False,
                                        )

                                    # Check if log channel is available before sending
                                    if bot.log_channel:
                                        await bot.log_channel.send(embed=embed)
                                    else:
                                        logger.debug("📝 Log channel not available for log summary")

                    except Exception as e:
                        logger.error(f"❌ Error reading log file: {str(e)}")

            except Exception as e:
                logger.error(f"❌ Error in log tail task: {str(e)}")
                await asyncio.sleep(3600)

    except asyncio.CancelledError:
        logger.debug("📝 Log tail task stopped")
        raise


async def rich_presence_task(bot: "NewsBot"):
    """Background task to update bot's rich presence."""
    logger.info("📱 Starting rich presence task")

    try:
        while True:
            try:
                # Wait for bot to be ready before updating presence
                if not bot.is_ready():
                    logger.debug("📱 Bot not ready yet, waiting...")
                    await asyncio.sleep(5)
                    continue
                
                if bot.rich_presence_mode == "automatic":
                    # Calculate time until next post
                    if bot.auto_post_interval > 0 and bot.last_post_time:
                        next_post = bot.last_post_time + datetime.timedelta(
                            seconds=bot.auto_post_interval
                        )
                        time_until = next_post - now_eastern()

                        logger.debug(
                            f"🕐 Rich presence: interval={bot.auto_post_interval}s, "
                            f"last_post={bot.last_post_time}, "
                            f"time_until={time_until.total_seconds():.0f}s"
                        )

                        if time_until.total_seconds() > 0:
                            hours = int(time_until.total_seconds() // 3600)
                            minutes = int((time_until.total_seconds() % 3600) // 60)

                            if bot._just_posted:
                                activity_name = "📰 Just posted news!"
                                bot._just_posted = False
                                logger.debug("📱 Rich presence: Just posted news!")
                            elif hours > 0:
                                activity_name = f"⏰ Next post in {hours}h {minutes}m"
                                logger.debug(
                                    f"📱 Rich presence: Next post in {hours}h {minutes}m"
                                )
                            else:
                                activity_name = f"⏰ Next post in {minutes}m"
                                logger.debug(
                                    f"📱 Rich presence: Next post in {minutes}m"
                                )
                        else:
                            activity_name = "📰 Ready to post news"
                            logger.debug("📱 Rich presence: Ready to post news")
                    else:
                        activity_name = "📰 Monitoring news channels"
                        logger.debug(
                            f"📱 Rich presence: Monitoring (interval={bot.auto_post_interval}, "
                            f"last_post={bot.last_post_time})"
                        )

                    activity = discord.Activity(
                        type=discord.ActivityType.watching, name=activity_name
                    )
                    await bot.change_presence(
                        status=discord.Status.online, activity=activity
                    )

                elif bot.rich_presence_mode == "maintenance":
                    activity = discord.Activity(
                        type=discord.ActivityType.playing, name="🔧 Under Maintenance"
                    )
                    await bot.change_presence(
                        status=discord.Status.idle, activity=activity
                    )
                    logger.debug("📱 Rich presence: Maintenance mode")

                await asyncio.sleep(30)  # Update every 30 seconds

            except Exception as e:
                logger.error(f"❌ Error updating rich presence: {str(e)}")
                await asyncio.sleep(30)

    except asyncio.CancelledError:
        logger.info("📱 Rich presence task stopped")
        raise


async def auto_post_task(bot: "NewsBot"):
    """Background task for automatic news posting."""
    logger.info("🔄 Starting auto-post task")

    try:
        while True:
            try:
                # Check if auto-posting is enabled
                if bot.auto_post_interval <= 0:
                    logger.debug("⏸️ Auto-posting disabled, checking again in 5 minutes")
                    await asyncio.sleep(300)  # Check every 5 minutes
                    continue

                logger.debug(
                    f"🔍 Auto-post check: interval={bot.auto_post_interval}s, force_flag={bot.force_auto_post}"
                )

                # Check if it's time to post
                if bot.last_post_time:
                    time_since_last = (
                        now_eastern() - bot.last_post_time
                    ).total_seconds()
                    logger.debug(
                        f"⏱️ Time since last post: {time_since_last:.0f}s (need {bot.auto_post_interval}s)"
                    )

                    if (
                        time_since_last < bot.auto_post_interval
                        and not bot.force_auto_post
                    ):
                        remaining = bot.auto_post_interval - time_since_last
                        logger.debug(f"⏳ Not time yet, waiting {remaining:.0f}s more")
                        await asyncio.sleep(60)  # Check every minute
                        continue
                else:
                    logger.debug("📅 No previous post time recorded")

                # Reset force flag if it was set
                if bot.force_auto_post:
                    logger.info(
                        "🚀 Force auto-post flag detected - posting immediately"
                    )
                    bot.force_auto_post = False

                # Trigger auto-post
                logger.info("🔄 Triggering automatic news post")

                # Check if the fetch_and_post_auto method is available on the bot
                if not hasattr(bot, "fetch_and_post_auto"):
                    logger.error("❌ No fetch_and_post_auto method found on bot!")
                    await asyncio.sleep(300)  # Wait 5 minutes before retrying
                    continue

                logger.debug("✅ Found fetch_and_post_auto method on bot")

                # Try posting from active channels
                post_successful = False
                try:
                    # Get active channels from cache
                    active_channels = await bot.json_cache.list_telegram_channels(
                        "activated"
                    )

                    if not active_channels:
                        logger.warning(
                            "⚠️ No active channels configured for auto-posting"
                        )
                        logger.info(
                            "💡 Use /news add_channel <channel_name> to add channels for auto-posting"
                        )
                        await asyncio.sleep(300)  # Wait 5 minutes before retrying
                        continue

                    logger.info(f"📡 Active channels: {active_channels}")

                    # Try posting from each channel until successful
                    for channel in active_channels:
                        logger.info(f"🔄 Attempting to fetch from channel: {channel}")

                        try:
                            result = await bot.fetch_and_post_auto(channel)
                            if result:
                                logger.info(f"✅ Successfully posted from {channel}")
                                post_successful = True
                                break
                            else:
                                logger.debug(f"❌ No post made from {channel}")
                        except Exception as e:
                            logger.error(f"❌ Failed to fetch from {channel}: {str(e)}")
                            continue

                    if post_successful:
                        bot.last_post_time = now_eastern()
                        bot.mark_just_posted()
                        logger.info("✅ Auto-post completed successfully")
                        await bot.save_auto_post_config()
                        
                        # Sleep for the full interval after successful post
                        logger.info(f"😴 Sleeping for {bot.auto_post_interval}s until next auto-post")
                        await asyncio.sleep(bot.auto_post_interval)
                        continue
                    else:
                        logger.warning("⚠️ No successful posts from any active channel")

                except Exception as e:
                    logger.error(f"❌ Auto-post failed: {str(e)}")
                    import traceback

                    logger.error(f"📋 Traceback: {traceback.format_exc()}")

                logger.debug("😴 Auto-post cycle complete, sleeping for 1 minute")
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"❌ Error in auto-post task: {str(e)}")
                import traceback

                logger.error(f"📋 Traceback: {traceback.format_exc()}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying

    except asyncio.CancelledError:
        logger.info("🔄 Auto-post task stopped")
        raise
