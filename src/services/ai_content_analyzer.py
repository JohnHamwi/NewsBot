# =============================================================================
# NewsBot AI Content Analyzer Module
# =============================================================================
# Advanced AI-powered content analysis including:
# - Sentiment analysis with emotional indicators
# - Auto-categorization with confidence scoring
# - Duplicate detection using similarity matching
# - Content quality assessment with detailed metrics
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import re
import asyncio
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from difflib import SequenceMatcher

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import discord

# =============================================================================
# Local Application Imports
# =============================================================================
try:
    from src.utils.base_logger import base_logger as logger
    from src.core.unified_config import unified_config as config
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from utils.base_logger import base_logger as logger
    from core.unified_config import config


# =============================================================================
# Content Safety Enumeration
# =============================================================================
class ContentSafety(Enum):
    """Content safety levels for filtering."""
    SAFE = "safe"                    # Safe for all audiences
    SENSITIVE = "sensitive"          # May need content warning
    GRAPHIC = "graphic"              # Contains graphic violence/gore
    DISTURBING = "disturbing"        # Extremely disturbing content
    BANNED = "banned"                # Should never be posted


# =============================================================================
# Sentiment Analysis Enumeration
# =============================================================================
class Sentiment(Enum):
    """Content sentiment types for news analysis."""
    POSITIVE = "positive"      # Good news, achievements
    NEGATIVE = "negative"      # Bad news, conflicts
    NEUTRAL = "neutral"        # Factual reporting
    URGENT = "urgent"         # Requires immediate attention
    CONCERNING = "concerning"  # Worrying developments


# =============================================================================
# News Category Enumeration
# =============================================================================
class NewsCategory(Enum):
    """News content categories for intelligent classification."""
    POLITICS = "politics"
    MILITARY = "military"
    ECONOMY = "economy"
    HEALTH = "health"
    INTERNATIONAL = "international"
    BREAKING = "breaking"
    SOCIAL = "social"
    SPORTS = "sports"
    TECHNOLOGY = "technology"
    CULTURE = "culture"


# =============================================================================
# Analysis Result Data Structures
# =============================================================================
@dataclass
class SentimentResult:
    """Sentiment analysis results with confidence and indicators."""
    sentiment: Sentiment
    confidence: float  # 0.0 - 1.0
    emotional_indicators: List[str]
    tone: str  # "formal", "urgent", "neutral", etc.


@dataclass
class CategoryResult:
    """Categorization results with primary and secondary categories."""
    primary_category: NewsCategory
    secondary_categories: List[NewsCategory]
    confidence: float  # 0.0 - 1.0
    category_indicators: Dict[str, List[str]]


@dataclass
class SafetyResult:
    """Content safety assessment with filtering decisions."""
    safety_level: ContentSafety
    confidence: float  # 0.0 - 1.0
    graphic_indicators: List[str]
    safety_issues: List[str]
    should_filter: bool
    content_warning: Optional[str]


@dataclass
class QualityScore:
    """Content quality assessment with detailed metrics."""
    overall_score: float  # 0.0 - 1.0
    completeness: float   # How complete the story is
    clarity: float        # How clear the writing is
    informativeness: float # How informative the content is
    media_quality: float  # Quality of attached media
    issues: List[str]     # Quality issues found


@dataclass
class ProcessedContent:
    """Fully processed content with comprehensive AI analysis."""
    original_content: str
    translated_content: str
    sentiment: SentimentResult
    categories: CategoryResult
    quality: QualityScore
    safety: SafetyResult
    similarity_score: float  # Similarity to recent posts
    should_post: bool
    posting_priority: int  # 1-5, higher = more important
    processing_notes: List[str]


