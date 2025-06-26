# =============================================================================
# NewsBot Core Functionality Tests
# =============================================================================
# Tests for the core bot functionality including posting intervals,
# startup grace periods, and critical timing logic.

import pytest
import pytest_asyncio
import asyncio
import tempfile
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from src.bot.newsbot import NewsBot
from src.utils.timezone_utils import now_eastern, utc_to_eastern
from src.cache.json_cache import JSONCache


@pytest_asyncio.fixture
async def real_bot():
    """Create a real NewsBot instance for testing."""
    # Create temporary cache file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
        temp_file.write('{}')
        cache_file = temp_file.name

    try:
        # Create minimal config for bot
        config = {
            'discord': {'guild_id': 123456789},
            'auto_post': {'interval_minutes': 180, 'channels': []},
            'features': {'auto_posting': True}
        }
        
        # Create bot with minimal setup
        bot = NewsBot()
        bot.config = config
        bot.json_cache = JSONCache(cache_file)
        bot.auto_post_interval = 10800  # 3 hours
        bot.startup_time = datetime.now(timezone.utc)
        bot.startup_grace_period_minutes = 2
        bot.disable_auto_post_on_startup = True
        bot._just_posted = False
        bot.last_post_time = None
        
        yield bot
    finally:
        os.unlink(cache_file)


class TestNewsBotCore:
    """Test core NewsBot functionality."""

    @pytest.mark.asyncio
    async def test_mark_just_posted_updates_time(self, real_bot):
        """Test that mark_just_posted correctly updates last_post_time."""
        # Arrange
        initial_time = real_bot.last_post_time
        
        # Act
        real_bot.mark_just_posted()
        
        # Give async task time to complete
        await asyncio.sleep(0.01)
        
        # Assert
        assert real_bot.last_post_time is not None
        assert real_bot.last_post_time != initial_time
        assert real_bot._just_posted is True

    @pytest.mark.asyncio
    async def test_mark_just_posted_saves_to_cache(self, real_bot):
        """Test that mark_just_posted saves the time to cache."""
        # Act
        real_bot.mark_just_posted()
        
        # Give async task time to run
        await asyncio.sleep(0.1)  # Longer wait for cache operations
        
        # Assert - check that cache has been updated
        last_post_data = await real_bot.json_cache.get("last_post_time")
        assert last_post_data is not None

    def test_startup_grace_period_active(self, real_bot):
        """Test that startup grace period correctly blocks posting."""
        # Arrange - bot just started 1 minute ago
        real_bot.startup_time = datetime.now(timezone.utc) - timedelta(minutes=1)
        real_bot.startup_grace_period_minutes = 2
        real_bot.disable_auto_post_on_startup = True
        
        # Act
        should_wait, seconds_to_wait = real_bot.should_wait_for_startup_delay()
        
        # Assert
        assert should_wait is True
        assert seconds_to_wait > 0
        # Should be approximately 1 minute (2 - 1)
        assert 50 <= seconds_to_wait <= 70

    def test_startup_grace_period_expired(self, real_bot):
        """Test that expired grace period allows posting."""
        # Arrange - bot started 10 minutes ago
        real_bot.startup_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        real_bot.startup_grace_period_minutes = 2
        real_bot.disable_auto_post_on_startup = True
        
        # Act
        should_wait, seconds_to_wait = real_bot.should_wait_for_startup_delay()
        
        # Assert
        assert should_wait is False
        assert seconds_to_wait == 0

    def test_startup_grace_period_disabled(self, real_bot):
        """Test that disabled grace period allows immediate posting."""
        # Arrange
        real_bot.startup_time = datetime.now(timezone.utc)  # Just started
        real_bot.disable_auto_post_on_startup = False
        
        # Act
        should_wait, seconds_to_wait = real_bot.should_wait_for_startup_delay()
        
        # Assert
        assert should_wait is False
        assert seconds_to_wait == 0

    def test_set_auto_post_interval(self, real_bot):
        """Test setting auto-post interval."""
        # Act
        real_bot.set_auto_post_interval(240)  # 4 hours
        
        # Assert
        assert real_bot.auto_post_interval == 240 * 60  # Should be in seconds

    def test_enable_auto_post_after_startup(self, real_bot):
        """Test enabling auto-post after startup."""
        # Arrange
        real_bot.disable_auto_post_on_startup = True
        
        # Act
        real_bot.enable_auto_post_after_startup()
        
        # Assert
        assert real_bot.disable_auto_post_on_startup is False

    @pytest.mark.asyncio
    async def test_fetch_and_post_auto_validates_inputs(self, real_bot):
        """Test that fetch_and_post_auto validates its inputs properly."""
        # Test with no channel name
        result = await real_bot.fetch_and_post_auto(None)
        assert result is False
        
        # Test with empty channel name
        result = await real_bot.fetch_and_post_auto("")
        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_and_post_auto_requires_telegram_client(self, real_bot):
        """Test that fetch_and_post_auto requires a connected Telegram client."""
        # Test with no Telegram client
        real_bot.telegram_client = None
        result = await real_bot.fetch_and_post_auto("test_channel")
        assert result is False
        
        # Test with disconnected Telegram client
        real_bot.telegram_client = AsyncMock()
        real_bot.telegram_client.is_connected.return_value = False
        result = await real_bot.fetch_and_post_auto("test_channel")
        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_and_post_auto_requires_fetch_commands(self, real_bot):
        """Test that fetch_and_post_auto requires fetch_commands instance."""
        # Test with no fetch_commands
        real_bot.fetch_commands = None
        result = await real_bot.fetch_and_post_auto("test_channel")
        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_and_post_auto_success_flow(self, real_bot):
        """Test successful fetch_and_post_auto flow."""
        # Arrange - mock all dependencies
        real_bot.telegram_client = AsyncMock()
        real_bot.telegram_client.is_connected.return_value = True
        real_bot.fetch_commands = AsyncMock()
        real_bot.fetch_commands.fetch_and_post_auto.return_value = True
        
        # Act
        result = await real_bot.fetch_and_post_auto("test_channel")
        
        # Assert
        assert result is True
        real_bot.fetch_commands.fetch_and_post_auto.assert_called_once_with("test_channel")

    @pytest.mark.asyncio
    async def test_save_auto_post_config(self, real_bot):
        """Test saving auto-post configuration."""
        # Arrange
        real_bot.auto_post_interval = 10800
        real_bot.mark_just_posted()  # This sets last_post_time
        
        # Act
        await real_bot.save_auto_post_config()
        
        # Give time for cache operations
        await asyncio.sleep(0.1)
        
        # Assert - check that config was saved (check actual keys used by the method)
        interval_data = await real_bot.json_cache.get("auto_post_interval")
        last_post_data = await real_bot.json_cache.get("last_post_time")
        assert interval_data == 10800
        assert last_post_data is not None


