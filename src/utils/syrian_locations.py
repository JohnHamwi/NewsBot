# =============================================================================
# NewsBot Syrian Location Detection Module
# =============================================================================
# This module provides functionality to detect and tag Syrian cities, regions, 
# and locations mentioned in news content, including comprehensive location
# mapping with Arabic names and regional categorization.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import re
from typing import Dict, List, Set, Optional

# =============================================================================
# Configuration Constants
# =============================================================================
# Comprehensive list of Syrian locations
SYRIAN_LOCATIONS = {
    # Major Cities
    "Damascus": {"emoji": "🏛️", "region": "Capital", "arabic": ["دمشق", "الشام"]},
    "Aleppo": {"emoji": "🏭", "region": "Northern Syria", "arabic": ["حلب"]},
    "Homs": {"emoji": "🏘️", "region": "Central Syria", "arabic": ["حمص"]},
    "Latakia": {"emoji": "🌊", "region": "Coastal Syria", "arabic": ["اللاذقية"]},
    "Tartus": {"emoji": "⚓", "region": "Coastal Syria", "arabic": ["طرطوس"]},
    "Daraa": {"emoji": "🌾", "region": "Southern Syria", "arabic": ["درعا"]},
    "Deir ez-Zor": {"emoji": "🏜️", "region": "Eastern Syria", "arabic": ["دير الزور"]},
    "Raqqa": {"emoji": "🏛️", "region": "Northern Syria", "arabic": ["الرقة"]},
    "Idlib": {"emoji": "🌄", "region": "Northwestern Syria", "arabic": ["إدلب"]},
    "Hasakah": {"emoji": "🌾", "region": "Northeastern Syria", "arabic": ["الحسكة"]},
    "Qamishli": {"emoji": "🏘️", "region": "Northeastern Syria", "arabic": ["القامشلي"]},
    "Palmyra": {"emoji": "🏛️", "region": "Central Syria", "arabic": ["تدمر"]},
    "Kobani": {"emoji": "🏘️", "region": "Northern Syria", "arabic": ["عين العرب"]},
    "Afrin": {"emoji": "🌿", "region": "Northwestern Syria", "arabic": ["عفرين"]},
    # Governorates
    "Damascus Governorate": {
        "emoji": "🏛️",
        "region": "Capital Region",
        "arabic": ["محافظة دمشق"],
    },
    "Aleppo Governorate": {
        "emoji": "🏭",
        "region": "Northern Syria",
        "arabic": ["محافظة حلب"],
    },
    "Homs Governorate": {
        "emoji": "🏘️",
        "region": "Central Syria",
        "arabic": ["محافظة حمص"],
    },
    "Latakia Governorate": {
        "emoji": "🌊",
        "region": "Coastal Syria",
        "arabic": ["محافظة اللاذقية"],
    },
    "Tartus Governorate": {
        "emoji": "⚓",
        "region": "Coastal Syria",
        "arabic": ["محافظة طرطوس"],
    },
    "Daraa Governorate": {
        "emoji": "🌾",
        "region": "Southern Syria",
        "arabic": ["محافظة درعا"],
    },
    "Deir ez-Zor Governorate": {
        "emoji": "🏜️",
        "region": "Eastern Syria",
        "arabic": ["محافظة دير الزور"],
    },
    "Raqqa Governorate": {
        "emoji": "🏛️",
        "region": "Northern Syria",
        "arabic": ["محافظة الرقة"],
    },
    "Idlib Governorate": {
        "emoji": "🌄",
        "region": "Northwestern Syria",
        "arabic": ["محافظة إدلب"],
    },
    "Hasakah Governorate": {
        "emoji": "🌾",
        "region": "Northeastern Syria",
        "arabic": ["محافظة الحسكة"],
    },
    "Quneitra Governorate": {
        "emoji": "🏔️",
        "region": "Southern Syria",
        "arabic": ["محافظة القنيطرة"],
    },
    "As-Suwayda Governorate": {
        "emoji": "🏔️",
        "region": "Southern Syria",
        "arabic": ["محافظة السويداء"],
    },
    "Rif Dimashq Governorate": {
        "emoji": "🏘️",
        "region": "Damascus Countryside",
        "arabic": ["محافظة ريف دمشق"],
    },
    # Important Towns and Areas
    "Douma": {"emoji": "🏘️", "region": "Damascus Countryside", "arabic": ["دوما"]},
    "Doueila": {"emoji": "🏘️", "region": "Damascus", "arabic": ["الدويلعة", "دويلعة"]},
    "Ghouta": {"emoji": "🌿", "region": "Damascus Countryside", "arabic": ["الغوطة"]},
    "Quneitra": {"emoji": "🏔️", "region": "Southern Syria", "arabic": ["القنيطرة"]},
    "As-Suwayda": {"emoji": "🏔️", "region": "Southern Syria", "arabic": ["السويداء"]},
    "Manbij": {"emoji": "🏘️", "region": "Northern Syria", "arabic": ["منبج"]},
    "Tal Afar": {"emoji": "🏘️", "region": "Northern Syria", "arabic": ["تل عفر"]},
    "Azaz": {"emoji": "🏘️", "region": "Northern Syria", "arabic": ["أعزاز"]},
    "Jarablus": {"emoji": "🏘️", "region": "Northern Syria", "arabic": ["جرابلس"]},
    "Al-Bab": {"emoji": "🏘️", "region": "Northern Syria", "arabic": ["الباب"]},
    "Saraqib": {"emoji": "🏘️", "region": "Northwestern Syria", "arabic": ["سراقب"]},
    "Khan Shaykhun": {
        "emoji": "🏘️",
        "region": "Northwestern Syria",
        "arabic": ["خان شيخون"],
    },
    "Maarat al-Numan": {
        "emoji": "🏘️",
        "region": "Northwestern Syria",
        "arabic": ["معرة النعمان"],
    },
}