# =============================================================================
# AI Content Analyzer Class
# =============================================================================
class AIContentAnalyzer:
    """
    Advanced AI-powered content analyzer for news intelligence.
    
    Features:
    - Multi-language sentiment analysis with emotional indicators
    - Intelligent content categorization with confidence scoring
    - Duplicate detection using similarity algorithms
    - Content quality assessment with detailed metrics
    - Smart posting decisions based on combined analysis
    - Comprehensive caching and performance optimization
    """
    
    def __init__(self, bot=None):
        """Initialize the AI Content Analyzer with keyword dictionaries."""
        # Recent posts cache for duplicate detection
        self.recent_posts_cache = []  # Store recent posts for comparison
        self.cache_size = 50  # Keep last 50 posts for comparison
        
        # Bot instance for Discord logging
        self.bot = bot
        
        # Sentiment analysis keywords
        self.sentiment_keywords = {
            Sentiment.POSITIVE: {
                'ar': ['نجح', 'تقدم', 'انتصار', 'تحسن', 'إنجاز', 'فوز', 'تطوير'],
                'en': ['success', 'progress', 'victory', 'improvement', 'achievement', 'win', 'development']
            },
            Sentiment.NEGATIVE: {
                'ar': ['قتل', 'دمار', 'هجوم', 'انفجار', 'ضحايا', 'خسائر', 'كارثة'],
                'en': ['killed', 'destruction', 'attack', 'explosion', 'casualties', 'losses', 'disaster']
            },
            Sentiment.URGENT: {
                'ar': ['عاجل', 'فوري', 'طارئ', 'خطير', 'حرج'],
                'en': ['urgent', 'immediate', 'emergency', 'critical', 'serious']
            },
            Sentiment.CONCERNING: {
                'ar': ['مقلق', 'خطر', 'تهديد', 'أزمة', 'توتر'],
                'en': ['concerning', 'danger', 'threat', 'crisis', 'tension']
            }
        }
        
        # Category classification keywords
        self.category_keywords = {
            NewsCategory.POLITICS: {
                'ar': ['حكومة', 'سياسة', 'رئيس', 'وزير', 'برلمان', 'انتخابات'],
                'en': ['government', 'politics', 'president', 'minister', 'parliament', 'elections']
            },
            NewsCategory.MILITARY: {
                'ar': ['جيش', 'عسكري', 'قوات', 'معركة', 'عملية', 'دفاع'],
                'en': ['army', 'military', 'forces', 'battle', 'operation', 'defense']
            },
            NewsCategory.ECONOMY: {
                'ar': ['اقتصاد', 'مال', 'بنك', 'استثمار', 'تجارة', 'أسعار'],
                'en': ['economy', 'money', 'bank', 'investment', 'trade', 'prices']
            },
            NewsCategory.HEALTH: {
                'ar': ['صحة', 'مرض', 'علاج', 'مستشفى', 'طبيب', 'دواء'],
                'en': ['health', 'disease', 'treatment', 'hospital', 'doctor', 'medicine']
            },
            NewsCategory.INTERNATIONAL: {
                'ar': ['دولي', 'عالمي', 'أمم متحدة', 'دبلوماسي', 'خارجي'],
                'en': ['international', 'global', 'united nations', 'diplomatic', 'foreign']
            }
        }
        
        # Content safety/graphic content detection keywords
        self.safety_keywords = {
            ContentSafety.GRAPHIC: {
                'ar': [
                    'دماء', 'دم', 'جثث', 'جثة', 'قطع أوصال', 'تقطعت أوصال', 'مقطوع', 
                    'مشوه', 'تشويه', 'حرق', 'محروق', 'ذبح', 'مذبوح', 'قطع رأس',
                    'رؤوس مقطوعة', 'أشلاء', 'بتر', 'مبتور', 'تمزق', 'ممزق'
                ],
                'en': [
                    'blood', 'gore', 'corpse', 'corpses', 'dismembered', 'dismemberment',
                    'severed', 'mutilated', 'mutilation', 'burned alive', 'beheaded',
                    'decapitated', 'body parts', 'limbs', 'severed head', 'torn apart',
                    'graphic violence', 'brutal', 'horrific injuries'
                ]
            },
            ContentSafety.DISTURBING: {
                'ar': [
                    'تعذيب', 'معذب', 'إعدام', 'أعدم', 'شنق', 'مشنوق', 'رجم',
                    'مرجوم', 'صلب', 'مصلوب', 'حرق حي', 'دفن حي', 'مدفون حي'
                ],
                'en': [
                    'torture', 'tortured', 'execution', 'executed', 'hanged', 'hanging',
                    'crucified', 'crucifixion', 'burned alive', 'buried alive', 'mass grave'
                ]
            },
            ContentSafety.SENSITIVE: {
                'ar': [
                    'قتل', 'قتيل', 'قتلى', 'ضحايا', 'ضحية', 'جريح', 'جرحى',
                    'إصابات', 'مصاب', 'انفجار', 'هجوم', 'اعتداء', 'عنف'
                ],
                'en': [
                    'killed', 'death', 'deaths', 'casualties', 'victims', 'injured',
                    'wounded', 'explosion', 'attack', 'violence', 'assault'
                ]
            }
        }
        
        logger.info("🤖 AI Content Analyzer initialized")

    async def _send_discord_log(self, embed_data: dict):
        """Send filtering decision to Discord log channel with interactive buttons."""
        try:
            if not self.bot or not hasattr(self.bot, 'log_channel') or not self.bot.log_channel:
                return
            
            # Check if Discord safety logging is enabled
            if hasattr(self.bot, 'automation_config'):
                config = getattr(self.bot, 'automation_config', {})
                if not config.get('discord_safety_logging', True):
                    return
            
            import discord
            from src.components.embeds.base_embed import BaseEmbed
            
            # Create embed based on safety level
            safety_level = embed_data.get('safety_level', 'safe')
            
            if safety_level in ['graphic', 'disturbing']:
                # Red embed for blocked content
                embed = discord.Embed(
                    title="🛡️ Content Filtered (BLOCKED)",
                    color=0xFF0000,  # Red
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="🚨 Action", value="**BLOCKED** - Content filtered for safety", inline=False)
            elif safety_level == 'sensitive':
                # Yellow embed for sensitive content
                embed = discord.Embed(
                    title="⚠️ Content Flagged (ALLOWED)",
                    color=0xFFFF00,  # Yellow
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="⚠️ Action", value="**ALLOWED** with content warning", inline=False)
            else:
                # Green embed for safe content
                embed = discord.Embed(
                    title="✅ Content Approved",
                    color=0x00FF00,  # Green
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="✅ Action", value="**APPROVED** - Content is safe", inline=False)
            
            # Add common fields
            embed.add_field(name="📊 Safety Level", value=f"`{safety_level.upper()}`", inline=True)
            embed.add_field(name="🎯 Confidence", value=f"`{embed_data.get('confidence', 0):.1%}`", inline=True)
            embed.add_field(name="📺 Channel", value=f"`{embed_data.get('channel', 'Unknown')}`", inline=True)
            
            # Add content preview (truncated)
            content_preview = embed_data.get('content', '')[:200]
            if len(embed_data.get('content', '')) > 200:
                content_preview += "..."
            embed.add_field(name="📝 Content Preview", value=f"```{content_preview}```", inline=False)
            
            # Add indicators if present
            indicators = embed_data.get('indicators', [])
            if indicators:
                indicators_text = ", ".join(indicators[:5])  # Show first 5 indicators
                if len(indicators) > 5:
                    indicators_text += f" (+{len(indicators) - 5} more)"
                embed.add_field(name="🔍 Detection Keywords", value=f"`{indicators_text}`", inline=False)
            
            # Add warning message if present
            warning = embed_data.get('content_warning')
            if warning:
                embed.add_field(name="⚠️ Content Warning", value=warning, inline=False)
            
            # Add footer
            embed.set_footer(text="NewsBot Content Safety System")
            
            # Create view with buttons only for blocked/flagged content
            view = None
            if safety_level in ['graphic', 'disturbing', 'sensitive']:
                view = ContentFilterView(
                    bot=self.bot,
                    embed_data=embed_data,
                    safety_level=safety_level
                )
            
            # Send embed with or without buttons
            message_content = ""
            
            # Ping user for flagged content that needs manual verification
            if safety_level in ['graphic', 'disturbing', 'sensitive']:
                # Get user ID from config
                if hasattr(self.bot, 'unified_config'):
                    user_id = self.bot.unified_config.get('admin.user_id')
                    if user_id:
                        message_content = f"<@{user_id}> 🚨 **Content flagged for manual verification** - Please review and take action (approve/blacklist)"
                        
                        # Set manual verification delay (1 hour = 3600 seconds)
                        if not hasattr(self.bot, '_manual_verification_delay_until'):
                            self.bot._manual_verification_delay_until = {}
                        
                        import datetime
                        delay_until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
                        self.bot._manual_verification_delay_until['auto_fetch'] = delay_until
                        
                        logger.info(f"🛡️ Manual verification required - auto-fetch delayed until {delay_until.strftime('%H:%M UTC')}")
            
            if view:
                await self.bot.log_channel.send(content=message_content, embed=embed, view=view)
            else:
                await self.bot.log_channel.send(content=message_content, embed=embed)
            
        except Exception as e:
            logger.error(f"❌ Failed to send Discord log: {e}")

    # =========================================================================
    # Content Safety Analysis Methods
    # =========================================================================
    async def analyze_content_safety(self, text: str, media: List = None, channel: str = None, telegram_message=None, message_id: int = None) -> SafetyResult:
        """
        Analyze content for graphic/disturbing material and safety concerns.
        
        Args:
            text: Content to analyze for safety
            media: Optional media attachments to consider
            telegram_message: Original telegram message for button actions
            message_id: Message ID for reference
            
        Returns:
            SafetyResult with safety assessment and filtering decision
        """
        try:
            text_lower = text.lower()
            safety_scores = {}
            graphic_indicators = []
            safety_issues = []
            
            # Check for graphic content keywords
            for safety_level, keywords in self.safety_keywords.items():
                score = 0
                found_keywords = []
                
                # Check Arabic keywords with word boundary consideration
                for keyword in keywords.get('ar', []):
                    # For short keywords like "دم", ensure it's not part of a larger word like "دمشق"
                    if len(keyword) <= 2:
                        # Use word boundary check for short keywords
                        import re
                        pattern = r'\b' + re.escape(keyword) + r'\b'
                        if re.search(pattern, text_lower):
                            score += 1
                            found_keywords.append(keyword)
                            graphic_indicators.append(f"Arabic: {keyword}")
                    else:
                        # For longer keywords, use simple contains check
                        if keyword in text_lower:
                            score += 1
                            found_keywords.append(keyword)
                            graphic_indicators.append(f"Arabic: {keyword}")
                
                # Check English keywords
                for keyword in keywords.get('en', []):
                    if keyword in text_lower:
                        score += 1
                        found_keywords.append(keyword)
                        graphic_indicators.append(f"English: {keyword}")
                
                # Normalize score
                total_keywords = len(keywords.get('ar', [])) + len(keywords.get('en', []))
                safety_scores[safety_level] = score / total_keywords if total_keywords > 0 else 0
            
            # Determine primary safety level
            primary_safety = ContentSafety.SAFE
            max_score = 0
            confidence = 0.0
            
            for safety_level, score in safety_scores.items():
                if score > max_score:
                    max_score = score
                    primary_safety = safety_level
                    confidence = min(score * 2, 1.0)  # Scale confidence
            
            # Special checks for extremely graphic content
            extremely_graphic_phrases = [
                'تقطعت أوصال', 'قطع أوصال', 'أشلاء', 'دماء في كل مكان',
                'dismembered', 'body parts', 'severed limbs', 'gore', 'graphic violence'
            ]
            
            for phrase in extremely_graphic_phrases:
                if phrase in text_lower:
                    primary_safety = ContentSafety.GRAPHIC
                    confidence = min(confidence + 0.3, 1.0)
                    safety_issues.append(f"Extremely graphic phrase detected: {phrase}")
                    break
            
            # Check for video content with violent keywords
            has_video = media and any(
                hasattr(m, 'video') or 
                (hasattr(m, 'document') and getattr(m.document, 'mime_type', '').startswith('video/'))
                for m in media if m
            )
            
            if has_video and primary_safety in [ContentSafety.GRAPHIC, ContentSafety.DISTURBING]:
                safety_issues.append("Video content with graphic descriptions - high risk")
                confidence = min(confidence + 0.2, 1.0)
            
            # Determine if content should be filtered
            should_filter = primary_safety in [ContentSafety.GRAPHIC, ContentSafety.DISTURBING]
            
            # Generate content warning if needed
            content_warning = None
            if primary_safety == ContentSafety.SENSITIVE:
                content_warning = "⚠️ Content may contain descriptions of violence or casualties"
            elif primary_safety == ContentSafety.GRAPHIC:
                content_warning = "🚨 Graphic content - contains descriptions of violence and injuries"
                should_filter = True  # Always filter graphic content
            elif primary_safety == ContentSafety.DISTURBING:
                content_warning = "🚨 Disturbing content - contains extremely violent material"
                should_filter = True  # Always filter disturbing content
            
            # Log safety analysis
            if should_filter:
                logger.warning(f"🛡️ Content filtered: {primary_safety.value} (confidence: {confidence:.2f})")
                logger.warning(f"🛡️ Indicators: {graphic_indicators[:3]}")  # Log first 3 indicators
            elif primary_safety != ContentSafety.SAFE:
                logger.info(f"🛡️ Content flagged as {primary_safety.value} (confidence: {confidence:.2f})")
            
            # Send Discord log for all non-safe content
            if primary_safety != ContentSafety.SAFE or should_filter:
                await self._send_discord_log({
                    'safety_level': primary_safety.value,
                    'confidence': confidence,
                    'content': text[:500],  # First 500 chars
                    'indicators': [ind.split(': ')[1] if ': ' in ind else ind for ind in graphic_indicators],
                    'content_warning': content_warning,
                    'channel': channel or 'Auto-Analysis',  # Use provided channel name
                    'telegram_message': telegram_message,  # Pass telegram message for media download
                    'message_id': message_id  # Pass message ID for reference
                })
            
            return SafetyResult(
                safety_level=primary_safety,
                confidence=confidence,
                graphic_indicators=graphic_indicators,
                safety_issues=safety_issues,
                should_filter=should_filter,
                content_warning=content_warning
            )
            
        except Exception as e:
            logger.error(f"❌ Error in safety analysis: {e}")
            # Fail safe - if analysis fails, assume content might be unsafe
            return SafetyResult(
                safety_level=ContentSafety.SENSITIVE,
                confidence=0.5,
                graphic_indicators=[],
                safety_issues=[f"Safety analysis failed: {str(e)}"],
                should_filter=False,  # Don't filter on analysis failure
                content_warning="⚠️ Content could not be analyzed for safety"
            )

    # =========================================================================
    # Sentiment Analysis Methods
    # =========================================================================
    async def analyze_sentiment(self, text: str) -> SentimentResult:
        """
        Analyze sentiment of news content with confidence scoring.
        
        Args:
            text: Content to analyze for sentiment
            
        Returns:
            SentimentResult with sentiment analysis and indicators
        """
        try:
            text_lower = text.lower()
            sentiment_scores = {}
            emotional_indicators = []
            
            # Calculate scores for each sentiment category
            for sentiment, keywords in self.sentiment_keywords.items():
                score = 0
                found_keywords = []
                
                # Check Arabic keywords
                for keyword in keywords['ar']:
                    if keyword in text_lower:
                        score += 1
                        found_keywords.append(keyword)
                
                # Check English keywords  
                for keyword in keywords['en']:
                    if keyword in text_lower:
                        score += 1
                        found_keywords.append(keyword)
                
                if found_keywords:
                    emotional_indicators.extend(found_keywords)
                    sentiment_scores[sentiment] = score
            
            # Determine primary sentiment
            if sentiment_scores:
                primary_sentiment = max(sentiment_scores.keys(), key=lambda k: sentiment_scores[k])
                confidence = min(1.0, sentiment_scores[primary_sentiment] / 5.0)
            else:
                primary_sentiment = Sentiment.NEUTRAL
                confidence = 0.8  # High confidence in neutral
            
            # Determine tone based on content and indicators
            tone = self._determine_tone(text, emotional_indicators)
            
            return SentimentResult(
                sentiment=primary_sentiment,
                confidence=confidence,
                emotional_indicators=emotional_indicators,
                tone=tone
            )
            
        except Exception as e:
            logger.error(f"❌ Error analyzing sentiment: {e}")
            # Return safe default
            return SentimentResult(
                sentiment=Sentiment.NEUTRAL,
                confidence=0.5,
                emotional_indicators=[],
                tone="neutral"
            )

    # =========================================================================
    # Content Categorization Methods
    # =========================================================================
    async def categorize_content(self, text: str) -> CategoryResult:
        """
        Categorize news content with confidence scoring.
        
        Args:
            text: Content to categorize
            
        Returns:
            CategoryResult with primary and secondary categories
        """
        try:
            text_lower = text.lower()
            category_scores = {}
            category_indicators = {}
            
            # Calculate scores for each category
            for category, keywords in self.category_keywords.items():
                score = 0
                found_keywords = []
                
                # Check Arabic keywords
                for keyword in keywords['ar']:
                    if keyword in text_lower:
                        score += 1
                        found_keywords.append(keyword)
                
                # Check English keywords
                for keyword in keywords['en']:
                    if keyword in text_lower:
                        score += 1
                        found_keywords.append(keyword)
                
                if found_keywords:
                    category_scores[category] = score
                    category_indicators[category.value] = found_keywords
            
            # Determine primary category
            if category_scores:
                primary_category = max(category_scores.keys(), key=lambda k: category_scores[k])
                confidence = min(1.0, category_scores[primary_category] / 3.0)
                
                # Get secondary categories (scores > 0 but not primary)
                secondary_categories = [
                    cat for cat, score in category_scores.items() 
                    if cat != primary_category and score > 0
                ]
            else:
                # Default to BREAKING if no specific category found
                primary_category = NewsCategory.BREAKING
                secondary_categories = []
                confidence = 0.6
                category_indicators = {}
            
            return CategoryResult(
                primary_category=primary_category,
                secondary_categories=secondary_categories,
                confidence=confidence,
                category_indicators=category_indicators
            )
            
        except Exception as e:
            logger.error(f"❌ Error categorizing content: {e}")
            # Return safe default
            return CategoryResult(
                primary_category=NewsCategory.BREAKING,
                secondary_categories=[],
                confidence=0.5,
                category_indicators={}
            )

    # =========================================================================
    # Duplicate Detection Methods
    # =========================================================================
    async def detect_duplicates(self, new_content: str, recent_posts: List[str] = None) -> float:
        """
        Detect duplicate content using similarity matching.
        
        Args:
            new_content: New content to check for duplicates
            recent_posts: Optional list of recent posts to compare against
            
        Returns:
            float: Highest similarity score (0.0-1.0)
        """
        try:
            # Use provided recent posts or cache
            posts_to_check = recent_posts if recent_posts is not None else self.recent_posts_cache
            
            if not posts_to_check:
                return 0.0
            
            # Clean content for comparison
            cleaned_new = self._clean_for_comparison(new_content)
            
            max_similarity = 0.0
            
            # Compare with each recent post
            for post in posts_to_check:
                cleaned_post = self._clean_for_comparison(post)
                similarity = SequenceMatcher(None, cleaned_new, cleaned_post).ratio()
                max_similarity = max(max_similarity, similarity)
            
            return max_similarity
            
        except Exception as e:
            logger.error(f"❌ Error detecting duplicates: {e}")
            return 0.0

    # =========================================================================
    # Content Quality Assessment Methods
    # =========================================================================
    async def assess_content_quality(self, content: str, media: List = None) -> QualityScore:
        """
        Assess content quality with detailed metrics.
        
        Args:
            content: Content to assess for quality
            media: Optional media attachments
            
        Returns:
            QualityScore with detailed quality metrics
        """
        try:
            issues = []
            
            # Assess different quality dimensions
            completeness = self._assess_completeness(content, issues)
            clarity = self._assess_clarity(content, issues)
            informativeness = self._assess_informativeness(content, issues)
            media_quality = self._assess_media_quality(media or [], issues)
            
            # Calculate overall score
            overall_score = (
                completeness * 0.3 +
                clarity * 0.25 +
                informativeness * 0.25 +
                media_quality * 0.2
            )
            
            return QualityScore(
                overall_score=overall_score,
                completeness=completeness,
                clarity=clarity,
                informativeness=informativeness,
                media_quality=media_quality,
                issues=issues
            )
            
        except Exception as e:
            logger.error(f"❌ Error assessing content quality: {e}")
            # Return safe default
            return QualityScore(
                overall_score=0.5,
                completeness=0.5,
                clarity=0.5,
                informativeness=0.5,
                media_quality=0.5,
                issues=["Quality assessment failed"]
            )

    # =========================================================================
    # Main Processing Method
    # =========================================================================
    async def process_content_intelligently(self, raw_content: str, channel: str, media: List = None, telegram_message=None, message_id: int = None) -> ProcessedContent:
        """
        Process content with comprehensive AI analysis including safety filtering.
        
        Args:
            raw_content: Raw content to process
            channel: Source channel for context
            media: Optional media attachments
            
        Returns:
            ProcessedContent with complete analysis results
        """
        try:
            processing_notes = []
            
            # Translate content if needed
            translated_content = await self._translate_content(raw_content)
            
            # Perform safety analysis first (most important)
            safety_result = await self.analyze_content_safety(translated_content, media, channel, telegram_message, message_id)
            
            # If content should be filtered for safety, stop processing
            if safety_result.should_filter:
                processing_notes.append(f"Content filtered for safety: {safety_result.safety_level.value}")
                processing_notes.extend(safety_result.safety_issues)
                
                # Return early with minimal processing for filtered content
                return ProcessedContent(
                    original_content=raw_content,
                    translated_content=translated_content,
                    sentiment=SentimentResult(Sentiment.NEGATIVE, 0.8, [], "concerning"),
                    categories=CategoryResult(NewsCategory.BREAKING, [], 0.6, {}),
                    quality=QualityScore(0.3, 0.3, 0.3, 0.3, 0.3, ["Content filtered for safety"]),
                    safety=safety_result,
                    similarity_score=0.0,
                    should_post=False,  # Never post filtered content
                    posting_priority=0,  # Lowest priority
                    processing_notes=processing_notes
                )
            
            # Perform all other analyses for safe content
            sentiment = await self.analyze_sentiment(raw_content)
            categories = await self.categorize_content(raw_content)
            quality = await self.assess_content_quality(raw_content, media)
            similarity = await self.detect_duplicates(raw_content)
            
            # Make posting decision
            should_post = self._decide_posting(sentiment, quality, similarity, categories, safety_result)
            
            # Calculate priority
            priority = self._calculate_priority(sentiment, categories, quality)
            
            # Add processing notes
            processing_notes.append(f"Analyzed by AI Content Analyzer")
            processing_notes.append(f"Sentiment: {sentiment.sentiment.value} ({sentiment.confidence:.2f})")
            processing_notes.append(f"Category: {categories.primary_category.value} ({categories.confidence:.2f})")
            processing_notes.append(f"Quality: {quality.overall_score:.2f}")
            processing_notes.append(f"Similarity: {similarity:.2f}")
            
            # Update cache with new content
            self._update_cache(raw_content)
            
            return ProcessedContent(
                original_content=raw_content,
                translated_content=translated_content,
                sentiment=sentiment,
                categories=categories,
                quality=quality,
                safety=safety_result,
                similarity_score=similarity,
                should_post=should_post,
                posting_priority=priority,
                processing_notes=processing_notes
            )
            
        except Exception as e:
            logger.error(f"❌ Error processing content intelligently: {e}")
            # Return safe default
            return ProcessedContent(
                original_content=raw_content,
                translated_content=raw_content,
                sentiment=SentimentResult(Sentiment.NEUTRAL, 0.5, [], "neutral"),
                categories=CategoryResult(NewsCategory.BREAKING, [], 0.5, {}),
                quality=QualityScore(0.5, 0.5, 0.5, 0.5, 0.5, []),
                safety=SafetyResult(ContentSafety.SAFE, 0.5, [], [], False, None),
                similarity_score=0.0,
                should_post=True,
                posting_priority=3,
                processing_notes=["Processing failed, using defaults"]
            )

    # =========================================================================
    # Helper Methods
    # =========================================================================
    def _determine_tone(self, text: str, indicators: List[str]) -> str:
        """Determine the tone of the content."""
        if any(word in indicators for word in ['عاجل', 'urgent', 'breaking']):
            return "urgent"
        elif any(word in indicators for word in ['رسمي', 'official', 'formal']):
            return "formal"
        elif len(indicators) > 3:
            return "emotional"
        else:
            return "neutral"

    def _clean_for_comparison(self, content: str) -> str:
        """Clean content for duplicate comparison."""
        # Remove special characters, normalize spaces
        cleaned = re.sub(r'[^\w\s]', '', content.lower())
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def _assess_completeness(self, content: str, issues: List[str]) -> float:
        """Assess how complete the content is."""
        length = len(content)
        
        if length < 20:
            issues.append("Content too short")
            return 0.2
        elif length < 50:
            issues.append("Content might be incomplete")
            return 0.5
        elif length > 1000:
            issues.append("Content might be too verbose")
            return 0.8
        else:
            return 0.9

    def _assess_clarity(self, content: str, issues: List[str]) -> float:
        """Assess how clear the content is."""
        # Check for excessive repetition
        words = content.lower().split()
        unique_words = set(words)
        
        if len(words) == 0:
            issues.append("No content to assess")
            return 0.0
        
        repetition_ratio = len(unique_words) / len(words)
        
        if repetition_ratio < 0.3:
            issues.append("Too much repetition")
            return 0.4
        elif repetition_ratio < 0.5:
            return 0.6
        else:
            return 0.9

    def _assess_informativeness(self, content: str, issues: List[str]) -> float:
        """Assess how informative the content is."""
        # Look for key information indicators
        info_indicators = ['who', 'what', 'when', 'where', 'why', 'how', 'من', 'ماذا', 'متى', 'أين', 'لماذا', 'كيف']
        
        content_lower = content.lower()
        info_count = sum(1 for indicator in info_indicators if indicator in content_lower)
        
        if info_count == 0:
            issues.append("Lacks informative content")
            return 0.3
        elif info_count < 3:
            return 0.6
        else:
            return 0.9

    def _assess_media_quality(self, media: List, issues: List[str]) -> float:
        """Assess the quality of attached media."""
        if not media:
            return 0.5  # Neutral score for no media
        
        score = 0.0
        for item in media:
            if hasattr(item, 'content_type'):
                if 'image' in item.content_type:
                    score += 0.3
                elif 'video' in item.content_type:
                    score += 0.5
                else:
                    score += 0.1
        
        return min(1.0, score)

    def _decide_posting(self, sentiment: SentimentResult, quality: QualityScore, 
                       similarity: float, categories: CategoryResult, safety: SafetyResult = None) -> bool:
        """Decide whether content should be posted."""
        # Never post if safety analysis says to filter
        if safety and safety.should_filter:
            return False
        
        # Don't post if quality is too low
        if quality.overall_score < 0.3:
            return False
        
        # Don't post if too similar to recent content
        if similarity > 0.8:
            return False
        
        # Don't post if sentiment confidence is too low
        if sentiment.confidence < 0.2:
            return False
        
        # Post everything else
        return True

    def _calculate_priority(self, sentiment: SentimentResult, categories: CategoryResult, 
                          quality: QualityScore) -> int:
        """Calculate posting priority (1-5, higher = more important)."""
        priority = 3  # Default priority
        
        # Adjust based on sentiment
        if sentiment.sentiment == Sentiment.URGENT:
            priority += 2
        elif sentiment.sentiment == Sentiment.CONCERNING:
            priority += 1
        elif sentiment.sentiment == Sentiment.POSITIVE:
            priority += 0
        elif sentiment.sentiment == Sentiment.NEGATIVE:
            priority += 1
        
        # Adjust based on category
        if categories.primary_category == NewsCategory.BREAKING:
            priority += 2
        elif categories.primary_category == NewsCategory.MILITARY:
            priority += 1
        elif categories.primary_category == NewsCategory.POLITICS:
            priority += 1
        
        # Adjust based on quality
        if quality.overall_score > 0.8:
            priority += 1
        elif quality.overall_score < 0.4:
            priority -= 1
        
        # Ensure priority is within bounds
        return max(1, min(5, priority))

    def _update_cache(self, content: str):
        """Update the recent posts cache."""
        self.recent_posts_cache.append(content)
        if len(self.recent_posts_cache) > self.cache_size:
            self.recent_posts_cache.pop(0)

    async def _translate_content(self, content: str) -> str:
        """Translate content if needed (placeholder for future implementation)."""
        # For now, return original content
        # Future: Implement actual translation logic
        return content

    # =========================================================================
    # Utility Methods
    # =========================================================================
    def get_category_emoji(self, category: NewsCategory) -> str:
        """Get emoji representation for news category."""
        emoji_map = {
            NewsCategory.POLITICS: "🏛️",
            NewsCategory.MILITARY: "⚔️",
            NewsCategory.ECONOMY: "💰",
            NewsCategory.HEALTH: "🏥",
            NewsCategory.INTERNATIONAL: "🌍",
            NewsCategory.BREAKING: "🚨",
            NewsCategory.SOCIAL: "👥",
            NewsCategory.SPORTS: "⚽",
            NewsCategory.TECHNOLOGY: "💻",
            NewsCategory.CULTURE: "🎭"
        }
        return emoji_map.get(category, "📰")

    def get_sentiment_emoji(self, sentiment: Sentiment) -> str:
        """Get emoji representation for sentiment."""
        emoji_map = {
            Sentiment.POSITIVE: "😊",
            Sentiment.NEGATIVE: "😔",
            Sentiment.NEUTRAL: "😐",
            Sentiment.URGENT: "⚠️",
            Sentiment.CONCERNING: "😰"
        }
        return emoji_map.get(sentiment, "📰")


