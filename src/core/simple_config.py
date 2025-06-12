"""
Simple Configuration Manager for NewsBot

This module provides a streamlined configuration system optimized for solo development.
It combines YAML-based configuration with environment variables and adds developer-friendly
features like automatic reload, configuration overrides, and profile support.
"""

import copy
import json
import logging
import os
import time
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

# Setup logger
logger = logging.getLogger("NewsBot")


class SimpleConfig:
    """
    Simplified configuration manager optimized for solo development.

    Features:
    - Single YAML file with environment variable substitution
    - Support for configuration profiles (dev, test, prod)
    - Live reloading of configuration when file changes
    - Type conversion (int, bool, str)
    - Runtime configuration overrides
    - Configuration snapshots
    """

    def __init__(self, config_file="config.yaml"):
        """
        Initialize the configuration manager.

        Args:
            config_file (str): Path to the configuration file
        """
        self._config_file = config_file
        self._config = None
        self._last_check_time = 0
        self._last_modified_time = 0
        self._active_profile = None
        self._runtime_overrides = {}

    def load(self, profile=None, config_file=None):
        """
        Load configuration from file with optional profile support.

        Args:
            profile (str, optional): Configuration profile to use (e.g., "dev", "prod")
            config_file (str, optional): Override the configuration file path

        Returns:
            bool: True if config loaded successfully, False otherwise
        """
        try:
            # Set profile from environment if specified
            if not profile:
                profile = os.getenv("CONFIG_PROFILE", None)

            if profile:
                self._active_profile = profile
                logger.info(f"Loading configuration with profile: {profile}")

            # Update config file path if provided
            if config_file:
                self._config_file = config_file

            # Check if file exists
            if not os.path.exists(self._config_file):
                logger.error(f"Configuration file not found: {self._config_file}")
                return False

            # Get file modification time
            self._last_modified_time = os.path.getmtime(self._config_file)

            # Load YAML config
            with open(self._config_file, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
                logger.debug(f"Configuration loaded from {self._config_file}")

            # Apply profile-specific overrides if they exist
            final_config = self._config.copy()
            if (
                profile
                and "profiles" in final_config
                and profile in final_config["profiles"]
            ):
                self._merge_config(final_config, final_config["profiles"][profile])

            # Substitute environment variables
            self._substitute_env_vars(final_config)

            # Apply runtime overrides
            for key, value in self._runtime_overrides.items():
                parts = key.split(".")
                current = final_config

                # Navigate to the right location
                for i, part in enumerate(parts[:-1]):
                    if part not in current:
                        current[part] = {}
                    current = current[part]

                # Set the value
                current[parts[-1]] = value

            self._config = final_config
            self._last_check_time = time.time()

            logger.info(f"Configuration loaded successfully from {self._config_file}")
            if profile:
                logger.info(f"Applied profile: {profile}")

            return True

        except FileNotFoundError:
            logger.warning(f"Configuration file not found: {self._config_file}")
            self._config = {}
            return False
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML: {e}")
            self._config = {}
            return False
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self._config = {}
            return False

    def _substitute_env_vars(self, config_dict):
        """
        Recursively substitute environment variables in configuration.

        Args:
            config_dict (dict): Dictionary to substitute values in
        """
        for key, value in list(config_dict.items()):
            if isinstance(value, dict):
                self._substitute_env_vars(value)
            elif (
                isinstance(value, str)
                and value.startswith("${")
                and value.endswith("}")
            ):
                env_var = value[2:-1]  # Remove ${ and }
                env_value = os.getenv(env_var)
                if env_value is not None:
                    try:
                        # Try to convert to appropriate type
                        if env_value.isdigit():
                            config_dict[key] = int(env_value)
                        elif env_value.lower() in ("true", "false"):
                            config_dict[key] = env_value.lower() == "true"
                        else:
                            config_dict[key] = env_value
                    except BaseException:
                        config_dict[key] = env_value
                else:
                    logger.warning(f"Environment variable not found: {env_var}")

    def _merge_config(self, base, override):
        """
        Recursively merge two configuration dictionaries.

        Args:
            base (dict): Base configuration to merge into
            override (dict): Configuration to apply on top of base
        """
        for key, value in override.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                # Recursively merge dictionaries
                self._merge_config(base[key], value)
            else:
                # Override or add value
                base[key] = value

    def check_for_changes(self):
        """
        Check if the configuration file has changed and reload if necessary.

        Returns:
            bool: True if config was reloaded, False otherwise
        """
        # Check for updates if it's been more than 5 seconds since last check
        now = time.time()
        if now - self._last_check_time < 5:
            return False

        try:
            self._last_check_time = now

            if not os.path.exists(self._config_file):
                return False

            mod_time = os.path.getmtime(self._config_file)
            if mod_time > self._last_modified_time:
                logger.debug(f"Configuration file changed, reloading")
                return self.load(self._active_profile)

        except Exception as e:
            logger.error(f"Error checking for configuration changes: {str(e)}")

        return False

    def get(self, key_path, default=None):
        """
        Get a configuration value by key path.

        Args:
            key_path (str): Dot-separated path to the configuration value
            default: Default value to return if key is not found

        Returns:
            The configuration value at the specified path, or default if not found
        """
        # Load config if not already loaded
        if self._config is None:
            self.load()

        # Check for changes
        self.check_for_changes()

        # Navigate to the correct nested dictionary
        keys = key_path.split(".")
        current = self._config

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default

        # Set the value
        return current

    def set(self, key_path, value, save=False):
        """
        Set a configuration value by key path.

        Args:
            key_path (str): Dot-separated path to the configuration value
            value: Value to set
            save (bool): Whether to save the changes to the config file

        Returns:
            bool: True if successful, False otherwise
        """
        # Apply overrides
        self._runtime_overrides[key_path] = value

        # Force reload of the configuration
        self.load(self._active_profile)

        # Save to file if requested
        if save:
            return self.save()

        return True

    def reload(self):
        """
        Reload configuration from file.

        Returns:
            bool: True if successful, False otherwise
        """
        # Reload config to reset to file values
        return self.load(self._active_profile)

    def save(self):
        """
        Save current configuration to file.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Make a copy of the config to save
            config_to_save = {}

            # Get the original config without runtime overrides
            original_overrides = self._runtime_overrides
            self._runtime_overrides = {}
            self.load(self._active_profile)

            # Restore runtime overrides
            self._runtime_overrides = original_overrides
            self.load(self._active_profile)

            # Apply permanent changes to the base config
            for key, value in self._runtime_overrides.items():
                keys = key.split(".")
                current = config_to_save

                # Create nested dictionaries as needed
                for i, k in enumerate(keys[:-1]):
                    if k not in current:
                        current[k] = {}
                    current = current[k]

                # Set the final value
                current[keys[-1]] = value

            # Create directory if it doesn't exist
            os.makedirs(
                os.path.dirname(os.path.abspath(self._config_file)), exist_ok=True
            )

            # Save as YAML or JSON based on file extension
            if self._config_file.endswith(".json"):
                with open(self._config_file, "w") as f:
                    json.dump(config_to_save, f, indent=2)
            else:
                with open(self._config_file, "w") as f:
                    yaml.dump(config_to_save, f, default_flow_style=False)

            logger.info(f"Configuration saved to {self._config_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save configuration: {str(e)}")
            return False

    def validate(self):
        """
        Validate that required configuration values are present.

        Returns:
            bool: True if the configuration is valid, False otherwise
        """
        # Load config if not already loaded
        if self._config is None:
            self.load()

        # Add validation logic here based on your requirements
        required_keys = ["bot.guild_id", "tokens.discord", "channels.news"]

        for key in required_keys:
            if not self.get(key):
                logger.error(f"Missing required configuration key: {key}")
                return False

        return True

    def get_active_profile(self):
        """
        Get the currently active configuration profile.

        Returns:
            str: Name of active profile, or None if no profile is active
        """
        return self._active_profile

    def create_snapshot(self, name=None):
        """
        Create a snapshot of the current configuration.

        Args:
            name (str, optional): Name for the snapshot, defaults to timestamp

        Returns:
            str: Name of the created snapshot
        """
        if not name:
            name = f"snapshot_{int(time.time())}"

        snapshot_dir = os.path.join(os.path.dirname(self._config_file), "snapshots")
        os.makedirs(snapshot_dir, exist_ok=True)

        snapshot_file = os.path.join(snapshot_dir, f"{name}.yaml")

        try:
            with open(snapshot_file, "w") as f:
                yaml.dump(self._config, f, default_flow_style=False)

            logger.info("Configuration snapshot created")
            return name

        except Exception as e:
            logger.error(f"Failed to create configuration snapshot: {str(e)}")
            return None


# Create global instance
config_manager = SimpleConfig()
config = config_manager
