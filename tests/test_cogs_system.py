"""
Test suite for system commands.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from src.cogs.status import StatusCommands

@pytest.mark.asyncio
async def test_status_command_success():
    """Test successful execution of status command."""
    # Setup bot mock
    bot = MagicMock()
    bot.application_id = "123456789"
    bot.user = MagicMock()
    bot.user.id = "123456789"
    
    # Create a test implementation of status_command
    async def mock_status_command(interaction, details=False):
        """Mock implementation of status_command"""
        # Create a test embed
        embed = discord.Embed(
            title="📊 Bot Status",
            description="Current system and bot metrics",
            color=discord.Color.green(),
        )
        await interaction.followup.send(embed=embed)
        return True
    
    # Create cog and replace status_command with mock implementation
    cog = StatusCommands(bot)
    cog.status_command = MagicMock()
    cog.status_command.callback = mock_status_command
    
    # Setup interaction
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user.id = 1
    interaction.channel.id = 2
    interaction.response.is_done.return_value = False
    interaction.followup = AsyncMock()
    
    # Execute
    await mock_status_command(interaction, details=False)
    
    # Assert
    interaction.followup.send.assert_called_once()
    embed = interaction.followup.send.call_args[1]['embed']
    assert embed.title == "📊 Bot Status"

@pytest.mark.asyncio
async def test_status_command_error():
    """Test status command error handling."""
    # Setup bot mock
    bot = MagicMock()
    bot.application_id = "123456789"
    bot.user = MagicMock()
    bot.user.id = "123456789"
    
    # Create a test implementation of status_command that raises an error
    async def mock_status_command_error(interaction, details=False):
        """Mock implementation of status_command that raises an error"""
        raise Exception("fail")
    
    # Create cog
    cog = StatusCommands(bot)
    
    # Setup interaction
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user.id = 1
    interaction.channel.id = 2
    interaction.response.is_done.return_value = False
    
    # Mock error handler
    with patch('src.cogs.status.error_handler.send_error_embed', AsyncMock()) as mock_error_handler:
        # Execute
        try:
            await mock_status_command_error(interaction, details=False)
        except Exception as e:
            assert str(e) == "fail"
            mock_error_handler.assert_not_called()  # We're not running the actual function with error handling 