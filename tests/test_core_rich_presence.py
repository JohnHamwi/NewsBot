import asyncio
from unittest.mock import AsyncMock

import pytest

from src.core import rich_presence
from src.core.rich_presence import set_maintenance_presence


def test_set_maintenance_presence_is_awaitable():
    assert asyncio.iscoroutinefunction(set_maintenance_presence)


@pytest.mark.asyncio
async def test_set_maintenance_presence():
    bot = AsyncMock()
    await rich_presence.set_maintenance_presence(bot)
    bot.change_presence.assert_awaited_once()
    args, kwargs = bot.change_presence.call_args
    assert kwargs["activity"].name == "⚠️ Under Maintenance"


@pytest.mark.asyncio
async def test_set_automatic_presence():
    bot = AsyncMock()
    await rich_presence.set_automatic_presence(bot, 3661)
    bot.change_presence.assert_awaited_once()
    args, kwargs = bot.change_presence.call_args
    assert "📰 News:" in kwargs["activity"].name
    assert "1h:01m" in kwargs["activity"].name


@pytest.mark.asyncio
async def test_set_posted_presence():
    bot = AsyncMock()
    await rich_presence.set_posted_presence(bot)
    bot.change_presence.assert_awaited_once()
    args, kwargs = bot.change_presence.call_args
    assert kwargs["activity"].name == "✅ Posted!"
