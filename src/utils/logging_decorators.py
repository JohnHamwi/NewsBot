"""
Logging Decorators Module

This module provides decorators for easy integration of structured logging
throughout the codebase.
"""

import asyncio
import functools
import time
from typing import Callable, TypeVar, cast

from src.utils.structured_logger import structured_logger

F = TypeVar("F", bound=Callable)


def log_command(component: str = None) -> Callable[[F], F]:
    """
    Decorator for logging Discord command execution with timing and context.

    Args:
        component: Component name for context

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        is_async = asyncio.iscoroutinefunction(func)

        @functools.wraps(func)
        async def async_wrapper(self, interaction, *args, **kwargs):
            command_name = func.__name__

            # Set up logging context
            start_time = time.time()
            structured_logger.info(
                f"Executing command: {command_name}",
                extras={
                    "args": str(args),
                    "kwargs": str(kwargs),
                    "user": str(interaction.user),
                    "channel": str(getattr(interaction, "channel", None)),
                },
            )

            try:
                result = await func(self, interaction, *args, **kwargs)
                duration = time.time() - start_time
                structured_logger.info(
                    f"Command executed: {command_name} (took {duration:.3f}s)"
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                structured_logger.error(
                    f"Error executing command: {command_name}",
                    extras={
                        "duration": duration,
                        "exception_type": type(e).__name__,
                        "exception": str(e),
                    },
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(self, interaction, *args, **kwargs):
            command_name = func.__name__

            # Set up logging context
            start_time = time.time()
            structured_logger.info(
                f"Executing command: {command_name}",
                extras={
                    "args": str(args),
                    "kwargs": str(kwargs),
                    "user": str(interaction.user),
                    "channel": str(getattr(interaction, "channel", None)),
                },
            )

            try:
                result = func(self, interaction, *args, **kwargs)
                duration = time.time() - start_time
                structured_logger.info(
                    f"Command executed: {command_name} (took {duration:.3f}s)"
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                structured_logger.error(
                    f"Error executing command: {command_name}",
                    extra_data={
                        "duration": duration,
                        "exception_type": type(e).__name__,
                        "exception": str(e),
                    },
                )
                raise

        return cast(F, async_wrapper if is_async else sync_wrapper)

    return decorator


def log_method(component: str = None) -> Callable[[F], F]:
    """
    Decorator for logging method execution with timing and context.

    Args:
        component: Component name for context

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        is_async = asyncio.iscoroutinefunction(func)

        @functools.wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            method_name = func.__name__

            structured_logger.debug(
                f"Executing method: {method_name}",
                extra_data={
                    "args": str(args) if args else None,
                    "class": self.__class__.__name__,
                },
            )

            try:
                result = await func(self, *args, **kwargs)
                return result
            except Exception as e:
                structured_logger.error(
                    f"Error executing method: {method_name}",
                    extra_data={
                        "exception_type": type(e).__name__,
                        "exception": str(e),
                    },
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            method_name = func.__name__

            structured_logger.debug(
                f"Executing method: {method_name}",
                extra_data={
                    "args": str(args) if args else None,
                    "class": self.__class__.__name__,
                },
            )

            try:
                result = func(self, *args, **kwargs)
                return result
            except Exception as e:
                structured_logger.error(
                    f"Error executing method: {method_name}",
                    extra_data={
                        "exception_type": type(e).__name__,
                        "exception": str(e),
                    },
                )
                raise

        return cast(F, async_wrapper if is_async else sync_wrapper)

    return decorator


def log_function(component: str) -> Callable[[F], F]:
    """
    Decorator for logging function execution with timing and context.

    Args:
        component: Component name for context

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        is_async = asyncio.iscoroutinefunction(func)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = func.__name__

            structured_logger.debug(f"Executing function: {func_name}")

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                structured_logger.error(
                    f"Error executing function: {func_name}",
                    extra_data={
                        "exception_type": type(e).__name__,
                        "exception": str(e),
                    },
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = func.__name__

            structured_logger.debug(f"Executing function: {func_name}")

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                structured_logger.error(
                    f"Error executing function: {func_name}",
                    extra_data={
                        "exception_type": type(e).__name__,
                        "exception": str(e),
                    },
                )
                raise

        return cast(F, async_wrapper if is_async else sync_wrapper)

    return decorator


def log_task(component: str) -> Callable[[F], F]:
    """
    Decorator for logging background task execution with comprehensive logging.

    Args:
        component: Component name for context

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        is_async = asyncio.iscoroutinefunction(func)
        if not is_async:
            raise ValueError("log_task can only be used with async functions")

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            task_name = func.__name__

            structured_logger.info(f"Starting background task: {task_name}")

            try:
                result = await func(*args, **kwargs)

                structured_logger.info(f"Completed background task: {task_name}")

                return result
            except asyncio.CancelledError:
                structured_logger.warning(f"Background task cancelled: {task_name}")
                raise
            except Exception as e:
                structured_logger.error(
                    f"Error in background task: {task_name}",
                    extra_data={
                        "exception_type": type(e).__name__,
                        "exception": str(e),
                    },
                )
                raise

        return cast(F, async_wrapper)

    return decorator
