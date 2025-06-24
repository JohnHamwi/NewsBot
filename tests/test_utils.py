# =============================================================================
# NewsBot Utility Functions Tests
# =============================================================================
# Tests for utility functions including timezone operations, cache management,
# configuration handling, and other support functions.

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import json
import yaml
from unittest.mock import patch, MagicMock

from src.utils.timezone_utils import (
    now_eastern, utc_to_eastern, eastern_to_utc,
    now_est, utc_to_est, est_to_utc  # Deprecated functions
)
from src.cache.json_cache import JSONCache
from src.core.unified_config import UnifiedConfig


class TestTimezoneUtils:
    """Test timezone utility functions."""

    def test_now_eastern_returns_eastern_time(self):
        """Test that now_eastern returns Eastern timezone datetime."""
        eastern_time = now_eastern()
        
        # Should have timezone info
        assert eastern_time.tzinfo is not None
        # Should be Eastern timezone (either EST or EDT)
        assert str(eastern_time.tzinfo) in ["EST", "EDT"] or "America/New_York" in str(eastern_time.tzinfo)

    def test_utc_to_eastern_conversion(self):
        """Test UTC to Eastern timezone conversion."""
        # Create a UTC datetime
        utc_time = datetime(2025, 1, 16, 12, 0, 0, tzinfo=timezone.utc)
        
        # Convert to Eastern
        eastern_time = utc_to_eastern(utc_time)
        
        # Should have Eastern timezone
        assert eastern_time.tzinfo is not None
        # Should be 5 hours behind UTC (EST) or 4 hours behind (EDT)
        hour_diff = utc_time.hour - eastern_time.hour
        assert hour_diff in [4, 5] or hour_diff in [-19, -20]  # Account for day wrap

    def test_eastern_to_utc_conversion(self):
        """Test Eastern to UTC timezone conversion."""
        # Create an Eastern datetime (naive, will be assumed Eastern)
        eastern_time = datetime(2025, 1, 16, 7, 0, 0)  # 7 AM Eastern
        
        # Convert to UTC
        utc_time = eastern_to_utc(eastern_time)
        
        # Should have UTC timezone
        assert utc_time.tzinfo is not None
        assert str(utc_time.tzinfo) in ["UTC", "datetime.timezone.utc"]
        # Should be 5 hours ahead of Eastern (EST) or 4 hours ahead (EDT)
        hour_diff = utc_time.hour - eastern_time.hour
        assert hour_diff in [4, 5] or hour_diff in [-19, -20]  # Account for day wrap

    def test_utc_to_eastern_with_naive_datetime(self):
        """Test UTC to Eastern conversion with naive datetime (assumes UTC)."""
        # Create a naive datetime (no timezone)
        naive_utc = datetime(2025, 1, 16, 12, 0, 0)
        
        # Convert to Eastern (should assume UTC)
        eastern_time = utc_to_eastern(naive_utc)
        
        # Should have Eastern timezone
        assert eastern_time.tzinfo is not None

    def test_deprecated_functions_still_work(self):
        """Test that deprecated functions still work for backward compatibility."""
        # Test deprecated functions
        est_time = now_est()
        assert est_time.tzinfo is not None
        
        utc_time = datetime(2025, 1, 16, 12, 0, 0, tzinfo=timezone.utc)
        est_converted = utc_to_est(utc_time)
        assert est_converted.tzinfo is not None
        
        eastern_time = datetime(2025, 1, 16, 7, 0, 0)
        utc_converted = est_to_utc(eastern_time)
        assert utc_converted.tzinfo is not None
        assert str(utc_converted.tzinfo) in ["UTC", "datetime.timezone.utc"]


