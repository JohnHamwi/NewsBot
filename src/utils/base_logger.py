"""
Base Logger Module

This module provides basic logging functionality without configuration dependencies.
"""

import os
import logging
import colorlog
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

# Load environment variables
load_dotenv()

# Eastern timezone (automatically handles EST/EDT)
EASTERN = ZoneInfo("America/New_York")


class EasternFormatter(logging.Formatter):
    """Custom formatter that uses Eastern timezone."""

    def formatTime(self, record, datefmt=None):
        """Override formatTime to use Eastern timezone."""
        dt = datetime.fromtimestamp(record.created, tz=EASTERN)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.isoformat()


class EasternColoredFormatter(colorlog.ColoredFormatter):
    """Custom colored formatter that uses Eastern timezone."""

    def formatTime(self, record, datefmt=None):
        """Override formatTime to use Eastern timezone."""
        dt = datetime.fromtimestamp(record.created, tz=EASTERN)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.isoformat()


def setup_logger(name: str) -> logging.Logger:
    """
    Set up a basic logger with console and file output.

    Args:
        name (str): Name of the logger

    Returns:
        logging.Logger: Configured logger instance
    """
    # Get debug mode from environment
    debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Create and configure logger
    logger = logging.getLogger(name)

    # Prevent duplicate handlers by checking if already configured
    if logger.handlers:
        return logger

    # Set level based on debug mode
    logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)

    # Create formatters with enhanced debug information
    console_formatter = colorlog.ColoredFormatter(
        "%(asctime)s | %(log_color)s[%(levelname)-5s]%(reset)s | %(message)s",
        datefmt="%Y-%m-%d | %I:%M:%S %p %Z",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        reset=True,
        secondary_log_colors={},
    )

    file_formatter = logging.Formatter(
        "%(asctime)s | [%(levelname)-5s] | %(message)s", datefmt="%Y-%m-%d | %I:%M:%S %p %Z"
    )

    # Create console handler
    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    logger.addHandler(console_handler)

    # Create file handler with rotation
    file_handler = RotatingFileHandler(
        "logs/newsbot.log", maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    logger.addHandler(file_handler)

    # Log initial debug mode status
    if debug_mode:
        logger.debug(
            "🔍 Debug mode is enabled - additional logging will be shown")
        logger.debug(f"🔧 Logger '{name}' initialized with DEBUG level")
    else:
        logger.info(f"🔧 Logger '{name}' initialized with INFO level")

    return logger


# Create a base logger instance
base_logger = setup_logger("NewsBot")
