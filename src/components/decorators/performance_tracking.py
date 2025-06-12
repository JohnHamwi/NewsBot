"""
Performance Tracking Decorator for Syrian NewsBot

Decorator for automatically tracking command execution performance.

Author: حَـــــنَّـــــا
Version: 3.0.0
"""

from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable, Optional

import discord

from src.utils.base_logger import base_logger as logger


def track_performance(command_name: Optional[str] = None):
    """
    Decorator to track command performance metrics.

    Args:
        command_name: Optional custom command name for tracking
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Extract interaction and bot from arguments
            interaction = None
            bot = None

            # Find interaction in arguments
            for arg in args:
                if isinstance(arg, discord.Interaction):
                    interaction = arg
                    bot = interaction.client
                    break

            # Get command name
            cmd_name = command_name or getattr(func, "__name__", "unknown_command")
            if interaction and interaction.command:
                cmd_name = interaction.command.name

            # Start timing
            start_time = time.time()
            success = True
            error = None

            try:
                # Execute the command
                result = await func(*args, **kwargs)
                return result

            except Exception as e:
                success = False
                error = e
                raise

            finally:
                # Calculate duration
                duration = time.time() - start_time

                # Record metrics if bot has performance metrics
                if (
                    bot
                    and hasattr(bot, "performance_metrics")
                    and bot.performance_metrics
                ):
                    user_id = interaction.user.id if interaction else None
                    bot.performance_metrics.record_command_execution(
                        command_name=cmd_name,
                        duration=duration,
                        success=success,
                        user_id=user_id,
                    )

                # Log performance
                status = "✅" if success else "❌"
                logger.debug(
                    f"{status} Command '{cmd_name}' executed in {duration:.3f}s "
                    f"(success={success})"
                )

                # Log error if occurred
                if error:
                    logger.error(f"Command '{cmd_name}' failed: {error}")

        return wrapper

    return decorator


def track_auto_post_performance(func: Callable) -> Callable:
    """
    Decorator specifically for tracking auto-posting performance.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        # Find bot instance in arguments
        bot = None
        for arg in args:
            if hasattr(arg, "performance_metrics"):
                bot = arg
                break

        start_time = time.time()
        success = True
        posts_count = 0

        try:
            result = await func(*args, **kwargs)

            # Try to extract posts count from result
            if isinstance(result, dict) and "posts_count" in result:
                posts_count = result["posts_count"]
            elif isinstance(result, bool) and result:
                posts_count = 1

            return result

        except Exception as e:
            success = False
            raise

        finally:
            duration = time.time() - start_time

            # Record auto-post metrics
            if bot and hasattr(bot, "performance_metrics") and bot.performance_metrics:
                bot.performance_metrics.record_auto_post(
                    success=success, duration=duration, posts_count=posts_count
                )

            # Log performance
            status = "✅" if success else "❌"
            logger.info(
                f"{status} Auto-post completed in {duration:.3f}s "
                f"(success={success}, posts={posts_count})"
            )

    return wrapper
