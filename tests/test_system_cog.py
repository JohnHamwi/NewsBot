import pytest
from unittest.mock import MagicMock
from src.cogs.status import StatusCommands
import discord

def test_system_commands_instantiation():
    bot = MagicMock(spec=discord.Client)
    cog = StatusCommands(bot)
    assert cog.bot is bot 