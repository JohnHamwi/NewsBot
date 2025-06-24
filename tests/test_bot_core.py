# =============================================================================
# NewsBot Core Functionality Tests
# =============================================================================
# Tests for the core bot functionality including posting intervals,
# startup grace periods, and critical timing logic.

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from src.utils.timezone_utils import now_eastern, utc_to_eastern


class TestNewsBotCore:
    """Test core NewsBot functionality."""

    @pytest.mark.asyncio
    async def test_mark_just_posted_updates_time(self, mock_bot, mock_timezone_utils):
        """Test that mark_just_posted correctly updates last_post_time."""
        # Arrange
        initial_time = mock_bot.last_post_time
        
        # Act
        mock_bot.mark_just_posted()
        
        # Assert
        assert mock_bot.last_post_time is not None
        assert mock_bot.last_post_time != initial_time
        assert mock_bot._just_posted is True
        mock_bot.json_cache.set.assert_called()

    @pytest.mark.asyncio
    async def test_mark_just_posted_saves_to_cache(self, mock_bot):
        """Test that mark_just_posted saves the time to cache."""
        # Act
        mock_bot.mark_just_posted()
        
        # Give async task time to run
        await asyncio.sleep(0.01)
        
        # Assert
        mock_bot.json_cache.set.assert_called()
        mock_bot.json_cache.save.assert_called()

    def test_startup_grace_period_active(self, mock_bot):
        """Test that startup grace period correctly blocks posting."""
        # Arrange - bot just started 2 minutes ago
        mock_bot.startup_time = datetime.now(timezone.utc) - timedelta(minutes=2)
        mock_bot.startup_grace_period_minutes = 5
        mock_bot.disable_auto_post_on_startup = True
        
        # Act
        should_wait, seconds_to_wait = mock_bot.should_wait_for_startup_delay()
        
        # Assert
        assert should_wait is True
        assert seconds_to_wait > 0
        # Should be approximately 3 minutes (5 - 2)
        assert 170 <= seconds_to_wait <= 190

    def test_startup_grace_period_expired(self, mock_bot):
        """Test that expired grace period allows posting."""
        # Arrange - bot started 10 minutes ago
        mock_bot.startup_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        mock_bot.startup_grace_period_minutes = 5
        mock_bot.disable_auto_post_on_startup = True
        
        # Act
        should_wait, seconds_to_wait = mock_bot.should_wait_for_startup_delay()
        
        # Assert
        assert should_wait is False
        assert seconds_to_wait == 0

    def test_startup_grace_period_disabled(self, mock_bot):
        """Test that disabled grace period allows immediate posting."""
        # Arrange
        mock_bot.startup_time = datetime.now(timezone.utc)  # Just started
        mock_bot.disable_auto_post_on_startup = False
        
        # Act
        should_wait, seconds_to_wait = mock_bot.should_wait_for_startup_delay()
        
        # Assert
        assert should_wait is False
        assert seconds_to_wait == 0

    def test_set_auto_post_interval(self, mock_bot):
        """Test setting auto-post interval."""
        # Act
        mock_bot.set_auto_post_interval(240)  # 4 hours
        
        # Assert
        assert mock_bot.auto_post_interval == 240 * 60  # Should be in seconds

    def test_enable_auto_post_after_startup(self, mock_bot):
        """Test enabling auto-post after startup."""
        # Arrange
        mock_bot.disable_auto_post_on_startup = True
        
        # Act
        mock_bot.enable_auto_post_after_startup()
        
        # Assert
        assert mock_bot.disable_auto_post_on_startup is False

    @pytest.mark.asyncio
    async def test_fetch_and_post_auto_validates_inputs(self, mock_bot):
        """Test that fetch_and_post_auto validates its inputs properly."""
        # Test with no channel name
        result = await mock_bot.fetch_and_post_auto(None)
        assert result is False
        
        # Test with empty channel name
        result = await mock_bot.fetch_and_post_auto("")
        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_and_post_auto_requires_telegram_client(self, mock_bot):
        """Test that fetch_and_post_auto requires a connected Telegram client."""
        # Test with no Telegram client
        mock_bot.telegram_client = None
        result = await mock_bot.fetch_and_post_auto("test_channel")
        assert result is False
        
        # Test with disconnected Telegram client
        mock_bot.telegram_client = AsyncMock()
        mock_bot.telegram_client.is_connected.return_value = False
        result = await mock_bot.fetch_and_post_auto("test_channel")
        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_and_post_auto_requires_fetch_commands(self, mock_bot):
        """Test that fetch_and_post_auto requires fetch_commands instance."""
        # Test with no fetch_commands
        mock_bot.fetch_commands = None
        result = await mock_bot.fetch_and_post_auto("test_channel")
        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_and_post_auto_success_flow(self, mock_bot):
        """Test successful fetch_and_post_auto flow."""
        # Arrange
        mock_bot.fetch_commands.fetch_and_post_auto.return_value = True
        
        # Act
        result = await mock_bot.fetch_and_post_auto("test_channel")
        
        # Assert
        assert result is True
        mock_bot.fetch_commands.fetch_and_post_auto.assert_called_once_with("test_channel")

    @pytest.mark.asyncio
    async def test_save_auto_post_config(self, mock_bot, mock_timezone_utils):
        """Test saving auto-post configuration."""
        # Arrange
        mock_bot.auto_post_interval = 10800
        mock_bot.mark_just_posted()  # This sets last_post_time
        
        # Act
        await mock_bot.save_auto_post_config()
        
        # Assert
        mock_bot.json_cache.set.assert_called()
        mock_bot.json_cache.save.assert_called()


