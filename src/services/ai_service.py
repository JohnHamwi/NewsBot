# =============================================================================
# NewsBot AI Service Module
# =============================================================================
# AI-related functionality including translation, title generation, and location
# detection using OpenAI GPT models for comprehensive text processing
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import asyncio
import os
import re
from typing import Optional, Tuple, Dict, Any

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import openai

# =============================================================================
# Local Application Imports
# =============================================================================
from src.utils.ai_utils import call_chatgpt_for_news
from src.utils import error_handler
from src.utils.base_logger import base_logger as logger
from src.utils.text_utils import remove_emojis

# =============================================================================
# AI Service Class
# =============================================================================

class AIService:
    """Service for handling AI translation, title generation, and location detection."""

    def __init__(self, bot):
        """Initialize the AI service with bot instance."""
        self.bot = bot
        self.logger = logger

        # Initialize OpenAI client
        self.openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def process_text_with_ai(
        self, arabic_text: str, timeout: int = 60
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Process Arabic text with AI to generate English translation, title, and location.

        Args:
            arabic_text: The Arabic text to process
            timeout: AI processing timeout in seconds

        Returns:
            Tuple of (english_translation, ai_title, location) or (None, None, None) if failed
        """
        try:
            return await asyncio.wait_for(
                self._process_text_internal(arabic_text), timeout=timeout
            )
        except asyncio.TimeoutError:
            self.logger.error(f"[AI] AI processing timed out after {timeout} seconds")
            return None, None, None
        except Exception as e:
            self.logger.error(f"[AI] AI processing failed: {str(e)}")
            await error_handler.send_error_embed(
                "AI Processing Error",
                e,
                context=f"Text length: {len(arabic_text)} characters",
                bot=self.bot,
            )
            return None, None, None

    async def _process_text_internal(
        self, arabic_text: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Internal AI processing logic using enhanced AI utils."""
        try:
            # Clean the Arabic text first
            cleaned_text = self._clean_arabic_text(arabic_text)

            if not cleaned_text.strip():
                self.logger.warning("[AI] No text to process after cleaning")
                return None, None, None

            # Use the enhanced AI utils function for comprehensive processing
            try:
                # Convert AsyncOpenAI to regular OpenAI for compatibility
                sync_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

                ai_result = call_chatgpt_for_news(cleaned_text, sync_client, self.logger)

                if ai_result and isinstance(ai_result, dict):
                    english_translation = ai_result.get("translation")
                    ai_title = ai_result.get("title", "أخبار سورية")
                    location = ai_result.get("location", "Unknown")

                    # Validate that we got meaningful results
                    if english_translation and english_translation.strip():
                        self.logger.info(f"[AI] Enhanced AI processing completed - Location: {location}")
                        return english_translation, ai_title, location
                    else:
                        self.logger.warning("[AI] Enhanced AI processing returned empty translation")
                        return None, None, None
                else:
                    self.logger.warning("[AI] Enhanced AI processing returned invalid result")
                    return None, None, None

            except Exception as e:
                self.logger.error(f"[AI] Enhanced AI processing failed, falling back to legacy method: {str(e)}")
                # Fallback to legacy processing without location
                english_translation = await self._translate_to_english(cleaned_text)
                ai_title = await self._generate_title(english_translation or cleaned_text)
                return english_translation, ai_title, "Unknown"

        except Exception as e:
            self.logger.error(f"[AI] Error in AI processing: {str(e)}")
            raise

    def get_ai_result_comprehensive(self, arabic_text: str) -> Dict[str, Any]:
        """
        Get comprehensive AI analysis including location, ad detection, and Syria relevance.

        Args:
            arabic_text: The Arabic text to analyze

        Returns:
            Dictionary with analysis results
        """
        try:
            cleaned_text = self._clean_arabic_text(arabic_text)

            if not cleaned_text.strip():
                return {
                    "title": "News Update",
                    "translation": "",
                    "location": "Unknown",
                    "is_ad": False,
                    "is_syria_related": False
                }

            # Use the enhanced AI utils function
            sync_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            result = call_chatgpt_for_news(cleaned_text, sync_client, self.logger)

            # Ensure all required fields are present
            if result and isinstance(result, dict):
                return {
                    "title": result.get("title", "أخبار سورية"),
                    "translation": result.get("translation", ""),
                    "location": result.get("location", "Unknown"),
                    "is_ad": result.get("is_ad", False),
                    "is_syria_related": result.get("is_syria_related", False)
                }
            else:
                return {
                    "title": "أخبار سورية",
                    "translation": "AI processing failed",
                    "location": "Unknown",
                    "is_ad": False,
                    "is_syria_related": False
                }

        except Exception as e:
            self.logger.error(f"[AI] Comprehensive AI analysis failed: {str(e)}")
            return {
                "title": "أخبار سورية",
                "translation": f"AI analysis failed: {str(e)}",
                "location": "Unknown",
                "is_ad": False,
                "is_syria_related": False
            }

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

        # Don't capitalize for Arabic text - just return as is
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
