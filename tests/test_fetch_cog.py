"""
Test suite for the FetchCog.
"""

import io
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import discord
import pytest

from src.cogs.fetch_cog import FetchCog
from src.utils import error_handler


# Mock Config
class MockConfig:
    GUILD_ID = 123456789
    ADMIN_USER_ID = 123456789
    DEBUG_MODE = False
    NEWS_ROLE_ID = 987654321


# Mock config module
def mock_config_get(key):
    if key == "bot.news_role_id":
        return 987654321
    return None


# Mock error handler
error_handler.send_error_embed = AsyncMock()


# Mock AI utils
def mock_call_chatgpt_for_news(*args, **kwargs):
    return {
        "title": "Test Title",
        "english": "Test English Translation",
        "is_ad": False,
        "is_not_syria": False,
    }


# Mock ad detection
def mock_call_chatgpt_for_news_ad(*args, **kwargs):
    return {
        "title": "Test Ad Title",
        "english": "Test Ad Translation",
        "is_ad": True,
        "is_not_syria": False,
    }


# Mock non-Syria content detection
def mock_call_chatgpt_for_news_not_syria(*args, **kwargs):
    return {
        "title": "Test Non-Syria Title",
        "english": "Test Non-Syria Translation",
        "is_ad": False,
        "is_not_syria": True,
    }


# Mock FetchView
class MockFetchView:
    def __init__(self, *args, **kwargs):
        pass

    async def do_post_to_news(self, interaction):
        return True


# Mock tempfile.NamedTemporaryFile
class MockNamedTemporaryFile:
    def __init__(self, delete=True, suffix=None):
        self.name = f"mock_temp_file{suffix}"
        self.delete = delete

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def write(self, data):
        pass


@pytest.fixture(autouse=True)
def mock_admin_user_id():
    with patch("src.cogs.fetch_cog.ADMIN_USER_ID", MockConfig.ADMIN_USER_ID):
        yield


@pytest.fixture(autouse=True)
def mock_fetch_view():
    with patch("src.cogs.fetch_cog.FetchView", MockFetchView):
        yield


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.telegram_client = MagicMock()
    bot.news_channel = MagicMock()
    bot.errors_channel = MagicMock()
    bot.log_channel = MagicMock()
    bot.json_cache = AsyncMock()
    bot.json_cache.get.return_value = []
    bot.json_cache.set = AsyncMock()
    bot.json_cache.list_telegram_channels = AsyncMock(
        return_value=["test_channel", "syria_news", "damascus_updates"]
    )

    # Make send methods coroutine-compatible
    bot.news_channel.send = AsyncMock()
    bot.errors_channel.send = AsyncMock()
    bot.log_channel.send = AsyncMock()

    # Mock datetime for error handler
    bot.last_error_ping_time = datetime.now()

    return bot


@pytest.fixture
def mock_message():
    message = MagicMock()
    message.text = "Test message with enough content to pass validation"
    message.date = datetime.now()

    # Create a proper media structure
    media = MagicMock()
    media.photo = True

    # Create a document with mime_type for video detection
    document = MagicMock()
    document.mime_type = "image/jpeg"
    media.document = document

    message.media = media
    message.id = 12345
    return message


@pytest.fixture
def mock_interaction():
    interaction = AsyncMock(spec=discord.Interaction)

    # Mock response methods
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.response.is_done = AsyncMock(return_value=False)
    interaction.followup.send = AsyncMock()

    # Mock user and channel
    interaction.user = MagicMock(spec=discord.User)
    interaction.user.id = MockConfig.ADMIN_USER_ID  # Use MockConfig
    interaction.channel = MagicMock(spec=discord.TextChannel)
    interaction.channel.id = 987654321

    # Mock message
    interaction.message = MagicMock()
    interaction.message.embeds = [MagicMock()]

    # Mock created_at timestamp
    interaction.created_at = datetime.now()

    return interaction


