"""
Structured Logger Module

This module provides structured logging functionality with JSON output for production environments.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class StructuredLogger:
    """
    A structured logger that outputs JSON-formatted logs for better parsing and analysis.
    """

    def __init__(self, name: str = "NewsBot"):
        """
        Initialize the structured logger.

        Args:
            name (str): Name of the logger
        """
        self.name = name
        self.debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

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
            "timestamp": datetime.utcnow().isoformat() + "Z",
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

        return json.dumps(log_entry, ensure_ascii=False)

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


# Create a default structured logger instance
structured_logger = StructuredLogger() 