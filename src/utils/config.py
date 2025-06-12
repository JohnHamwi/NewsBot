"""
Configuration Management Module

This module handles the bot's configuration settings, loading them from environment
variables and providing validation to ensure all required settings are present.
"""

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Load environment variables from config/.env
config_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config"
)
env_path = os.path.join(config_dir, ".env")
load_dotenv(env_path)


class Config:
    """
    Configuration loader for NewsBot.
    Loads and validates environment variables and settings for the bot.

    This class provides static access to configuration values loaded from environment
    variables. It includes validation to ensure all required settings are present
    and properly formatted.

    Attributes:
        DISCORD_TOKEN (str): The Discord bot token for authentication
        GUILD_ID (int): The ID of the Discord server (guild) the bot operates in
        LOG_CHANNEL_ID (int): The ID of the channel where bot logs are sent
        ERRORS_CHANNEL_ID (int): The ID of the channel where error reports are sent
        NEWS_CHANNEL_ID (int): The ID of the channel where news updates are posted
        ADMIN_ROLE_ID (int): The ID of the admin role for privileged commands
        ADMIN_USER_ID (int): The ID of the admin user for privileged commands
        DEBUG_MODE (bool): Whether debug mode is enabled
    """

    # Discord Authentication
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")

    # Server (Guild) Configuration
    GUILD_ID: Optional[int] = (
        int(os.getenv("GUILD_ID")) if os.getenv("GUILD_ID") else None
    )

    # Channel IDs
    LOG_CHANNEL_ID: Optional[int] = (
        int(os.getenv("LOG_CHANNEL_ID")) if os.getenv("LOG_CHANNEL_ID") else None
    )
    ERRORS_CHANNEL_ID: Optional[int] = (
        int(os.getenv("ERRORS_CHANNEL_ID")) if os.getenv("ERRORS_CHANNEL_ID") else None
    )
    NEWS_CHANNEL_ID: Optional[int] = (
        int(os.getenv("NEWS_CHANNEL_ID")) if os.getenv("NEWS_CHANNEL_ID") else None
    )

    # Role IDs
    ADMIN_ROLE_ID: Optional[int] = (
        int(os.getenv("ADMIN_ROLE_ID")) if os.getenv("ADMIN_ROLE_ID") else None
    )
    ADMIN_USER_ID: Optional[int] = (
        int(os.getenv("ADMIN_USER_ID")) if os.getenv("ADMIN_USER_ID") else None
    )

    # Discord Bot Configuration
    APPLICATION_ID = os.getenv("APPLICATION_ID")

    # Telegram Configuration
    TELEGRAM_API_ID: int = int(os.getenv("TELEGRAM_API_ID", 0))
    TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH", "")

    # Debug Configuration
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "").lower() == "true"

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @staticmethod
    def validate() -> bool:
        """
        Validate that all required configuration values are present and correct.
        Returns True if valid, False otherwise.
        """
        # Import logger here to avoid circular import
        from src.utils.base_logger import base_logger as logger

        # Check Discord token
        if not Config.DISCORD_TOKEN:
            logger.error("❌ Missing DISCORD_TOKEN in environment variables")
            return False

        # Check Guild ID
        if not Config.GUILD_ID:
            logger.error("❌ Missing or invalid GUILD_ID in environment variables")
            return False

        # Check Channel IDs
        if not Config.LOG_CHANNEL_ID:
            logger.error(
                "❌ Missing or invalid LOG_CHANNEL_ID in environment variables"
            )
            return False

        if not Config.ERRORS_CHANNEL_ID:
            logger.error(
                "❌ Missing or invalid ERRORS_CHANNEL_ID in environment variables"
            )
            return False

        if not Config.NEWS_CHANNEL_ID:
            logger.error(
                "❌ Missing or invalid NEWS_CHANNEL_ID in environment variables"
            )
            return False

        # Check Role IDs
        if not Config.ADMIN_ROLE_ID:
            logger.error("❌ Missing or invalid ADMIN_ROLE_ID in environment variables")
            return False

        return True

    @classmethod
    def get_config_status(cls) -> dict:
        """
        Get the current status of all configuration values.

        Returns:
            dict: Dictionary containing the status of each configuration value:
                - is_set: Whether the value is set
                - value: The current value (masked for sensitive data)
        """
        return {
            "discord_token": {
                "is_set": bool(cls.DISCORD_TOKEN),
                "value": "***" if cls.DISCORD_TOKEN else None,
            },
            "guild_id": {"is_set": bool(cls.GUILD_ID), "value": cls.GUILD_ID},
            "log_channel_id": {
                "is_set": bool(cls.LOG_CHANNEL_ID),
                "value": cls.LOG_CHANNEL_ID,
            },
            "errors_channel_id": {
                "is_set": bool(cls.ERRORS_CHANNEL_ID),
                "value": cls.ERRORS_CHANNEL_ID,
            },
            "news_channel_id": {
                "is_set": bool(cls.NEWS_CHANNEL_ID),
                "value": cls.NEWS_CHANNEL_ID,
            },
            "admin_role_id": {
                "is_set": bool(cls.ADMIN_ROLE_ID),
                "value": cls.ADMIN_ROLE_ID,
            },
        }

    @classmethod
    def get_guild_id(cls) -> int:
        """Get the guild ID"""
        return cls.GUILD_ID

    @classmethod
    def is_admin(cls, role_ids: List[int]) -> bool:
        """Check if the given role IDs include the admin role"""
        return cls.ADMIN_ROLE_ID in role_ids

    @classmethod
    def get_channel_id(cls, channel_type: str) -> Optional[int]:
        """Get a channel ID by type (news, errors, log)"""
        channel_map = {
            "news": cls.NEWS_CHANNEL_ID,
            "errors": cls.ERRORS_CHANNEL_ID,
            "log": cls.LOG_CHANNEL_ID,
        }
        return channel_map.get(channel_type.lower())

    @classmethod
    def get_debug_info(cls) -> Dict[str, Any]:
        """
        Get debug information about the configuration.
        Safely returns configuration info without exposing sensitive values.

        Returns:
            Dict[str, Any]: Debug information about configuration
        """
        return {
            "guild_id": bool(cls.GUILD_ID),
            "log_channel_configured": bool(cls.LOG_CHANNEL_ID),
            "news_channel_configured": bool(cls.NEWS_CHANNEL_ID),
            "telegram_configured": all(
                [cls.TELEGRAM_API_ID, cls.TELEGRAM_API_HASH]
            ),
        }


def get_guild_ids() -> List[int]:
    """
    Get list of guild IDs from environment variables
    Returns a list of integer guild IDs
    """
    guild_ids_str = os.getenv("GUILD_IDS", "")
    if not guild_ids_str:
        return []

    # Split by comma and convert to integers, ignoring empty strings
    return [
        int(guild_id.strip())
        for guild_id in guild_ids_str.split(",")
        if guild_id.strip()
    ]
