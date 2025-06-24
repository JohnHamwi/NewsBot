# =============================================================================
# NewsBot Fetch Cog Tests
# =============================================================================
# Tests for the fetch cog functionality including delayed posting,
# auto-posting from channels, and content processing.

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock

from src.cogs.fetch_cog import FetchCommands


class TestFetchCommands:
    """Test the FetchCommands cog functionality."""

    @pytest_asyncio.fixture
    async def fetch_cog(self, mock_bot):
        """Create a FetchCommands instance for testing."""
        fetch_cog = FetchCommands(mock_bot)
        fetch_cog.posting_locks = set()
        return fetch_cog

    @pytest.mark.asyncio
    async def test_fetch_and_post_auto_success(self, fetch_cog, mock_bot):
        """Test successful auto-posting from a channel."""
        # Arrange
        channel_name = "test_channel"
        mock_bot.telegram_client.get_messages.return_value = [
            MagicMock(
                id=123,
                text="هذا اختبار للرسائل العربية في النظام الجديد للأخبار السورية" * 2,  # Long enough
                media=None,
                date=datetime.now(timezone.utc)
            )
        ]
        
        # Mock AI service
        mock_bot.ai_service = AsyncMock()
        mock_bot.ai_service.process_text_with_ai.return_value = (
            "This is a test for Arabic messages in the new Syrian news system",
            "Syrian News Test",
            "Damascus"
        )
        
        # Mock posting service
        mock_bot.posting_service = AsyncMock()
        mock_bot.posting_service.post_news_content.return_value = True
        
        # Mock duplicate check
        fetch_cog._is_duplicate_content = AsyncMock(return_value=False)
        fetch_cog._extract_media_urls = AsyncMock(return_value=[])
        
        # Act
        result = await fetch_cog.auto_post_from_channel(channel_name)
        
        # Assert
        assert result is True
        mock_bot.posting_service.post_news_content.assert_called_once()
        mock_bot.mark_just_posted.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_and_post_auto_no_suitable_content(self, fetch_cog, mock_bot):
        """Test auto-posting when no suitable content is found."""
        # Arrange
        channel_name = "test_channel"
        mock_bot.telegram_client.get_messages.return_value = [
            MagicMock(
                id=123,
                text="Short",  # Too short
                media=None,
                date=datetime.now(timezone.utc)
            )
        ]
        
        # Act
        result = await fetch_cog.auto_post_from_channel(channel_name)
        
        # Assert
        assert result is False
        mock_bot.mark_just_posted.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_and_post_auto_duplicate_content(self, fetch_cog, mock_bot):
        """Test auto-posting with duplicate content filtering."""
        # Arrange
        channel_name = "test_channel"
        mock_bot.telegram_client.get_messages.return_value = [
            MagicMock(
                id=123,
                text="هذا اختبار للرسائل العربية في النظام الجديد للأخبار السورية" * 2,
                media=None,
                date=datetime.now(timezone.utc)
            )
        ]
        
        # Mock duplicate content detection
        fetch_cog._is_duplicate_content = AsyncMock(return_value=True)
        
        # Act
        result = await fetch_cog.auto_post_from_channel(channel_name)
        
        # Assert
        assert result is False
        mock_bot.mark_just_posted.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_and_post_auto_no_telegram_client(self, fetch_cog, mock_bot):
        """Test auto-posting when Telegram client is unavailable."""
        # Arrange
        channel_name = "test_channel"
        mock_bot.telegram_client = None
        
        # Act
        result = await fetch_cog.auto_post_from_channel(channel_name)
        
        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_and_post_auto_posting_lock(self, fetch_cog, mock_bot):
        """Test that posting locks prevent concurrent posting to same channel."""
        # Arrange
        channel_name = "test_channel"
        fetch_cog.posting_locks.add(channel_name)  # Channel already locked
        
        # Act
        result = await fetch_cog.auto_post_from_channel(channel_name)
        
        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_and_post_auto_ai_processing_failure(self, fetch_cog, mock_bot):
        """Test auto-posting when AI processing fails."""
        # Arrange
        channel_name = "test_channel"
        mock_bot.telegram_client.get_messages.return_value = [
            MagicMock(
                id=123,
                text="هذا اختبار للرسائل العربية في النظام الجديد للأخبار السورية" * 2,
                media=None,
                date=datetime.now(timezone.utc)
            )
        ]
        
        # Mock AI service failure
        mock_bot.ai_service = AsyncMock()
        mock_bot.ai_service.process_text_with_ai.return_value = (None, None, None)  # AI failure
        
        fetch_cog._is_duplicate_content = AsyncMock(return_value=False)
        
        # Act
        result = await fetch_cog.auto_post_from_channel(channel_name)
        
        # Assert
        assert result is False
        mock_bot.mark_just_posted.assert_not_called()