@pytest.fixture
def mock_unauthorized_interaction():
    interaction = AsyncMock(spec=discord.Interaction)

    # Mock response methods
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.response.is_done = AsyncMock(return_value=False)
    interaction.followup.send = AsyncMock()

    # Mock user and channel with unauthorized ID
    interaction.user = MagicMock(spec=discord.User)
    interaction.user.id = 111222333  # Different from ADMIN_USER_ID
    interaction.channel = MagicMock(spec=discord.TextChannel)
    interaction.channel.id = 987654321

    # Mock message
    interaction.message = MagicMock()
    interaction.message.embeds = [MagicMock()]

    return interaction


@pytest.mark.asyncio
async def test_autocomplete_activated_channels(mock_bot, mock_interaction):
    """Test the autocomplete_activated_channels method."""
    # Setup
    cog = FetchCog(mock_bot)

    # Execute
    choices = await cog.autocomplete_activated_channels(mock_interaction, "test")

    # Assert
    assert len(choices) == 1
    assert choices[0].name == "@test_channel"
    assert choices[0].value == "test_channel"
    mock_bot.json_cache.list_telegram_channels.assert_called_once_with("activated")


@pytest.mark.asyncio
async def test_autocomplete_activated_channels_exception(mock_bot, mock_interaction):
    """Test the autocomplete_activated_channels method with an exception."""
    # Setup
    mock_bot.json_cache.list_telegram_channels.side_effect = Exception("Test error")
    cog = FetchCog(mock_bot)

    # Execute
    choices = await cog.autocomplete_activated_channels(mock_interaction, "test")

    # Assert
    assert len(choices) == 0
    mock_bot.json_cache.list_telegram_channels.assert_called_once_with("activated")


@pytest.mark.asyncio
async def test_fetch_command_unauthorized(mock_unauthorized_interaction):
    """Test fetch command with unauthorized user."""
    # Setup
    with (
        patch("src.cogs.fetch_cog.Config", MockConfig),
        patch("src.core.config_manager.config.get", side_effect=mock_config_get),
        patch(
            "src.cogs.ai_utils.call_chatgpt_for_news",
            side_effect=mock_call_chatgpt_for_news,
        ),
    ):

        mock_bot = MagicMock()
        mock_bot.log_channel = MagicMock()

        cog = FetchCog(mock_bot)
        channel_name = "test_channel"

        # Execute
        await cog.fetch.callback(cog, mock_unauthorized_interaction, channel_name)

        # Assert
        mock_unauthorized_interaction.response.send_message.assert_called_once_with(
            "You are not authorized to use this command."
        )
        error_handler.send_error_embed.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_command_no_channel(mock_bot, mock_interaction):
    """Test fetch command with no channel specified."""
    # Setup
    with (
        patch("src.cogs.fetch_cog.Config", MockConfig),
        patch("src.core.config_manager.config.get", side_effect=mock_config_get),
        patch(
            "src.cogs.ai_utils.call_chatgpt_for_news",
            side_effect=mock_call_chatgpt_for_news,
        ),
    ):

        cog = FetchCog(mock_bot)
        channel_name = ""  # Empty channel name

        # Execute
        await cog.fetch.callback(cog, mock_interaction, channel_name)

        # Assert
        mock_interaction.response.send_message.assert_called_once_with(
            "You must select a channel."
        )


@pytest.mark.asyncio
async def test_fetch_command_invalid_number(mock_bot, mock_interaction):
    """Test fetch command with invalid number parameter."""
    # Setup
    with (
        patch("src.cogs.fetch_cog.Config", MockConfig),
        patch("src.core.config_manager.config.get", side_effect=mock_config_get),
        patch(
            "src.cogs.ai_utils.call_chatgpt_for_news",
            side_effect=mock_call_chatgpt_for_news,
        ),
    ):

        cog = FetchCog(mock_bot)
        channel_name = "test_channel"
        number = 20  # Greater than maximum allowed (10)

        # Execute
        await cog.fetch.callback(cog, mock_interaction, channel_name, number)

        # Assert
        mock_interaction.response.send_message.assert_called_once_with(
            "Number must be between 1 and 10."
        )


