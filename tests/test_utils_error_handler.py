"""
Test suite for error handler utilities.
"""

import sys
import types
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from src.utils.error_handler import ErrorContext, ErrorHandler, error_handler


@pytest.fixture
def error_handler():
    """Create a fresh error handler instance for each test."""
    return ErrorHandler()


def test_error_context_basic():
    err = ValueError("fail")
    ctx = ErrorContext(err, "testloc")
    d = ctx.to_dict()
    assert d["error_type"] == "ValueError"
    assert "fail" in d["error_message"]
    assert d["location"] == "testloc"
    assert "system_info" in d


def test_error_metrics_and_spike(error_handler):
    # Add errors to history
    for _ in range(10):
        ctx = ErrorContext(ValueError("fail"), "loc")
        ctx.timestamp = datetime.now() - timedelta(minutes=5)
        error_handler._add_to_history(ctx)
    metrics = error_handler.get_error_metrics()
    assert "error_counts" in metrics
    assert "recent_errors" in metrics
    assert isinstance(metrics["error_counts"], dict)
    # Simulate spike
    for _ in range(10):
        ctx = ErrorContext(ValueError("fail"), "loc")
        ctx.timestamp = datetime.now()
        error_handler._add_to_history(ctx)
    patterns = error_handler._analyze_error_patterns()
    assert "recent_spike" in patterns


@pytest.mark.asyncio
async def test_send_error_embed(monkeypatch, error_handler):
    """Test sending error embed."""

    class DummyEmbed:
        def __init__(self, title=None, description=None, color=None, timestamp=None):
            self.title = title
            self.description = description
            self.color = color
            self.timestamp = timestamp
            self.fields = []

        def add_field(self, name=None, value=None, inline=None):
            self.fields.append({"name": name, "value": value, "inline": inline})
            return self

    class DummyColor:
        @property
        def red(self):
            return 0xFF0000

    class DummyChannel:
        async def send(self, embed=None, content=None):
            self.sent_embed = embed
            self.sent_content = content
            return True

    class DummyBot:
        def __init__(self):
            self.errors_channel = DummyChannel()

    # Patch discord components
    monkeypatch.setattr("discord.Embed", DummyEmbed)
    monkeypatch.setattr("discord.Color", DummyColor)

    # Execute
    await error_handler.send_error_embed(
        "Test Error", Exception("test failure"), bot=DummyBot()
    )

    # Assert
    assert error_handler.error_history[-1].error_type == "Exception"
    assert error_handler.error_history[-1].error_message == "test failure"


def test_error_handler_metrics_structure(error_handler):
    """Test error metrics structure."""
    metrics = error_handler.get_metrics()

    assert isinstance(metrics, dict)
    assert "error_counts" in metrics
    assert "error_total" in metrics
    assert "success_rate" in metrics
    assert "recent_error" in metrics
    assert "details" in metrics
