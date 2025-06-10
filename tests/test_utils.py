import pytest
from src.utils import config

# Example: test config loading

def test_config_values():
    assert hasattr(config.Config, 'DISCORD_TOKEN')
    assert hasattr(config.Config, 'GUILD_ID')

# Add more tests for utility functions as needed 