# Syrian Government Officials and Indicators
SYRIAN_GOVERNMENT_INDICATORS = {
    # Government Titles (Arabic)
    "ministers": [
        "وزير الاقتصاد", "وزير الصناعة", "وزير التجارة", "وزير الداخلية", 
        "وزير الخارجية", "وزير الدفاع", "وزير التربية", "وزير الصحة",
        "وزير العدل", "وزير المالية", "وزير النقل", "وزير الزراعة",
        "وزير الطاقة", "وزير الإعلام", "وزير الثقافة", "وزير السياحة",
        "رئيس الوزراء", "نائب رئيس الوزراء", "وزير الدولة"
    ],
    # Presidential and High-Level Titles (Arabic)
    "presidential": [
        "الرئيس السوري", "رئيس الجمهورية", "رئيس سوريا", "الرئيس أحمد الشرع",
        "أحمد الشرع", "الشرع", "القائد العام", "رئيس مجلس الوزراء",
        "رئيس الحكومة", "القيادة السورية", "الرئاسة السورية"
    ],
    # Government Titles (English)
    "ministers_en": [
        "Minister of Economy", "Minister of Industry", "Minister of Trade", 
        "Minister of Interior", "Minister of Foreign Affairs", "Minister of Defense",
        "Minister of Education", "Minister of Health", "Minister of Justice",
        "Minister of Finance", "Minister of Transport", "Minister of Agriculture",
        "Minister of Energy", "Minister of Information", "Minister of Culture",
        "Minister of Tourism", "Prime Minister", "Deputy Prime Minister", "Minister of State"
    ],
    # Presidential and High-Level Titles (English)
    "presidential_en": [
        "Syrian President", "President of Syria", "Ahmed al-Sharaa", "Ahmad al-Sharaa",
        "al-Sharaa", "Commander in Chief", "Syrian Leadership", "Syrian Presidency"
    ],
    # Known Syrian Officials (last names commonly mentioned)
    "official_names": [
        "الشعار", "Al-Sha'ar", "المقداد", "Mekdad", "الخطيب", "Al-Khatib",
        "عرنوس", "Arnous", "المنسي", "Al-Mansi", "العبد الله", "Abdullah",
        "الشرع", "al-Sharaa", "أحمد الشرع", "Ahmed al-Sharaa"
    ],
    # Government Institutions
    "institutions": [
        "وزارة الاقتصاد", "وزارة الصناعة", "وزارة التجارة", "وزارة الداخلية",
        "وزارة الخارجية", "وزارة الدفاع", "وزارة التربية", "وزارة الصحة",
        "الحكومة السورية", "مجلس الوزراء", "رئاسة الجمهورية"
    ],
    # Government Institutions (English)
    "institutions_en": [
        "Ministry of Economy", "Ministry of Industry", "Ministry of Trade",
        "Ministry of Interior", "Ministry of Foreign Affairs", "Ministry of Defense",
        "Syrian Government", "Council of Ministers", "Presidency"
    ]
}