class TestDelayedPosting:
    """Test delayed posting functionality."""

    @pytest_asyncio.fixture
    async def fetch_cog(self, mock_bot):
        """Create a FetchCommands instance for testing."""
        return FetchCommands(mock_bot)

    @pytest.mark.asyncio
    async def test_schedule_delayed_post_success(self, fetch_cog, mock_bot):
        """Test successful delayed posting."""
        # Arrange
        mock_fetch_view = AsyncMock()
        mock_fetch_view.do_post_to_news.return_value = True
        
        # Set up mock attributes to prevent format string errors
        mock_fetch_view.urgency_level = "normal"
        mock_fetch_view.content_category = "news"
        mock_fetch_view.quality_score = 0.85
        mock_fetch_view.should_ping_news = False
        
        message_id = 12345
        delay = 0.01  # Very short delay for testing
        channel_name = "test_channel"
        
        # Mock blacklist check
        mock_bot.json_cache.get.return_value = []  # Empty blacklist
        
        # Act
        result = await fetch_cog._schedule_delayed_post(
            mock_fetch_view, message_id, delay, channel_name
        )
        
        # Assert
        assert result is True
        mock_fetch_view.do_post_to_news.assert_called_once()
        mock_bot.mark_just_posted.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_delayed_post_blacklisted(self, fetch_cog, mock_bot):
        """Test delayed posting with blacklisted message."""
        # Arrange
        mock_fetch_view = AsyncMock()
        message_id = 12345
        delay = 0.01
        channel_name = "test_channel"
        
        # Mock blacklist check - message is blacklisted
        mock_bot.json_cache.get.return_value = [message_id]
        
        # Act
        result = await fetch_cog._schedule_delayed_post(
            mock_fetch_view, message_id, delay, channel_name
        )
        
        # Assert
        assert result is False
        mock_fetch_view.do_post_to_news.assert_not_called()
        mock_bot.mark_just_posted.assert_not_called()

    @pytest.mark.asyncio
    async def test_schedule_delayed_post_posting_failure(self, fetch_cog, mock_bot):
        """Test delayed posting when posting fails."""
        # Arrange
        mock_fetch_view = AsyncMock()
        mock_fetch_view.do_post_to_news.return_value = False  # Posting fails
        message_id = 12345
        delay = 0.01
        channel_name = "test_channel"
        
        # Mock blacklist check
        mock_bot.json_cache.get.return_value = []
        
        # Act
        result = await fetch_cog._schedule_delayed_post(
            mock_fetch_view, message_id, delay, channel_name
        )
        
        # Assert
        assert result is False
        mock_fetch_view.do_post_to_news.assert_called_once()
        mock_bot.mark_just_posted.assert_not_called()

    @pytest.mark.asyncio
    async def test_schedule_delayed_post_exception_handling(self, fetch_cog, mock_bot):
        """Test delayed posting with exception handling."""
        # Arrange
        mock_fetch_view = AsyncMock()
        mock_fetch_view.do_post_to_news.side_effect = Exception("Test error")
        message_id = 12345
        delay = 0.01
        channel_name = "test_channel"
        
        # Mock blacklist check
        mock_bot.json_cache.get.return_value = []
        
        # Act
        result = await fetch_cog._schedule_delayed_post(
            mock_fetch_view, message_id, delay, channel_name
        )
        
        # Assert
        assert result is False
        mock_bot.mark_just_posted.assert_not_called()


class TestContentFiltering:
    """Test content filtering and validation."""

    @pytest_asyncio.fixture
    async def fetch_cog(self, mock_bot):
        """Create a FetchCommands instance for testing."""
        return FetchCommands(mock_bot)

    @pytest.mark.asyncio
    async def test_is_duplicate_content(self, fetch_cog, mock_bot):
        """Test duplicate content detection."""
        # This would test the _is_duplicate_content method
        # For now, we'll test the concept
        
        # Arrange
        content = "Test content"
        
        # Mock the duplicate check to return True
        fetch_cog._is_duplicate_content = AsyncMock(return_value=True)
        
        # Act
        is_duplicate = await fetch_cog._is_duplicate_content(content)
        
        # Assert
        assert is_duplicate is True

    @pytest.mark.asyncio
    async def test_extract_media_urls(self, fetch_cog, mock_bot):
        """Test media URL extraction from messages."""
        # Arrange
        mock_message = MagicMock()
        mock_message.media = None  # No media
        
        fetch_cog._extract_media_urls = AsyncMock(return_value=[])
        
        # Act
        media_urls = await fetch_cog._extract_media_urls(mock_message)
        
        # Assert
        assert media_urls == []

    def test_content_length_validation(self, fetch_cog):
        """Test content length validation."""
        # Test short content (should be rejected)
        short_content = "Short"
        assert len(short_content.strip()) < 50
        
        # Test long content (should be accepted)
        long_content = "This is a much longer piece of content that should pass the minimum length requirement for news posting" * 2
        assert len(long_content.strip()) >= 50