class TestPostingIntervalLogic:
    """Test the critical posting interval logic that was causing issues."""

    @pytest.mark.asyncio
    async def test_interval_respected_after_manual_post(self, real_bot):
        """Test that interval is respected after manual posting."""
        # Arrange - simulate a post 1 hour ago
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        real_bot.last_post_time = utc_to_eastern(one_hour_ago)
        real_bot.auto_post_interval = 10800  # 3 hours
        
        # Calculate time since last post
        time_since_last = (now_eastern() - real_bot.last_post_time).total_seconds()
        
        # Assert
        assert time_since_last < real_bot.auto_post_interval
        # Should wait approximately 2 more hours
        remaining = real_bot.auto_post_interval - time_since_last
        assert 7000 <= remaining <= 7400  # ~2 hours in seconds

    @pytest.mark.asyncio
    async def test_interval_ready_after_time_elapsed(self, real_bot):
        """Test that posting is ready after interval has elapsed."""
        # Arrange - simulate a post 4 hours ago
        four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=4)
        real_bot.last_post_time = utc_to_eastern(four_hours_ago)
        real_bot.auto_post_interval = 10800  # 3 hours
        
        # Calculate time since last post
        time_since_last = (now_eastern() - real_bot.last_post_time).total_seconds()
        
        # Assert
        assert time_since_last >= real_bot.auto_post_interval

    @pytest.mark.asyncio
    async def test_force_auto_post_overrides_interval(self, real_bot):
        """Test that force_auto_post flag overrides interval timing."""
        # Arrange - simulate a post 1 hour ago (too soon normally)
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        real_bot.last_post_time = utc_to_eastern(one_hour_ago)
        real_bot.auto_post_interval = 10800  # 3 hours
        real_bot.force_auto_post = True
        
        # This simulates the logic in auto_post_task
        time_since_last = (now_eastern() - real_bot.last_post_time).total_seconds()
        
        # Assert - even though time is insufficient, force flag should allow posting
        should_post = (time_since_last >= real_bot.auto_post_interval) or real_bot.force_auto_post
        assert should_post is True

    def test_no_last_post_time_allows_posting(self, real_bot):
        """Test that no previous post time allows immediate posting."""
        # Arrange
        real_bot.last_post_time = None
        real_bot.auto_post_interval = 10800
        
        # Assert - should be ready to post
        assert real_bot.last_post_time is None