@pytest.mark.asyncio
async def test_fetch_command_success(mock_bot, mock_message, mock_interaction):
    """Test successful execution of fetch command."""
    # Setup
    with (
        patch("src.cogs.fetch_cog.Config", MockConfig),
        patch("src.core.config_manager.config.get", side_effect=mock_config_get),
        patch(
            "src.cogs.ai_utils.call_chatgpt_for_news",
            side_effect=mock_call_chatgpt_for_news,
        ),
    ):

        # Mock iter_messages to return a list with our message
        async def mock_iter_messages(*args, **kwargs):
            yield mock_message

        mock_bot.telegram_client.iter_messages = mock_iter_messages
        mock_bot.telegram_client.download_media = AsyncMock(return_value=b"test_bytes")

        cog = FetchCog(mock_bot)
        channel_name = "test_channel"

        # Execute
        await cog.fetch.callback(cog, mock_interaction, channel_name)

        # Assert
        mock_interaction.response.defer.assert_called_once()
        mock_interaction.followup.send.assert_called()


@pytest.mark.asyncio
async def test_fetch_command_no_messages(mock_bot, mock_interaction):
    """Test fetch command when no messages are found."""
    # Setup
    with (
        patch("src.cogs.fetch_cog.Config", MockConfig),
        patch("src.core.config_manager.config.get", side_effect=mock_config_get),
        patch(
            "src.cogs.ai_utils.call_chatgpt_for_news",
            side_effect=mock_call_chatgpt_for_news,
        ),
    ):

        # Mock iter_messages to return an empty list
        async def mock_iter_messages(*args, **kwargs):
            # This is an empty async generator
            if False:
                yield None

        mock_bot.telegram_client.iter_messages = mock_iter_messages

        cog = FetchCog(mock_bot)
        channel_name = "test_channel"

        # Execute
        await cog.fetch.callback(cog, mock_interaction, channel_name)

        # Assert
        mock_interaction.response.defer.assert_called_once()
        mock_interaction.followup.send.assert_called_with(
            "No valid posts found (with both media and text). Try again later."
        )


@pytest.mark.asyncio
async def test_fetch_command_error(mock_bot, mock_interaction):
    """Test fetch command error handling."""
    # Setup
    with (
        patch("src.cogs.fetch_cog.Config", MockConfig),
        patch("src.core.config_manager.config.get", side_effect=mock_config_get),
        patch(
            "src.cogs.ai_utils.call_chatgpt_for_news",
            side_effect=mock_call_chatgpt_for_news,
        ),
    ):

        # Use a different approach to mock the exception
        mock_bot.telegram_client.iter_messages = MagicMock()
        mock_bot.telegram_client.iter_messages.side_effect = Exception("Test error")

        cog = FetchCog(mock_bot)
        channel_name = "test_channel"

        # Execute
        await cog.fetch.callback(cog, mock_interaction, channel_name)

        # Assert
        mock_interaction.response.defer.assert_called_once()
        # Accept any error message that contains our error text
        assert any(
            "Test error" in str(args[0])
            for args, _ in mock_interaction.followup.send.call_args_list
        )


