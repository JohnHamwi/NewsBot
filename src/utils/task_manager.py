# =============================================================================
# NewsBot Task Manager Module
# =============================================================================
# This module provides utilities for managing background tasks with error 
# recovery, automatic restarts, graceful shutdown, rate limiting, and 
# comprehensive error logging and reporting capabilities.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import asyncio
import functools
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, TypeVar

# =============================================================================
# Local Application Imports
# =============================================================================
from src.utils.base_logger import base_logger as logger
from src.utils.error_handler import error_handler

# =============================================================================
# Type Variables
# =============================================================================
T = TypeVar("T")


# =============================================================================
# Task Manager Main Class
# =============================================================================
class TaskManager:
    """
    Manages background tasks with error recovery and graceful shutdown.
    
    Features:
    - Automatic task recovery with exponential backoff
    - Rate limiting for restart attempts
    - Graceful shutdown handling
    - Comprehensive error logging and reporting
    - Task status monitoring and metrics
    """

    def __init__(self, bot=None):
        """
        Initialize the task manager.

        Args:
            bot: Optional bot instance for error reporting
        """
        self.bot = bot
        self.tasks: Dict[str, asyncio.Task] = {}
        self.restart_counts: Dict[str, int] = {}
        self.last_restart_time: Dict[str, datetime] = {}
        self.max_restarts = 5  # Maximum restarts in restart_window
        self.restart_window = 60  # seconds
        self.backoff_factor = 1.5  # Exponential backoff factor
        self.shutdown_requested = False

    # =========================================================================
    # Task Management Methods
    # =========================================================================
    async def start_task(
        self,
        name: str,
        coro: Callable[..., Coroutine],
        *args,
        restart_on_failure: bool = True,
        **kwargs,
    ) -> None:
        """
        Start a background task with error recovery.

        Args:
            name: Unique name for the task
            coro: Coroutine function to run as a task
            *args: Arguments to pass to the coroutine
            restart_on_failure: Whether to restart the task on failure
            **kwargs: Keyword arguments to pass to the coroutine
        """
        if name in self.tasks and not self.tasks[name].done():
            logger.warning(f"Task {name} is already running")
            return

        self.restart_counts.setdefault(name, 0)
        self.last_restart_time.setdefault(
            name, datetime.now() - timedelta(seconds=self.restart_window)
        )

        wrapped_coro = self._create_wrapped_task(
            name, coro, restart_on_failure, *args, **kwargs
        )
        task = asyncio.create_task(wrapped_coro)
        self.tasks[name] = task
        logger.info(f"Started task: {name}")

    def _create_wrapped_task(
        self,
        name: str,
        coro: Callable[..., Coroutine],
        restart_on_failure: bool,
        *args,
        **kwargs,
    ) -> Coroutine:
        """
        Create a wrapped task with error handling and recovery.

        Args:
            name: Task name
            coro: Coroutine function
            restart_on_failure: Whether to restart on failure
            *args: Arguments for the coroutine
            **kwargs: Keyword arguments for the coroutine

        Returns:
            Wrapped coroutine
        """

        async def wrapped_task():
            while not self.shutdown_requested:
                try:
                    logger.debug(f"Task {name} starting")
                    await coro(*args, **kwargs)
                    logger.info(f"Task {name} completed normally")
                    break  # Task completed normally, no need to restart
                except asyncio.CancelledError:
                    logger.info(f"Task {name} was cancelled")
                    break
                except Exception as e:
                    # Log the error
                    logger.error(f"Error in task {name}: {str(e)}")

                    # Report the error if bot is available
                    if self.bot:
                        try:
                            await error_handler.send_error_embed(
                                error_title=f"Task Error: {name}",
                                error=e,
                                context=f"Background task failure in {name}",
                                bot=self.bot,
                            )
                        except Exception as report_error:
                            logger.error(
                                f"Failed to report task error: {str(report_error)}"
                            )

                    # Handle task restart
                    if not restart_on_failure:
                        logger.warning(f"Task {name} failed and will not be restarted")
                        break

                    # Check if we should restart (rate limiting)
                    now = datetime.now()
                    time_since_last_restart = (
                        now - self.last_restart_time[name]
                    ).total_seconds()

                    # Reset restart count if outside window
                    if time_since_last_restart > self.restart_window:
                        self.restart_counts[name] = 0

                    # Increment restart count
                    self.restart_counts[name] += 1
                    self.last_restart_time[name] = now

                    # Check if we've hit the restart limit
                    if self.restart_counts[name] > self.max_restarts:
                        logger.error(
                            f"Task {name} failed too many times ({self.restart_counts[name]}), not restarting"
                        )
                        if self.bot:
                            try:
                                await error_handler.send_error_embed(
                                    error_title=f"Task Terminated: {name}",
                                    error=Exception(
                                        f"Task failed after {self.restart_counts[name]} restart attempts"
                                    ),
                                    context=f"Task {name} has been terminated due to too many failures",
                                    bot=self.bot,
                                )
                            except Exception:
                                pass
                        break

                    # Calculate backoff time
                    backoff_time = min(
                        60, 2 * (self.backoff_factor ** (self.restart_counts[name] - 1))
                    )
                    logger.warning(
                        f"Task {name} will restart in {backoff_time:.1f} seconds "
                        f"(attempt {self.restart_counts[name]})"
                    )

                    # Wait before restarting
                    try:
                        await asyncio.sleep(backoff_time)
                    except asyncio.CancelledError:
                        logger.info(f"Task {name} restart was cancelled during backoff")
                        break

        return wrapped_task()

    # =========================================================================
    # Task Query and Control Methods
    # =========================================================================
    def get_task(self, name: str) -> Optional[asyncio.Task]:
        """
        Get a task by name.

        Args:
            name: Task name

        Returns:
            Task object or None if not found
        """
        return self.tasks.get(name)

    def is_running(self, name: str) -> bool:
        """
        Check if a task is running.

        Args:
            name: Task name

        Returns:
            True if the task is running, False otherwise
        """
        task = self.get_task(name)
        return task is not None and not task.done()

    async def stop_task(self, name: str, timeout: float = 5.0) -> bool:
        """
        Stop a running task gracefully.

        Args:
            name: Task name
            timeout: Maximum time to wait for the task to stop

        Returns:
            True if the task was stopped, False otherwise
        """
        task = self.get_task(name)
        if not task or task.done():
            return True

        task.cancel()
        try:
            # Use gather with return_exceptions=True to handle CancelledError gracefully
            await asyncio.gather(task, return_exceptions=True)
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Task {name} did not stop within {timeout} seconds")
            return False
        except Exception as e:
            logger.error(f"Error stopping task {name}: {str(e)}")
            return False

    async def stop_all_tasks(self, timeout: float = 5.0) -> None:
        """
        Stop all running tasks gracefully.

        Args:
            timeout: Maximum time to wait for each task to stop
        """
        self.shutdown_requested = True
        for name in list(self.tasks.keys()):
            await self.stop_task(name, timeout)

    async def start_all_tasks(self) -> None:
        """
        Start all configured background tasks.
        
        This method is called during bot startup to initialize background tasks.
        Currently, no default tasks are configured, but this method can be extended
        to start specific tasks as needed.
        """
        logger.info("🚀 Starting background tasks...")
        
        # For now, we don't have any default tasks to start
        # This method exists to satisfy the interface expected by the bot
        # Future tasks can be added here as needed
        
        logger.info("✅ Background tasks startup completed")

    def get_task_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics about all tasks.

        Returns:
            Dictionary of task statistics
        """
        stats = {}
        for name, task in self.tasks.items():
            stats[name] = {
                "running": not task.done(),
                "restart_count": self.restart_counts.get(name, 0),
                "last_restart": self.last_restart_time.get(name),
                "cancelled": task.cancelled() if hasattr(task, "cancelled") else None,
                "exception": (
                    task.exception()
                    if hasattr(task, "exception")
                    and task.done()
                    and not task.cancelled()
                    else None
                ),
            }
        return stats


# Create a global instance for easy access
task_manager = TaskManager()


def set_bot_instance(bot):
    """
    Set the bot instance for the global task manager.

    Args:
        bot: Bot instance
    """
    global task_manager
    task_manager.bot = bot
