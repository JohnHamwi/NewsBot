# =============================================================================
# NewsBot Background Tasks Module
# =============================================================================
# This module contains all background tasks for the NewsBot including
# monitoring, auto-posting, rich presence updates, resource monitoring,
# and comprehensive notification systems.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import asyncio
import datetime
import os
import platform
from typing import TYPE_CHECKING
import time as time_module  # Import time module with alias to avoid scope issues

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import discord
import psutil
from discord.ext import commands

# =============================================================================
# Local Application Imports
# =============================================================================
from src.core.unified_config import unified_config as config
from src.utils import error_handler
from src.utils.base_logger import base_logger as logger
from src.utils.task_manager import task_manager
from src.utils.timezone_utils import now_eastern

# =============================================================================
# Type Checking Imports
# =============================================================================
if TYPE_CHECKING:
    from .newsbot import NewsBot

# =============================================================================
# Configuration Constants
# =============================================================================
__version__ = config.get("bot.version") or "4.5.0"


# =============================================================================
# Startup and Shutdown Notification Functions
# =============================================================================
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
            
            # Add startup protection info
            if bot.disable_auto_post_on_startup:
                embed.add_field(
                    name="🛡️ Startup Protection",
                    value="```Auto-posting disabled on startup```",
                    inline=False
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


# =============================================================================
# Task Management Functions
# =============================================================================
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


# =============================================================================
# Resource Monitoring Functions
# =============================================================================
async def resource_monitor(bot: "NewsBot") -> None:
    """Monitor CPU and RAM usage and alert if thresholds are exceeded."""
    from src.core.unified_config import unified_config as config
    
    # Load configuration
    alerts_enabled = config.get("monitoring.resource_alerts.enabled", True)
    cpu_threshold = config.get("monitoring.resource_alerts.cpu_threshold", 80.0)
    ram_threshold = config.get("monitoring.resource_alerts.ram_threshold", 70.0)
    check_interval = config.get("monitoring.resource_alerts.check_interval", 60)
    admin_user_id = config.get("bot.admin_user_id", 0)
    
    process = psutil.Process()

    logger.debug(f"🛡️ Starting resource monitor - Alerts enabled: {alerts_enabled}")
    if not alerts_enabled:
        logger.info("🔇 Resource alerts are disabled in configuration")
        return  # Exit early if alerts are disabled

    try:
        while True:
            try:
                cpu = psutil.cpu_percent()
                ram = process.memory_percent()

                if cpu > cpu_threshold or ram > ram_threshold:
                    await send_resource_alert(bot, cpu, ram, process.pid, admin_user_id)

                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"❌ Error in resource monitor: {str(e)}")
                await asyncio.sleep(check_interval)

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
                    # Check if we're in startup grace period
                    should_wait, seconds_to_wait = bot.should_wait_for_startup_delay()
                    if should_wait:
                        delay_minutes = int(seconds_to_wait // 60)
                        delay_seconds = int(seconds_to_wait % 60)
                        if delay_minutes > 0:
                            activity_name = f"🛡️ Grace period: {delay_minutes}m {delay_seconds}s"
                        else:
                            activity_name = f"🛡️ Grace period: {delay_seconds}s"
                        
                        # Actually apply the grace period activity to the bot's presence
                        activity = discord.Activity(type=discord.ActivityType.watching, name=activity_name)
                        await bot.change_presence(status=discord.Status.online, activity=activity)
                        logger.debug(f"📱 Rich presence: Startup grace period - {seconds_to_wait}s remaining")
                    # Use the enhanced rich presence system
                    else:
                        from src.core.rich_presence import set_automatic_presence
                        
                        # Calculate seconds until next post if automation is enabled
                        seconds_until_next_post = 0
                        automation_enabled = bot.automation_config.get('enabled', True) if hasattr(bot, 'automation_config') else True
                        
                        # Check if we're still in startup grace period (same as auto-post task)
                        in_startup_grace, _ = bot.should_wait_for_startup_delay()
                        
                        if (automation_enabled and 
                            bot.auto_post_interval > 0 and 
                            bot.last_post_time and
                            not in_startup_grace):
                            
                            # Calculate next post time
                            next_post = bot.last_post_time + datetime.timedelta(seconds=bot.auto_post_interval)
                            current_time = now_eastern()
                            time_until = next_post - current_time
                            
                            # Only show countdown if next post is in the future
                            if time_until.total_seconds() > 0:
                                seconds_until_next_post = int(time_until.total_seconds())
                                # Only log when the countdown changes by more than 60 seconds using class variable
                                current_time_seconds = time_module.time()
                                if not hasattr(bot.__class__, '_last_rich_presence_log_seconds') or \
                                   abs(seconds_until_next_post - getattr(bot.__class__, '_last_rich_presence_log_seconds', 0)) > 60 or \
                                   (current_time_seconds - getattr(bot.__class__, '_last_rich_presence_log_time', 0)) > 60:
                                    logger.debug(f"📱 Rich presence: Next post in {seconds_until_next_post}s")
                                    bot.__class__._last_rich_presence_log_seconds = seconds_until_next_post
                                    bot.__class__._last_rich_presence_log_time = current_time_seconds
                            else:
                                # Post is overdue, should post soon
                                seconds_until_next_post = 0
                                current_time_seconds = time_module.time()
                                if not hasattr(bot.__class__, '_last_rich_presence_overdue_log') or \
                                   (current_time_seconds - bot.__class__._last_rich_presence_overdue_log) > 60:
                                    logger.debug("📱 Rich presence: Post overdue, should post soon")
                                    bot.__class__._last_rich_presence_overdue_log = current_time_seconds
                        else:
                            # Only log this once every 5 minutes using class variable
                            current_time_seconds = time_module.time()
                            if not hasattr(bot.__class__, '_last_rich_presence_no_automation_log') or \
                               (current_time_seconds - bot.__class__._last_rich_presence_no_automation_log) > 300:
                                logger.debug("📱 Rich presence: No automation or no last post time")
                                bot.__class__._last_rich_presence_no_automation_log = current_time_seconds
                        
                        # Use the enhanced rich presence function
                        await set_automatic_presence(bot, seconds_until_next_post)

                elif bot.rich_presence_mode == "maintenance":
                    activity = discord.Activity(
                        type=discord.ActivityType.playing, name="🔧 Under Maintenance"
                    )
                    await bot.change_presence(
                        status=discord.Status.idle, activity=activity
                    )
                    logger.debug("📱 Rich presence: Maintenance mode")

                # VPS OPTIMIZATION: Update presence every 60 seconds instead of 30 to reduce CPU
                await asyncio.sleep(60)  # Update every minute

            except Exception as e:
                logger.error(f"❌ Error updating rich presence: {str(e)}")
                await asyncio.sleep(30)

    except asyncio.CancelledError:
        logger.info("📱 Rich presence task stopped")
        raise


async def auto_post_task(bot: "NewsBot"):
    """
    Background task for automatic news posting with interval management.
    
    This task continuously monitors the posting schedule and automatically
    posts content from configured Telegram channels at the specified interval.
    
    Key Features:
    - Respects startup grace period to prevent posting during initialization
    - Enforces posting intervals to prevent spam (default: 3 hours)
    - Handles manual verification delays for flagged content
    - Implements channel rotation for fair distribution
    - Comprehensive error handling and recovery
    
    Flow:
    1. Check startup grace period (prevents posting for 5 minutes after restart)
    2. Check manual verification delays (pauses auto-posting after flagged content)
    3. Verify auto-posting is enabled (interval > 0)
    4. Calculate time since last post vs required interval
    5. If time elapsed >= interval, select next channel and attempt posting
    6. If successful, update last_post_time via mark_just_posted()
    
    Args:
        bot (NewsBot): The bot instance containing configuration and state
        
    Note:
        This task runs indefinitely until the bot shuts down. It uses
        asyncio.sleep() for timing control and error recovery.
    """
    logger.info("🔄 Starting auto-post task")

    try:
        while True:
            try:
                # CRITICAL: Check startup grace period first
                # This prevents any posting during the initial startup window
                should_wait, seconds_to_wait = bot.should_wait_for_startup_delay()
                if should_wait:
                    minutes_remaining = seconds_to_wait // 60
                    seconds_remaining = seconds_to_wait % 60
                    logger.info(
                        f"🛡️ STARTUP GRACE PERIOD ACTIVE: {minutes_remaining}m {seconds_remaining}s remaining - AUTO-POSTING DISABLED"
                    )
                    logger.info(
                        f"⏳ Bot will not post any content until {minutes_remaining} minutes after startup"
                    )
                    await asyncio.sleep(30)  # Check every 30 seconds during grace period
                    continue

                # Check for manual verification delay (activated after flagged content)
                if hasattr(bot, '_manual_verification_delay_until') and 'auto_fetch' in bot._manual_verification_delay_until:
                    now_utc = datetime.datetime.now(datetime.timezone.utc)
                    delay_until = bot._manual_verification_delay_until['auto_fetch']
                    
                    if now_utc < delay_until:
                        time_remaining = delay_until - now_utc
                        minutes_remaining = int(time_remaining.total_seconds() // 60)
                        logger.info(
                            f"🛡️ MANUAL VERIFICATION DELAY ACTIVE: {minutes_remaining}m remaining - AUTO-POSTING DISABLED"
                        )
                        logger.info(
                            f"⏳ Waiting for manual verification of flagged content - auto-posting resumes at {delay_until.strftime('%H:%M UTC')}"
                        )
                        await asyncio.sleep(60)  # Check every minute during delay
                        continue
                    else:
                        # Delay period has expired, remove the restriction
                        logger.info("🚀 Manual verification delay expired - auto-posting resumed")
                        del bot._manual_verification_delay_until['auto_fetch']

                # Check if auto-posting is enabled (interval must be > 0)
                if bot.auto_post_interval <= 0:
                    logger.debug("⏸️ Auto-posting disabled, checking again in 5 minutes")
                    await asyncio.sleep(300)  # Check every 5 minutes
                    continue

                logger.debug(
                    f"🔍 Auto-post check: interval={bot.auto_post_interval}s, force_flag={bot.force_auto_post}"
                )

                # Calculate time since last post to determine if interval has elapsed
                if bot.last_post_time:
                    time_since_last = (
                        now_eastern() - bot.last_post_time
                    ).total_seconds()
                    logger.debug(
                        f"⏱️ Time since last post: {time_since_last:.0f}s (need {bot.auto_post_interval}s)"
                    )

                    # Check if we need to wait longer before next post
                    if (
                        time_since_last < bot.auto_post_interval
                        and not bot.force_auto_post
                    ):
                        remaining = bot.auto_post_interval - time_since_last
                        remaining_minutes = remaining / 60
                        logger.debug(f"⏳ Not time yet, waiting {remaining_minutes:.1f} minutes more")
                        await asyncio.sleep(60)  # Check every minute
                        continue
                    else:
                        logger.debug("📅 Ready to post - time interval met")
                elif not bot.last_post_time:
                    logger.debug("📅 No previous post time recorded - ready to post")
                else:
                    logger.debug("📅 Ready to post - all conditions met")

                # Reset force flag if it was set (one-time override)
                if bot.force_auto_post:
                    logger.info(
                        "🚀 Force auto-post flag detected - posting immediately"
                    )
                    bot.force_auto_post = False

                # Begin auto-posting process
                logger.info("🔄 Triggering automatic news post")

                # Verify the fetch_and_post_auto method is available
                if not hasattr(bot, "fetch_and_post_auto"):
                    logger.error("❌ No fetch_and_post_auto method found on bot!")
                    await asyncio.sleep(300)  # Wait 5 minutes before retrying
                    continue

                logger.debug("✅ Found fetch_and_post_auto method on bot")

                # Channel selection and posting attempt
                try:
                    # Get the next channel using rotation system for fairness
                    channel = await bot.json_cache.get_next_channel_for_rotation()

                    if not channel:
                        logger.warning(
                            "⚠️ No active channels configured for auto-posting"
                        )
                        logger.info(
                            "💡 Use /admin channels activate <channel_name> to add channels for auto-posting"
                        )
                        await asyncio.sleep(300)  # Wait 5 minutes before retrying
                        continue

                    logger.info(f"🔄 Using channel rotation - selected channel: {channel}")

                    # Attempt to fetch and post from the selected channel
                    try:
                        result = await bot.fetch_and_post_auto(channel)
                        if result:
                            # IMPORTANT: Update last post time and mark content as posted
                            # This ensures interval timing is properly maintained
                            bot.mark_just_posted()  # Sets last_post_time and saves to cache
                            
                            # Update rich presence to show posting status
                            from src.core.rich_presence import mark_content_posted
                            await mark_content_posted(bot)
                            
                            logger.info(f"✅ Successfully posted from {channel} at {bot.last_post_time}")
                            
                            # Brief pause before next check to allow interval timing
                            await asyncio.sleep(60)
                        else:
                            logger.info(f"ℹ️ No suitable content found in {channel}")
                            # If no content found, wait before trying again
                            await asyncio.sleep(300)  # Wait 5 minutes before next attempt
                    except Exception as e:
                        logger.error(f"❌ Failed to fetch from {channel}: {str(e)}")
                        # If this channel fails, we'll try the next one in the next cycle
                        # This prevents getting stuck on a broken channel

                except Exception as e:
                    logger.error(f"❌ Auto-post failed: {str(e)}")
                    await asyncio.sleep(300)  # Wait 5 minutes on error

            except Exception as e:
                logger.error(f"❌ Auto-post loop error: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    except asyncio.CancelledError:
        logger.info("🔄 Auto-post task stopped")
        raise
