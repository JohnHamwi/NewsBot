"""
Text utilities for the NewsBot.

Contains functions for text processing, cleaning, and manipulation.
"""

import re
import unicodedata


def remove_emojis(text: str) -> str:
    """
    Remove emojis and other special characters from text.

    Args:
        text: The input text to process

    Returns:
        The text with emojis removed
    """
    if not text:
        return ""

    # Pattern to match emoji characters
    emoji_pattern = re.compile(
        "["
        "\U0001f600-\U0001f64f"  # emoticons
        "\U0001f300-\U0001f5ff"  # symbols & pictographs
        "\U0001f680-\U0001f6ff"  # transport & map symbols
        "\U0001f700-\U0001f77f"  # alchemical symbols
        "\U0001f780-\U0001f7ff"  # Geometric Shapes
        "\U0001f800-\U0001f8ff"  # Supplemental Arrows-C
        "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
        "\U0001fa00-\U0001fa6f"  # Chess Symbols
        "\U0001fa70-\U0001faff"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027b0"  # Dingbats
        "\U000024c2-\U0001f251"
        "]+",
        flags=re.UNICODE,
    )

    # Remove emojis
    text = emoji_pattern.sub(r"", text)

    # Remove control characters
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")

    # Clean up double spaces and whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def truncate_text(text: str, max_length: int = 1000, add_ellipsis: bool = True) -> str:
    """
    Truncate text to a maximum length.

    Args:
        text: The input text to truncate
        max_length: The maximum length
        add_ellipsis: Whether to add "..." at the end of truncated text

    Returns:
        The truncated text
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    truncated = text[:max_length]

    # Try to truncate at word boundary
    last_space = truncated.rfind(" ")
    if (
        last_space > max_length * 0.8
    ):  # Only truncate at word if we're not losing too much
        truncated = truncated[:last_space]

    if add_ellipsis:
        truncated += "..."

    return truncated
