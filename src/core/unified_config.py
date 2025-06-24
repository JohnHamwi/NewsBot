"""
Unified Configuration System for NewsBot
Replaces all existing configuration systems with a single, clean approach.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Union
from datetime import datetime

from src.utils.debug_logger import debug_logger, debug_context


class UnifiedConfig:
    """
    Single, unified configuration system for NewsBot.
    
    Features:
    - Single source of truth for all configuration
    - Automatic migration from legacy systems
    - Real-time updates with persistence
    - Validation and type checking
    - Environment-specific overrides
    """
    
    def __init__(self, config_file: str = "config/unified_config.yaml"):
        self.config_file = Path(config_file)
        self.config_data = {}
        self.runtime_overrides = {}
        self.last_modified = None
        
        # Initialize configuration
        self._initialize_config()
    
    @debug_context("Config Initialization")
    def _initialize_config(self):
        """Initialize the unified configuration system."""
        debug_logger.info("Initializing unified configuration system")
        
        # Ensure config directory exists
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load or create configuration
        if self.config_file.exists():
            self._load_config()
        else:
            self._create_default_config()
            self._migrate_legacy_configs()
        
        # Validate configuration
        self._validate_config()
    
    def _load_config(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config_data = yaml.safe_load(f) or {}
            
            self.last_modified = self.config_file.stat().st_mtime
            debug_logger.info(f"Configuration loaded from {self.config_file}")
            
        except Exception as e:
            debug_logger.error(f"Failed to load configuration", error=e)
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default configuration structure."""
        self.config_data = {
            'meta': {
                'version': '1.0.0',
                'created': datetime.now().isoformat(),
                'description': 'Unified NewsBot Configuration'
            },
            
            # Core bot settings
            'bot': {
                'application_id': None,
                'guild_id': None,
                'admin_user_id': None,
                'news_role_id': None,
                'debug_mode': False,
                'version': '4.5.0'
            },
            
            # Discord settings
            'discord': {
                'token': None,
                'channels': {
                    'news': None,
                    'logs': None,
                    'errors': None
                }
            },
            
            # Telegram settings
            'telegram': {
                'api_id': None,
                'api_hash': None,
                'phone_number': None
            },
            
            # OpenAI settings
            'openai': {
                'api_key': None,
                'model': 'gpt-3.5-turbo',
                'max_tokens': 4000
            },
            
            # Automation settings
            'automation': {
                'enabled': True,
                'interval_minutes': 180,  # 3 hours
                'startup_delay_minutes': 5,
                'require_media': True,
                'require_text': True,
                'min_content_length': 50,
                'use_ai_filtering': True,
                'max_posts_per_session': 1
            },
            
            # Channel management
            'channels': {
                'active': [],
                'blacklisted_posts': [],
                'channel_metadata': {}
            },
            
            # Feature flags
            'features': {
                'auto_posting': True,
                'ai_translation': True,
                'ai_categorization': True,
                'location_detection': True,
                'news_role_pinging': True,
                'forum_tags': True,
                'rich_presence': True,
                'health_monitoring': True
            },
            
            # Monitoring settings
            'monitoring': {
                'health_checks': True,
                'performance_tracking': True,
                'log_level': 'INFO',
                'max_log_size_mb': 50,
                'log_retention_days': 30
            },
            
            # Environment-specific overrides
            'environments': {
                'development': {
                    'bot': {'debug_mode': True},
                    'automation': {'interval_minutes': 60},
                    'monitoring': {'log_level': 'DEBUG'}
                },
                'production': {
                    'bot': {'debug_mode': False},
                    'automation': {'interval_minutes': 180},
                    'monitoring': {'log_level': 'INFO'}
                }
            }
        }
        
        self._save_config()
        debug_logger.info("Created default configuration")
    
    @debug_context("Legacy Config Migration")
    def _migrate_legacy_configs(self):
        """Migrate configuration from legacy systems."""
        debug_logger.info("Starting legacy configuration migration")
        
        migrated_sources = []
        
        # Migrate from config_profiles.yaml
        old_yaml = Path("config/config_profiles.yaml")
        if old_yaml.exists():
            self._migrate_from_yaml(old_yaml)
            migrated_sources.append("config_profiles.yaml")
        
        # Migrate from VPS config.yaml
        vps_yaml = Path("config/config.yaml")
        if vps_yaml.exists():
            self._migrate_from_yaml(vps_yaml)
            migrated_sources.append("config.yaml")
        
        # Migrate from botdata.json
        botdata_json = Path("data/botdata.json")
        if botdata_json.exists():
            self._migrate_from_json(botdata_json)
            migrated_sources.append("botdata.json")
        
        if migrated_sources:
            debug_logger.info(f"Migrated configuration from: {', '.join(migrated_sources)}")
            self._save_config()
        else:
            debug_logger.info("No legacy configurations found to migrate")
    
    def _migrate_from_yaml(self, yaml_file: Path):
        """Migrate configuration from a YAML file."""
        try:
            with open(yaml_file, 'r') as f:
                legacy_data = yaml.safe_load(f) or {}
            
            # Map legacy structure to new structure
            if 'bot' in legacy_data:
                self.config_data['bot'].update(legacy_data['bot'])
            
            if 'tokens' in legacy_data:
                if 'discord' in legacy_data['tokens']:
                    self.config_data['discord']['token'] = legacy_data['tokens']['discord']
            
            if 'channels' in legacy_data:
                self.config_data['discord']['channels'].update(legacy_data['channels'])
            
            if 'telegram' in legacy_data:
                self.config_data['telegram'].update(legacy_data['telegram'])
            
            if 'openai' in legacy_data:
                self.config_data['openai'].update(legacy_data['openai'])
            
            if 'automation' in legacy_data:
                self.config_data['automation'].update(legacy_data['automation'])
            
            debug_logger.info(f"Migrated configuration from {yaml_file}")
            
        except Exception as e:
            debug_logger.error(f"Failed to migrate from {yaml_file}", error=e)
    
    def _migrate_from_json(self, json_file: Path):
        """Migrate configuration from JSON cache file."""
        try:
            with open(json_file, 'r') as f:
                legacy_data = json.load(f)
            
            # Migrate channel data
            if 'telegram_channels' in legacy_data:
                self.config_data['channels']['active'] = legacy_data['telegram_channels']
            
            if 'blacklisted_posts' in legacy_data:
                self.config_data['channels']['blacklisted_posts'] = legacy_data['blacklisted_posts']
            
            if 'channel_metadata' in legacy_data:
                self.config_data['channels']['channel_metadata'] = legacy_data['channel_metadata']
            
            # Migrate automation config
            if 'automation_config' in legacy_data:
                auto_config = legacy_data['automation_config']
                self.config_data['automation'].update(auto_config)
            
            debug_logger.info(f"Migrated data from {json_file}")
            
        except Exception as e:
            debug_logger.error(f"Failed to migrate from {json_file}", error=e)
    
    def _validate_config(self):
        """Validate the configuration."""
        required_fields = [
            ('bot.application_id', 'Discord Application ID'),
            ('bot.guild_id', 'Discord Guild ID'),
            ('discord.token', 'Discord Bot Token'),
            ('discord.channels.news', 'News Channel ID'),
            ('telegram.api_id', 'Telegram API ID'),
            ('telegram.api_hash', 'Telegram API Hash'),
            ('openai.api_key', 'OpenAI API Key')
        ]
        
        missing = []
        for field, description in required_fields:
            if not self.get(field):
                missing.append(f"{field} ({description})")
        
        if missing:
            debug_logger.warning(f"Missing required configuration: {', '.join(missing)}")
        else:
            debug_logger.info("Configuration validation passed")
    
    def _save_config(self):
        """Save configuration to file."""
        try:
            # Update metadata
            self.config_data['meta']['last_updated'] = datetime.now().isoformat()
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config_data, f, default_flow_style=False, indent=2)
            
            self.last_modified = self.config_file.stat().st_mtime
            debug_logger.info("Configuration saved")
            
        except Exception as e:
            debug_logger.error("Failed to save configuration", error=e)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation (e.g., 'bot.version')
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        # Check runtime overrides first
        if key in self.runtime_overrides:
            return self.runtime_overrides[key]
        
        # Get from main config
        keys = key.split('.')
        value = self.config_data
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any, persist: bool = True, runtime_only: bool = False):
        """
        Set a configuration value.
        
        Args:
            key: Configuration key in dot notation
            value: Value to set
            persist: Whether to save to file immediately
            runtime_only: If True, only set in runtime overrides
        """
        if runtime_only:
            self.runtime_overrides[key] = value
            debug_logger.info(f"Set runtime override: {key} = {value}")
            return
        
        # Set in main config
        keys = key.split('.')
        config = self.config_data
        
        # Navigate to the parent dictionary
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
        
        if persist:
            self._save_config()
        
        debug_logger.info(f"Set configuration: {key} = {value}")
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get an entire configuration section."""
        return self.get(section, {})
    
    def reload(self):
        """Reload configuration from file."""
        debug_logger.info("Reloading configuration")
        self._load_config()
        self._validate_config()
    
    def backup_legacy_configs(self):
        """Create backups of legacy configuration files."""
        backup_dir = Path("config/legacy_backup")
        backup_dir.mkdir(exist_ok=True)
        
        legacy_files = [
            "config/config_profiles.yaml",
            "config/config.yaml",
            "data/botdata.json"
        ]
        
        for file_path in legacy_files:
            file_path = Path(file_path)
            if file_path.exists():
                backup_path = backup_dir / f"{file_path.name}.backup"
                backup_path.write_bytes(file_path.read_bytes())
                debug_logger.info(f"Backed up {file_path} to {backup_path}")
    
    def get_environment_config(self, environment: str = None) -> Dict[str, Any]:
        """Get environment-specific configuration."""
        if not environment:
            environment = os.getenv('NODE_ENV', 'production')
        
        env_config = self.get(f'environments.{environment}', {})
        
        # Merge with base config
        merged_config = self.config_data.copy()
        self._deep_merge(merged_config, env_config)
        
        return merged_config
    
    def _deep_merge(self, base: Dict, override: Dict):
        """Deep merge two dictionaries."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def export_for_legacy_compatibility(self):
        """Export configuration in legacy format for backward compatibility."""
        return {
            'bot': self.get_section('bot'),
            'discord': self.get_section('discord'),
            'telegram': self.get_section('telegram'),
            'openai': self.get_section('openai'),
            'automation': self.get_section('automation'),
            'channels': self.get_section('channels'),
            'features': self.get_section('features')
        }
    
    def generate_migration_report(self) -> str:
        """Generate a report of the migration process."""
        lines = [
            "🔄 CONFIGURATION MIGRATION REPORT",
            "=" * 50,
            "",
            f"✅ Unified configuration created: {self.config_file}",
            f"📅 Migration completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "📋 Configuration Status:",
            f"  • Bot Settings: {'✅' if self.get('bot.application_id') else '❌'} Configured",
            f"  • Discord Token: {'✅' if self.get('discord.token') else '❌'} Configured", 
            f"  • Telegram API: {'✅' if self.get('telegram.api_id') else '❌'} Configured",
            f"  • OpenAI API: {'✅' if self.get('openai.api_key') else '❌'} Configured",
            f"  • Active Channels: {len(self.get('channels.active', []))} channels",
            "",
            "🎛️ Feature Status:",
        ]
        
        features = self.get_section('features')
        for feature, enabled in features.items():
            status = "✅" if enabled else "❌"
            lines.append(f"  • {feature}: {status}")
        
        lines.extend([
            "",
            "⚙️ Next Steps:",
            "  1. Review unified configuration file",
            "  2. Test bot functionality",
            "  3. Remove legacy configuration files if everything works",
            "  4. Update deployment scripts to use unified config"
        ])
        
        return "\n".join(lines)


# Global unified configuration instance
unified_config = UnifiedConfig()

# Legacy compatibility exports
def get(key: str, default: Any = None) -> Any:
    """Legacy compatibility function."""
    return unified_config.get(key, default)

def get_section(section: str) -> Dict[str, Any]:
    """Legacy compatibility function."""
    return unified_config.get_section(section) 