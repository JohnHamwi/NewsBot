"""
Content Cleaner Module

This module provides functionality to clean news content by removing sources,
emojis, Telegram links, hashtags, and other unwanted elements.
"""

import re
from typing import List, Tuple


class ContentCleaner:
    """Cleans news content by removing unwanted elements."""

    def __init__(self):
        """Initialize the content cleaner with compiled patterns."""
        self.patterns = self._compile_patterns()

    def _compile_patterns(self) -> dict:
        """Compile regex patterns for efficient content cleaning."""
        patterns = {}

        # Source attribution patterns (Arabic and English)
        patterns["sources"] = [
            # Arabic source patterns
            re.compile(r"المصدر\s*:.*$", re.MULTILINE | re.IGNORECASE),
            re.compile(r"مصدر\s*:.*$", re.MULTILINE | re.IGNORECASE),
            re.compile(r"من\s*:.*$", re.MULTILINE | re.IGNORECASE),
            re.compile(r"عن\s*:.*$", re.MULTILINE | re.IGNORECASE),
            re.compile(r"نقلاً?\s*عن\s*:.*$", re.MULTILINE | re.IGNORECASE),
            re.compile(r"نقلاً?\s*عن.*$", re.MULTILINE | re.IGNORECASE),  # Without colon
            re.compile(r"بحسب\s*:.*$", re.MULTILINE | re.IGNORECASE),
            re.compile(r"وفقاً?\s*لـ?.*$", re.MULTILINE | re.IGNORECASE),
            re.compile(r"حسب\s*:.*$", re.MULTILINE | re.IGNORECASE),
            re.compile(r"المرجع\s*:.*$", re.MULTILINE | re.IGNORECASE),
            re.compile(r"الخبر\s*:.*$", re.MULTILINE | re.IGNORECASE),
            # More comprehensive Arabic patterns
            re.compile(r"المصدر.*$", re.MULTILINE | re.IGNORECASE),  # Without colon
            re.compile(
                r"قناة\s+[\u0600-\u06FF\s]+.*$", re.MULTILINE | re.IGNORECASE
            ),  # Channel mentions
            re.compile(
                r"شبكة\s+[\u0600-\u06FF\s]+.*$", re.MULTILINE | re.IGNORECASE
            ),  # Network mentions
            re.compile(
                r"وكالة\s+[\u0600-\u06FF\s]+.*$", re.MULTILINE | re.IGNORECASE
            ),  # Agency mentions
            # English source patterns
            re.compile(r"source\s*:.*$", re.MULTILINE | re.IGNORECASE),
            re.compile(r"via\s*:.*$", re.MULTILINE | re.IGNORECASE),
            re.compile(r"from\s*:.*$", re.MULTILINE | re.IGNORECASE),
            re.compile(r"according\s*to.*$", re.MULTILINE | re.IGNORECASE),
            re.compile(r"reported\s*by.*$", re.MULTILINE | re.IGNORECASE),
            re.compile(r"credit\s*:.*$", re.MULTILINE | re.IGNORECASE),
            re.compile(r"courtesy\s*of.*$", re.MULTILINE | re.IGNORECASE),
            # Channel/media mentions
            re.compile(r"@\w+", re.IGNORECASE),  # @mentions
            re.compile(r"قناة\s*\w+", re.IGNORECASE),  # Arabic "channel"
            re.compile(r"شبكة\s*\w+", re.IGNORECASE),  # Arabic "network"
            re.compile(r"موقع\s*\w+", re.IGNORECASE),  # Arabic "website"
            re.compile(r"صفحة\s*\w+", re.IGNORECASE),  # Arabic "page"
        ]

        # Emoji pattern (comprehensive Unicode ranges)
        patterns["emojis"] = re.compile(
            "["
            "\U0001f600-\U0001f64f"  # emoticons
            "\U0001f300-\U0001f5ff"  # symbols & pictographs
            "\U0001f680-\U0001f6ff"  # transport & map symbols
            "\U0001f700-\U0001f77f"  # alchemical symbols
            "\U0001f780-\U0001f7ff"  # Geometric Shapes Extended
            "\U0001f800-\U0001f8ff"  # Supplemental Arrows-C
            "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
            "\U0001fa00-\U0001fa6f"  # Chess Symbols
            "\U0001fa70-\U0001faff"  # Symbols and Pictographs Extended-A
            "\U00002702-\U000027b0"  # Dingbats
            "\U000024c2-\U0001f251"  # Enclosed characters
            "\U0001f004"  # Mahjong tile
            "\U0001f0cf"  # Playing card
            "\U0001f18e"  # Negative squared AB
            "\U0001f191-\U0001f251"  # Squared symbols
            "\U0001f926-\U0001f937"  # Additional emoticons
            "\U0001f938-\U0001f93a"  # More emoticons
            "\U0001f93c-\U0001f945"  # Even more emoticons
            "\U0001f947-\U0001f978"  # Awards and more
            "\U0001f97a-\U0001f9cb"  # Additional symbols
            "\U0001f9cd-\U0001f9ff"  # More symbols
            "\U0001fa70-\U0001faff"  # Extended symbols
            "]+",
            flags=re.UNICODE,
        )

        # URL patterns
        patterns["urls"] = [
            # HTTP/HTTPS URLs
            re.compile(
                r"https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?",
                re.IGNORECASE,
            ),
            # Telegram links
            re.compile(r"t\.me/\w+", re.IGNORECASE),
            re.compile(r"telegram\.me/\w+", re.IGNORECASE),
            # Generic domain patterns
            re.compile(
                r"\b\w+\.(com|org|net|gov|edu|info|co|me|tv|news)\b", re.IGNORECASE
            ),
        ]

        # Hashtag patterns
        patterns["hashtags"] = [
            re.compile(r"#\w+", re.IGNORECASE),  # English hashtags
            re.compile(
                r"#[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+",
                re.IGNORECASE,
            ),  # Arabic hashtags
        ]

        # Additional cleanup patterns
        patterns["cleanup"] = [
            # Multiple spaces/newlines
            re.compile(r"\s+", re.MULTILINE),
            # Leading/trailing whitespace
            re.compile(r"^\s+|\s+$", re.MULTILINE),
            # Empty lines
            re.compile(r"\n\s*\n", re.MULTILINE),
            # Special characters that might be artifacts
            re.compile(r"[▪▫•◦‣⁃]", re.IGNORECASE),  # Bullet points
            re.compile(r"[⬅➡⬆⬇↗↘↙↖]", re.IGNORECASE),  # Arrows
            re.compile(r"[✓✔✗✘]", re.IGNORECASE),  # Check marks
        ]

        # Telegram-specific patterns
        patterns["telegram"] = [
            # Forward indicators
            re.compile(r"Forwarded from.*$", re.MULTILINE | re.IGNORECASE),
            re.compile(r"محول من.*$", re.MULTILINE | re.IGNORECASE),
            # Join channel messages
            re.compile(r"Join.*channel.*$", re.MULTILINE | re.IGNORECASE),
            re.compile(r"انضم.*قناة.*$", re.MULTILINE | re.IGNORECASE),
            # Subscribe messages
            re.compile(r"Subscribe.*$", re.MULTILINE | re.IGNORECASE),
            re.compile(r"اشترك.*$", re.MULTILINE | re.IGNORECASE),
        ]

        # Media reference patterns (video IDs, media codes, etc.)
        patterns["media_refs"] = [
            # YouTube-style video IDs and similar codes
            re.compile(r"-[A-Za-z0-9]{6,}", re.IGNORECASE),  # Matches -16DSuWU pattern
            re.compile(
                r"[A-Za-z0-9]{8,}-[A-Za-z0-9]{4,}", re.IGNORECASE
            ),  # UUID-like patterns
            # Common media reference patterns
            re.compile(
                r"\b[A-Za-z0-9]{10,}\b", re.IGNORECASE
            ),  # Long alphanumeric codes
            # Video/media indicators followed by codes
            re.compile(
                r"(?:video|media|clip|episode)[\s:]*[A-Za-z0-9-_]{6,}", re.IGNORECASE
            ),
            # Arabic equivalents
            re.compile(r"(?:فيديو|مقطع|حلقة)[\s:]*[A-Za-z0-9-_]{6,}", re.IGNORECASE),
        ]

        return patterns

    def remove_sources(self, text: str) -> str:
        """Remove source attributions from text."""
        for pattern in self.patterns["sources"]:
            text = pattern.sub("", text)
        return text

    def remove_emojis(self, text: str) -> str:
        """Remove all emojis from text."""
        return self.patterns["emojis"].sub("", text)

    def remove_urls(self, text: str) -> str:
        """Remove URLs and links from text."""
        for pattern in self.patterns["urls"]:
            text = pattern.sub("", text)
        return text

    def remove_hashtags(self, text: str) -> str:
        """Remove hashtags from text."""
        for pattern in self.patterns["hashtags"]:
            text = pattern.sub("", text)
        return text

    def remove_telegram_artifacts(self, text: str) -> str:
        """Remove Telegram-specific artifacts."""
        for pattern in self.patterns["telegram"]:
            text = pattern.sub("", text)
        return text

    def remove_media_references(self, text: str) -> str:
        """Remove media reference codes and IDs."""
        for pattern in self.patterns["media_refs"]:
            text = pattern.sub("", text)
        return text

    def cleanup_whitespace(self, text: str) -> str:
        """Clean up excessive whitespace and formatting."""
        # Replace multiple spaces with single space
        text = re.sub(r" +", " ", text)
        # Replace multiple newlines with single newline
        text = re.sub(r"\n+", "\n", text)
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split("\n")]
        # Remove empty lines
        lines = [line for line in lines if line]
        return "\n".join(lines)

    def clean_content(self, text: str, preserve_structure: bool = True) -> str:
        """
        Perform comprehensive content cleaning.

        Args:
            text: The text to clean
            preserve_structure: Whether to preserve paragraph structure

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        original_text = text

        # Step 1: Remove sources and attributions
        text = self.remove_sources(text)

        # Step 2: Remove Telegram artifacts
        text = self.remove_telegram_artifacts(text)

        # Step 3: Remove URLs and links
        text = self.remove_urls(text)

        # Step 4: Remove hashtags
        text = self.remove_hashtags(text)

        # Step 5: Remove media references
        text = self.remove_media_references(text)

        # Step 6: Remove emojis
        text = self.remove_emojis(text)

        # Step 7: Clean up whitespace
        text = self.cleanup_whitespace(text)

        # Step 8: Final validation
        if len(text.strip()) < 10:  # If text is too short after cleaning
            # Return original but with minimal cleaning
            text = self.remove_urls(original_text)
            text = self.remove_hashtags(text)
            text = self.cleanup_whitespace(text)

        return text.strip()

    def get_cleaning_stats(self, original: str, cleaned: str) -> dict:
        """
        Get statistics about what was cleaned.

        Args:
            original: Original text
            cleaned: Cleaned text

        Returns:
            Dictionary with cleaning statistics
        """
        return {
            "original_length": len(original),
            "cleaned_length": len(cleaned),
            "reduction_percentage": (
                round((1 - len(cleaned) / len(original)) * 100, 1) if original else 0
            ),
            "emojis_removed": len(self.patterns["emojis"].findall(original)),
            "urls_removed": sum(
                len(pattern.findall(original)) for pattern in self.patterns["urls"]
            ),
            "hashtags_removed": sum(
                len(pattern.findall(original)) for pattern in self.patterns["hashtags"]
            ),
            "sources_removed": sum(
                len(pattern.findall(original)) for pattern in self.patterns["sources"]
            ),
        }


# Global instance for easy access
content_cleaner = ContentCleaner()


def clean_news_content(text: str, preserve_structure: bool = True) -> str:
    """
    Convenience function to clean news content.

    Args:
        text: The text to clean
        preserve_structure: Whether to preserve paragraph structure

    Returns:
        Cleaned text
    """
    return content_cleaner.clean_content(text, preserve_structure)


def get_content_cleaning_stats(original: str, cleaned: str) -> dict:
    """
    Convenience function to get cleaning statistics.

    Args:
        original: Original text
        cleaned: Cleaned text

    Returns:
        Dictionary with cleaning statistics
    """
    return content_cleaner.get_cleaning_stats(original, cleaned)