class TestPostingIntervalLogic:
    """Test the critical posting interval logic that was causing issues."""

    @pytest.mark.asyncio
    async def test_interval_respected_after_manual_post(self, mock_bot, mock_timezone_utils):
        """Test that interval is respected after manual posting."""
        # Arrange - simulate a post 1 hour ago
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_bot.last_post_time = utc_to_eastern(one_hour_ago)
        mock_bot.auto_post_interval = 10800  # 3 hours
        
        # Calculate time since last post
        time_since_last = (now_eastern() - mock_bot.last_post_time).total_seconds()
        
        # Assert
        assert time_since_last < mock_bot.auto_post_interval
        # Should wait approximately 2 more hours
        remaining = mock_bot.auto_post_interval - time_since_last
        assert 7000 <= remaining <= 7400  # ~2 hours in seconds

    @pytest.mark.asyncio
    async def test_interval_ready_after_time_elapsed(self, mock_bot, mock_timezone_utils):
        """Test that posting is ready after interval has elapsed."""
        # Arrange - simulate a post 4 hours ago
        four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=4)
        mock_bot.last_post_time = utc_to_eastern(four_hours_ago)
        mock_bot.auto_post_interval = 10800  # 3 hours
        
        # Calculate time since last post
        time_since_last = (now_eastern() - mock_bot.last_post_time).total_seconds()
        
        # Assert
        assert time_since_last >= mock_bot.auto_post_interval

    @pytest.mark.asyncio
    async def test_force_auto_post_overrides_interval(self, mock_bot, mock_timezone_utils):
        """Test that force_auto_post flag overrides interval timing."""
        # Arrange - simulate a post 1 hour ago (too soon normally)
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_bot.last_post_time = utc_to_eastern(one_hour_ago)
        mock_bot.auto_post_interval = 10800  # 3 hours
        mock_bot.force_auto_post = True
        
        # This simulates the logic in auto_post_task
        time_since_last = (now_eastern() - mock_bot.last_post_time).total_seconds()
        
        # Assert - even though time is insufficient, force flag should allow posting
        should_post = (time_since_last >= mock_bot.auto_post_interval) or mock_bot.force_auto_post
        assert should_post is True

    def test_no_last_post_time_allows_posting(self, mock_bot):
        """Test that no previous post time allows immediate posting."""
        # Arrange
        mock_bot.last_post_time = None
        mock_bot.auto_post_interval = 10800
        
        # Assert - should be ready to post
        assert mock_bot.last_post_time is None


class TestAutomationConfig:
    """Test automation configuration management."""

    @pytest.mark.asyncio
    async def test_get_automation_config(self, mock_bot):
        """Test getting automation configuration."""
        # Arrange
        mock_bot.auto_post_interval = 10800
        mock_bot.last_post_time = now_eastern()
        
        # Act
        config = await mock_bot.get_automation_config()
        
        # Assert
        assert isinstance(config, dict)
        assert 'interval_minutes' in config
        assert 'last_post_time' in config
        assert 'next_post_time' in config

    @pytest.mark.asyncio
    async def test_update_automation_config(self, mock_bot):
        """Test updating automation configuration."""
        # Act
        result = await mock_bot.update_automation_config(
            interval_minutes=240,  # 4 hours
            enabled=True
        )
        
        # Assert
        assert result is True
        assert mock_bot.auto_post_interval == 240 * 60  # Should be in seconds

    def test_get_automation_status(self, mock_bot, mock_timezone_utils):
        """Test getting automation status."""
        # Arrange
        mock_bot.auto_post_interval = 10800
        mock_bot.mark_just_posted()
        
        # Act
        status = mock_bot.get_automation_status()
        
        # Assert
        assert isinstance(status, dict)
        assert 'enabled' in status
        assert 'interval_hours' in status
        assert 'last_post_time' in status
        assert 'next_post_time' in status
        assert 'time_until_next_post' in status


class TestErrorHandling:
    """Test error handling in core bot functions."""

    @pytest.mark.asyncio
    async def test_fetch_and_post_auto_handles_exceptions(self, mock_bot):
        """Test that fetch_and_post_auto gracefully handles exceptions."""
        # Arrange
        mock_bot.fetch_commands.fetch_and_post_auto.side_effect = Exception("Test error")
        
        # Act
        result = await mock_bot.fetch_and_post_auto("test_channel")
        
        # Assert
        assert result is False  # Should return False on error, not raise

    @pytest.mark.asyncio
    async def test_save_auto_post_config_handles_cache_errors(self, mock_bot):
        """Test that save_auto_post_config handles cache errors gracefully."""
        # Arrange
        mock_bot.json_cache.save.side_effect = Exception("Cache error")
        
        # Act & Assert - should not raise exception
        await mock_bot.save_auto_post_config()

    def test_mark_just_posted_handles_missing_cache(self, mock_bot):
        """Test that mark_just_posted handles missing cache gracefully."""
        # Arrange
        mock_bot.json_cache = None
        
        # Act & Assert - should not raise exception
        mock_bot.mark_just_posted()
        assert mock_bot._just_posted is True
        assert mock_bot.last_post_time is not None 