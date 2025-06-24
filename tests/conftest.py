# =============================================================================
# NewsBot Test Configuration & Fixtures
# =============================================================================
# Shared test fixtures and configuration for the NewsBot test suite.
# Provides mock objects and test data for comprehensive testing.

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import json

# Import our modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bot.newsbot import NewsBot
from src.cache.json_cache import JSONCache
from src.core.unified_config import UnifiedConfig


# =============================================================================
# Async Test Configuration
# =============================================================================
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Mock Configuration
# =============================================================================
@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        'bot': {
            'application_id': 123456789,
            'guild_id': 987654321,
            'admin_user_id': 111222333,
            'debug_mode': True,
            'version': '4.5.0'
        },
        'automation': {
            'enabled': True,
            'interval_minutes': 180,
            'startup_delay_minutes': 5,
            'require_media': True,
            'require_text': True,
            'min_content_length': 50
        },
        'channels': {
            'active': ['test_channel_1', 'test_channel_2'],
            'blacklisted_posts': [],
            'channel_metadata': {}
        }
    }


# =============================================================================
# Temporary Directory Fixtures
# =============================================================================
@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def temp_config_file(temp_dir, mock_config):
    """Create a temporary config file for testing."""
    config_file = temp_dir / "test_config.yaml"
    config_file.parent.mkdir(exist_ok=True)
    
    import yaml
    with open(config_file, 'w') as f:
        yaml.dump(mock_config, f)
    
    return config_file


# =============================================================================
# Bot Fixtures
# =============================================================================
@pytest.fixture
def mock_bot():
    """Create a mock NewsBot instance for testing."""
    # Create a mock bot that doesn't initialize the actual Discord client
    bot = MagicMock()
    
    # Mock essential attributes
    bot.user = MagicMock()
    bot.user.id = 123456789
    bot.latency = 0.05
    bot.startup_time = datetime.now(timezone.utc)
    bot.auto_post_interval = 10800  # 3 hours in seconds
    bot.last_post_time = None
    bot.force_auto_post = False
    bot.telegram_auth_failed = False
    bot.disable_auto_post_on_startup = True
    bot._just_posted = False
    bot.startup_grace_period_minutes = 5
    
    # Mock cache
    bot.json_cache = AsyncMock(spec=JSONCache)
    bot.json_cache.get.return_value = None
    bot.json_cache.set = AsyncMock()
    bot.json_cache.save = AsyncMock()
    bot.json_cache.get_next_channel_for_rotation = AsyncMock(return_value="test_channel")
    
    # Mock Telegram client
    bot.telegram_client = AsyncMock()
    bot.telegram_client.is_connected = AsyncMock(return_value=True)
    bot.telegram_client.get_messages = AsyncMock(return_value=[])
    
    # Mock fetch commands
    bot.fetch_commands = AsyncMock()
    bot.fetch_commands.fetch_and_post_auto = AsyncMock(return_value=True)
    bot.fetch_commands.auto_post_from_channel = AsyncMock(return_value=True)
    
    # Mock essential methods
    bot.mark_just_posted = MagicMock()
    bot.should_wait_for_startup_delay = MagicMock(return_value=(False, 0))
    bot.fetch_and_post_auto = AsyncMock(return_value=True)
    bot.save_auto_post_config = AsyncMock()
    bot.get_automation_config = AsyncMock(return_value={
        'interval_minutes': 180,
        'last_post_time': None,
        'next_post_time': None
    })
    bot.update_automation_config = AsyncMock(return_value=True)
    bot.get_automation_status = MagicMock(return_value={
        'enabled': True,
        'interval_hours': 3,
        'last_post_time': None,
        'next_post_time': None,
        'time_until_next_post': None
    })
    bot.set_auto_post_interval = MagicMock()
    bot.enable_auto_post_after_startup = MagicMock()
    bot.is_closed = MagicMock(return_value=False)
    
    # Mock services
    bot.ai_service = AsyncMock()
    bot.posting_service = AsyncMock()
    bot.posting_service.post_news_content = AsyncMock(return_value=True)
    
    # Mock manual verification delay
    bot._manual_verification_delay_until = {}
    
    return bot


@pytest.fixture
async def json_cache(temp_dir):
    """Create a real JSONCache instance for testing."""
    cache_file = temp_dir / "test_cache.json"
    cache = JSONCache(str(cache_file))
    await cache.initialize()
    yield cache


# =============================================================================
# Mock External Services
# =============================================================================
@pytest.fixture
def mock_telegram_client():
    """Mock Telegram client for testing."""
    client = AsyncMock()
    client.is_connected.return_value = True
    client.get_messages.return_value = [
        MagicMock(
            id=1,
            text="Test Arabic message للاختبار",
            media=None,
            date=datetime.now(timezone.utc)
        )
    ]
    return client


@pytest.fixture
def mock_ai_service():
    """Mock AI service for testing."""
    service = AsyncMock()
    service.process_text_with_ai.return_value = (
        "Test English translation for testing",
        "Test News Title",
        "Damascus"
    )
    return service


# =============================================================================
# Test Data Fixtures
# =============================================================================
@pytest.fixture
def sample_message():
    """Sample Telegram message for testing."""
    return MagicMock(
        id=12345,
        text="هذا اختبار للرسائل العربية في النظام الجديد للأخبار السورية",
        media=None,
        date=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_content_data():
    """Sample content data for testing posting."""
    return {
        "text": "هذا اختبار للرسائل العربية",
        "translation": "This is a test for Arabic messages",
        "title": "Test News Article",
        "location": "Damascus",
        "media_urls": [],
        "source_channel": "test_channel",
        "message_id": 12345
    }


# =============================================================================
# Time Fixtures
# =============================================================================
@pytest.fixture
def fixed_time():
    """Fixed time for consistent testing."""
    return datetime(2025, 1, 16, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_timezone_utils(fixed_time):
    """Mock timezone utilities with fixed time."""
    with patch('src.utils.timezone_utils.now_eastern') as mock_now:
        from src.utils.timezone_utils import utc_to_eastern
        mock_now.return_value = utc_to_eastern(fixed_time)
        yield mock_now 