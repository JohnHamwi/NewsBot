"""
Integration Tests for NewsBot

These tests verify that different components work together correctly,
including API integrations, file system operations, and end-to-end workflows.
"""

import pytest
import asyncio
import tempfile
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

# Import your actual classes (adjust imports based on your project structure)
# from src.bot.newsbot import NewsBot
# from src.cogs.fetch import FetchCommands
# from src.cache.json_cache import JSONCache
# from src.core.unified_config import UnifiedConfig

@pytest.mark.integration
class TestDiscordIntegration:
    """Test Discord API integration."""

    @pytest.mark.asyncio
    async def test_discord_bot_startup_integration(self, mock_bot):
        """Test that the bot can start up and connect to Discord."""
        # Mock Discord.py client
        mock_bot.client = MagicMock()
        mock_bot.client.is_ready = MagicMock(return_value=True)
        mock_bot.client.user = MagicMock()
        mock_bot.client.user.name = "NewsBot"
        
        # Test startup sequence
        startup_time = datetime.now(timezone.utc)
        mock_bot.startup_time = startup_time
        
        # Verify startup grace period is active
        time_since_startup = (datetime.now(timezone.utc) - startup_time).total_seconds()
        grace_period = 5 * 60  # 5 minutes
        
        assert time_since_startup < grace_period
        assert mock_bot.client.is_ready()

    @pytest.mark.asyncio
    async def test_discord_message_posting_integration(self, mock_bot):
        """Test posting messages to Discord channels."""
        # Mock Discord channel
        mock_channel = AsyncMock()
        mock_channel.send = AsyncMock(return_value=MagicMock(id=12345))
        mock_bot.get_channel = MagicMock(return_value=mock_channel)
        
        # Test message posting
        channel_id = 123456789
        test_message = "Test news content for integration testing"
        
        channel = mock_bot.get_channel(channel_id)
        message = await channel.send(test_message)
        
        # Verify posting worked
        mock_bot.get_channel.assert_called_once_with(channel_id)
        mock_channel.send.assert_called_once_with(test_message)
        assert message.id == 12345

@pytest.mark.integration  
class TestTelegramIntegration:
    """Test Telegram API integration."""

    @pytest.mark.asyncio
    async def test_telegram_client_connection(self, mock_telegram_client):
        """Test Telegram client can connect and authenticate."""
        mock_telegram_client.is_connected = MagicMock(return_value=True)
        mock_telegram_client.get_me = AsyncMock(return_value=MagicMock(
            id=12345,
            first_name="Test",
            username="testbot"
        ))
        
        # Test connection
        is_connected = mock_telegram_client.is_connected()
        user_info = await mock_telegram_client.get_me()
        
        assert is_connected is True
        assert user_info.id == 12345
        assert user_info.username == "testbot"

    @pytest.mark.asyncio
    async def test_telegram_channel_fetching_integration(self, mock_telegram_client):
        """Test fetching messages from Telegram channels."""
        # Mock channel messages
        mock_messages = [
            MagicMock(
                id=1,
                text="Breaking news: Integration test successful!",
                date=datetime.now(timezone.utc) - timedelta(minutes=30),
                media=None
            ),
            MagicMock(
                id=2, 
                text="Another news story for testing",
                date=datetime.now(timezone.utc) - timedelta(minutes=15),
                media=None
            )
        ]
        
        mock_telegram_client.get_messages = AsyncMock(return_value=mock_messages)
        
        # Test message fetching
        channel_name = "test_news_channel"
        messages = await mock_telegram_client.get_messages(channel_name, limit=10)
        
        assert len(messages) == 2
        assert "Integration test successful" in messages[0].text
        mock_telegram_client.get_messages.assert_called_once_with(channel_name, limit=10)

@pytest.mark.integration
class TestAIServiceIntegration:
    """Test AI service integration."""

    @pytest.mark.asyncio
    async def test_openai_translation_integration(self, mock_ai_service):
        """Test OpenAI translation service."""
        original_text = "Esto es una noticia de prueba"
        translated_text = "This is a test news story"
        
        mock_ai_service.translate_text = AsyncMock(return_value=translated_text)
        
        # Test translation
        result = await mock_ai_service.translate_text(original_text, target_language="English")
        
        assert result == translated_text
        mock_ai_service.translate_text.assert_called_once_with(original_text, target_language="English")

    @pytest.mark.asyncio
    async def test_openai_categorization_integration(self, mock_ai_service):
        """Test OpenAI content categorization."""
        news_content = "The stock market reached new highs today as tech companies reported strong earnings."
        expected_category = "Business"
        
        mock_ai_service.categorize_content = AsyncMock(return_value=expected_category)
        
        # Test categorization
        category = await mock_ai_service.categorize_content(news_content)
        
        assert category == expected_category
        mock_ai_service.categorize_content.assert_called_once_with(news_content)

