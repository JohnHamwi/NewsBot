# =============================================================================
# NewsBot Logger Module
# =============================================================================
# This module provides a custom logging setup for the bot with colored console
# output, file logging with rotation, command usage tracking, error tracking,
# and comprehensive performance metrics collection.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
from typing import Any, Dict, Optional

# =============================================================================
# Local Application Imports
# =============================================================================
from src.utils.base_logger import base_logger


# =============================================================================
# Bot Logger Main Class
# =============================================================================
class BotLogger:
    """
    Custom logger class for the Discord bot.

    This class provides:
    - Colored console logging
    - File logging with rotation
    - Command usage tracking
    - Error tracking
    - Performance metrics

    Attributes:
        logger (logging.Logger): The main logger instance
        command_count (int): Total number of commands executed
        error_count (int): Total number of errors encountered
        command_latencies (Dict[str, float]): Average latency for each command
        command_usage (Dict[str, int]): Usage count for each command
    """

    def __init__(self):
        """Initialize the logger with custom formatting and handlers."""
        # Initialize metrics
        self.command_count: int = 0
        self.error_count: int = 0
        self.command_latencies: Dict[str, float] = {}
        self.command_usage: Dict[str, int] = {}
        self.logger = base_logger

    # =========================================================================
    # Basic Logging Methods
    # =========================================================================
    def debug(
        self, message: str, context: str = "", extras: Dict[str, Any] = None
    ) -> None:
        """
        Log a debug message.

        Args:
            message: Log message
            context: Context information
            extras: Extra fields for structured logging
        """
        if context:
            self.logger.debug(f"{message} | {context}")
        else:
            self.logger.debug(message)

    def info(
        self, message: str, context: str = "", extras: Dict[str, Any] = None
    ) -> None:
        """
        Log an info message.

        Args:
            message: Log message
            context: Context information
            extras: Extra fields for structured logging
        """
        if context:
            self.logger.info(f"{message} | {context}")
        else:
            self.logger.info(message)

    def warning(
        self, message: str, context: str = "", extras: Dict[str, Any] = None
    ) -> None:
        """
        Log a warning message.

        Args:
            message: Log message
            context: Context information
            extras: Extra fields for structured logging
        """
        if context:
            self.logger.warning(f"{message} | {context}")
        else:
            self.logger.warning(message)

    def error(
        self, message: str, context: str = "", extras: Dict[str, Any] = None
    ) -> None:
        """
        Log an error message and increment error count.

        Args:
            message: Log message
            context: Context information
            extras: Extra fields for structured logging
        """
        if context:
            self.logger.error(f"{message} | {context}", exc_info=True)
        else:
            self.logger.error(message, exc_info=True)

        self.error_count += 1

    def critical(
        self, message: str, context: str = "", extras: Dict[str, Any] = None
    ) -> None:
        """
        Log a critical message and increment error count.

        Args:
            message: Log message
            context: Context information
            extras: Extra fields for structured logging
        """
        if context:
            self.logger.critical(f"{message} | {context}", exc_info=True)
        else:
            self.logger.critical(message, exc_info=True)

        self.error_count += 1

    # =========================================================================
    # Command Tracking Methods
    # =========================================================================
    def command(
        self, command_name: str, duration: float, extras: Dict[str, Any] = None
    ) -> None:
        """
        Log command execution and update metrics.

        Args:
            command_name: Name of the command executed
            duration: Time taken to execute the command in seconds
            extras: Extra fields for structured logging
        """
        # Update metrics
        self.command_count += 1
        self.command_usage[command_name] = self.command_usage.get(command_name, 0) + 1

        # Update average latency
        current_avg = self.command_latencies.get(command_name, 0)
        current_count = self.command_usage[command_name]
        new_avg = ((current_avg * (current_count - 1)) + duration) / current_count
        self.command_latencies[command_name] = new_avg

        # Log command execution in debug mode
        self.debug(
            f"Command executed: {command_name} | "
            f"Duration: {duration:.2f}s | "
            f"Avg Duration: {new_avg:.2f}s | "
            f"Usage Count: {current_count}"
        )

    # =========================================================================
    # Metrics Management Methods
    # =========================================================================
    def get_metrics(self) -> Dict:
        """
        Get current logging metrics.

        Returns:
            Dict: Dictionary containing:
                - command_count: Total commands executed
                - error_count: Total errors encountered
                - command_usage: Usage count per command
                - command_latencies: Average latency per command
        """
        return {
            "command_count": self.command_count,
            "error_count": self.error_count,
            "command_usage": self.command_usage.copy(),
            "command_latencies": self.command_latencies.copy(),
        }

    def reset_metrics(self) -> None:
        """Reset all metrics to zero."""
        self.command_count = 0
        self.error_count = 0
        self.command_latencies.clear()
        self.command_usage.clear()


# =============================================================================
# Module-Level Functions
# =============================================================================
def get_logger(name: str = "NewsBot"):
    """
    Get a logger instance.

    Args:
        name: Logger name

    Returns:
        BotLogger: Logger instance
    """
    return BotLogger()
