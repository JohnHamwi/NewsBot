# =============================================================================
# NewsBot Error Handler Module
# =============================================================================
# This module provides comprehensive error handling functionality for the 
# NewsBot, including error tracking, rate limiting, metrics collection,
# and Discord error reporting with enhanced context information.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import asyncio
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, ParamSpec, TypeVar, Union

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import discord

# =============================================================================
# Local Application Imports
# =============================================================================
from src.components.embeds.base_embed import ErrorEmbed
from src.utils.base_logger import base_logger as logger
from src.utils.structured_logger import structured_logger

# =============================================================================
# Type Variables
# =============================================================================
# Type variables for generic function handling
P = ParamSpec("P")
T = TypeVar("T")


# =============================================================================
# Error Context Data Class
# =============================================================================
@dataclass
class ErrorContext:
    """Stores context about an error occurrence."""

    error: Exception
    location: str
    timestamp: datetime = datetime.now()
    extra_info: Dict[str, Any] = None

    @property
    def error_type(self) -> str:
        """Get the error type name."""
        return type(self.error).__name__

    def to_dict(self) -> Dict[str, Any]:
        """Convert error context to dictionary."""
        return {
            "error_type": self.error_type,
            "error_message": str(self.error),
            "location": self.location,
            "timestamp": self.timestamp.isoformat(),
            "extra_info": self.extra_info or {},
        }


# =============================================================================
# Rate Limiting Class
# =============================================================================
class RateLimit:
    """Rate limiting for error reporting."""

    def __init__(self, max_calls: int, time_window: int):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls: List[datetime] = []

    def is_rate_limited(self) -> bool:
        """Check if rate limited."""
        now = datetime.now()
        self.calls = [
            t for t in self.calls if now - t < timedelta(seconds=self.time_window)
        ]
        if len(self.calls) >= self.max_calls:
            return True
        self.calls.append(now)
        return False


