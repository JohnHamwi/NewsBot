# =============================================================================
# NewsBot Base Logger Module
# =============================================================================
# This module provides basic logging functionality without configuration 
# dependencies. It includes timezone-aware logging with Eastern time zone
# support, colored console output, and daily rotating file handlers.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from zoneinfo import ZoneInfo

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import colorlog
from dotenv import load_dotenv

# =============================================================================
# Environment Configuration
# =============================================================================
# Load environment variables
load_dotenv()

# Eastern timezone (automatically handles EST/EDT transitions)
EASTERN = ZoneInfo("America/New_York")


# =============================================================================
# Custom Handler Classes
# =============================================================================
class EasternTimedRotatingFileHandler(TimedRotatingFileHandler):
    """Custom TimedRotatingFileHandler that uses Eastern timezone for rotation."""

    def __init__(
        self,
        filename,
        when="midnight",
        interval=1,
        backupCount=0,
        encoding=None,
        delay=False,
        utc=False,
        atTime=None,
    ):
        """Initialize with Eastern timezone."""
        # Force UTC to False since we want Eastern time
        super().__init__(
            filename,
            when,
            interval,
            backupCount,
            encoding,
            delay,
            utc=False,
            atTime=atTime,
        )

    def computeRollover(self, currentTime):
        """Override to use Eastern timezone for rollover calculation."""
        # Convert current time to Eastern timezone
        dt = datetime.fromtimestamp(currentTime, tz=EASTERN)

        # Calculate next midnight in Eastern time
        next_midnight = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        next_midnight = next_midnight.replace(day=next_midnight.day + 1)

        # Convert back to timestamp
        return next_midnight.timestamp()


# =============================================================================
# Custom Formatter Classes
# =============================================================================
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


# =============================================================================
# Logger Setup Function
# =============================================================================
def setup_logger(name: str) -> logging.Logger:
    """
    Set up a basic logger with console and daily rotating file output.

    Creates a new log file every day at midnight EST with format: newsbot_YYYY-MM-DD.log

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
    console_formatter = EasternColoredFormatter(
        "%(asctime)s | %(log_color)s[%(levelname)-5s]%(reset)s | %(message)s",
        datefmt="%Y-%m-%d | %I:%M:%S %p",
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

    file_formatter = EasternFormatter(
        "%(asctime)s | [%(levelname)-5s] | %(message)s",
        datefmt="%Y-%m-%d | %I:%M:%S %p",
    )

    # Create console handler
    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    logger.addHandler(console_handler)

    # Create daily rotating file handler
    # This will create a new log file every day at midnight EST
    # Files will be named: newsbot_2025-01-15.log, newsbot_2025-01-16.log, etc.
    file_handler = EasternTimedRotatingFileHandler(
        filename="logs/newsbot.log",
        when="midnight",
        interval=1,
        backupCount=30,  # Keep 30 days of logs
        encoding="utf-8",
    )

    # Set the suffix for rotated files to include the date
    file_handler.suffix = "%Y-%m-%d"

    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    logger.addHandler(file_handler)

    # Log initial debug mode status
    if debug_mode:
        logger.debug("🔍 Debug mode is enabled - additional logging will be shown")
        logger.debug(f"🔧 Logger '{name}' initialized with DEBUG level")
    else:
        logger.info(f"🔧 Logger '{name}' initialized with INFO level")

    logger.info(f"📅 Daily log rotation enabled - new file created at midnight EST")
    logger.info(f"📁 Log files will be kept for 30 days")

    return logger


# =============================================================================
# Base Logger Instance
# =============================================================================
# Create a base logger instance
base_logger = setup_logger("NewsBot")
