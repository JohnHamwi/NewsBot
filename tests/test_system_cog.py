from unittest.mock import MagicMock

import discord
import pytest

from src.cogs.status import StatusCommands


def test_system_commands_instantiation():
    bot = MagicMock(spec=discord.Client)
    cog = StatusCommands(bot)
    assert cog.bot is bot
