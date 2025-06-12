"""
Tests for the log API module.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord import app_commands
from discord.ext import commands

from src.monitoring.log_api import LogAPICog


@pytest.mark.asyncio
async def test_setup():
    """Test the setup function."""
    # Mock the bot
    bot = MagicMock()
    bot.add_cog = AsyncMock()

    # Call the setup function
    from src.monitoring.log_api import setup

    await setup(bot)

    # Verify the cog was added to the bot
    bot.add_cog.assert_called_once()
    args, kwargs = bot.add_cog.call_args
    assert isinstance(args[0], LogAPICog)