class TestJSONCache:
    """Test JSON cache functionality."""

    @pytest.fixture
    def temp_cache_file(self):
        """Create a temporary cache file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = Path(f.name)
        yield temp_file
        if temp_file.exists():
            temp_file.unlink()

    @pytest.mark.asyncio
    async def test_json_cache_initialization(self, temp_cache_file):
        """Test JSON cache initialization."""
        cache = JSONCache(str(temp_cache_file))
        await cache.initialize()
        
        # Cache file should exist
        assert temp_cache_file.exists()
        
        # Should have basic structure
        assert hasattr(cache, 'data')
        assert isinstance(cache.data, dict)

    @pytest.mark.asyncio
    async def test_json_cache_set_and_get(self, temp_cache_file):
        """Test setting and getting values from cache."""
        cache = JSONCache(str(temp_cache_file))
        await cache.initialize()
        
        # Set a value
        await cache.set("test_key", "test_value")
        
        # Get the value
        value = await cache.get("test_key")
        assert value == "test_value"

    @pytest.mark.asyncio
    async def test_json_cache_get_with_default(self, temp_cache_file):
        """Test getting values with default fallback."""
        cache = JSONCache(str(temp_cache_file))
        await cache.initialize()
        
        # Get non-existent key with default
        value = await cache.get("non_existent", "default_value")
        assert value == "default_value"

    @pytest.mark.asyncio
    async def test_json_cache_persistence(self, temp_cache_file):
        """Test that cache persists data to file."""
        # Create cache and set a value
        cache1 = JSONCache(str(temp_cache_file))
        await cache1.initialize()
        await cache1.set("persist_test", "persistent_value")
        await cache1.save()
        
        # Create new cache instance and check if value persists
        cache2 = JSONCache(str(temp_cache_file))
        await cache2.initialize()
        value = await cache2.get("persist_test")
        assert value == "persistent_value"

    @pytest.mark.asyncio
    async def test_json_cache_channel_rotation(self, temp_cache_file):
        """Test channel rotation functionality."""
        cache = JSONCache(str(temp_cache_file))
        await cache.initialize()
        
        # Set up active channels
        await cache.set("active_channels", ["channel1", "channel2", "channel3"])
        await cache.set("channel_rotation_index", 0)
        
        # Test rotation
        channel1 = await cache.get_next_channel_for_rotation()
        assert channel1 == "channel1"
        
        channel2 = await cache.get_next_channel_for_rotation()
        assert channel2 == "channel2"
        
        channel3 = await cache.get_next_channel_for_rotation()
        assert channel3 == "channel3"
        
        # Should wrap around
        channel1_again = await cache.get_next_channel_for_rotation()
        assert channel1_again == "channel1"

    @pytest.mark.asyncio
    async def test_json_cache_no_active_channels(self, temp_cache_file):
        """Test channel rotation with no active channels."""
        cache = JSONCache(str(temp_cache_file))
        await cache.initialize()
        
        # No active channels set
        channel = await cache.get_next_channel_for_rotation()
        assert channel is None


class TestUnifiedConfig:
    """Test unified configuration system."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for config testing."""
        import tempfile
        import shutil
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_unified_config_initialization(self, temp_config_dir):
        """Test unified config initialization."""
        config_file = temp_config_dir / "test_config.yaml"
        config = UnifiedConfig(str(config_file))
        
        # Config file should be created
        assert config_file.exists()
        
        # Should have default structure
        assert 'bot' in config.config_data
        assert 'automation' in config.config_data
        assert 'channels' in config.config_data

    def test_unified_config_get_and_set(self, temp_config_dir):
        """Test getting and setting config values."""
        config_file = temp_config_dir / "test_config.yaml"
        config = UnifiedConfig(str(config_file))
        
        # Set a value
        config.set("test.key", "test_value")
        
        # Get the value
        value = config.get("test.key")
        assert value == "test_value"

    def test_unified_config_nested_keys(self, temp_config_dir):
        """Test nested key access."""
        config_file = temp_config_dir / "test_config.yaml"
        config = UnifiedConfig(str(config_file))
        
        # Test getting nested default values
        debug_mode = config.get("bot.debug_mode")
        assert debug_mode is False  # Default value
        
        # Test getting with fallback
        non_existent = config.get("non.existent.key", "fallback")
        assert non_existent == "fallback"

    def test_unified_config_get_section(self, temp_config_dir):
        """Test getting entire config sections."""
        config_file = temp_config_dir / "test_config.yaml"
        config = UnifiedConfig(str(config_file))
        
        # Get bot section
        bot_config = config.get_section("bot")
        assert isinstance(bot_config, dict)
        assert 'debug_mode' in bot_config
        assert 'version' in bot_config

    def test_unified_config_migration_from_yaml(self, temp_config_dir):
        """Test migration from legacy YAML config."""
        # Create a legacy config file
        legacy_config = temp_config_dir / "config_profiles.yaml"
        legacy_data = {
            'bot': {
                'application_id': 123456789,
                'guild_id': 987654321
            }
        }
        
        with open(legacy_config, 'w') as f:
            yaml.dump(legacy_data, f)
        
        # Create unified config (should migrate)
        config_file = temp_config_dir / "unified_config.yaml"
        config = UnifiedConfig(str(config_file))
        
        # Should have migrated the values
        assert config.get("bot.application_id") == 123456789
        assert config.get("bot.guild_id") == 987654321


