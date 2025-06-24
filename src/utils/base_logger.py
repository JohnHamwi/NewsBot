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
import glob
from datetime import datetime, timedelta
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
class DailyLogFileHandler(logging.FileHandler):
    """Custom FileHandler that creates a new log file each day with date in filename."""

    def __init__(self, base_filename, mode='a', encoding=None, delay=False):
        """Initialize with base filename pattern."""
        self.base_filename = base_filename
        self.current_date = None
        self.current_filename = None
        
        # Create initial filename
        self._update_filename()
        
        super().__init__(self.current_filename, mode, encoding, delay)

    def _update_filename(self):
        """Update filename based on current Eastern date."""
        current_date = datetime.now(EASTERN).strftime("%Y-%m-%d")
        
        if current_date != self.current_date:
            self.current_date = current_date
            # Create filename like: logs/2025-01-16.log
            base_dir = os.path.dirname(self.base_filename)
            self.current_filename = os.path.join(base_dir, f"{current_date}.log")

    def emit(self, record):
        """Override emit to check if we need a new file for a new day."""
        self._update_filename()
        
        # If filename changed, we need to switch to new file
        if self.baseFilename != self.current_filename:
            # Close current file
            if self.stream:
                self.stream.close()
                self.stream = None
            
            # Update to new filename
            self.baseFilename = self.current_filename
            
            # Let parent class handle opening new file
            if not self.delay:
                self.stream = self._open()

        super().emit(record)


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
# Utility Functions
# =============================================================================
def cleanup_old_logs(logs_dir: str = "logs", keep_days: int = 30):
    """
    Clean up old log files, keeping only the specified number of days.
    
    Args:
        logs_dir (str): Directory containing log files
        keep_days (int): Number of days of logs to keep
    """
    try:
        if not os.path.exists(logs_dir):
            return
        
        # Calculate cutoff date
        cutoff_date = datetime.now(EASTERN) - timedelta(days=keep_days)
        
        # Find all log files matching the pattern (YYYY-MM-DD.log)
        log_pattern = os.path.join(logs_dir, "????-??-??.log")
        log_files = glob.glob(log_pattern)
        
        deleted_count = 0
        for log_file in log_files:
            try:
                # Extract date from filename (YYYY-MM-DD.log)
                filename = os.path.basename(log_file)
                if filename.endswith(".log") and len(filename) == 14:  # YYYY-MM-DD.log = 14 chars
                    date_str = filename[:-4]  # Remove ".log"
                    try:
                        file_date = datetime.strptime(date_str, "%Y-%m-%d")
                        file_date = file_date.replace(tzinfo=EASTERN)
                        
                        # Delete if older than cutoff
                        if file_date < cutoff_date:
                            os.remove(log_file)
                            deleted_count += 1
                            
                    except ValueError:
                        # Skip files that don't match the expected date format
                        continue
                        
            except Exception as e:
                # Skip files that can't be processed
                continue
        
        if deleted_count > 0:
            print(f"🗑️ Cleaned up {deleted_count} old log files (older than {keep_days} days)")
            
    except Exception as e:
        # Silently handle cleanup errors to avoid disrupting logging
        pass


# =============================================================================
# Logger Setup Function
# =============================================================================
def setup_logger(name: str) -> logging.Logger:
    """
    Set up a basic logger with console and daily rotating file output.

    Creates a new log file every day with format: newsbot_YYYY-MM-DD.log

    Args:
        name (str): Name of the logger

    Returns:
        logging.Logger: Configured logger instance
    """
    # Debug mode disabled by default (can be enabled via config if needed)
    debug_mode = False

    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Clean up old log files (keep 30 days)
    cleanup_old_logs("logs", 30)

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

    # Create daily log file handler
    # This will create files like: logs/2025-01-16.log, logs/2025-01-17.log, etc.
    # Each day gets its own file automatically
    file_handler = DailyLogFileHandler(
        base_filename="logs/newsbot.log",
        mode='a',
        encoding="utf-8"
    )

    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    logger.addHandler(file_handler)

    # Log initial debug mode status
    if debug_mode:
        logger.debug("🔍 Debug mode is enabled - additional logging will be shown")
        logger.debug(f"🔧 Logger '{name}' initialized with DEBUG level")
    else:
        logger.info(f"🔧 Logger '{name}' initialized with INFO level")

    # Get current date for log message
    current_date = datetime.now(EASTERN).strftime("%Y-%m-%d")
    logger.info(f"📅 Daily log files enabled - today's log: {current_date}.log")
    logger.info(f"📁 Each day gets its own log file in the logs/ folder")

    return logger


# =============================================================================
# Base Logger Instance
# =============================================================================
# Create a base logger instance
base_logger = setup_logger("NewsBot")
