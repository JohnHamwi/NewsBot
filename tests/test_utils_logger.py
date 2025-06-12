from unittest.mock import MagicMock

import pytest

from src.utils.logger import BotLogger, get_logger


def test_logger_creation():
    """Test that logger can be created."""
    logger = get_logger()
    assert isinstance(logger, BotLogger)
    assert hasattr(logger, "debug")
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")


def test_botlogger_command_and_metrics():
    logger = BotLogger()
    logger.logger = MagicMock()
    logger.command("testcmd", 1.23)
    metrics = logger.get_metrics()
    assert "command_count" in metrics
    assert metrics["command_usage"]["testcmd"] == 1
    assert "command_latencies" in metrics
    assert "testcmd" in metrics["command_latencies"]


def test_botlogger_error_and_critical():
    logger = BotLogger()
    logger.logger = MagicMock()
    logger.error("errormsg", context="ctx")
    logger.critical("critmsg", context="ctx")
    assert logger.error_count == 2


def test_botlogger_reset_metrics():
    """Test that metrics can be reset."""
    logger = BotLogger()
    logger.logger = MagicMock()
    logger.command("testcmd", 1.23)
    logger.error("test error")

    # Verify metrics exist
    metrics = logger.get_metrics()
    assert metrics["command_count"] > 0
    assert metrics["error_count"] > 0

    # Reset and verify
    logger.reset_metrics()
    metrics = logger.get_metrics()
    assert metrics["command_count"] == 0
    assert metrics["error_count"] == 0
    assert len(metrics["command_usage"]) == 0
    assert len(metrics["command_latencies"]) == 0
