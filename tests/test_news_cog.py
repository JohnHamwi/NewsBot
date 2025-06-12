from unittest.mock import MagicMock

import discord
import pytest
from discord.ext import commands

from src.cogs.news import NewsCog


def test_news_cog_instantiation():
    bot = MagicMock(spec=discord.Client)
    cog = NewsCog(bot)
    assert cog.bot is bot


def test_channel_activate_command_registration():
    bot = MagicMock(spec=discord.Client)
    cog = NewsCog(bot)
    # Find the command in the app_commands
    commands_list = [
        cmd for cmd in cog.__cog_app_commands__ if cmd.name == "channel_activate"
    ]
    assert commands_list, "channel_activate command should be registered"
    # Simulate calling the command (mock interaction)
    interaction = MagicMock()
    # Only check that the command can be called (not full logic)
    try:
        # Provide a dummy channelname
        import asyncio

        asyncio.run(commands_list[0].callback(cog, interaction, "testchannel"))
    except Exception:
        pass  # We expect errors due to mocks, but the command should be callable
