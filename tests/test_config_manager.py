"""
Test suite for the ConfigManager class.
"""

import os
import pytest
import yaml
from unittest.mock import patch, mock_open
from src.core.config_manager import ConfigManager

@pytest.fixture
def sample_config():
    return """
bot:
  version: "1.5.0"
  debug_mode: false
  application_id: ${APP_ID}
channels:
  news: ${NEWS_CHAN}
  errors: "123456"
"""

@pytest.fixture
def mock_env_vars():
    return {
        "APP_ID": "987654",
        "NEWS_CHAN": "123789"
    }

def test_singleton_pattern():
    """Test that ConfigManager follows singleton pattern."""
    config1 = ConfigManager()
    config2 = ConfigManager()
    assert config1 is config2

@patch.dict(os.environ, {"APP_ID": "987654", "NEWS_CHAN": "123789"})
@patch("builtins.open", new_callable=mock_open)
def test_env_var_substitution(mock_file, sample_config):
    """Test environment variable substitution in config."""
    mock_file.return_value.read.return_value = sample_config
    
    config = ConfigManager()
    config.reload_config()
    
    assert config.get("bot.application_id") == "987654"
    assert config.get("channels.news") == "123789"
    assert config.get("channels.errors") == "123456"

def test_get_with_dot_notation():
    """Test getting values using dot notation."""
    config = ConfigManager()
    config._config = {
        "bot": {
            "version": "1.5.0",
            "debug": False
        },
        "channels": {
            "news": "123"
        }
    }
    
    assert config.get("bot.version") == "1.5.0"
    assert config.get("channels.news") == "123"
    assert config.get("nonexistent.path") is None
    assert config.get("nonexistent.path", "default") == "default"

@patch.dict(os.environ, {
    "APP_ID": "987654",
    "GUILD_ID": "123456",
    "NEWS_CHAN": "111",
    "ERROR_CHAN": "222",
    "LOG_CHAN": "333",
    "DISCORD_TOKEN": "abc",
    "TELEGRAM_API_ID": "123",
    "TELEGRAM_API_HASH": "xyz"
})
@patch("builtins.open", new_callable=mock_open)
def test_config_validation(mock_file):
    """Test configuration validation."""
    valid_config = """
bot:
  application_id: ${APP_ID}
  guild_id: ${GUILD_ID}
channels:
  news: ${NEWS_CHAN}
  errors: ${ERROR_CHAN}
  logs: ${LOG_CHAN}
tokens:
  discord: ${DISCORD_TOKEN}
  telegram:
    api_id: ${TELEGRAM_API_ID}
    api_hash: ${TELEGRAM_API_HASH}
"""
    mock_file.return_value.read.return_value = valid_config
    
    config = ConfigManager()
    config.reload_config()
    assert config.validate() is True

@patch.dict(os.environ, {})
@patch("builtins.open", new_callable=mock_open)
def test_config_validation_missing_required(mock_file):
    """Test configuration validation with missing required values."""
    invalid_config = """
bot:
  version: "1.5.0"
channels:
  news: ""
"""
    mock_file.return_value.read.return_value = invalid_config
    
    config = ConfigManager()
    config.reload_config()
    assert config.validate() is False

def test_raw_config_is_copy():
    """Test that raw_config returns a copy of the configuration."""
    config = ConfigManager()
    config._config = {"test": {"value": 123}}
    
    raw = config.raw_config
    raw["test"]["value"] = 456
    
    assert config._config["test"]["value"] == 123 