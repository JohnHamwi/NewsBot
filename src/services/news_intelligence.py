# =============================================================================
# NewsBot News Intelligence Service Module
# =============================================================================
# Provides intelligent analysis of news content for:
# - Breaking news detection with urgency scoring
# - Content urgency assessment and source credibility
# - Smart posting decisions with timing logic
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import re
import asyncio
from enum import Enum
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

# =============================================================================
# Local Application Imports
# =============================================================================
try:
    from src.utils.base_logger import base_logger as logger
    from src.core.config_manager import config
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from utils.base_logger import base_logger as logger
    from core.config_manager import config


# =============================================================================
# Urgency Level Enumeration
# =============================================================================
class UrgencyLevel(Enum):
    """Content urgency levels for intelligent posting decisions."""
    BREAKING = "breaking"      # Immediate posting required
    IMPORTANT = "important"    # High priority posting
    NORMAL = "normal"         # Regular posting flow
    LOW = "low"              # Low priority, can be delayed


# =============================================================================
# News Analysis Data Structure
# =============================================================================
@dataclass
class NewsAnalysis:
    """Results of comprehensive news content analysis."""
    urgency_level: UrgencyLevel
    urgency_score: float  # 0.0 - 1.0
    breaking_indicators: List[str]
    source_credibility: float  # 0.0 - 1.0
    time_sensitivity: bool
    should_ping: bool
    confidence: float  # 0.0 - 1.0


