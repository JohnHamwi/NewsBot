"""
Syrian Time Localization Module

This module provides functionality to handle Syrian local time (Damascus timezone)
for news events and timestamps.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import pytz

# Syrian timezone (Damascus)
SYRIAN_TIMEZONE = pytz.timezone("Asia/Damascus")


class SyrianTimeHandler:
    """Handles Syrian local time conversions and formatting."""

    def __init__(self):
        """Initialize the Syrian time handler."""
        self.syrian_tz = SYRIAN_TIMEZONE

    def now_syrian(self) -> datetime:
        """
        Get current time in Syrian timezone.

        Returns:
            Current datetime in Syrian timezone
        """
        return datetime.now(self.syrian_tz)

    def to_syrian_time(self, dt: datetime) -> datetime:
        """
        Convert a datetime to Syrian timezone.

        Args:
            dt: Datetime to convert (can be naive or timezone-aware)

        Returns:
            Datetime converted to Syrian timezone
        """
        if dt.tzinfo is None:
            # Assume UTC if naive
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(self.syrian_tz)

    def format_syrian_time(
        self,
        dt: Optional[datetime] = None,
        include_timezone: bool = True,
        format_style: str = "full",
    ) -> str:
        """
        Format datetime in Syrian timezone.

        Args:
            dt: Datetime to format (defaults to now)
            include_timezone: Whether to include timezone info
            format_style: 'full', 'short', 'time_only', or 'date_only'

        Returns:
            Formatted time string
        """
        if dt is None:
            dt = self.now_syrian()
        elif dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
            dt = dt.astimezone(self.syrian_tz)
        elif dt.tzinfo != self.syrian_tz:
            dt = dt.astimezone(self.syrian_tz)

        # Format based on style
        if format_style == "full":
            if include_timezone:
                return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
            else:
                return dt.strftime("%Y-%m-%d %H:%M:%S")
        elif format_style == "short":
            if include_timezone:
                return dt.strftime("%m/%d %H:%M %Z")
            else:
                return dt.strftime("%m/%d %H:%M")
        elif format_style == "time_only":
            if include_timezone:
                return dt.strftime("%H:%M:%S %Z")
            else:
                return dt.strftime("%H:%M:%S")
        elif format_style == "date_only":
            return dt.strftime("%Y-%m-%d")
        else:
            # Default to full format
            if include_timezone:
                return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
            else:
                return dt.strftime("%Y-%m-%d %H:%M:%S")

    def format_relative_time(self, dt: datetime) -> str:
        """
        Format time relative to now in Syrian timezone.

        Args:
            dt: Datetime to format

        Returns:
            Relative time string (e.g., "2 hours ago", "just now")
        """
        now = self.now_syrian()

        # Convert to Syrian time if needed
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(self.syrian_tz)

        diff = now - dt

        if diff.total_seconds() < 60:
            return "just now"
        elif diff.total_seconds() < 3600:  # Less than 1 hour
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff.total_seconds() < 86400:  # Less than 1 day
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.days < 7:  # Less than 1 week
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        else:
            # For older dates, show the actual date
            return self.format_syrian_time(dt, format_style="short")

    def get_timezone_info(self) -> dict:
        """
        Get information about Syrian timezone.

        Returns:
            Dictionary with timezone information
        """
        now = self.now_syrian()
        utc_now = datetime.now(timezone.utc)

        # Calculate offset
        offset = now.utcoffset()
        offset_hours = offset.total_seconds() / 3600

        return {
            "timezone_name": "Asia/Damascus",
            "current_time": self.format_syrian_time(now),
            "utc_offset": f"UTC{'+' if offset_hours >= 0 else ''}{offset_hours:g}",
            "is_dst": now.dst() != timedelta(0),
            "timezone_abbreviation": now.strftime("%Z"),
        }

    def parse_time_mentions(self, text: str) -> list:
        """
        Parse time mentions in text and convert to Syrian time.

        Args:
            text: Text to parse for time mentions

        Returns:
            List of detected time mentions with Syrian time
        """
        import re

        time_patterns = [
            # Common time formats
            r"\b(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)?\b",
            r"\b(\d{1,2}):(\d{2}):(\d{2})\s*(AM|PM|am|pm)?\b",
            # Arabic time indicators
            r"الساعة\s*(\d{1,2}):(\d{2})",
            r"في\s*(\d{1,2}):(\d{2})",
        ]

        detected_times = []

        for pattern in time_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                detected_times.append(
                    {
                        "original": match.group(0),
                        "position": match.span(),
                        "syrian_context": f"Syrian time: {match.group(0)}",
                    }
                )

        return detected_times


# Global instance for easy access
syrian_time_handler = SyrianTimeHandler()


def now_syrian() -> datetime:
    """
    Convenience function to get current Syrian time.

    Returns:
        Current datetime in Syrian timezone
    """
    return syrian_time_handler.now_syrian()


def to_syrian_time(dt: datetime) -> datetime:
    """
    Convenience function to convert datetime to Syrian timezone.

    Args:
        dt: Datetime to convert

    Returns:
        Datetime in Syrian timezone
    """
    return syrian_time_handler.to_syrian_time(dt)


def format_syrian_time(
    dt: Optional[datetime] = None,
    include_timezone: bool = True,
    format_style: str = "full",
) -> str:
    """
    Convenience function to format Syrian time.

    Args:
        dt: Datetime to format (defaults to now)
        include_timezone: Whether to include timezone info
        format_style: Format style

    Returns:
        Formatted time string
    """
    return syrian_time_handler.format_syrian_time(dt, include_timezone, format_style)


def format_relative_syrian_time(dt: datetime) -> str:
    """
    Convenience function to format relative Syrian time.

    Args:
        dt: Datetime to format

    Returns:
        Relative time string
    """
    return syrian_time_handler.format_relative_time(dt)


def get_syrian_timezone_info() -> dict:
    """
    Convenience function to get Syrian timezone info.

    Returns:
        Dictionary with timezone information
    """
    return syrian_time_handler.get_timezone_info()
