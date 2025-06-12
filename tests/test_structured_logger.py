"""
Test module for structured logger functionality.
"""

import json
import logging
import os
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.utils.structured_logger import StructuredLogger, structured_logger


class TestStructuredLogger:
    """Test the structured logger implementation."""

    def test_basic_logging(self):
        """Test basic logging functionality."""
        with patch("builtins.print") as mock_print:
            structured_logger.info("Test message")
            mock_print.assert_called_once()

            # Parse the JSON output
            call_args = mock_print.call_args[0][0]
            log_data = json.loads(call_args)

            assert log_data["level"] == "INFO"
            assert log_data["message"] == "Test message"
            assert log_data["logger"] == "NewsBot"
            assert "timestamp" in log_data

    def test_logging_with_extra_data(self):
        """Test logging with extra data fields."""
        with patch("builtins.print") as mock_print:
            extra_data = {"field1": "value1", "field2": 123}
            structured_logger.info("Test message", extra_data=extra_data)

            call_args = mock_print.call_args[0][0]
            log_data = json.loads(call_args)

            assert log_data["level"] == "INFO"
            assert log_data["message"] == "Test message"
            assert log_data["data"] == extra_data

    def test_error_logging_with_exception(self):
        """Test error logging with exception."""
        with patch("builtins.print") as mock_print:
            test_exception = ValueError("Test error")
            structured_logger.error("Error occurred", error=test_exception)

            call_args = mock_print.call_args[0][0]
            log_data = json.loads(call_args)

            assert log_data["level"] == "ERROR"
            assert log_data["message"] == "Error occurred"
            assert log_data["error"]["type"] == "ValueError"
            assert log_data["error"]["message"] == "Test error"

    def test_debug_mode_enabled(self):
        """Test debug logging when debug mode is enabled."""
        with patch.dict(os.environ, {"DEBUG_MODE": "true"}):
            logger = StructuredLogger("TestLogger")
            with patch("builtins.print") as mock_print:
                logger.debug("Debug message")
                mock_print.assert_called_once()

                call_args = mock_print.call_args[0][0]
                log_data = json.loads(call_args)
                assert log_data["level"] == "DEBUG"

    def test_debug_mode_disabled(self):
        """Test debug logging when debug mode is disabled."""
        with patch.dict(os.environ, {"DEBUG_MODE": "false"}):
            logger = StructuredLogger("TestLogger")
            with patch("builtins.print") as mock_print:
                logger.debug("Debug message")
                mock_print.assert_not_called()

    def test_all_log_levels(self):
        """Test all log levels."""
        with patch("builtins.print") as mock_print:
            structured_logger.info("Info message")
            structured_logger.warning("Warning message")
            structured_logger.error("Error message")
            structured_logger.critical("Critical message")

            assert mock_print.call_count == 4

            # Check each call
            calls = mock_print.call_args_list
            levels = []
            for call in calls:
                log_data = json.loads(call[0][0])
                levels.append(log_data["level"])

            assert "INFO" in levels
            assert "WARNING" in levels
            assert "ERROR" in levels
            assert "CRITICAL" in levels

    def test_custom_logger_name(self):
        """Test creating logger with custom name."""
        custom_logger = StructuredLogger("CustomLogger")
        with patch("builtins.print") as mock_print:
            custom_logger.info("Test message")

            call_args = mock_print.call_args[0][0]
            log_data = json.loads(call_args)
            assert log_data["logger"] == "CustomLogger"

    def test_json_serialization(self):
        """Test that complex data structures are properly serialized."""
        with patch("builtins.print") as mock_print:
            complex_data = {
                "list": [1, 2, 3],
                "dict": {"nested": "value"},
                "string": "test",
                "number": 42,
                "boolean": True,
                "null": None,
            }
            structured_logger.info("Complex data", extra_data=complex_data)

            call_args = mock_print.call_args[0][0]
            log_data = json.loads(call_args)
            assert log_data["data"] == complex_data

    def test_unicode_handling(self):
        """Test that Unicode characters are handled properly."""
        with patch("builtins.print") as mock_print:
            unicode_message = "Test with Arabic: مرحبا بك"
            unicode_data = {"arabic": "السلام عليكم", "emoji": "🚀"}

            structured_logger.info(unicode_message, extra_data=unicode_data)

            call_args = mock_print.call_args[0][0]
            log_data = json.loads(call_args)
            assert log_data["message"] == unicode_message
            assert log_data["data"] == unicode_data