# =============================================================================
# Admin Ping Rate Limiter Class
# =============================================================================
class AdminPingRateLimiter:
    """Rate limiter specifically for admin pings to prevent spam."""
    
    def __init__(self, cooldown_hours: int = 3):
        """Initialize with cooldown period in hours."""
        self.cooldown_hours = cooldown_hours
        self.last_ping_time: Optional[datetime] = None
        self.pending_errors: List[ErrorContext] = []
        self.max_pending_errors = 50  # Keep last 50 errors for summary
    
    def add_error(self, error_ctx: ErrorContext) -> None:
        """Add an error to the pending list."""
        self.pending_errors.append(error_ctx)
        # Keep only recent errors
        if len(self.pending_errors) > self.max_pending_errors:
            self.pending_errors.pop(0)
    
    def should_ping_admin(self) -> bool:
        """Check if enough time has passed to ping admin again."""
        if self.last_ping_time is None:
            return True
        
        now = datetime.now()
        cooldown_delta = timedelta(hours=self.cooldown_hours)
        return (now - self.last_ping_time) >= cooldown_delta
    
    def mark_ping_sent(self) -> None:
        """Mark that a ping has been sent and reset the timer."""
        self.last_ping_time = datetime.now()
        logger.info(f"🔔 Admin ping sent - next ping available in {self.cooldown_hours} hours")
    
    def get_time_until_next_ping(self) -> Optional[timedelta]:
        """Get time remaining until next ping is allowed."""
        if self.last_ping_time is None:
            return None
        
        now = datetime.now()
        cooldown_delta = timedelta(hours=self.cooldown_hours)
        next_ping_time = self.last_ping_time + cooldown_delta
        
        if now >= next_ping_time:
            return None
        
        return next_ping_time - now
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of pending errors for the ping message."""
        if not self.pending_errors:
            return {
                "total_count": 0,
                "error_types": {},
                "recent_errors": [],
                "time_range": None
            }
        
        # Count errors by type
        error_types = {}
        for error in self.pending_errors:
            error_type = error.error_type
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        # Get time range
        earliest = min(error.timestamp for error in self.pending_errors)
        latest = max(error.timestamp for error in self.pending_errors)
        
        # Get most recent errors (up to 5)
        recent_errors = sorted(self.pending_errors, key=lambda x: x.timestamp, reverse=True)[:5]
        
        return {
            "total_count": len(self.pending_errors),
            "error_types": error_types,
            "recent_errors": [error.to_dict() for error in recent_errors],
            "time_range": {
                "earliest": earliest.isoformat(),
                "latest": latest.isoformat()
            }
        }
    
    def clear_pending_errors(self) -> None:
        """Clear the pending errors list after sending summary."""
        self.pending_errors.clear()


# =============================================================================
# Error Handler Main Class
# =============================================================================
class ErrorHandler:
    """Handles error reporting and tracking."""

    def __init__(self):
        """Initialize error handler."""
        self.error_history: List[ErrorContext] = []
        self.rate_limits: Dict[str, RateLimit] = {}
        self.total_operations = 0
        self.total_errors = 0
        self.max_history = 100
        # Admin ping rate limiter - ping once every 3 hours
        self.admin_ping_limiter = AdminPingRateLimiter(cooldown_hours=3)

    # =========================================================================
    # Error History Management
    # =========================================================================
    def _add_to_history(self, error_ctx: ErrorContext) -> None:
        """Add error to history, maintaining max size."""
        self.error_history.append(error_ctx)
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)
        self.total_errors += 1
        
        # Add to admin ping limiter for potential admin notification
        self.admin_ping_limiter.add_error(error_ctx)

    # =========================================================================
    # Error Metrics and Reporting
    # =========================================================================
    def get_error_metrics(self) -> Dict[str, Any]:
        """Get error metrics for the last 24 hours."""
        now = datetime.now()
        day_ago = now - timedelta(days=1)

        # Filter recent errors
        recent_errors = [e for e in self.error_history if e.timestamp > day_ago]

        # Count by type
        error_counts = {}
        for err in recent_errors:
            err_type = err.error_type
            error_counts[err_type] = error_counts.get(err_type, 0) + 1

        # Calculate success rate (assuming 1000 operations per day)
        total_errors = len(recent_errors)
        success_rate = max(0, 100 - (total_errors / 10))

        # Get most recent error
        recent_error = recent_errors[-1].to_dict() if recent_errors else None

        return {
            "error_counts": error_counts,
            "error_total": total_errors,
            "success_rate": round(success_rate, 1),
            "recent_error": recent_error,
            "details": self._format_error_details(error_counts),
        }

    def _format_error_details(self, error_counts: Dict[str, int]) -> str:
        """Format error counts into a readable string."""
        if not error_counts:
            return "No errors in the last 24 hours"

        details = []
        for err_type, count in error_counts.items():
            details.append(f"{err_type}: {count}")
        return "\n".join(details)

    # =========================================================================
    # Discord Error Reporting
    # =========================================================================
    async def send_error_embed(
        self,
        error_title: str,
        error: Exception,
        context: Optional[str] = None,
        user: Optional[discord.User] = None,
        channel: Optional[discord.TextChannel] = None,
        bot: Optional[discord.Client] = None,
    ) -> None:
        """
        Send a detailed error embed with enhanced information to Discord.
        Includes rate-limited admin pinging to prevent spam.
        """
        # Check rate limit for error reporting
        rate_limit_key = f"error_{error_title}"
        if rate_limit_key not in self.rate_limits:
            self.rate_limits[rate_limit_key] = RateLimit(max_calls=5, time_window=60)

        if self.rate_limits[rate_limit_key].is_rate_limited():
            logger.warning(f"Rate limited error report: {error_title}")
            return

        # Create error context
        error_ctx = ErrorContext(
            error=error,
            location=error_title,
            extra_info={
                "user_id": user.id if user else None,
                "channel_id": channel.id if channel else None,
                "context": context,
            },
        )

        self._add_to_history(error_ctx)

        # Create enhanced error embed
        embed = discord.Embed(
            title=f"❌ {error_title}",
            description="An error has occurred",
            color=0xFF0000,  # Red
            timestamp=datetime.now(),
        )

        # Add error details
        embed.add_field(
            name="Error Type", value=f"`{error_ctx.error_type}`", inline=True
        )

        embed.add_field(name="Error Message", value=f"```{str(error)}```", inline=False)

        if context:
            embed.add_field(name="Context", value=f"```{context}```", inline=False)

        if user:
            embed.add_field(
                name="User", value=f"{user.mention} (`{user.id}`)", inline=True
            )

        if channel:
            embed.add_field(
                name="Channel", value=f"{channel.mention} (`{channel.id}`)", inline=True
            )

        # Send to error channel if bot is provided
        if bot and hasattr(bot, "errors_channel") and bot.errors_channel:
            try:
                # Check if we should ping admin
                should_ping = self.admin_ping_limiter.should_ping_admin()
                admin_user_id = None
                
                # Get admin user ID from bot config
                if hasattr(bot, 'config'):
                    admin_user_id = getattr(bot.config, 'admin_user_id', None) or getattr(bot.config.bot, 'admin_user_id', None)
                elif hasattr(bot, 'unified_config'):
                    admin_user_id = bot.unified_config.get('bot.admin_user_id')
                
                if should_ping and admin_user_id:
                    # Send error with admin ping and summary
                    error_summary = self.admin_ping_limiter.get_error_summary()
                    
                    # Create summary embed
                    summary_embed = discord.Embed(
                        title="🔔 Error Alert Summary",
                        description=f"Multiple errors detected - ping cooldown: {self.admin_ping_limiter.cooldown_hours} hours",
                        color=0xFF6B00,  # Orange
                        timestamp=datetime.now(),
                    )
                    
                    summary_embed.add_field(
                        name="📊 Error Statistics",
                        value=f"**Total Errors:** {error_summary['total_count']}\n" +
                              "\n".join([f"**{err_type}:** {count}" for err_type, count in error_summary['error_types'].items()]),
                        inline=False
                    )
                    
                    if error_summary['time_range']:
                        earliest = datetime.fromisoformat(error_summary['time_range']['earliest'])
                        latest = datetime.fromisoformat(error_summary['time_range']['latest'])
                        summary_embed.add_field(
                            name="⏰ Time Range",
                            value=f"**From:** {earliest.strftime('%H:%M:%S')}\n**To:** {latest.strftime('%H:%M:%S')}",
                            inline=True
                        )
                    
                    next_ping_time = self.admin_ping_limiter.get_time_until_next_ping()
                    if next_ping_time:
                        hours = int(next_ping_time.total_seconds() // 3600)
                        minutes = int((next_ping_time.total_seconds() % 3600) // 60)
                        summary_embed.add_field(
                            name="⏳ Next Ping Available",
                            value=f"In {hours}h {minutes}m",
                            inline=True
                        )
                    
                    # Send ping message with summary
                    ping_message = f"<@{admin_user_id}> 🚨 **Error Alert**"
                    await bot.errors_channel.send(content=ping_message, embed=summary_embed)
                    await bot.errors_channel.send(embed=embed)
                    
                    # Mark ping as sent and clear pending errors
                    self.admin_ping_limiter.mark_ping_sent()
                    self.admin_ping_limiter.clear_pending_errors()
                    
                    logger.info(f"🔔 Admin pinged for errors - next ping in {self.admin_ping_limiter.cooldown_hours} hours")
                else:
                    # Send error without ping
                    await bot.errors_channel.send(embed=embed)
                    
                    if admin_user_id:
                        # Log when next ping will be available
                        time_until_next = self.admin_ping_limiter.get_time_until_next_ping()
                        if time_until_next:
                            hours = int(time_until_next.total_seconds() // 3600)
                            minutes = int((time_until_next.total_seconds() % 3600) // 60)
                            logger.debug(f"⏰ Admin ping on cooldown - next ping in {hours}h {minutes}m")
                
            except Exception as e:
                logger.error(f"Failed to send error embed: {str(e)}")


# =============================================================================
# Global Error Handler Instance
# =============================================================================
# Global instance
error_handler = ErrorHandler()

# Placeholder for send_error_embed so it can be patched at runtime


async def send_error_embed(
    error_title: str,
    error: Exception,
    context: Optional[str] = None,
    user: Optional[Any] = None,
    channel: Optional[Any] = None,
    bot: Optional[Any] = None,
) -> None:
    """
    Send a detailed error embed to the specified Discord channel and log the error.
    Args:
        error_title (str): The title of the error
        error (Exception): The exception object
        context (Optional[str]): Additional context for the error
        user (Optional[Any]): The user who triggered the error (if any)
        channel (Optional[Any]): The Discord channel to send the embed to
        bot (Optional[Any]): The bot instance (for logging)
    """
    pass


def get_error_metrics() -> dict:
    """
    Get error metrics for the last 24 hours, including error counts and recent errors.
    Returns:
        dict: Error metrics including error_counts, success_rate, and recent_errors.
    """
    return error_handler.get_error_metrics()