# Regional groupings
SYRIAN_REGIONS = {
    "Capital": [
        "Damascus",
        "Damascus Governorate",
        "Rif Dimashq Governorate",
        "Douma",
        "Ghouta",
    ],
    "Northern Syria": [
        "Aleppo",
        "Aleppo Governorate",
        "Raqqa",
        "Raqqa Governorate",
        "Manbij",
        "Azaz",
        "Jarablus",
        "Al-Bab",
        "Kobani",
    ],
    "Northwestern Syria": [
        "Idlib",
        "Idlib Governorate",
        "Afrin",
        "Saraqib",
        "Khan Shaykhun",
        "Maarat al-Numan",
    ],
    "Northeastern Syria": ["Hasakah", "Hasakah Governorate", "Qamishli"],
    "Eastern Syria": ["Deir ez-Zor", "Deir ez-Zor Governorate"],
    "Central Syria": ["Homs", "Homs Governorate", "Palmyra"],
    "Coastal Syria": ["Latakia", "Latakia Governorate", "Tartus", "Tartus Governorate"],
    "Southern Syria": [
        "Daraa",
        "Daraa Governorate",
        "Quneitra",
        "Quneitra Governorate",
        "As-Suwayda",
        "As-Suwayda Governorate",
    ],
    "Damascus Countryside": ["Rif Dimashq Governorate", "Douma", "Ghouta"],
}


