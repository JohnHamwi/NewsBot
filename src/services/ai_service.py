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
from src.core.unified_config import unified_config as config

# =============================================================================
# AI Service Class
# =============================================================================

class AIService:
    """Service for handling AI translation, title generation, and location detection."""

    def __init__(self, bot):
        """Initialize the AI service with bot instance."""
        self.bot = bot
        self.logger = logger

        # Initialize OpenAI client using config manager
        api_key = config.get("openai.api_key")
        if not api_key:
            logger.error("❌ OpenAI API key not found in configuration")
            self.openai_client = None
        else:
            self.openai_client = openai.AsyncOpenAI(api_key=api_key)
            logger.debug("✅ OpenAI client initialized from config")

    async def process_text_with_ai(self, text: str, require_media: bool = True) -> tuple:
        """
        Enhanced AI processing with comprehensive debugging.
        """
        try:
            self.logger.debug(f"🧠 [AI-DEBUG] Starting AI processing for text (length: {len(text)})")
            self.logger.debug(f"🧠 [AI-DEBUG] Require media: {require_media}")
            
            # Clean and prepare text
            cleaned_text = self._clean_arabic_text(text)
            self.logger.debug(f"🧠 [AI-DEBUG] Text cleaned, new length: {len(cleaned_text)}")
            
            if len(cleaned_text) < 50:
                self.logger.debug(f"🧠 [AI-DEBUG] Text too short ({len(cleaned_text)} chars), skipping AI processing")
                return None, None, None

            # Call AI processing
            self.logger.debug("🧠 [AI-DEBUG] Calling ChatGPT for news processing...")
            ai_result = await call_chatgpt_for_news(cleaned_text)
            self.logger.debug(f"🧠 [AI-DEBUG] ChatGPT response type: {type(ai_result)}")
            
            if ai_result and isinstance(ai_result, dict):
                english_translation = ai_result.get("translation")
                ai_title = ai_result.get("title", "أخبار سورية")
                location = ai_result.get("location", "Unknown")
                
                self.logger.debug(f"🧠 [AI-DEBUG] Initial AI results:")
                self.logger.debug(f"🧠 [AI-DEBUG]   - Translation: {english_translation[:100] if english_translation else 'None'}...")
                self.logger.debug(f"🧠 [AI-DEBUG]   - Title: {ai_title}")
                self.logger.debug(f"🧠 [AI-DEBUG]   - Location: {location}")

                # If location is Unknown or not specific enough, use intelligent location detection
                if location in ["Unknown", "Syria", ""] and english_translation:
                    self.logger.debug("🧠 [AI-DEBUG] Basic AI returned generic location, trying intelligent detection...")
                    try:
                        intelligent_location = await self.detect_intelligent_location(cleaned_text, english_translation)
                        self.logger.debug(f"🧠 [AI-DEBUG] Intelligent location result: {intelligent_location}")
                        if intelligent_location and not intelligent_location.endswith("Unknown"):
                            location = intelligent_location.replace("📍 ", "")  # Remove emoji for consistency
                            self.logger.debug(f"🧠 [AI-DEBUG] Location improved from intelligent detection: {location}")
                    except Exception as e:
                        self.logger.debug(f"🧠 [AI-DEBUG] Intelligent location detection failed: {str(e)}")

                # Validate that we got meaningful results
                if english_translation and english_translation.strip():
                    self.logger.debug(f"🧠 [AI-DEBUG] AI processing completed successfully")
                    return english_translation, ai_title, location
                else:
                    self.logger.debug("🧠 [AI-DEBUG] No valid translation received")
            else:
                self.logger.debug(f"🧠 [AI-DEBUG] Invalid AI result format: {ai_result}")

        except Exception as e:
            self.logger.debug(f"🧠 [AI-DEBUG] Exception in AI processing: {str(e)}")
            self.logger.error(f"[AI] Error in AI processing: {str(e)}")

        self.logger.debug("🧠 [AI-DEBUG] AI processing failed, returning None")
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
                api_key = config.get("openai.api_key")
                if not api_key:
                    logger.error("❌ OpenAI API key not found in configuration")
                    return None, None, None
                
                sync_client = openai.OpenAI(api_key=api_key)
                ai_result = call_chatgpt_for_news(cleaned_text, sync_client, self.logger)

                if ai_result and isinstance(ai_result, dict):
                    english_translation = ai_result.get("translation")
                    ai_title = ai_result.get("title", "أخبار سورية")
                    location = ai_result.get("location", "Unknown")

                    # If location is Unknown or not specific enough, use intelligent location detection
                    if location in ["Unknown", "Syria", ""] and english_translation:
                        self.logger.info("[AI] Basic AI returned generic location, trying intelligent detection...")
                        try:
                            intelligent_location = await self.detect_intelligent_location(cleaned_text, english_translation)
                            if intelligent_location and not intelligent_location.endswith("Unknown"):
                                location = intelligent_location.replace("📍 ", "")  # Remove emoji for consistency
                                self.logger.info(f"[AI] Intelligent location detection improved result: {location}")
                        except Exception as e:
                            self.logger.warning(f"[AI] Intelligent location detection failed: {str(e)}")

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
            api_key = config.get("openai.api_key")
            if not api_key:
                logger.error("❌ OpenAI API key not found in configuration")
                return {
                    "title": "أخبار سورية",
                    "translation": "OpenAI API key not configured",
                    "location": "Unknown",
                    "is_ad": False,
                    "is_syria_related": False
                }
            
            sync_client = openai.OpenAI(api_key=api_key)
            result = call_chatgpt_for_news(cleaned_text, sync_client, self.logger)

            # Ensure all required fields are present
            if result and isinstance(result, dict):
                base_location = result.get("location", "Unknown")
                translation = result.get("translation", "")
                
                # If location is Unknown or not specific enough, use intelligent location detection
                final_location = base_location
                if base_location in ["Unknown", "Syria", ""] and translation:
                    self.logger.info("[AI] Basic AI returned generic location, trying intelligent detection...")
                    try:
                        # Use asyncio to run the async method in sync context
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            intelligent_location = loop.run_until_complete(
                                self.detect_intelligent_location(cleaned_text, translation)
                            )
                            if intelligent_location and not intelligent_location.endswith("Unknown"):
                                final_location = intelligent_location.replace("📍 ", "")  # Remove emoji for consistency
                                self.logger.info(f"[AI] Intelligent location detection improved result: {final_location}")
                        finally:
                            loop.close()
                    except Exception as e:
                        self.logger.warning(f"[AI] Intelligent location detection failed: {str(e)}")
                
                return {
                    "title": result.get("title", "أخبار سورية"),
                    "translation": translation,
                    "location": final_location,
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

    async def detect_intelligent_location(self, arabic_text: str, english_translation: str) -> str:
        """
        Intelligently detect location using AI research and contextual analysis.
        
        Args:
            arabic_text: Original Arabic text
            english_translation: English translation
            
        Returns:
            str: Detected location with confidence level
        """
        try:
            # Enhanced location detection prompt
            location_prompt = f"""
You are a news location detection expert. Your task is to determine the most likely location of a news event based on the content provided.

INSTRUCTIONS:
1. Analyze the Arabic and English text for location clues (places, landmarks, institutions, etc.)
2. Use your knowledge of Syrian geography, current events, and news context
3. Research and cross-reference known locations of mentioned landmarks/institutions
4. Provide the most specific location possible (city, district, or region)
5. Include confidence level: HIGH, MEDIUM, or LOW

ARABIC TEXT:
{arabic_text}

ENGLISH TRANSLATION:
{english_translation}

ANALYSIS GUIDELINES:
- Look for specific landmarks, churches, mosques, hospitals, schools, government buildings
- Consider recent Syrian news context and conflict zones
- Match institution names with known locations
- Use geographical and political context clues
- Consider linguistic/dialectal hints about regions

RESPONSE FORMAT:
Location: [Most specific location possible]
Confidence: [HIGH/MEDIUM/LOW]
Reasoning: [Brief explanation of how you determined this location]

Examples:
- "Mar Elias Church" → Likely in Damascus (Bab Touma district) or Aleppo
- "Damascus University" → Damascus
- "Aleppo Citadel" → Aleppo Old City
- "Palmyra ruins" → Palmyra, Homs Governorate

Provide your analysis:
"""

            # Get AI response using OpenAI
            if not self.openai_client:
                logger.warning("[AI-LOCATION] OpenAI client not available, using fallback")
                return self._detect_location_fallback(arabic_text, english_translation)
                
            response_obj = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a Syrian news location detection expert with deep knowledge of Syrian geography, landmarks, and current events."},
                    {"role": "user", "content": location_prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            response = response_obj.choices[0].message.content
            
            if response and "Location:" in response:
                # Parse the structured response
                lines = response.strip().split('\n')
                location = ""
                confidence = ""
                reasoning = ""
                
                for line in lines:
                    if line.startswith("Location:"):
                        location = line.replace("Location:", "").strip()
                    elif line.startswith("Confidence:"):
                        confidence = line.replace("Confidence:", "").strip()
                    elif line.startswith("Reasoning:"):
                        reasoning = line.replace("Reasoning:", "").strip()
                
                # Format the result with accuracy percentage
                if location and location.lower() != "unknown":
                    if confidence == "HIGH":
                        return f"📍 {location} (95% accuracy)"
                    elif confidence == "MEDIUM":
                        return f"📍 {location} (75% accuracy)"
                    else:
                        return f"📍 {location} (50% accuracy)"
                
            # Fallback to simple detection if AI research fails
            return self._detect_location_fallback(arabic_text, english_translation)
            
        except Exception as e:
            logger.error(f"[AI-LOCATION] Error in intelligent location detection: {str(e)}")
            return self._detect_location_fallback(arabic_text, english_translation)

    def _detect_location_fallback(self, arabic_text: str, english_translation: str) -> str:
        """
        Fallback location detection using pattern matching.
        
        Args:
            arabic_text: Original Arabic text
            english_translation: English translation
            
        Returns:
            str: Detected location or "Unknown"
        """
        try:
            # Combine texts for analysis
            combined_text = f"{arabic_text} {english_translation}".lower()
            
            # Known Syrian locations and landmarks
            location_patterns = {
                "Damascus": ["damascus", "دمشق", "الشام", "bab touma", "باب توما", "umayyad mosque", "الجامع الأموي"],
                "Aleppo": ["aleppo", "حلب", "citadel", "قلعة حلب", "great mosque", "الجامع الكبير"],
                "Homs": ["homs", "حمص", "khalid ibn walid", "خالد بن الوليد"],
                "Latakia": ["latakia", "اللاذقية", "mediterranean", "البحر المتوسط"],
                "Tartus": ["tartus", "طرطوس", "arwad", "أرواد"],
                "Daraa": ["daraa", "درعا", "hauran", "حوران"],
                "Deir ez-Zor": ["deir ez-zor", "دير الزور", "euphrates", "الفرات"],
                "Raqqa": ["raqqa", "الرقة"],
                "Hasakah": ["hasakah", "الحسكة"],
                "Idlib": ["idlib", "إدلب"],
                "Palmyra": ["palmyra", "تدمر", "tadmur"],
                "Quneitra": ["quneitra", "القنيطرة", "golan", "الجولان"]
            }
            
            # Check for location matches
            for location, patterns in location_patterns.items():
                for pattern in patterns:
                    if pattern in combined_text:
                        return f"📍 {location} (85% accuracy)"
            
            # Check for specific landmarks that indicate locations
            landmark_locations = {
                "mar elias": "Damascus (Bab Touma) (90% accuracy)",
                "umayyad mosque": "Damascus (95% accuracy)",
                "aleppo citadel": "Aleppo (95% accuracy)",
                "krak des chevaliers": "Homs Governorate (90% accuracy)",
                "palmyra ruins": "Palmyra (95% accuracy)",
                "damascus university": "Damascus (95% accuracy)",
                "aleppo university": "Aleppo (95% accuracy)",
                "tishreen university": "Latakia (95% accuracy)"
            }
            
            for landmark, location in landmark_locations.items():
                if landmark in combined_text:
                    return f"📍 {location}"
            
            return "📍 Unknown"
            
        except Exception as e:
            logger.error(f"[AI-LOCATION] Error in fallback location detection: {str(e)}")
            return "📍 Unknown"