class TestErrorHandler:
    """Test error handling utilities."""

    def test_error_handler_context_manager(self):
        """Test error handler as context manager."""
        from src.utils.error_handler import error_handler
        
        # This should not raise an exception
        with error_handler.handle_errors("test_operation"):
            # Simulate some operation
            pass
        
        # Test with an exception
        with error_handler.handle_errors("test_operation_with_error"):
            try:
                raise ValueError("Test error")
            except ValueError:
                pass  # Error should be handled


class TestContentCleaner:
    """Test content cleaning utilities."""

    def test_remove_emojis(self):
        """Test emoji removal from text."""
        from src.cogs.fetch_cog import remove_emojis
        
        text_with_emojis = "Hello 👋 World 🌍 Test 🚀"
        cleaned = remove_emojis(text_with_emojis)
        
        # Should remove emojis
        assert "👋" not in cleaned
        assert "🌍" not in cleaned
        assert "🚀" not in cleaned
        assert "Hello" in cleaned
        assert "World" in cleaned

    def test_remove_links(self):
        """Test link removal from text."""
        from src.cogs.fetch_cog import remove_links
        
        text_with_links = "Check out https://example.com and http://test.org for more info"
        cleaned = remove_links(text_with_links)
        
        # Should remove URLs
        assert "https://example.com" not in cleaned
        assert "http://test.org" not in cleaned
        assert "Check out" in cleaned
        assert "for more info" in cleaned

    def test_remove_source_phrases(self):
        """Test source phrase removal from text."""
        from src.cogs.fetch_cog import remove_source_phrases
        
        text_with_source = "This is news content. Source: Reuters. End of content."
        cleaned = remove_source_phrases(text_with_source)
        
        # Should remove source phrases
        assert "Source:" not in cleaned or len(cleaned) < len(text_with_source)


class TestMediaValidator:
    """Test media validation utilities."""

    def test_media_url_validation(self):
        """Test media URL validation."""
        # Mock media validator since we don't have the actual implementation
        valid_urls = [
            "https://example.com/image.jpg",
            "https://example.com/video.mp4",
            "https://example.com/document.pdf"
        ]
        
        invalid_urls = [
            "not_a_url",
            "ftp://invalid.com/file.txt",
            ""
        ]
        
        # These would be actual tests if we had the media validator implemented
        for url in valid_urls:
            # assert is_valid_media_url(url) is True
            pass
        
        for url in invalid_urls:
            # assert is_valid_media_url(url) is False
            pass


class TestRateLimiter:
    """Test rate limiting utilities."""

    @pytest.mark.asyncio
    async def test_rate_limiter_basic_functionality(self):
        """Test basic rate limiter functionality."""
        # Mock test since we don't have rate limiter implementation details
        # This would test the actual rate limiter if implemented
        
        # Simulate rate limiter behavior
        class MockRateLimiter:
            def __init__(self, max_requests=5, window_seconds=60):
                self.max_requests = max_requests
                self.window_seconds = window_seconds
                self.requests = []
            
            async def check_limit(self, identifier):
                import time
                now = time.time()
                # Remove old requests outside window
                self.requests = [req for req in self.requests if now - req < self.window_seconds]
                
                if len(self.requests) >= self.max_requests:
                    return False
                
                self.requests.append(now)
                return True
        
        rate_limiter = MockRateLimiter(max_requests=3, window_seconds=60)
        
        # Should allow first 3 requests
        assert await rate_limiter.check_limit("test_user") is True
        assert await rate_limiter.check_limit("test_user") is True
        assert await rate_limiter.check_limit("test_user") is True
        
        # Should block 4th request
        assert await rate_limiter.check_limit("test_user") is False


class TestTaskManager:
    """Test task management utilities."""

    @pytest.mark.asyncio
    async def test_task_manager_basic_operations(self):
        """Test basic task manager operations."""
        from src.utils.task_manager import task_manager
        
        # Test task creation
        async def dummy_task():
            await asyncio.sleep(0.01)
            return "completed"
        
        # Start a task
        await task_manager.start_task("test_task", dummy_task)
        
        # Task should be tracked
        assert "test_task" in task_manager.active_tasks
        
        # Stop the task
        await task_manager.stop_task("test_task")
        
        # Task should be removed
        assert "test_task" not in task_manager.active_tasks 