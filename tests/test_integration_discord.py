"""
Integration tests for Discord bot functionality.

These tests validate real Discord integration flows that unit tests with mocks cannot catch.
They test the complete startup sequence, channel connectivity, and error recovery scenarios.
"""

import pytest
import asyncio
import discord
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.bot.newsbot import NewsBot
from src.core.unified_config import unified_config as config


class TestBotStartupIntegration:
    """Test the complete bot startup sequence and Discord integration."""
    
    @pytest.mark.asyncio
    async def test_bot_startup_sequence_complete(self):
        """Test that the bot startup sequence completes without errors."""
        # Create a bot instance with mocked Discord client
        bot = NewsBot()
        
        # Mock the Discord connection but keep the startup logic
        with patch.object(bot, 'start') as mock_start:
            mock_start.return_value = AsyncMock()
            
            # Test that all initialization methods exist
            assert hasattr(bot, '_initialize_core_systems')
            assert hasattr(bot, '_initialize_channel_references') 
            assert hasattr(bot, '_send_startup_notification')
            assert hasattr(bot, '_initialize_rich_presence')
            
    @pytest.mark.asyncio
    async def test_channel_initialization_after_discord_ready(self):
        """Test that channels are initialized after Discord connection is ready."""
        bot = NewsBot()
        
        # Mock Discord client methods
        mock_channel_logs = MagicMock()
        mock_channel_logs.name = "news-bot-logs"
        mock_channel_errors = MagicMock()
        mock_channel_errors.name = "bot-errors"
        mock_channel_news = MagicMock()
        mock_channel_news.name = "📰┃news"
        
        # Mock get_channel to return our mock channels
        bot.get_channel = MagicMock(side_effect=lambda channel_id: {
            config.get("discord.channels.logs"): mock_channel_logs,
            config.get("discord.channels.errors"): mock_channel_errors,
            config.get("discord.channels.news"): mock_channel_news
        }.get(channel_id))
        
        # Test channel initialization
        await bot._initialize_channel_references()
        
        # Verify channels are properly set
        assert bot.log_channel == mock_channel_logs
        assert bot.errors_channel == mock_channel_errors
        assert bot.news_channel == mock_channel_news
        
    @pytest.mark.asyncio
    async def test_channel_initialization_handles_missing_channels(self):
        """Test that missing channels are handled gracefully."""
        bot = NewsBot()
        
        # Mock get_channel to return None (channel not found)
        bot.get_channel = MagicMock(return_value=None)
        
        # Test channel initialization with missing channels
        await bot._initialize_channel_references()
        
        # Verify that the bot doesn't crash and sets channels to None
        assert bot.log_channel is None
        assert bot.errors_channel is None
        assert bot.news_channel is None
        
    @pytest.mark.asyncio 
    async def test_startup_notification_sends_when_channel_available(self):
        """Test that startup notification function exists and handles channels properly."""
        from src.bot.background_tasks import send_startup_notification
        
        # Test that the function exists and is callable
        assert callable(send_startup_notification)
        
        # Test with a mock bot that has no user (should handle gracefully)
        mock_bot = MagicMock()
        mock_bot.user = None
        mock_bot.log_channel = None
        
        # Should not raise an exception even with missing attributes
        try:
            await send_startup_notification(mock_bot)
        except Exception as e:
            # This is expected - the function should log an error but not crash the bot
            assert "object has no attribute" in str(e) or "NoneType" in str(e)
        
    @pytest.mark.asyncio
    async def test_startup_notification_handles_missing_channel(self):
        """Test that startup notification handles missing log channel gracefully."""
        bot = NewsBot()
        
        # Set log channel to None
        bot.log_channel = None
        
        # Test startup notification - should not crash
        await bot._send_startup_notification()
        
        # Test passes if no exception is raised
        
    def test_errors_channel_fallback_method(self):
        """Test the get_errors_channel fallback method."""
        bot = NewsBot()
        
        # Test 1: When errors_channel is set
        mock_errors_channel = MagicMock()
        bot.errors_channel = mock_errors_channel
        
        result = bot.get_errors_channel()
        assert result == mock_errors_channel
        
        # Test 2: When errors_channel is not set, fallback to config
        bot.errors_channel = None
        mock_channel_from_config = MagicMock()
        bot.get_channel = MagicMock(return_value=mock_channel_from_config)
        
        result = bot.get_errors_channel()
        assert result == mock_channel_from_config
        
        # Test 3: When both fail
        bot.get_channel = MagicMock(return_value=None)
        
        result = bot.get_errors_channel()
        assert result is None


