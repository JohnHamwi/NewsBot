"""
Translation Module

This module provides functionality to translate Arabic news content to English
using OpenAI ChatGPT API for better accessibility in Discord posts.
"""

import re
from typing import Optional, Dict
import logging
import asyncio
from openai import OpenAI
from src.utils.config import Config

logger = logging.getLogger(__name__)


class ChatGPTTranslator:
    """Handles Arabic to English translation using ChatGPT."""
    
    def __init__(self):
        """Initialize the ChatGPT translator."""
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY) if hasattr(Config, 'OPENAI_API_KEY') else None
        
        # Fallback vocabulary for when API is unavailable
        self.fallback_vocabulary = {
            "عاجل": "Breaking",
            "دمشق": "Damascus",
            "حلب": "Aleppo", 
            "حمص": "Homs",
            "إدلب": "Idlib",
            "درعا": "Daraa",
            "انفجار": "explosion",
            "قصف": "bombing",
            "اشتباكات": "clashes",
            "هجوم": "attack",
        }
    
    def generate_title(self, arabic_text: str) -> str:
        """
        Generate a concise Arabic title (3-6 words) using ChatGPT.
        
        Args:
            arabic_text: The Arabic text to create a title from
            
        Returns:
            String with 3-6 Arabic words that summarize the news
        """
        if not self.client:
            return self._extract_title_fallback(arabic_text)
        
        try:
            prompt = f"""
            Create a concise Arabic news headline (3-6 words maximum) from this Syrian news text.
            The title should capture the main event and location if mentioned.
            Make it sound like a proper news headline in Arabic.
            Return ONLY the Arabic title, no explanation or quotes.
            
            Examples of good titles:
            - عاجل انفجار في دمشق
            - قصف على حلب اليوم
            - اشتباكات في إدلب
            - هجوم على حمص
            
            Text: {arabic_text}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.3
            )
            
            result = response.choices[0].message.content.strip()
            
            # Clean up any quotes or extra formatting
            result = result.strip('"\'""''')
            
            # Validate result contains Arabic and is reasonable length
            if re.search(r'[\u0600-\u06FF]', result) and len(result.split()) <= 6:
                return result
            else:
                return self._extract_title_fallback(arabic_text)
                
        except Exception as e:
            logger.error(f"ChatGPT title generation failed: {e}")
            return self._extract_title_fallback(arabic_text)
    
    def _extract_title_fallback(self, arabic_text: str) -> str:
        """Fallback title extraction without API."""
        # Clean the text first
        text = re.sub(r'[^\u0600-\u06FF\s]', ' ', arabic_text)
        words = text.split()
        
        # Priority words
        priority_words = {
            'عاجل', 'انفجار', 'قصف', 'غارة', 'اشتباكات', 'هجوم', 
            'دمشق', 'حلب', 'حمص', 'إدلب', 'درعا'
        }
        
        # Stop words to avoid
        stop_words = {
            'في', 'من', 'إلى', 'على', 'عن', 'مع', 'بعد', 'قبل', 'أن', 
            'التوقيت', 'الموقع', 'الساعة'
        }
        
        meaningful_words = []
        
        # Add priority words first
        for word in words:
            if word in priority_words and word not in meaningful_words:
                meaningful_words.append(word)
        
        # Add other meaningful words
        for word in words:
            if (len(word) > 2 and 
                word not in stop_words and 
                word not in meaningful_words and
                len(meaningful_words) < 6):
                meaningful_words.append(word)
        
        # Ensure we have at least 3 words
        if len(meaningful_words) < 3:
            for word in words:
                if (word not in meaningful_words and 
                    word not in stop_words and 
                    len(meaningful_words) < 6):
                    meaningful_words.append(word)
                if len(meaningful_words) >= 3:
                    break
        
        return ' '.join(meaningful_words[:6]) if meaningful_words else 'أخبار سورية'
    
    def translate_to_english(self, arabic_text: str) -> str:
        """
        Translate Arabic text to English using ChatGPT.
        
        Args:
            arabic_text: The Arabic text to translate
            
        Returns:
            English translation of the text
        """
        if not self.client:
            return self._translate_fallback(arabic_text)
        
        try:
            prompt = f"""
            Translate this Syrian Arabic news text to clear, professional English.
            Provide ONLY the English translation, no explanations or notes.
            Keep the same structure and formatting as the original.
            Make it sound like proper English news reporting.
            
            Arabic text:
            {arabic_text}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.2
            )
            
            result = response.choices[0].message.content.strip()
            
            # Validate the result is in English and reasonable
            if result and len(result) > 10 and not re.search(r'[\u0600-\u06FF]', result):
                return result
            else:
                return self._translate_fallback(arabic_text)
                
        except Exception as e:
            logger.error(f"ChatGPT translation failed: {e}")
            return self._translate_fallback(arabic_text)
    
    def _translate_fallback(self, text: str) -> str:
        """
        Enhanced fallback translation using vocabulary mapping.
        
        Args:
            text: Arabic text to translate
            
        Returns:
            English translation using vocabulary
        """
        # Enhanced vocabulary for better fallback translations
        enhanced_vocab = {
            # Breaking news terms
            'عاجل': 'Breaking',
            'خبر عاجل': 'Breaking News',
            'آخر الأخبار': 'Latest News',
            
            # Actions and events
            'انفجار': 'explosion',
            'قصف': 'bombing',
            'اشتباكات': 'clashes',
            'هجوم': 'attack',
            'غارة': 'airstrike',
            'قتل': 'killed',
            'جرح': 'wounded',
            'إصابة': 'injury',
            'إصابات': 'casualties',
            'ضحايا': 'victims',
            'شهداء': 'martyrs',
            'مقتل': 'death of',
            
            # Locations
            'دمشق': 'Damascus',
            'حلب': 'Aleppo',
            'حمص': 'Homs',
            'حماة': 'Hama',
            'إدلب': 'Idlib',
            'درعا': 'Daraa',
            'اللاذقية': 'Latakia',
            'طرطوس': 'Tartus',
            'الرقة': 'Raqqa',
            'دير الزور': 'Deir ez-Zor',
            'القامشلي': 'Qamishli',
            'الحسكة': 'Hasakah',
            'السويداء': 'Sweida',
            'القنيطرة': 'Quneitra',
            'ريف دمشق': 'Damascus countryside',
            'ريف حلب': 'Aleppo countryside',
            'ريف حمص': 'Homs countryside',
            'ريف إدلب': 'Idlib countryside',
            
            # Areas and districts
            'حي': 'neighborhood',
            'منطقة': 'area',
            'مدينة': 'city',
            'قرية': 'village',
            'بلدة': 'town',
            'محافظة': 'governorate',
            'ريف': 'countryside',
            'شمال': 'north',
            'جنوب': 'south',
            'شرق': 'east',
            'غرب': 'west',
            'وسط': 'center',
            
            # Military and security
            'الجيش': 'army',
            'القوات': 'forces',
            'الشرطة': 'police',
            'الأمن': 'security',
            'المعارضة': 'opposition',
            'النظام': 'regime',
            'الميليشيات': 'militias',
            'المسلحين': 'armed groups',
            'الإرهابيين': 'terrorists',
            
            # Time expressions
            'اليوم': 'today',
            'أمس': 'yesterday',
            'الآن': 'now',
            'صباح': 'morning',
            'مساء': 'evening',
            'ليل': 'night',
            'فجر': 'dawn',
            'ظهر': 'noon',
            'الساعة': 'at',
            
            # Common phrases
            'تشير التقارير': 'reports indicate',
            'وردت أنباء': 'news came',
            'أفادت مصادر': 'sources reported',
            'حسب المصادر': 'according to sources',
            'في حين': 'while',
            'من جهة أخرى': 'on the other hand',
            'في السياق': 'in context',
            'وفي تطور': 'in a development',
        }
        
        # Apply vocabulary translation
        translated = text
        for arabic, english in enhanced_vocab.items():
            translated = re.sub(r'\b' + re.escape(arabic) + r'\b', english, translated, flags=re.IGNORECASE)
        
        return translated


# Global instance
chatgpt_translator = ChatGPTTranslator()


def translate_arabic_to_english(text: str) -> str:
    """
    Convenience function to translate Arabic text to English using ChatGPT.
    
    Args:
        text: Arabic text to translate
        
    Returns:
        English translation
    """
    return chatgpt_translator.translate_to_english(text)


def generate_arabic_title(text: str) -> str:
    """
    Convenience function to generate Arabic title using ChatGPT.
    
    Args:
        text: Arabic text to create title from
        
    Returns:
        3-6 word Arabic news title
    """
    return chatgpt_translator.generate_title(text) 