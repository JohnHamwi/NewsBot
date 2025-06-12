"""
AI Service

This service handles all AI-related functionality including translation
and title generation for the NewsBot. Extracted from fetch_view.py.
"""

import asyncio
import os
import re
from typing import Optional, Tuple

import openai

from src.utils import error_handler
from src.utils.base_logger import base_logger as logger
from src.utils.text_utils import remove_emojis


class AIService:
    """Service for handling AI translation and title generation."""

    def __init__(self, bot):
        """Initialize the AI service with bot instance."""
        self.bot = bot
        self.logger = logger

        # Initialize OpenAI client
        self.openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def process_text_with_ai(
        self, arabic_text: str, timeout: int = 60
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Process Arabic text with AI to generate English translation and title.

        Args:
            arabic_text: The Arabic text to process
            timeout: AI processing timeout in seconds

        Returns:
            Tuple of (english_translation, ai_title) or (None, None) if failed
        """
        try:
            return await asyncio.wait_for(
                self._process_text_internal(arabic_text), timeout=timeout
            )
        except asyncio.TimeoutError:
            self.logger.error(f"[AI] AI processing timed out after {timeout} seconds")
            return None, None
        except Exception as e:
            self.logger.error(f"[AI] AI processing failed: {str(e)}")
            await error_handler.send_error_embed(
                "AI Processing Error",
                e,
                context=f"Text length: {len(arabic_text)} characters",
                bot=self.bot,
            )
            return None, None

    async def _process_text_internal(
        self, arabic_text: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Internal AI processing logic."""
        try:
            # Clean the Arabic text first
            cleaned_text = self._clean_arabic_text(arabic_text)

            if not cleaned_text.strip():
                self.logger.warning("[AI] No text to process after cleaning")
                return None, None

            # Generate translation and title
            english_translation = await self._translate_to_english(cleaned_text)
            ai_title = await self._generate_title(english_translation or cleaned_text)

            return english_translation, ai_title

        except Exception as e:
            self.logger.error(f"[AI] Error in AI processing: {str(e)}")
            raise

    def _clean_arabic_text(self, text: str) -> str:
        """Clean Arabic text for AI processing."""
        if not text:
            return ""

        # Remove emojis
        cleaned = remove_emojis(text)

        # Remove hashtags
        cleaned = re.sub(r"#\w+", "", cleaned)

        # Remove URLs
        cleaned = re.sub(r"https?://\S+", "", cleaned)

        # Remove specific patterns like network signatures
        cleaned = re.sub(r"\.?شبكة.?اخبار.?سوريا.?_?الحرة", "", cleaned)

        # Normalize whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned

    async def _translate_to_english(self, arabic_text: str) -> Optional[str]:
        """Translate Arabic text to English using OpenAI."""
        try:
            self.logger.debug("[AI] Starting translation to English")

            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a professional Arabic-to-English translator specializing in news content. "
                            "Translate the following Arabic text to clear, natural English. "
                            "Maintain the original meaning and tone. "
                            "If the text contains news content, preserve important details like names, places, and dates."
                        ),
                    },
                    {"role": "user", "content": arabic_text},
                ],
                max_tokens=1000,
                temperature=0.3,
            )

            translation = response.choices[0].message.content.strip()

            if translation:
                # Clean the translation
                translation = self._clean_translation(translation)
                self.logger.debug(
                    f"[AI] Translation completed: {len(translation)} characters"
                )
                return translation
            else:
                self.logger.warning("[AI] Empty translation received")
                return None

        except Exception as e:
            self.logger.error(f"[AI] Translation failed: {str(e)}")
            return None

    async def _generate_title(self, text: str) -> Optional[str]:
        """Generate a concise Arabic title from the text using OpenAI."""
        try:
            self.logger.debug("[AI] Starting Arabic title generation")

            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a news headline writer for Arabic news. "
                            "Create a concise, informative Arabic headline (3-6 words) from the following text. "
                            "The headline should capture the main news event or topic in Arabic. "
                            "Use active voice and present tense when possible. "
                            "Do not use quotation marks or special formatting. "
                            "Respond ONLY in Arabic."
                        ),
                    },
                    {
                        "role": "user",
                        "content": text[
                            :500
                        ],  # Limit input length for title generation
                    },
                ],
                max_tokens=50,
                temperature=0.3,
            )

            title = response.choices[0].message.content.strip()

            if title:
                # Clean the title
                title = self._clean_title(title)
                self.logger.debug(f"[AI] Arabic title generated: {title}")
                return title
            else:
                self.logger.warning("[AI] Empty Arabic title received")
                return None

        except Exception as e:
            self.logger.error(f"[AI] Arabic title generation failed: {str(e)}")
            return None

    def _clean_translation(self, translation: str) -> str:
        """Clean the AI-generated translation."""
        if not translation:
            return ""

        # Remove any remaining hashtags or URLs
        cleaned = re.sub(r"#\w+", "", translation)
        cleaned = re.sub(r"https?://\S+", "", cleaned)

        # Remove quotation marks that might be added by AI
        cleaned = cleaned.strip("\"'")

        # Normalize whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned

    def _clean_title(self, title: str) -> str:
        """Clean the AI-generated title."""
        if not title:
            return ""

        # Remove quotation marks
        cleaned = title.strip("\"'")

        # Remove any prefixes like "Title:" or "Headline:"
        cleaned = re.sub(r"^(title|headline):\s*", "", cleaned, flags=re.IGNORECASE)

        # Ensure it's not too long (max 6 words)
        words = cleaned.split()
        if len(words) > 6:
            cleaned = " ".join(words[:6])

        # Capitalize first letter
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]

        return cleaned.strip()

    def extract_arabic_title(self, arabic_text: str, max_words: int = 5) -> str:
        """Extract a short Arabic title from the text."""
        if not arabic_text:
            return ""

        # Clean the text
        cleaned = self._clean_arabic_text(arabic_text)

        if not cleaned:
            return ""

        # Split into words and take the first few
        words = cleaned.split()
        title_length = min(max_words, max(3, len(words)))

        if title_length > 0:
            return " ".join(words[:title_length])

        return ""