# =============================================================================
# Content Filter View for Interactive Buttons
# =============================================================================
class ContentFilterView(discord.ui.View):
    """View for content filtering decisions with post/download/blacklist buttons."""
    
    def __init__(self, bot, embed_data: dict, safety_level: str):
        super().__init__(timeout=3600)  # 1 hour timeout
        self.bot = bot
        self.embed_data = embed_data
        self.safety_level = safety_level
        self.original_content = embed_data.get('content', '')
        self.channel = embed_data.get('channel', 'Unknown')
        
        # Store message data for potential posting
        self.message_id = embed_data.get('message_id')
        self.telegram_message = embed_data.get('telegram_message')
        
    @discord.ui.button(label="📤 Post Anyway", style=discord.ButtonStyle.success)
    async def post_anyway(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Post the filtered content anyway (admin override)."""
        try:
            # Check if user is admin
            from src.core.unified_config import unified_config as unified_config
            admin_user_id = unified_config.get("bot.admin_user_id")
            if not admin_user_id or interaction.user.id != int(admin_user_id):
                await interaction.response.send_message("❌ Only admins can override content filtering.", ephemeral=True)
                return
            
            await interaction.response.defer()
            
            # Create a simple override notification
            embed = discord.Embed(
                title="⚠️ Admin Override - Content Posted",
                description=f"Content from **{self.channel}** was posted despite safety filtering.",
                color=0xFF8C00  # Orange
            )
            embed.add_field(name="Safety Level", value=f"`{self.safety_level.upper()}`", inline=True)
            embed.add_field(name="Override by", value=f"<@{interaction.user.id}>", inline=True)
            embed.add_field(name="Original Content", value=f"```{self.original_content[:500]}```", inline=False)
            
            # Add warning
            embed.add_field(
                name="⚠️ Warning", 
                value="This content was flagged by the safety system but posted by admin override.", 
                inline=False
            )
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            await interaction.followup.edit_message(interaction.message.id, view=self)
            await interaction.followup.send(embed=embed)
            
            # Clear manual verification delay since admin took action
            if hasattr(self.bot, '_manual_verification_delay_until') and 'auto_fetch' in self.bot._manual_verification_delay_until:
                del self.bot._manual_verification_delay_until['auto_fetch']
                logger.info("🚀 Manual verification delay cleared - admin approved content")
            
            logger.warning(f"🛡️ [ADMIN-OVERRIDE] Content posted despite safety filtering by {interaction.user.id}: {self.safety_level}")
            
        except Exception as e:
            logger.error(f"Error in post anyway: {e}")
            await interaction.followup.send(f"❌ Error posting content: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="📥 Download Media", style=discord.ButtonStyle.secondary)
    async def download_media(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Download the media from the filtered content."""
        try:
            # Check if user is admin
            from src.core.unified_config import unified_config as unified_config
            admin_user_id = unified_config.get("bot.admin_user_id")
            if not admin_user_id or interaction.user.id != int(admin_user_id):
                await interaction.response.send_message("❌ Only admins can download media.", ephemeral=True)
                return
            
            await interaction.response.defer()
            
            # Check if we have telegram message data
            if not self.telegram_message:
                await interaction.followup.send("❌ No telegram message data available for download.", ephemeral=True)
                return
            
            # Try to download media using the media service
            try:
                from src.services.media_service import MediaService
                import os
                
                media_service = MediaService(self.bot)
                
                if hasattr(self.telegram_message, 'media') and self.telegram_message.media:
                    # Download media
                    media_files, temp_path = await media_service.download_media_with_timeout(
                        self.telegram_message, self.telegram_message.media
                    )
                    
                    if media_files:
                        # Create download notification
                        embed = discord.Embed(
                            title="📥 Media Downloaded",
                            description=f"Media from **{self.channel}** has been downloaded.",
                            color=0x00FF00
                        )
                        embed.add_field(name="Files Downloaded", value=f"`{len(media_files)} files`", inline=True)
                        embed.add_field(name="Downloaded by", value=f"<@{interaction.user.id}>", inline=True)
                        embed.add_field(name="Safety Level", value=f"`{self.safety_level.upper()}`", inline=True)
                        
                        # Try to attach the first file if it's small enough
                        try:
                            if media_files and len(media_files) > 0:
                                file_path = media_files[0]
                                if os.path.exists(file_path) and os.path.getsize(file_path) < 8 * 1024 * 1024:  # 8MB limit
                                    discord_file = discord.File(file_path)
                                    await interaction.followup.send(embed=embed, file=discord_file)
                                else:
                                    embed.add_field(name="Note", value="File too large to attach to Discord", inline=False)
                                    await interaction.followup.send(embed=embed)
                            else:
                                await interaction.followup.send(embed=embed)
                        except Exception as e:
                            logger.warning(f"Could not attach file to Discord: {e}")
                            await interaction.followup.send(embed=embed)
                        
                        logger.info(f"📥 [DOWNLOAD] Media downloaded by {interaction.user.id} from {self.channel}: {len(media_files)} files")
                    else:
                        await interaction.followup.send("❌ Failed to download media files.", ephemeral=True)
                else:
                    await interaction.followup.send("❌ No media available for download.", ephemeral=True)
                    
            except Exception as e:
                logger.error(f"Error downloading media: {e}")
                await interaction.followup.send(f"❌ Error downloading media: {str(e)}", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in download media button: {e}")
            await interaction.followup.send(f"❌ Error downloading media: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="🚫 Blacklist Post", style=discord.ButtonStyle.danger)
    async def blacklist_post(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Blacklist the message to prevent future processing."""
        try:
            # Check if user is admin
            from src.core.unified_config import unified_config as unified_config
            admin_user_id = unified_config.get("bot.admin_user_id")
            if not admin_user_id or interaction.user.id != int(admin_user_id):
                await interaction.response.send_message("❌ Only admins can blacklist posts.", ephemeral=True)
                return

            await interaction.response.defer()

            # Add message ID to blacklist
            if hasattr(self.bot, 'json_cache') and self.bot.json_cache and self.message_id:
                blacklisted_posts = await self.bot.json_cache.get("blacklisted_posts") or []
                if self.message_id not in blacklisted_posts:
                    blacklisted_posts.append(self.message_id)
                    await self.bot.json_cache.set("blacklisted_posts", blacklisted_posts)
                    await self.bot.json_cache.save()

                    # Create blacklist confirmation
                    embed = discord.Embed(
                        title="🚫 Post Blacklisted",
                        description=f"Message **{self.message_id}** from **{self.channel}** has been blacklisted.",
                        color=0xFF0000
                    )
                    embed.add_field(name="Message ID", value=str(self.message_id), inline=True)
                    embed.add_field(name="Channel", value=self.channel, inline=True)
                    embed.add_field(name="Safety Level", value=f"`{self.safety_level.upper()}`", inline=True)
                    embed.add_field(name="Blacklisted by", value=f"<@{interaction.user.id}>", inline=True)

                    # Disable all buttons
                    for item in self.children:
                        item.disabled = True

                    await interaction.followup.edit_message(interaction.message.id, view=self)
                    await interaction.followup.send(embed=embed)

                    # Clear manual verification delay since admin took action
                    if hasattr(self.bot, '_manual_verification_delay_until') and 'auto_fetch' in self.bot._manual_verification_delay_until:
                        del self.bot._manual_verification_delay_until['auto_fetch']
                        logger.info("🚀 Manual verification delay cleared - admin blacklisted content")

                    logger.info(f"🚫 [BLACKLIST] Content safety post {self.message_id} from {self.channel} blacklisted by {interaction.user.id}")
                else:
                    await interaction.followup.send(f"⚠️ Message **{self.message_id}** is already blacklisted.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Cache not available for blacklisting or no message ID.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error in blacklist button: {e}")
            await interaction.followup.send(f"❌ Error blacklisting post: {str(e)}", ephemeral=True)
    
    async def on_timeout(self):
        """Called when the view times out."""
        # Disable all buttons
        for item in self.children:
            item.disabled = True 