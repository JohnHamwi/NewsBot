"""
Configuration Manager Module

This module provides configuration management functionality for NewsBot.
"""

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml

from src.core.config_validator import apply_defaults, validate_config
from src.utils.base_logger import base_logger as logger


class ConfigManager:
    """
    Configuration manager that loads settings from a YAML file and environment variables.
    Supports type conversion, caching, and environment variable substitution.
    """

    _instance: Optional["ConfigManager"] = None

    def __new__(cls, config_file="config/config.yaml"):
        """
        Implement singleton pattern to ensure only one ConfigManager instance exists.

        Args:
            config_file (str): Path to the configuration file

        Returns:
            The singleton ConfigManager instance
        """
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_file="config/config.yaml"):
        """
        Initialize the configuration manager with the specified config file.

        Args:
            config_file (str): Path to the configuration file
        """
        # Only initialize once due to singleton pattern
        if getattr(self, "_initialized", False):
            return

        self._config_file = config_file
        self._config = None
        self._last_check_time = 0
        self._last_modified_time = 0
        self._runtime_overrides = {}
        self._initialized = True

    def load(self):
        """
        Load configuration from the YAML file and substitute environment variables.
        """
        if not self._config:  # Only load if not already loaded
            self._load_config()

    def _load_config(self):
        """
        Internal method to load configuration from the YAML file.
        """
        try:
            # Load environment variables
            from dotenv import load_dotenv

            load_dotenv("config/.env")

            # Load YAML config
            with open(self._config_file, "r", encoding="utf-8") as file:
                self._config = yaml.safe_load(file) or {}
                logger.debug(f"✅ Configuration loaded from {self._config_file}")

            # Substitute environment variables
            self._substitute_env_vars(self._config)

            # Get file modification time
            self._last_modified_time = os.path.getmtime(self._config_file)
            self._last_check_time = time.time()

        except FileNotFoundError:
            logger.warning(f"⚠️ Configuration file not found: {self._config_file}")
            self._config = {}
        except yaml.YAMLError as e:
            logger.error(f"❌ Error parsing YAML configuration: {e}")
            self._config = {}
        except Exception as e:
            logger.error(f"❌ Unexpected error loading configuration: {e}")
            self._config = {}

    def reload_config(self):
        """
        Force reload the configuration file.
        """
        self._load_config()

    def _substitute_env_vars(self, config_dict):
        """
        Recursively substitute environment variables in the configuration.

        Args:
            config_dict (dict): Dictionary to substitute values in
        """
        for key, value in config_dict.items():
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
                            config_dict[key] = int(
                                env_value
                            )  # Convert to int if possible
                        elif env_value.lower() in ("true", "false"):
                            config_dict[key] = (
                                env_value.lower() == "true"
                            )  # Convert to bool
                        else:
                            config_dict[key] = env_value
                    except BaseException:
                        config_dict[key] = env_value

    def get(self, key_path, default=None):
        """
        Get a configuration value by its path.

        Args:
            key_path (str): Dot-separated path to the configuration value
            default: Default value to return if the key is not found

        Returns:
            The configuration value, or the default if not found
        """
        self.check_for_changes()

        # Check runtime overrides first
        if key_path in self._runtime_overrides:
            return self._runtime_overrides[key_path]

        # If no config loaded, load it now
        if self._config is None:
            self.load()

        keys = key_path.split(".")
        current = self._config

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default

        # Return the actual value type, don't convert to string
        return current

    def set_override(self, key_path, value):
        """
        Set a runtime override for a configuration value.

        Args:
            key_path (str): Dot-separated path to the configuration value
            value: The value to set
        """
        self._runtime_overrides[key_path] = value

    def clear_override(self, key_path=None):
        """
        Clear a runtime override, or all overrides if no key is specified.

        Args:
            key_path (str, optional): Dot-separated path to clear, or None for all
        """
        if key_path is None:
            self._runtime_overrides = {}
        elif key_path in self._runtime_overrides:
            del self._runtime_overrides[key_path]

    def check_for_changes(self):
        """
        Check if the configuration file has changed and reload if necessary.
        """
        now = time.time()
        if now - self._last_check_time < 5:
            return False

        try:
            # Check for changes only every 5 seconds
            self._last_check_time = now

            if not os.path.exists(self._config_file):
                return False

            mod_time = os.path.getmtime(self._config_file)
            if mod_time > self._last_modified_time:
                self._load_config()
                return True

        except Exception:
            pass

        return False

    def validate(self) -> bool:
        """
        Validate the configuration against the schema.

        Returns:
            bool: True if the configuration is valid, False otherwise
        """
        self.load()

        # Use schema validation
        is_valid, errors = validate_config(self._config)

        if not is_valid:
            for error in errors:
                logging.getLogger("NewsBot").error(f"Configuration error: {error}")
            return False

        # Apply defaults for missing values
        self._config = apply_defaults(self._config)

        return True

    def get_validation_errors(self) -> List[str]:
        """
        Get a list of validation errors for the current configuration.

        Returns:
            List of error messages
        """
        self.load()
        _, errors = validate_config(self._config)
        return errors

    @property
    def raw_config(self):
        """
        Get a copy of the raw configuration dictionary.

        Returns:
            dict: A copy of the configuration dictionary
        """
        if self._config is None:
            self.load()
        return self._config.copy() if self._config else {}


# Create global instance
config = ConfigManager()