@pytest.mark.asyncio
async def test_auto_post_success(mock_bot, mock_message):
    """Test successful auto-posting."""
    # Setup
    with (
        patch("src.cogs.fetch_cog.Config", MockConfig),
        patch("src.core.config_manager.config.get", side_effect=mock_config_get),
        patch(
            "src.cogs.ai_utils.call_chatgpt_for_news",
            side_effect=mock_call_chatgpt_for_news,
        ),
    ):

        # Configure the proper mock for auto_post test
        mock_temp_file_context = MagicMock()
        mock_temp_file = MagicMock()
        mock_temp_file.name = "test_temp_file.jpg"
        mock_temp_file_context.__enter__.return_value = mock_temp_file

        # Set up the message
        mock_message.media.photo = True

        # Mock iter_messages with proper async generator
        async def mock_iter_messages(*args, **kwargs):
            yield mock_message

        # Prepare tempfile and file operations mocks
        mock_open_context = MagicMock()
        mock_file = MagicMock()
        mock_file.read.return_value = b"test_bytes"
        mock_open_context.__enter__.return_value = mock_file

        # Create a context where all patching happens at once
        with (
            patch("tempfile.NamedTemporaryFile", return_value=mock_temp_file_context),
            patch("builtins.open", return_value=mock_open_context),
            patch("os.remove"),
            patch("src.cogs.fetch_cog.FetchView", autospec=True) as MockFetchViewClass,
            patch(
                "src.cogs.fetch_cog.FetchView.do_post_to_news",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):

            # Configure the FetchView mock to return from do_post_to_news correctly
            view_instance = MockFetchViewClass.return_value
            view_instance.do_post_to_news = AsyncMock(return_value=True)

            # Set up the bot's telegram client methods
            mock_bot.telegram_client.iter_messages = mock_iter_messages
            mock_bot.telegram_client.download_media = AsyncMock(return_value=True)

            cog = FetchCog(mock_bot)
            channel_name = "test_channel"

            # Execute
            result = await cog.fetch_and_post_auto(channel_name)

            # Assert
            assert result is True


@pytest.mark.asyncio
async def test_auto_post_no_messages(mock_bot):
    """Test auto-posting when no messages are found."""
    # Setup
    with (
        patch("src.cogs.fetch_cog.Config", MockConfig),
        patch("src.core.config_manager.config.get", side_effect=mock_config_get),
        patch(
            "src.cogs.ai_utils.call_chatgpt_for_news",
            side_effect=mock_call_chatgpt_for_news,
        ),
    ):

        # Mock iter_messages to return an empty list
        async def mock_iter_messages(*args, **kwargs):
            # This is an empty async generator
            if False:
                yield None

        mock_bot.telegram_client.iter_messages = mock_iter_messages

        cog = FetchCog(mock_bot)
        channel_name = "test_channel"

        # Execute
        result = await cog.fetch_and_post_auto(channel_name)

        # Assert
        assert result is False
        mock_bot.news_channel.send.assert_not_called()


@pytest.mark.asyncio
async def test_auto_post_error(mock_bot):
    """Test auto-posting error handling."""
    # Setup
    with (
        patch("src.cogs.fetch_cog.Config", MockConfig),
        patch("src.core.config_manager.config.get", side_effect=mock_config_get),
        patch(
            "src.cogs.ai_utils.call_chatgpt_for_news",
            side_effect=mock_call_chatgpt_for_news,
        ),
    ):

        # Use a different approach to mock the exception
        mock_bot.telegram_client.iter_messages = MagicMock()
        mock_bot.telegram_client.iter_messages.side_effect = Exception("Test error")

        cog = FetchCog(mock_bot)
        channel_name = "test_channel"

        # Execute
        result = await cog.fetch_and_post_auto(channel_name)

        # Assert
        assert result is False


@pytest.mark.asyncio
async def test_clear_blacklist(mock_bot, mock_interaction):
    """Test clear_blacklist command."""
    # Setup
    with (
        patch("src.cogs.fetch_cog.Config", MockConfig),
        patch("src.core.config_manager.config.get", side_effect=mock_config_get),
    ):

        cog = FetchCog(mock_bot)

        # Execute
        await cog.clear_blacklist(mock_interaction)

        # Assert
        mock_bot.json_cache.set.assert_called_once_with("blacklisted_posts", [])
        mock_interaction.response.send_message.assert_called_once()
        # Check that the embed has the right title
        embed = mock_interaction.response.send_message.call_args[1]["embed"]
        assert embed.title == "🗑️ Blacklist Cleared"


@pytest.mark.asyncio
async def test_clear_blacklist_unauthorized(mock_bot, mock_unauthorized_interaction):
    """Test clear_blacklist command with unauthorized user."""
    # Setup
    with (
        patch("src.cogs.fetch_cog.Config", MockConfig),
        patch("src.core.config_manager.config.get", side_effect=mock_config_get),
    ):

        cog = FetchCog(mock_bot)

        # Execute
        await cog.clear_blacklist(mock_unauthorized_interaction)

        # Assert
        mock_unauthorized_interaction.response.send_message.assert_called_once_with(
            "You are not authorized to use this command.", ephemeral=True
        )
        mock_bot.json_cache.set.assert_not_called()