# =============================================================================
# Syrian Location Detector Main Class
# =============================================================================
class SyrianLocationDetector:
    """
    Detects Syrian locations in text and provides regional context.
    
    Features:
    - Comprehensive location pattern matching
    - Arabic and English name recognition
    - Regional categorization and grouping
    - Location metadata with emojis
    - Efficient compiled regex patterns
    """

    def __init__(self):
        """Initialize the location detector with compiled patterns."""
        self.location_patterns = self._compile_patterns()

    # =========================================================================
    # Pattern Compilation Methods
    # =========================================================================
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for efficient location detection."""
        patterns = {}

        for location, data in SYRIAN_LOCATIONS.items():
            # Create pattern for English name
            english_pattern = rf"\b{re.escape(location)}\b"

            # Create patterns for Arabic names with common prefixes/prepositions
            arabic_patterns = []
            for arabic_name in data.get("arabic", []):
                # Add the base name
                arabic_patterns.append(re.escape(arabic_name))
                
                # Add common Arabic prepositions and prefixes
                # ب (in/at), في (in), من (from), إلى (to), عند (at), لدى (at/with)
                # و (and), ال (the), ك (like/as)
                prefixes = ["ب", "في", "من", "إلى", "عند", "لدى", "و", "ال", "ك"]
                for prefix in prefixes:
                    arabic_patterns.append(re.escape(prefix + arabic_name))
                    # Also handle cases where there might be spaces
                    arabic_patterns.append(re.escape(prefix) + r"\s*" + re.escape(arabic_name))

            # Combine all patterns
            all_patterns = [english_pattern] + arabic_patterns
            combined_pattern = "|".join(all_patterns)

            patterns[location] = re.compile(combined_pattern, re.IGNORECASE)

        return patterns

    # =========================================================================
    # Location Detection Methods
    # =========================================================================
    def detect_locations(self, text: str) -> List[Dict[str, str]]:
        """
        Detect Syrian locations mentioned in the text.

        Args:
            text: The text to analyze

        Returns:
            List of detected locations with metadata
        """
        detected = []
        seen_locations = set()

        for location, pattern in self.location_patterns.items():
            if pattern.search(text) and location not in seen_locations:
                location_data = SYRIAN_LOCATIONS[location]
                detected.append({
                    "name": location,
                    "emoji": location_data["emoji"],
                    "region": location_data["region"],
                    "arabic": location_data.get("arabic", [])
                })
                seen_locations.add(location)

        return detected

    # =========================================================================
    # Regional Analysis Methods
    # =========================================================================
    def get_regional_summary(
        self, locations: List[Dict[str, str]]
    ) -> Dict[str, List[str]]:
        """
        Group detected locations by region.

        Args:
            locations: List of detected locations

        Returns:
            Dictionary mapping regions to location lists
        """
        regional_summary = {}
        
        for location in locations:
            region = location["region"]
            if region not in regional_summary:
                regional_summary[region] = []
            regional_summary[region].append(location["name"])
            
        return regional_summary

    # =========================================================================
    # Formatting Methods
    # =========================================================================
    def format_location_tags(self, locations: List[Dict[str, str]]) -> str:
        """
        Format detected locations as Discord-friendly tags.

        Args:
            locations: List of detected locations

        Returns:
            Formatted string with location tags
        """
        if not locations:
            return ""

        # Group by region for better organization
        regional_summary = self.get_regional_summary(locations)
        
        formatted_parts = []
        for region, location_names in regional_summary.items():
            if len(location_names) == 1:
                location_data = next(
                    loc for loc in locations 
                    if loc["name"] == location_names[0]
                )
                formatted_parts.append(
                    f"{location_data['emoji']} **{location_names[0]}**"
                )
            else:
                location_emojis = [
                    next(loc for loc in locations if loc["name"] == name)["emoji"]
                    for name in location_names
                ]
                formatted_parts.append(
                    f"{location_emojis[0]} **{region}**: {', '.join(location_names)}"
                )
        
        return " | ".join(formatted_parts)


# =============================================================================
# Module-Level Functions
# =============================================================================
# Global detector instance
location_detector = SyrianLocationDetector()


def detect_syrian_locations(text: str) -> List[Dict[str, str]]:
    """
    Convenience function to detect Syrian locations in text.

    Args:
        text: Text to analyze

    Returns:
        List of detected locations with metadata
    """
    return location_detector.detect_locations(text)


def format_syrian_location_tags(text: str) -> str:
    """
    Convenience function to format Syrian location tags from text.

    Args:
        text: Text to analyze

    Returns:
        Formatted location tags string
    """
    locations = detect_syrian_locations(text)
    return location_detector.format_location_tags(locations)


def detect_syrian_location(text: str) -> str:
    """
    Detect the primary Syrian location mentioned in text.
    Enhanced with government official detection.

    Args:
        text: Text to analyze

    Returns:
        Primary location name or "Damascus" if Syrian officials mentioned
    """
    if not text:
        return ""
    
    # First check for Syrian government officials
    if detect_syrian_government_official(text):
        return "Damascus"  # Government officials are typically in Damascus
    
    locations = detect_syrian_locations(text)
    return locations[0]["name"] if locations else ""


def detect_syrian_government_official(text: str) -> bool:
    """
    Detect if the text mentions Syrian government officials, ministers, or institutions.
    
    Args:
        text: Text to analyze
        
    Returns:
        bool: True if Syrian government officials are mentioned
    """
    if not text:
        return False
    
    text_lower = text.lower()
    
    # Check for minister titles (Arabic)
    for minister_title in SYRIAN_GOVERNMENT_INDICATORS["ministers"]:
        if minister_title in text:
            return True
    
    # Check for presidential titles (Arabic)
    for presidential_title in SYRIAN_GOVERNMENT_INDICATORS["presidential"]:
        if presidential_title in text:
            return True
    
    # Check for minister titles (English)  
    for minister_title in SYRIAN_GOVERNMENT_INDICATORS["ministers_en"]:
        if minister_title.lower() in text_lower:
            return True
    
    # Check for presidential titles (English)
    for presidential_title in SYRIAN_GOVERNMENT_INDICATORS["presidential_en"]:
        if presidential_title.lower() in text_lower:
            return True
            
    # Check for known official names
    for official_name in SYRIAN_GOVERNMENT_INDICATORS["official_names"]:
        if official_name.lower() in text_lower:
            return True
            
    # Check for government institutions (Arabic)
    for institution in SYRIAN_GOVERNMENT_INDICATORS["institutions"]:
        if institution in text:
            return True
            
    # Check for government institutions (English)
    for institution in SYRIAN_GOVERNMENT_INDICATORS["institutions_en"]:
        if institution.lower() in text_lower:
            return True
    
    return False


# =============================================================================
# AI-Powered Location Detection
# =============================================================================
async def detect_location_with_ai(text: str, bot=None) -> str:
    """
    Use AI to intelligently detect locations in text, with regex fallback.
    
    Args:
        text: The text to analyze for locations
        bot: Bot instance for AI service access (optional)
    
    Returns:
        Detected location string (e.g., "Damascus, Syria" or "Unknown")
    """
    try:
        # First try AI detection if bot is available
        if bot and hasattr(bot, 'fetch_commands'):
            # Use the AI service for intelligent location detection
            from src.services.ai_service import AIService
            
            ai_service = AIService(bot)
            ai_result = ai_service.get_ai_result_comprehensive(text)
            
            if ai_result and ai_result.get('location') and ai_result['location'] != 'Unknown':
                ai_location = ai_result['location'].strip()
                
                # Validate and format the AI result
                if ai_location and ai_location.lower() not in ['unknown', 'unclear', 'not specified', 'n/a', 'none']:
                    # If it's a Syrian city without "Syria" suffix, add it
                    syrian_cities = ['Damascus', 'Aleppo', 'Homs', 'Hama', 'Latakia', 'Tartus', 
                                   'Daraa', 'Idlib', 'Raqqa', 'Deir ez-Zor', 'Hasakah', 'Qamishli']
                    
                    for city in syrian_cities:
                        if city.lower() in ai_location.lower() and 'syria' not in ai_location.lower():
                            ai_location = f"{city}, Syria"
                            break
                    
                    return ai_location
        
        # Fallback to regex-based detection
        regex_location = detect_syrian_location(text)
        if regex_location:
            # Format Syrian cities properly
            return f"{regex_location}, Syria" if regex_location != "Syria" else "Syria"
        
        return "Unknown"
        
    except Exception as e:
        # If AI fails, fall back to regex detection
        try:
            regex_location = detect_syrian_location(text)
            return f"{regex_location}, Syria" if regex_location and regex_location != "Syria" else "Syria"
        except:
            return "Unknown"


def detect_location_smart(text: str, bot=None) -> str:
    """
    Smart location detection that combines AI and regex methods.
    
    Args:
        text: Text to analyze
        bot: Bot instance (optional, for AI access)
    
    Returns:
        Detected location or "Unknown"
    """
    import asyncio
    
    try:
        # Try to run the async AI detection
        if bot:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a task for async execution
                task = asyncio.create_task(detect_location_with_ai(text, bot))
                # This won't work in sync context, so fall back to regex
                pass
            else:
                return asyncio.run(detect_location_with_ai(text, bot))
    except:
        pass
    
    # Fallback to regex-based detection
    regex_location = detect_syrian_location(text)
    if regex_location and regex_location != "Syria":
        return f"{regex_location}, Syria"
    elif regex_location == "Syria":
        return "Syria"
    else:
        return "Unknown"
