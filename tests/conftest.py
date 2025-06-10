"""
Pytest configuration and shared fixtures.
"""

import pytest
import discord
from discord.ext import commands
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.config_manager import config
import os
import sys
import logging

class MockBot(commands.Bot):
    """Mock bot class for testing."""
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        self.news_channel = AsyncMock(spec=discord.TextChannel)
        self.errors_channel = AsyncMock(spec=discord.TextChannel)
        self.log_channel = AsyncMock(spec=discord.TextChannel)
        self.json_cache = MagicMock()
        self.metrics = MagicMock()
        self.rbac = MagicMock()
        self.telegram_client = AsyncMock()
        self.debug_mode = False

@pytest.fixture
def mock_config():
    """Provide a mock configuration."""
    return {
        'bot': {
            'version': '1.5.0',
            'guild_id': '123456789',
            'application_id': '987654321',
            'debug_mode': False
        },
        'channels': {
            'news': '111111111',
            'errors': '222222222',
            'logs': '333333333'
        },
        'tokens': {
            'discord': 'mock_token',
            'telegram': {
                'api_id': 'mock_api_id',
                'api_hash': 'mock_api_hash'
            }
        }
    }

@pytest.fixture
async def bot():
    """Provide a mock bot instance."""
    return MockBot()

@pytest.fixture
async def mock_interaction():
    """Provide a mock Discord interaction."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.channel = AsyncMock(spec=discord.TextChannel)
    interaction.user = AsyncMock(spec=discord.Member)
    return interaction

@pytest.fixture
def mock_guild():
    """Provide a mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = int(config.get('bot.guild_id', '123456789'))
    return guild

@pytest.fixture
def mock_member():
    """Provide a mock Discord member."""
    member = MagicMock(spec=discord.Member)
    member.guild_permissions = discord.Permissions(administrator=True)
    return member

@pytest.fixture
def mock_message():
    """Provide a mock Discord message."""
    message = AsyncMock(spec=discord.Message)
    message.channel = AsyncMock(spec=discord.TextChannel)
    return message

class BaseCogTest:
    """Base class for testing cogs."""
    
    @pytest.fixture
    async def cog(self, bot):
        """Should be overridden by specific cog test classes."""
        raise NotImplementedError("Cog fixture must be implemented by subclass")
    
    @pytest.fixture
    def mock_config(self):
        """Override with specific config for your cog if needed."""
        return {}
    
    @pytest.fixture(autouse=True)
    def setup_mocks(self, mock_config):
        """Setup basic mocks that most cogs will need."""
        with patch('src.core.config_manager.ConfigManager._config', mock_config):
            yield 

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Set up the test environment with mock environment variables.
    This fixture runs automatically for all tests.
    """
    # Save original environment variables
    original_env = os.environ.copy()
    
    # Set mock environment variables for testing
    os.environ["TELEGRAM_API_ID"] = "12345"
    os.environ["TELEGRAM_API_HASH"] = "mock_hash_for_testing"
    os.environ["ADMIN_USER_ID"] = "123456789"
    os.environ["DISCORD_TOKEN"] = "mock_discord_token"
    
    # Mock config values
    mock_config = {
        'telegram.api_id': 12345,
        'telegram.api_hash': 'mock_hash_for_testing',
        'bot.admin_role_id': 123456789,
        'tokens.discord': 'mock_discord_token',
        'bot.guild_id': 987654321,
        'channels.news': 111111,
        'channels.errors': 222222,
        'channels.logs': 333333,
        'bot.admin_role_id': 444444,
        'bot.application_id': 'mock_app_id',
        'bot.news_role_id': 555555,
    }
    
    # Apply patching to prevent actual API connections
    with patch('telethon.TelegramClient.__init__', return_value=None), \
         patch('telethon.TelegramClient.start', return_value=None), \
         patch('telethon.TelegramClient.connect', return_value=None), \
         patch('src.core.config_manager.ConfigManager.get', side_effect=lambda key, default=None: mock_config.get(key, default)):
        
        yield
    
    # Restore original environment variables after all tests
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture
def mock_fetch_cog_init():
    """
    Patch FetchCog initialization to avoid real API calls and use mocked values.
    """
    # Save the original __init__ method
    original_init = None
    
    try:
        # Import the FetchCog class
        from src.cogs.fetch_cog import FetchCog
        original_init = FetchCog.__init__
        
        # Create a new init method that sets required attributes
        def mock_init(self, bot):
            self.bot = bot
            self.news_role_id = 555555
            
            # Add any other required attributes
            from src.utils.base_logger import base_logger
            self.logger = base_logger
            
            # Initialize necessary attributes used in tests
            self.telegram_client = bot.telegram_client if hasattr(bot, 'telegram_client') else None
            
            # Create a mock RBAC system that always allows access
            from unittest.mock import MagicMock
            self.bot.rbac = MagicMock()
            self.bot.rbac.has_permission = MagicMock(return_value=True)
            
            # Create error_handler attribute
            from src.utils import error_handler
            self.error_handler = error_handler
        
        # Apply the mock
        FetchCog.__init__ = mock_init
        yield
    finally:
        # Restore the original method if it was saved
        if original_init:
            from src.cogs.fetch_cog import FetchCog
            FetchCog.__init__ = original_init 

@pytest.fixture(autouse=True)
def patch_error_handler():
    """
    Patch the error handler to prevent issues with main.py's patched version.
    """
    from unittest.mock import patch
    
    # Create a simple error handler function that doesn't try to use attributes from MagicMock objects
    async def mock_send_error_embed(error_title, error, context=None, user=None, channel=None, bot=None):
        logging.debug(f"Mock error handler called: {error_title} - {error}")
        return None
    
    # Patch only the send_error_embed function
    with patch('src.utils.error_handler.send_error_embed', mock_send_error_embed):
        yield 