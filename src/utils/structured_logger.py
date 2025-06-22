# =============================================================================
# NewsBot Structured Logger Module
# =============================================================================
# This module provides structured logging functionality with JSON output for 
# production environments, including custom datetime encoding and formatted
# log entries with timestamps, levels, and additional metadata.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

# =============================================================================
# Third-Party Library Imports
# =============================================================================
from dotenv import load_dotenv

# =============================================================================
# Local Application Imports
# =============================================================================
from .timezone_utils import now_eastern

# =============================================================================
# Environment Configuration
# =============================================================================
# Load environment variables
load_dotenv()


# =============================================================================
# JSON Encoder Classes
# =============================================================================
class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# =============================================================================
# Structured Logger Main Class
# =============================================================================
class StructuredLogger:
    """
    A structured logger that outputs JSON-formatted logs for better parsing and analysis.
    
    Features:
    - JSON-formatted log output for production environments
    - Eastern timezone timestamp handling
    - Debug mode support from environment variables
    - Structured data inclusion in log entries
    - Error object serialization
    """

    def __init__(self, name: str = "NewsBot"):
        """
        Initialize the structured logger.

        Args:
            name (str): Name of the logger
        """
        self.name = name
        self.debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

    # =========================================================================
    # Message Formatting Methods
    # =========================================================================
    def _format_message(
        self,
        level: str,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
    ) -> str:
        """
        Format a log message as structured JSON.

        Args:
            level (str): Log level
            message (str): Log message
            extra_data (Dict[str, Any], optional): Additional data to include
            error (Exception, optional): Exception object if logging an error

        Returns:
            str: JSON-formatted log message
        """
        log_entry = {
            "timestamp": now_eastern().isoformat(),
            "level": level,
            "logger": self.name,
            "message": message,
        }

        if extra_data:
            log_entry["data"] = extra_data

        if error:
            log_entry["error"] = {
                "type": type(error).__name__,
                "message": str(error),
            }

        return json.dumps(log_entry, ensure_ascii=False, cls=DateTimeEncoder)

    # =========================================================================
    # Logging Level Methods
    # =========================================================================
    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log a debug message."""
        if self.debug_mode:
            print(self._format_message("DEBUG", message, extra_data))

    def info(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log an info message."""
        print(self._format_message("INFO", message, extra_data))

    def warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log a warning message."""
        print(self._format_message("WARNING", message, extra_data))

    def error(
        self,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
    ):
        """Log an error message."""
        print(self._format_message("ERROR", message, extra_data, error))

    def critical(
        self,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
    ):
        """Log a critical message."""
        print(self._format_message("CRITICAL", message, extra_data, error))


# =============================================================================
# Module-Level Logger Instance
# =============================================================================
# Create a default structured logger instance
structured_logger = StructuredLogger()