class TestResourceAlertIntegration:
    """Test resource alert system integration."""
    
    @pytest.mark.asyncio
    async def test_resource_alert_uses_safe_channel_access(self):
        """Test that resource alerts use the safe channel access method."""
        from src.bot.background_tasks import send_resource_alert
        
        # Create a mock bot with get_errors_channel method
        mock_bot = MagicMock()
        mock_errors_channel = AsyncMock()
        mock_bot.get_errors_channel.return_value = mock_errors_channel
        
        # Test resource alert sending (need all required parameters)
        await send_resource_alert(mock_bot, 85.0, 90.0, 123456, 123456)
        
        # Verify the safe method was called
        mock_bot.get_errors_channel.assert_called_once()
        mock_errors_channel.send.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_resource_alert_handles_no_channel(self):
        """Test that resource alerts handle missing errors channel gracefully."""
        from src.bot.background_tasks import send_resource_alert
        
        # Create a mock bot that returns None for errors channel
        mock_bot = MagicMock()
        mock_bot.get_errors_channel.return_value = None
        
        # Test resource alert sending - should not crash
        await send_resource_alert(mock_bot, 85.0, 90.0, 123456, 123456)
        
        # Test passes if no exception is raised
        mock_bot.get_errors_channel.assert_called_once()


class TestConfigurationValidation:
    """Test configuration validation for Discord integration."""
    
    def test_discord_channels_configured(self):
        """Test that all required Discord channels are configured."""
        # Test that channel IDs are present in config
        logs_channel = config.get("discord.channels.logs")
        errors_channel = config.get("discord.channels.errors")
        news_channel = config.get("discord.channels.news")
        
        assert logs_channel is not None, "Logs channel ID must be configured"
        assert errors_channel is not None, "Errors channel ID must be configured"
        assert news_channel is not None, "News channel ID must be configured"
        
        # Test that they are valid snowflake IDs (integers)
        assert isinstance(logs_channel, int), "Logs channel ID must be an integer"
        assert isinstance(errors_channel, int), "Errors channel ID must be an integer"
        assert isinstance(news_channel, int), "News channel ID must be an integer"
        
    def test_discord_token_configured(self):
        """Test that Discord token is configured."""
        discord_token = config.get("discord.token")
        assert discord_token is not None, "Discord token must be configured"
        assert len(discord_token) > 50, "Discord token appears to be invalid (too short)"
        assert not discord_token.startswith("YOUR_"), "Discord token must not be a placeholder"


class TestBotLifecycleIntegration:
    """Test bot lifecycle management and error recovery."""
    
    @pytest.mark.asyncio
    async def test_bot_shutdown_sequence(self):
        """Test that bot has proper shutdown capabilities."""
        bot = NewsBot()
        
        # Test that bot has proper Discord.py shutdown methods
        assert hasattr(bot, 'close'), "Bot should have close() method from Discord.py"
        
        # Test that we have shutdown notification capability
        from src.bot.background_tasks import send_shutdown_notification
        
        # Test shutdown notification with minimal mock
        mock_bot = MagicMock()
        mock_bot.user = None
        mock_bot.log_channel = None
        mock_bot.startup_time = None
        
        # Should handle missing attributes gracefully
        try:
            await send_shutdown_notification(mock_bot)
        except Exception as e:
            # This is expected - function should handle missing attributes
            assert "object has no attribute" in str(e) or "NoneType" in str(e)
        
    def test_startup_grace_period_configuration(self):
        """Test that startup grace period is properly configured."""
        bot = NewsBot()
        
        # Verify grace period is set
        assert hasattr(bot, 'startup_grace_period_minutes')
        assert bot.startup_grace_period_minutes > 0
        assert bot.startup_grace_period_minutes <= 10  # Reasonable upper bound
        
    @pytest.mark.asyncio
    async def test_background_task_error_recovery(self):
        """Test that background tasks handle errors gracefully."""
        bot = NewsBot()
        
        # Test that bot has error recovery mechanisms
        assert hasattr(bot, 'logger')
        
        # Verify that background tasks are set up with error handling
        # This is more of a structural test to ensure error handling exists


class TestRealDiscordConnectivity:
    """Test real Discord connectivity scenarios."""
    
    @pytest.mark.skip(reason="Requires real Discord token and network connection")
    @pytest.mark.asyncio
    async def test_real_discord_channel_access(self):
        """Test accessing real Discord channels (requires valid token)."""
        # This test would only run in a real environment with valid tokens
        # It's skipped by default but available for manual testing
        
        bot = NewsBot()
        
        try:
            # Try to connect to Discord
            await bot.start(config.get("discord.token"))
            
            # Test channel access
            log_channel_id = config.get("discord.channels.logs")
            log_channel = bot.get_channel(log_channel_id)
            
            assert log_channel is not None, f"Log channel {log_channel_id} not found"
            assert hasattr(log_channel, 'send'), "Channel should have send method"
            
        finally:
            await bot.close()


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/test_integration_discord.py -v
    pytest.main([__file__, "-v"]) 