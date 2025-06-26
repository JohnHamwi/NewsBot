#!/usr/bin/env python3
"""
Simple Configuration Manager
============================
Single source of truth for all bot configuration.
Eliminates the complexity of multiple config files.
"""

import json
import yaml
import os
from typing import Any, Dict, Optional
from pathlib import Path

class SimpleConfigManager:
    """
    Ultra-simple configuration manager that eliminates config complexity.
    
    Features:
    - Single config file (config/bot.yaml)
    - Simple get/set methods
    - Automatic saving
    - No nested complexity
    """
    
    def __init__(self, config_path: str = "config/bot.yaml"):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(exist_ok=True)
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Error loading config: {e}")
                return self._create_default_config()
        else:
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create simple default configuration."""
        default = {
            # Core Settings
            "posting_interval_minutes": 60,
            "startup_delay_minutes": 2,
            "max_posts_per_session": 1,
            
            # Channels
            "active_channels": [
                "moraselalthawrah",
                "jh_team", 
                "shaamnetwork",
                "alktroone",
                "alhourya_news",
                "alekhbariahsy",
                "samsyria01"
            ],
            
            # Features
            "auto_posting_enabled": True,
            "ai_analysis_enabled": True,
            "translation_enabled": True,
            
            # Quality Thresholds
            "min_content_length": 50,
            "require_media": False,
            "use_ai_filtering": True,
            
            # Performance
            "cache_ttl_hours": 1,
            "max_concurrent_analyses": 3,
            
            # Monitoring
            "health_checks_enabled": True,
            "performance_tracking": True,
            "log_level": "INFO"
        }
        
        self._save_config(default)
        return default
    
    def _save_config(self, config: Dict[str, Any] = None) -> None:
        """Save configuration to file."""
        config_to_save = config or self._config
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(config_to_save, f, default_flow_style=False, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and save immediately."""
        self._config[key] = value
        self._save_config()
        print(f"✅ Config updated: {key} = {value}")
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values."""
        return self._config.copy()
    
    def update_multiple(self, updates: Dict[str, Any]) -> None:
        """Update multiple values at once."""
        self._config.update(updates)
        self._save_config()
        print(f"✅ Config updated with {len(updates)} changes")
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        self._config = self._create_default_config()
        print("✅ Config reset to defaults")

# Global instance
config_manager = SimpleConfigManager()

# Convenience functions
def get_config(key: str, default: Any = None) -> Any:
    """Get a configuration value."""
    return config_manager.get(key, default)

def set_config(key: str, value: Any) -> None:
    """Set a configuration value."""
    config_manager.set(key, value)

def set_posting_interval(minutes: int) -> None:
    """Simple function to set posting interval."""
    if minutes < 1:
        raise ValueError("Interval must be at least 1 minute")
    set_config("posting_interval_minutes", minutes)
    print(f"🕐 Posting interval set to {minutes} minutes")

def get_posting_interval() -> int:
    """Get the posting interval in minutes."""
    return get_config("posting_interval_minutes", 60)

def get_active_channels() -> list:
    """Get list of active channels."""
    return get_config("active_channels", [])

def add_channel(channel_name: str) -> None:
    """Add a channel to active channels."""
    channels = get_active_channels()
    if channel_name not in channels:
        channels.append(channel_name)
        set_config("active_channels", channels)
        print(f"✅ Added channel: {channel_name}")
    else:
        print(f"ℹ️ Channel already active: {channel_name}")

def remove_channel(channel_name: str) -> None:
    """Remove a channel from active channels."""
    channels = get_active_channels()
    if channel_name in channels:
        channels.remove(channel_name)
        set_config("active_channels", channels)
        print(f"✅ Removed channel: {channel_name}")
    else:
        print(f"ℹ️ Channel not found: {channel_name}")

def show_config() -> None:
    """Display current configuration in a readable format."""
    config = config_manager.get_all()
    print("\n📋 Current Bot Configuration:")
    print("=" * 40)
    
    # Core settings
    print(f"🕐 Posting Interval: {config.get('posting_interval_minutes', 60)} minutes")
    print(f"🚀 Startup Delay: {config.get('startup_delay_minutes', 2)} minutes")
    print(f"📝 Max Posts/Session: {config.get('max_posts_per_session', 1)}")
    
    # Channels
    channels = config.get('active_channels', [])
    print(f"\n📡 Active Channels ({len(channels)}):")
    for channel in channels:
        print(f"  • {channel}")
    
    # Features
    print(f"\n🎛️ Features:")
    print(f"  • Auto Posting: {'✅' if config.get('auto_posting_enabled') else '❌'}")
    print(f"  • AI Analysis: {'✅' if config.get('ai_analysis_enabled') else '❌'}")
    print(f"  • Translation: {'✅' if config.get('translation_enabled') else '❌'}")
    
    print("=" * 40)

if __name__ == "__main__":
    # Command line interface for easy config management
    import sys
    
    if len(sys.argv) < 2:
        show_config()
        print("\nUsage:")
        print("  python config_manager.py show")
        print("  python config_manager.py set-interval 30")
        print("  python config_manager.py add-channel channel_name")
        print("  python config_manager.py remove-channel channel_name")
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == "show":
        show_config()
    elif command == "set-interval" and len(sys.argv) == 3:
        try:
            minutes = int(sys.argv[2])
            set_posting_interval(minutes)
        except ValueError:
            print("❌ Invalid interval. Must be a number.")
    elif command == "add-channel" and len(sys.argv) == 3:
        add_channel(sys.argv[2])
    elif command == "remove-channel" and len(sys.argv) == 3:
        remove_channel(sys.argv[2])
    else:
        print("❌ Unknown command or wrong number of arguments")
        print("Use: python config_manager.py show") 