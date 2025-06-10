"""
JSON Cache Module

This module provides JSON-based caching functionality for the bot.
"""

import json
import os
from typing import Any, Optional, List, Dict
from src.utils.base_logger import base_logger as logger
import datetime


class JSONCache:
    """
    JSON file-based cache manager for the bot.
    Stores:
    - latest_news: List[str]
    - telegram_channels: List[str]
    """

    def __init__(self, json_path: str = "data/botdata.json"):
        self.json_path = os.path.abspath(json_path)
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.json_path):
            with open(self.json_path, 'w') as f:
                json.dump({"latest_news": [], "telegram_channels": []}, f)

    def _read(self) -> Dict[str, Any]:
        self._ensure_file()
        with open(self.json_path, 'r') as f:
            return json.load(f)

    def _write(self, data: Dict[str, Any]):
        with open(self.json_path, 'w') as f:
            json.dump(data, f, indent=2)

    async def save(self):
        """Explicitly save the current cache to disk and log the save."""
        try:
            # Just re-write the file with current data
            data = self._read()
            self._write(data)
            logger.info("✅ Cache saved to botdata.json")
        except Exception as e:
            logger.error(f"Failed to save cache: {str(e)}")

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        try:
            data = self._read()
            data[key] = value
            self._write(data)
            await self.save()
            return True
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {str(e)}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        try:
            data = self._read()
            return data.get(key)
        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {str(e)}")
            return None

    async def delete(self, key: str) -> bool:
        try:
            data = self._read()
            if key in data:
                del data[key]
                self._write(data)
                await self.save()
            return True
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {str(e)}")
            return False

    async def add_telegram_channel(self, channel: str) -> bool:
        if not channel:
            return False
        try:
            data = self._read()
            channel = channel.lower()
            now = datetime.datetime.utcnow().isoformat()
            # Prevent duplicate activation
            if channel in data.get("telegram_channels", []):
                logger.info(f"Channel {channel} is already activated.")
                return False
            # Remove from deactivated if present
            if channel in data.get("deactivated_channels", []):
                data["deactivated_channels"].remove(channel)
            if channel not in data.get("telegram_channels", []):
                data.setdefault("telegram_channels", []).append(channel)
            # Update metadata
            meta = data.setdefault("channel_metadata", {}).setdefault(channel, {})
            meta["status"] = "activated"
            meta["date_added"] = now
            meta["date_deactivated"] = None
            if "notes" in meta:
                del meta["notes"]
            self._write(data)
            await self.save()
            return True
        except Exception as e:
            logger.error(f"Failed to add telegram channel {channel}: {str(e)}")
            return False

    async def remove_telegram_channel(self, channel: str) -> bool:
        if not channel:
            return False
        try:
            data = self._read()
            channel = channel.lower()
            now = datetime.datetime.utcnow().isoformat()
            # Prevent duplicate deactivation
            if channel in data.get("deactivated_channels", []):
                logger.info(f"Channel {channel} is already deactivated.")
                return False
            if channel in data.get("telegram_channels", []):
                data["telegram_channels"].remove(channel)
                if channel not in data.get("deactivated_channels", []):
                    data.setdefault("deactivated_channels", []).append(channel)
                # Update metadata
                meta = data.setdefault("channel_metadata", {}).setdefault(channel, {})
                meta["status"] = "deactivated"
                meta["date_deactivated"] = now
                self._write(data)
                await self.save()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove telegram channel {channel}: {str(e)}")
            return False

    async def get_channel_metadata(self, channel: str) -> dict:
        try:
            data = self._read()
            return data.get("channel_metadata", {}).get(channel.lower(), {})
        except Exception as e:
            logger.error(f"Failed to get metadata for channel {channel}: {str(e)}")
            return {}

    async def list_telegram_channels(self, status: str = "activated") -> List[str]:
        try:
            data = self._read()
            if status == "activated":
                return sorted(data.get("telegram_channels", []))
            elif status == "deactivated":
                return sorted(data.get("deactivated_channels", []))
            elif status == "all":
                return sorted(set(data.get("telegram_channels", []) + data.get("deactivated_channels", [])))
            else:
                return []
        except Exception as e:
            logger.error(f"Failed to list telegram channels: {str(e)}")
            return []

    async def set_channel_status(self, channel: str, status: str) -> bool:
        """
        Set the status of a Telegram channel (activated/deactivated) and update metadata.
        """
        if not channel or status not in ("activated", "deactivated"):
            logger.error(f"Invalid channel or status for set_channel_status: {channel}, {status}")
            return False
        try:
            data = self._read()
            channel = channel.lower()
            now = datetime.datetime.utcnow().isoformat()
            meta = data.setdefault("channel_metadata", {}).setdefault(channel, {})
            meta["status"] = status
            if status == "deactivated":
                meta["date_deactivated"] = now
                # Move to deactivated_channels
                if channel not in data.get("deactivated_channels", []):
                    data.setdefault("deactivated_channels", []).append(channel)
                if channel in data.get("telegram_channels", []):
                    data["telegram_channels"].remove(channel)
                logger.info(f"Channel {channel} marked as deactivated.")
            elif status == "activated":
                meta["date_deactivated"] = None
                meta["date_added"] = now
                # Move to telegram_channels
                if channel not in data.get("telegram_channels", []):
                    data.setdefault("telegram_channels", []).append(channel)
                if channel in data.get("deactivated_channels", []):
                    data["deactivated_channels"].remove(channel)
                logger.info(f"Channel {channel} marked as activated.")
            self._write(data)
            await self.save()
            return True
        except Exception as e:
            logger.error(f"Failed to set status for channel {channel}: {str(e)}")
            return False