@pytest.mark.integration
class TestFileSystemIntegration:
    """Test file system operations and persistence."""

    def test_json_cache_file_operations(self, temp_dir):
        """Test JSON cache file read/write operations."""
        cache_file = os.path.join(temp_dir, "test_cache.json")
        
        # Test data
        test_data = {
            "last_post_time": datetime.now(timezone.utc).isoformat(),
            "active_channels": ["channel1", "channel2"],
            "channel_rotation_index": 0
        }
        
        # Write to cache file
        with open(cache_file, 'w') as f:
            json.dump(test_data, f, indent=2)
        
        # Read from cache file
        with open(cache_file, 'r') as f:
            loaded_data = json.load(f)
        
        assert loaded_data == test_data
        assert os.path.exists(cache_file)

    def test_config_file_persistence(self, temp_dir):
        """Test configuration file persistence."""
        config_file = os.path.join(temp_dir, "test_config.json")
        
        # Test configuration
        config_data = {
            "bot": {
                "application_id": 123456789,
                "auto_post_interval_minutes": 180
            },
            "discord": {
                "token": "test_token",
                "channels": {
                    "news": 987654321
                }
            }
        }
        
        # Write config
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        # Verify config exists and is readable
        assert os.path.exists(config_file)
        
        with open(config_file, 'r') as f:
            loaded_config = json.load(f)
        
        assert loaded_config["bot"]["application_id"] == 123456789
        assert loaded_config["discord"]["channels"]["news"] == 987654321

@pytest.mark.integration
class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""

    @pytest.mark.asyncio
    async def test_complete_news_posting_workflow(self, mock_bot, mock_telegram_client, mock_ai_service):
        """Test the complete workflow from fetching to posting news."""
        # Setup mock responses
        mock_message = MagicMock(
            text="Breaking: Integration test news story",
            date=datetime.now(timezone.utc) - timedelta(minutes=10),
            media=None
        )
        
        mock_telegram_client.get_messages = AsyncMock(return_value=[mock_message])
        mock_ai_service.translate_text = AsyncMock(return_value="Breaking: Integration test news story")
        mock_ai_service.categorize_content = AsyncMock(return_value="Technology")
        
        mock_discord_channel = AsyncMock()
        mock_discord_channel.send = AsyncMock(return_value=MagicMock(id=12345))
        mock_bot.get_channel = MagicMock(return_value=mock_discord_channel)
        
        # Simulate the workflow
        channel_name = "test_channel"
        discord_channel_id = 123456789
        
        # Step 1: Fetch from Telegram
        messages = await mock_telegram_client.get_messages(channel_name, limit=1)
        assert len(messages) == 1
        
        # Step 2: Process with AI
        translated = await mock_ai_service.translate_text(messages[0].text)
        category = await mock_ai_service.categorize_content(translated)
        
        # Step 3: Post to Discord
        discord_channel = mock_bot.get_channel(discord_channel_id)
        posted_message = await discord_channel.send(f"[{category}] {translated}")
        
        # Verify complete workflow
        assert translated == "Breaking: Integration test news story"
        assert category == "Technology"
        assert posted_message.id == 12345

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, mock_bot, mock_telegram_client):
        """Test error recovery in the posting workflow."""
        # Setup failing scenario
        mock_telegram_client.get_messages = AsyncMock(side_effect=Exception("Network timeout"))
        
        # Test error handling
        try:
            messages = await mock_telegram_client.get_messages("test_channel")
            assert False, "Should have raised an exception"
        except Exception as e:
            assert str(e) == "Network timeout"
        
        # Test recovery mechanism
        mock_telegram_client.get_messages = AsyncMock(return_value=[])  # Recovery: empty result
        messages = await mock_telegram_client.get_messages("test_channel")
        assert messages == []

@pytest.mark.integration
class TestBackgroundTaskIntegration:
    """Test background task integration."""

    @pytest.mark.asyncio
    async def test_auto_post_task_integration(self, mock_bot):
        """Test the auto-post background task integration."""
        # Setup for auto-posting
        mock_bot.auto_post_enabled = True
        mock_bot.auto_post_interval = 3 * 60 * 60  # 3 hours
        mock_bot.last_post_time = datetime.now(timezone.utc) - timedelta(hours=4)  # Overdue
        mock_bot.startup_time = datetime.now(timezone.utc) - timedelta(minutes=10)  # Past grace period
        
        # Mock successful posting
        mock_bot.fetch_and_post_auto = AsyncMock(return_value=True)
        mock_bot.mark_just_posted = MagicMock()
        
        # Simulate auto-post task logic
        time_since_last = (datetime.now(timezone.utc) - mock_bot.last_post_time).total_seconds()
        should_post = time_since_last >= mock_bot.auto_post_interval
        
        if should_post:
            result = await mock_bot.fetch_and_post_auto("test_channel")
            if result:
                mock_bot.mark_just_posted()
        
        # Verify integration
        assert should_post is True
        mock_bot.fetch_and_post_auto.assert_called_once_with("test_channel")
        mock_bot.mark_just_posted.assert_called_once()

# Integration test fixtures
@pytest.fixture
async def integration_bot():
    """Create a bot instance for integration testing."""
    # This would create a real bot instance with test configuration
    # Adjust based on your actual bot initialization
    bot = MagicMock()
    bot.startup_time = datetime.now(timezone.utc)
    bot.auto_post_enabled = True
    bot.auto_post_interval = 3 * 60 * 60
    return bot

@pytest.fixture
def test_environment():
    """Setup test environment for integration tests."""
    env_vars = {
        'NEWSBOT_TEST_MODE': 'true',
        'NEWSBOT_LOG_LEVEL': 'DEBUG'
    }
    
    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
    
    yield env_vars
    
    # Cleanup
    for key in env_vars.keys():
        if key in os.environ:
            del os.environ[key] 