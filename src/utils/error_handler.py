"""
Error Handler Module

This module provides comprehensive error handling functionality for the NewsBot.
"""

import asyncio
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, ParamSpec, TypeVar, Union

import discord

from src.components.embeds.base_embed import ErrorEmbed
from src.utils.base_logger import base_logger as logger
from src.utils.structured_logger import structured_logger

# Type variables for generic function handling
P = ParamSpec("P")
T = TypeVar("T")


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


class ErrorHandler:
    """Handles error reporting and tracking."""

    def __init__(self):
        """Initialize error handler."""
        self.error_history: List[ErrorContext] = []
        self.rate_limits: Dict[str, RateLimit] = {}
        self.total_operations = 0
        self.total_errors = 0
        self.max_history = 100

    def _add_to_history(self, error_ctx: ErrorContext) -> None:
        """Add error to history, maintaining max size."""
        self.error_history.append(error_ctx)
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)
        self.total_errors += 1

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
        if bot and hasattr(bot, "errors_channel"):
            try:
                await bot.errors_channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Failed to send error embed: {str(e)}")


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