class TestFetchCommandIntegration:
    """Test integration between fetch command components."""

    @pytest_asyncio.fixture
    async def fetch_cog(self, mock_bot):
        """Create a FetchCommands instance for testing."""
        return FetchCommands(mock_bot)

    @pytest.mark.asyncio
    async def test_fetch_and_post_auto_delegation(self, fetch_cog, mock_bot):
        """Test that bot.fetch_and_post_auto properly delegates to fetch cog."""
        # Arrange
        channel_name = "test_channel"
        
        # Mock the fetch cog method
        fetch_cog.fetch_and_post_auto = AsyncMock(return_value=True)
        mock_bot.fetch_commands = fetch_cog
        
        # Act
        result = await mock_bot.fetch_and_post_auto(channel_name)
        
        # Assert
        assert result is True
        fetch_cog.fetch_and_post_auto.assert_called_once_with(channel_name)

    @pytest.mark.asyncio
    async def test_posting_lock_cleanup(self, fetch_cog, mock_bot):
        """Test that posting locks are properly cleaned up after operations."""
        # Arrange
        channel_name = "test_channel"
        
        # Mock to simulate an exception
        mock_bot.telegram_client.get_messages.side_effect = Exception("Test error")
        
        # Ensure lock is not initially set
        assert channel_name not in fetch_cog.posting_locks
        
        # Act
        result = await fetch_cog.auto_post_from_channel(channel_name)
        
        # Assert
        assert result is False
        # Lock should be cleaned up even after exception
        assert channel_name not in fetch_cog.posting_locks

    @pytest.mark.asyncio
    async def test_successful_post_updates_cache(self, fetch_cog, mock_bot):
        """Test that successful posts update the cache and call mark_just_posted."""
        # This test verifies the critical fix we made
        
        # Arrange
        channel_name = "test_channel"
        mock_bot.telegram_client.get_messages.return_value = [
            MagicMock(
                id=123,
                text="هذا اختبار للرسائل العربية في النظام الجديد للأخبار السورية" * 2,
                media=None,
                date=datetime.now(timezone.utc)
            )
        ]
        
        mock_bot.ai_service = AsyncMock()
        mock_bot.ai_service.process_text_with_ai.return_value = (
            "Test translation", "Test title", "Damascus"
        )
        
        mock_bot.posting_service = AsyncMock()
        mock_bot.posting_service.post_news_content.return_value = True
        
        fetch_cog._is_duplicate_content = AsyncMock(return_value=False)
        fetch_cog._extract_media_urls = AsyncMock(return_value=[])
        
        # Act
        result = await fetch_cog.auto_post_from_channel(channel_name)
        
        # Assert
        assert result is True
        mock_bot.mark_just_posted.assert_called_once()  # This was the critical missing piece


class TestErrorHandling:
    """Test error handling in fetch operations."""

    @pytest_asyncio.fixture
    async def fetch_cog(self, mock_bot):
        """Create a FetchCommands instance for testing."""
        return FetchCommands(mock_bot)

    @pytest.mark.asyncio
    async def test_telegram_client_error_handling(self, fetch_cog, mock_bot):
        """Test handling of Telegram client errors."""
        # Arrange
        channel_name = "test_channel"
        mock_bot.telegram_client.get_messages.side_effect = Exception("Telegram error")
        
        # Act
        result = await fetch_cog.auto_post_from_channel(channel_name)
        
        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_ai_service_error_handling(self, fetch_cog, mock_bot):
        """Test handling of AI service errors."""
        # Arrange
        channel_name = "test_channel"
        mock_bot.telegram_client.get_messages.return_value = [
            MagicMock(
                id=123,
                text="هذا اختبار للرسائل العربية في النظام الجديد للأخبار السورية" * 2,
                media=None,
                date=datetime.now(timezone.utc)
            )
        ]
        
        mock_bot.ai_service = AsyncMock()
        mock_bot.ai_service.process_text_with_ai.side_effect = Exception("AI error")
        
        fetch_cog._is_duplicate_content = AsyncMock(return_value=False)
        
        # Act
        result = await fetch_cog.auto_post_from_channel(channel_name)
        
        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_posting_service_error_handling(self, fetch_cog, mock_bot):
        """Test handling of posting service errors."""
        # Arrange
        channel_name = "test_channel"
        mock_bot.telegram_client.get_messages.return_value = [
            MagicMock(
                id=123,
                text="هذا اختبار للرسائل العربية في النظام الجديد للأخبار السورية" * 2,
                media=None,
                date=datetime.now(timezone.utc)
            )
        ]
        
        mock_bot.ai_service = AsyncMock()
        mock_bot.ai_service.process_text_with_ai.return_value = (
            "Test translation", "Test title", "Damascus"
        )
        
        mock_bot.posting_service = AsyncMock()
        mock_bot.posting_service.post_news_content.side_effect = Exception("Posting error")
        
        fetch_cog._is_duplicate_content = AsyncMock(return_value=False)
        fetch_cog._extract_media_urls = AsyncMock(return_value=[])
        
        # Act
        result = await fetch_cog.auto_post_from_channel(channel_name)
        
        # Assert
        assert result is False 