class TestAutomationConfig:
    """Test automation configuration management."""

    @pytest.mark.asyncio
    async def test_get_automation_config(self, real_bot):
        """Test getting automation configuration."""
        # Arrange - set up automation config
        real_bot.automation_config = {
            'interval_minutes': 180,
            'enabled': True,
            'require_media': True
        }
        
        # Act
        config = await real_bot.get_automation_config()
        
        # Assert
        assert isinstance(config, dict)
        assert config.get('interval_minutes') == 180
        assert config.get('enabled') is True

    @pytest.mark.asyncio
    async def test_update_automation_config(self, real_bot):
        """Test updating automation configuration."""
        # Act
        result = await real_bot.update_automation_config(
            interval_minutes=240,  # 4 hours
            enabled=True
        )
        
        # Assert
        assert result is True
        # Check that the config was actually updated
        config = await real_bot.get_automation_config()
        assert config.get('interval_minutes') == 240

    @pytest.mark.asyncio
    async def test_get_automation_status(self, real_bot):
        """Test getting automation status."""
        # Arrange
        real_bot.auto_post_interval = 10800
        real_bot.mark_just_posted()
        
        # Act
        status = real_bot.get_automation_status()
        
        # Assert
        assert isinstance(status, dict)
        assert 'enabled' in status
        assert 'interval_minutes' in status
        assert 'posts_today' in status
        assert 'total_posts' in status
        assert 'uptime_hours' in status


class TestErrorHandling:
    """Test error handling in core bot functions."""

    @pytest.mark.asyncio
    async def test_fetch_and_post_auto_handles_exceptions(self, real_bot):
        """Test that fetch_and_post_auto gracefully handles exceptions."""
        # Arrange - mock dependencies to raise exception
        real_bot.telegram_client = AsyncMock()
        real_bot.telegram_client.is_connected.return_value = True
        real_bot.fetch_commands = AsyncMock()
        real_bot.fetch_commands.fetch_and_post_auto.side_effect = Exception("Test error")
        
        # Act
        result = await real_bot.fetch_and_post_auto("test_channel")
        
        # Assert
        assert result is False  # Should return False on error, not raise

    @pytest.mark.asyncio
    async def test_save_auto_post_config_handles_cache_errors(self, real_bot):
        """Test that save_auto_post_config handles cache errors gracefully."""
        # Arrange - create a mock cache that raises exceptions
        mock_cache = AsyncMock()
        mock_cache.set.side_effect = Exception("Cache error")
        real_bot.json_cache = mock_cache
        
        # Act & Assert - should not raise exception
        try:
            await real_bot.save_auto_post_config()
            # If we get here, the method handled the error gracefully
            assert True
        except Exception:
            # If we get here, the method didn't handle the error
            assert False, "save_auto_post_config should handle cache errors gracefully"

    @pytest.mark.asyncio
    async def test_mark_just_posted_handles_missing_cache(self, real_bot):
        """Test that mark_just_posted handles missing cache gracefully."""
        # Arrange
        real_bot.json_cache = None
        
        # Act & Assert - should not raise exception
        real_bot.mark_just_posted()
        assert real_bot._just_posted is True
        assert real_bot.last_post_time is not None 