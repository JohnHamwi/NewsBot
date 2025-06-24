# =============================================================================
# NewsBot Configuration Validator Module
# =============================================================================
# This module provides schema-based validation for the NewsBot configuration
# including type validation, required field checking, default value handling,
# and detailed error messages for configuration management.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# =============================================================================
# Local Application Imports
# =============================================================================
from src.utils.base_logger import base_logger as logger
from src.utils.debug_logger import debug_logger, debug_context


# =============================================================================
# Exception Classes
# =============================================================================
class ValidationError(Exception):
    """Exception raised for configuration validation errors."""
    pass


# =============================================================================
# Enhanced Configuration Validator
# =============================================================================
"""
Comprehensive configuration validation system for NewsBot.
Validates all required settings and provides detailed error messages.
"""

class ConfigValidator:
    """Enhanced configuration validator with detailed error reporting."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    @debug_context("Config Validation")
    def validate_all(self, config_data: Dict[str, Any]) -> bool:
        """
        Validate all configuration sections.
        
        Returns:
            bool: True if all validations pass, False otherwise
        """
        self.errors = []
        self.warnings = []
        
        # Define validation rules
        validations = [
            self._validate_discord_config,
            self._validate_telegram_config,
            self._validate_openai_config,
            self._validate_channels_config,
            self._validate_bot_config,
            self._validate_automation_config
        ]
        
        # Run all validations
        for validation in validations:
            try:
                validation(config_data)
            except Exception as e:
                self.errors.append(f"Validation error in {validation.__name__}: {str(e)}")
        
        # Log results
        if self.errors:
            debug_logger.error("Configuration validation failed", 
                             error_count=len(self.errors), 
                             errors=self.errors,
                             warnings=self.warnings)
        elif self.warnings:
            debug_logger.warning("Configuration validation passed with warnings",
                               warning_count=len(self.warnings),
                               warnings=self.warnings)
        else:
            debug_logger.info("Configuration validation passed completely")
            
        return len(self.errors) == 0
    
    def _validate_discord_config(self, config: Dict[str, Any]):
        """Validate Discord configuration section."""
        discord_config = config.get('discord', {})
        
        # Required fields
        required_fields = ['token', 'guild_id']
        for field in required_fields:
            if not discord_config.get(field):
                self.errors.append(f"Discord.{field} is required but missing or empty")
        
        # Token validation
        token = discord_config.get('token', '')
        if token and not self._is_valid_discord_token(token):
            self.errors.append("Discord token format appears invalid")
            
        # Guild ID validation
        guild_id = discord_config.get('guild_id')
        if guild_id and not str(guild_id).isdigit():
            self.errors.append("Discord guild_id must be a numeric string or integer")
    
    def _validate_telegram_config(self, config: Dict[str, Any]):
        """Validate Telegram configuration section."""
        telegram_config = config.get('telegram', {})
        
        # Required fields
        required_fields = ['api_id', 'api_hash', 'phone_number']
        for field in required_fields:
            if not telegram_config.get(field):
                self.errors.append(f"Telegram.{field} is required but missing or empty")
        
        # API ID validation
        api_id = telegram_config.get('api_id')
        if api_id and not str(api_id).isdigit():
            self.errors.append("Telegram api_id must be numeric")
            
        # Phone number validation
        phone = telegram_config.get('phone_number', '')
        if phone and not re.match(r'^\+?[\d\s\-()]+$', phone):
            self.warnings.append("Telegram phone_number format may be invalid")
    
    def _validate_openai_config(self, config: Dict[str, Any]):
        """Validate OpenAI configuration section."""
        openai_config = config.get('openai', {})
        
        # Required fields
        api_key = openai_config.get('api_key')
        if not api_key:
            self.errors.append("OpenAI.api_key is required but missing or empty")
        elif not api_key.startswith('sk-'):
            self.errors.append("OpenAI API key should start with 'sk-'")
    
    def _validate_channels_config(self, config: Dict[str, Any]):
        """Validate channels configuration section."""
        # Check for channels in new discord.channels format first
        discord_config = config.get('discord', {})
        channels_config = discord_config.get('channels', {})
        
        # If not found in discord.channels, check legacy channels format
        if not channels_config:
            channels_config = config.get('channels', {})
        
        # Required channels
        required_channels = ['news', 'logs', 'errors']
        for channel in required_channels:
            channel_id = channels_config.get(channel)
            if not channel_id:
                self.errors.append(f"Channels.{channel} is required but missing or empty")
            elif not str(channel_id).isdigit():
                self.errors.append(f"Channels.{channel} must be a numeric Discord channel ID")
    
    def _validate_bot_config(self, config: Dict[str, Any]):
        """Validate bot configuration section."""
        bot_config = config.get('bot', {})
        
        # Required fields
        news_role_id = bot_config.get('news_role_id')
        if not news_role_id:
            self.errors.append("Bot.news_role_id is required but missing or empty")
        elif not str(news_role_id).isdigit():
            self.errors.append("Bot.news_role_id must be a numeric Discord role ID")
    
    def _validate_automation_config(self, config: Dict[str, Any]):
        """Validate automation configuration section."""
        automation_config = config.get('automation', {})
        
        # Check for active channels in different locations
        active_channels = []
        
        # Check automation.active_channels
        if automation_config.get('active_channels'):
            active_channels = automation_config.get('active_channels', [])
        # Check channels.active (new format)
        elif config.get('channels', {}).get('active'):
            active_channels = config.get('channels', {}).get('active', [])
        
        if not active_channels:
            self.warnings.append("No active_channels configured - bot won't auto-post")
        elif not isinstance(active_channels, list):
            self.errors.append("Active channels must be a list")
        
        # Validate intervals
        intervals = automation_config.get('intervals', {})
        if intervals:
            auto_post_interval = intervals.get('auto_post_minutes')
            if auto_post_interval and (not isinstance(auto_post_interval, (int, float)) or auto_post_interval <= 0):
                self.errors.append("Automation.intervals.auto_post_minutes must be a positive number")
    
    def _is_valid_discord_token(self, token: str) -> bool:
        """Basic Discord token format validation."""
        # Discord bot tokens typically have a specific format
        if not token:
            return False
        
        # Basic pattern check (this is simplified)
        parts = token.split('.')
        return len(parts) >= 3 and len(parts[0]) > 0
    
    def get_validation_report(self) -> str:
        """Generate a detailed validation report."""
        report_lines = []
        
        if self.errors:
            report_lines.append("❌ CONFIGURATION ERRORS:")
            for i, error in enumerate(self.errors, 1):
                report_lines.append(f"  {i}. {error}")
            report_lines.append("")
        
        if self.warnings:
            report_lines.append("⚠️ CONFIGURATION WARNINGS:")
            for i, warning in enumerate(self.warnings, 1):
                report_lines.append(f"  {i}. {warning}")
            report_lines.append("")
        
        if not self.errors and not self.warnings:
            report_lines.append("✅ All configuration validation checks passed!")
        
        return "\n".join(report_lines)


# Global validator instance
config_validator = ConfigValidator()


# NewsBot configuration schema
NEWSBOT_CONFIG_SCHEMA = {
    "bot.version": {
        "type": "str",
        "required": True,
    },
    "bot.guild_id": {
        "type": "int",
        "required": True,
    },
    "bot.application_id": {
        "type": "str_or_int",
        "required": True,
    },
    "bot.debug_mode": {
        "type": "bool",
        "default": False,
    },
    "bot.admin_role_id": {
        "type": "int",
        "required": True,
    },
    "bot.news_role_id": {
        "type": "int",
        "required": True,
    },
    "channels.news": {
        "type": "int",
        "required": True,
    },
    "channels.errors": {
        "type": "int",
        "required": True,
    },
    "channels.logs": {
        "type": "int",
        "required": True,
    },
    "tokens.discord": {
        "type": "str",
        "required": True,
        "min_length": 10,
    },
    "telegram.api_id": {
        "type": "int",
        "required": True,
    },
    "telegram.api_hash": {
        "type": "str",
        "required": True,
    },
    "monitoring.metrics.port": {
        "type": "int",
        "default": 8000,
        "min": 1024,
        "max": 65535,
    },
    "monitoring.metrics.collection_interval": {
        "type": "int",
        "default": 60,
        "min": 10,
        "max": 3600,
    },
    "security.rate_limits.default": {
        "type": "int",
        "default": 5,
        "min": 1,
    },
    "security.rate_limits.cooldown": {
        "type": "int",
        "default": 60,
        "min": 1,
    },
}


def validate_config(config: Dict) -> Tuple[bool, List[str]]:
    """
    Validate the NewsBot configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Tuple of (is_valid, error_messages)
    """
    return config_validator.validate_all(config), config_validator.get_validation_report()


def apply_defaults(config: Dict) -> Dict:
    """
    Apply default values to configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Updated configuration with defaults
    """
    return ConfigValidator.apply_defaults(config, NEWSBOT_CONFIG_SCHEMA)
