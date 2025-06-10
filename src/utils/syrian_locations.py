"""
Syrian Location Detection Module

This module provides functionality to detect and tag Syrian cities, regions, and locations
mentioned in news content.
"""

import re
from typing import List, Dict, Set

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
    "Damascus Governorate": {"emoji": "🏛️", "region": "Capital Region", "arabic": ["محافظة دمشق"]},
    "Aleppo Governorate": {"emoji": "🏭", "region": "Northern Syria", "arabic": ["محافظة حلب"]},
    "Homs Governorate": {"emoji": "🏘️", "region": "Central Syria", "arabic": ["محافظة حمص"]},
    "Latakia Governorate": {"emoji": "🌊", "region": "Coastal Syria", "arabic": ["محافظة اللاذقية"]},
    "Tartus Governorate": {"emoji": "⚓", "region": "Coastal Syria", "arabic": ["محافظة طرطوس"]},
    "Daraa Governorate": {"emoji": "🌾", "region": "Southern Syria", "arabic": ["محافظة درعا"]},
    "Deir ez-Zor Governorate": {"emoji": "🏜️", "region": "Eastern Syria", "arabic": ["محافظة دير الزور"]},
    "Raqqa Governorate": {"emoji": "🏛️", "region": "Northern Syria", "arabic": ["محافظة الرقة"]},
    "Idlib Governorate": {"emoji": "🌄", "region": "Northwestern Syria", "arabic": ["محافظة إدلب"]},
    "Hasakah Governorate": {"emoji": "🌾", "region": "Northeastern Syria", "arabic": ["محافظة الحسكة"]},
    "Quneitra Governorate": {"emoji": "🏔️", "region": "Southern Syria", "arabic": ["محافظة القنيطرة"]},
    "As-Suwayda Governorate": {"emoji": "🏔️", "region": "Southern Syria", "arabic": ["محافظة السويداء"]},
    "Rif Dimashq Governorate": {"emoji": "🏘️", "region": "Damascus Countryside", "arabic": ["محافظة ريف دمشق"]},
    
    # Important Towns and Areas
    "Douma": {"emoji": "🏘️", "region": "Damascus Countryside", "arabic": ["دوما"]},
    "Ghouta": {"emoji": "🌿", "region": "Damascus Countryside", "arabic": ["الغوطة"]},
    "Quneitra": {"emoji": "🏔️", "region": "Southern Syria", "arabic": ["القنيطرة"]},
    "As-Suwayda": {"emoji": "🏔️", "region": "Southern Syria", "arabic": ["السويداء"]},
    "Manbij": {"emoji": "🏘️", "region": "Northern Syria", "arabic": ["منبج"]},
    "Tal Afar": {"emoji": "🏘️", "region": "Northern Syria", "arabic": ["تل عفر"]},
    "Azaz": {"emoji": "🏘️", "region": "Northern Syria", "arabic": ["أعزاز"]},
    "Jarablus": {"emoji": "🏘️", "region": "Northern Syria", "arabic": ["جرابلس"]},
    "Al-Bab": {"emoji": "🏘️", "region": "Northern Syria", "arabic": ["الباب"]},
    "Saraqib": {"emoji": "🏘️", "region": "Northwestern Syria", "arabic": ["سراقب"]},
    "Khan Shaykhun": {"emoji": "🏘️", "region": "Northwestern Syria", "arabic": ["خان شيخون"]},
    "Maarat al-Numan": {"emoji": "🏘️", "region": "Northwestern Syria", "arabic": ["معرة النعمان"]},
}

# Regional groupings
SYRIAN_REGIONS = {
    "Capital": ["Damascus", "Damascus Governorate", "Rif Dimashq Governorate", "Douma", "Ghouta"],
    "Northern Syria": ["Aleppo", "Aleppo Governorate", "Raqqa", "Raqqa Governorate", "Manbij", "Azaz", "Jarablus", "Al-Bab", "Kobani"],
    "Northwestern Syria": ["Idlib", "Idlib Governorate", "Afrin", "Saraqib", "Khan Shaykhun", "Maarat al-Numan"],
    "Northeastern Syria": ["Hasakah", "Hasakah Governorate", "Qamishli"],
    "Eastern Syria": ["Deir ez-Zor", "Deir ez-Zor Governorate"],
    "Central Syria": ["Homs", "Homs Governorate", "Palmyra"],
    "Coastal Syria": ["Latakia", "Latakia Governorate", "Tartus", "Tartus Governorate"],
    "Southern Syria": ["Daraa", "Daraa Governorate", "Quneitra", "Quneitra Governorate", "As-Suwayda", "As-Suwayda Governorate"],
    "Damascus Countryside": ["Rif Dimashq Governorate", "Douma", "Ghouta"]
}


class SyrianLocationDetector:
    """Detects Syrian locations in text and provides regional context."""
    
    def __init__(self):
        """Initialize the location detector with compiled patterns."""
        self.location_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for efficient location detection."""
        patterns = {}
        
        for location, data in SYRIAN_LOCATIONS.items():
            # Create pattern for English name
            english_pattern = rf'\b{re.escape(location)}\b'
            
            # Create patterns for Arabic names
            arabic_patterns = []
            for arabic_name in data.get("arabic", []):
                arabic_patterns.append(re.escape(arabic_name))
            
            # Combine all patterns
            all_patterns = [english_pattern] + arabic_patterns
            combined_pattern = '|'.join(all_patterns)
            
            patterns[location] = re.compile(combined_pattern, re.IGNORECASE)
        
        return patterns
    
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
    
    def get_regional_summary(self, locations: List[Dict[str, str]]) -> Dict[str, List[str]]:
        """
        Group detected locations by region.
        
        Args:
            locations: List of detected locations
            
        Returns:
            Dictionary mapping regions to lists of locations
        """
        regional_summary = {}
        
        for location in locations:
            region = location["region"]
            if region not in regional_summary:
                regional_summary[region] = []
            regional_summary[region].append(location["name"])
        
        return regional_summary
    
    def format_location_tags(self, locations: List[Dict[str, str]]) -> str:
        """
        Format detected locations as tags for Discord embed.
        
        Args:
            locations: List of detected locations
            
        Returns:
            Formatted string with location tags
        """
        if not locations:
            return ""
        
        # Group by region
        regional_summary = self.get_regional_summary(locations)
        
        tags = []
        for region, region_locations in regional_summary.items():
            if len(region_locations) == 1:
                location_data = next(loc for loc in locations if loc["name"] == region_locations[0])
                tags.append(f"{location_data['emoji']} {region_locations[0]}")
            else:
                # Multiple locations in same region
                emoji = locations[0]["emoji"]  # Use first emoji for region
                location_names = ", ".join(region_locations)
                tags.append(f"{emoji} {region} ({location_names})")
        
        return " | ".join(tags)


# Global instance for easy access
syrian_location_detector = SyrianLocationDetector()


def detect_syrian_locations(text: str) -> List[Dict[str, str]]:
    """
    Convenience function to detect Syrian locations in text.
    
    Args:
        text: The text to analyze
        
    Returns:
        List of detected locations with metadata
    """
    return syrian_location_detector.detect_locations(text)


def format_syrian_location_tags(text: str) -> str:
    """
    Convenience function to get formatted location tags for text.
    
    Args:
        text: The text to analyze
        
    Returns:
        Formatted location tags string
    """
    locations = detect_syrian_locations(text)
    return syrian_location_detector.format_location_tags(locations) 