# =============================================================================
# News Intelligence Service Class
# =============================================================================
class NewsIntelligenceService:
    """
    Intelligent news analysis service for content prioritization and urgency detection.
    
    Features:
    - Breaking news detection with keyword analysis
    - Source credibility assessment with priority sources
    - Time sensitivity analysis for urgent content
    - Smart posting decisions with delay calculations
    - Comprehensive logging and fallback mechanisms
    """
    
    def __init__(self):
        """Initialize the News Intelligence Service with configuration."""
        # Arabic breaking news keywords
        self.breaking_keywords_ar = [
            "عاجل", "الآن", "فوري", "طارئ", "هام", "مستجدات",
            "تطورات", "حصري", "لحظة", "مباشر"
        ]
        
        # English breaking news keywords
        self.breaking_keywords_en = [
            "breaking", "urgent", "now", "immediate", "alert", 
            "flash", "developing", "live", "just in", "update"
        ]
        
        # Priority sources with high credibility
        self.priority_sources = config.get("intelligence.priority_sources", [
            "alekhbariahsy", "syrianobserver", "orient_news"
        ])
        
        # Source credibility cache for performance
        self.source_credibility_cache = {}
        
        logger.info("🧠 News Intelligence Service initialized")

    # =========================================================================
    # Main Analysis Method
    # =========================================================================
    async def analyze_urgency(self, content: str, channel: str, media: List = None) -> NewsAnalysis:
        """
        Analyze content to determine urgency level and posting priority.
        
        Args:
            content: News content text to analyze
            channel: Source channel name for credibility assessment
            media: Optional media attachments for urgency scoring
            
        Returns:
            NewsAnalysis with comprehensive urgency assessment
        """
        try:
            # Calculate individual component scores
            keyword_score = await self._calculate_keyword_urgency(content)
            source_score = await self._calculate_source_credibility(channel)
            time_score = await self._calculate_time_sensitivity(content)
            media_score = await self._calculate_media_urgency(media or [])
            
            # Combine scores with weighted importance
            urgency_score = (
                keyword_score * 0.4 +    # Keywords are most important
                source_score * 0.3 +     # Source credibility matters
                time_score * 0.2 +       # Time indicators
                media_score * 0.1        # Media presence
            )
            
            # Determine urgency level based on score
            urgency_level = self._determine_urgency_level(urgency_score)
            
            # Always ping news role for all posts as requested
            should_ping = True
            
            # Get breaking indicators for logging
            breaking_indicators = await self._get_breaking_indicators(content)
            
            # Create comprehensive analysis result
            analysis = NewsAnalysis(
                urgency_level=urgency_level,
                urgency_score=urgency_score,
                breaking_indicators=breaking_indicators,
                source_credibility=source_score,
                time_sensitivity=time_score > 0.5,
                should_ping=should_ping,
                confidence=min(0.95, (urgency_score + source_score) / 2)
            )
            
            logger.info(f"📊 News analysis: {urgency_level.value} (score: {urgency_score:.2f})")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing urgency: {e}")
            # Return safe default for reliability
            return NewsAnalysis(
                urgency_level=UrgencyLevel.NORMAL,
                urgency_score=0.5,
                breaking_indicators=[],
                source_credibility=0.5,
                time_sensitivity=False,
                should_ping=True,  # Always ping as requested
                confidence=0.3
            )

    # =========================================================================
    # Keyword Urgency Analysis
    # =========================================================================
    async def _calculate_keyword_urgency(self, content: str) -> float:
        """Calculate urgency score based on breaking news keywords (0.0-1.0)."""
        content_lower = content.lower()
        
        # Check for breaking news keywords
        breaking_found = 0
        total_keywords = len(self.breaking_keywords_ar) + len(self.breaking_keywords_en)
        
        for keyword in self.breaking_keywords_ar + self.breaking_keywords_en:
            if keyword in content_lower:
                breaking_found += 1
                
        # Additional urgent patterns
        urgent_patterns = [
            r'\b(just|now|moments ago|minutes ago)\b',
            r'\b(developing|unfolding|ongoing)\b',
            r'[🚨⚠️🔴]',  # Urgent emojis
            r'\b(confirmed|reports|sources)\b.*\b(say|confirm|report)\b'
        ]
        
        pattern_matches = 0
        for pattern in urgent_patterns:
            if re.search(pattern, content_lower):
                pattern_matches += 1
        
        # Calculate combined score
        keyword_score = (breaking_found / total_keywords) * 0.7
        pattern_score = (pattern_matches / len(urgent_patterns)) * 0.3
        
        return min(1.0, keyword_score + pattern_score)

    # =========================================================================
    # Source Credibility Assessment
    # =========================================================================
    async def _calculate_source_credibility(self, channel: str) -> float:
        """Calculate source credibility score (0.0-1.0)."""
        # Check cache first for performance
        if channel in self.source_credibility_cache:
            return self.source_credibility_cache[channel]
        
        # Priority sources get high credibility
        if channel in self.priority_sources:
            credibility = 0.9
        elif "official" in channel.lower() or "news" in channel.lower():
            credibility = 0.7
        elif len(channel) > 10:  # Longer names often more legitimate
            credibility = 0.6
        else:
            credibility = 0.4
        
        # Cache the result for future use
        self.source_credibility_cache[channel] = credibility
        return credibility

    # =========================================================================
    # Time Sensitivity Analysis
    # =========================================================================
    async def _calculate_time_sensitivity(self, content: str) -> float:
        """Calculate time sensitivity score (0.0-1.0)."""
        time_indicators = [
            "now", "الآن", "just", "moments", "minutes ago",
            "developing", "live", "ongoing", "current", "today"
        ]
        
        content_lower = content.lower()
        matches = sum(1 for indicator in time_indicators if indicator in content_lower)
        
        return min(1.0, matches / len(time_indicators) * 2)

    # =========================================================================
    # Media Urgency Assessment
    # =========================================================================
    async def _calculate_media_urgency(self, media: List) -> float:
        """Calculate media urgency score based on attachments (0.0-1.0)."""
        if not media:
            return 0.0
        
        # More media often indicates more important news
        media_count = len(media)
        
        # Check for urgent media types
        urgent_media_score = 0.0
        for item in media:
            if hasattr(item, 'content_type'):
                if 'video' in item.content_type:
                    urgent_media_score += 0.3  # Videos often more urgent
                elif 'image' in item.content_type:
                    urgent_media_score += 0.2  # Images add context
        
        # Combine media count and type scores
        count_score = min(0.5, media_count / 5.0)  # Cap at 0.5
        return min(1.0, count_score + urgent_media_score)

    # =========================================================================
    # Urgency Level Determination
    # =========================================================================
    def _determine_urgency_level(self, urgency_score: float) -> UrgencyLevel:
        """Determine urgency level based on calculated score."""
        if urgency_score >= 0.8:
            return UrgencyLevel.BREAKING
        elif urgency_score >= 0.6:
            return UrgencyLevel.IMPORTANT
        elif urgency_score >= 0.3:
            return UrgencyLevel.NORMAL
        else:
            return UrgencyLevel.LOW

    # =========================================================================
    # Breaking Indicators Extraction
    # =========================================================================
    async def _get_breaking_indicators(self, content: str) -> List[str]:
        """Extract breaking news indicators found in content."""
        indicators = []
        content_lower = content.lower()
        
        for keyword in self.breaking_keywords_ar + self.breaking_keywords_en:
            if keyword in content_lower:
                indicators.append(keyword)
        
        return indicators

    # =========================================================================
    # Posting Decision Helpers
    # =========================================================================
    async def should_post_immediately(self, analysis: NewsAnalysis) -> bool:
        """Determine if content should be posted immediately."""
        return analysis.urgency_level in [UrgencyLevel.BREAKING, UrgencyLevel.IMPORTANT]

    async def get_posting_delay(self, analysis: NewsAnalysis) -> int:
        """Get recommended posting delay in seconds."""
        delay_map = {
            UrgencyLevel.BREAKING: 0,      # Immediate
            UrgencyLevel.IMPORTANT: 30,    # 30 seconds
            UrgencyLevel.NORMAL: 300,      # 5 minutes
            UrgencyLevel.LOW: 900          # 15 minutes
        }
        return delay_map.get(analysis.urgency_level, 300)

    async def format_urgency_indicator(self, analysis: NewsAnalysis) -> str:
        """Format urgency indicator for display."""
        indicators = {
            UrgencyLevel.BREAKING: "🚨",
            UrgencyLevel.IMPORTANT: "📢", 
            UrgencyLevel.NORMAL: "📅",
            UrgencyLevel.LOW: "📝"
        }
        return indicators.get(analysis.urgency_level, "📰") 