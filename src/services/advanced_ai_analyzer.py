"""
Advanced AI Content Analysis System for NewsBot
Provides multi-dimensional content analysis including emotional intelligence,
credibility assessment, viral potential prediction, and cultural context awareness.
"""
import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import re

import openai
from src.utils.base_logger import base_logger as logger
from src.core.unified_config import unified_config as config


class EmotionalDimension(Enum):
    """Emotional dimensions for content analysis."""
    ANGER = "anger"
    FEAR = "fear"
    HOPE = "hope"
    SADNESS = "sadness"
    JOY = "joy"
    URGENCY = "urgency"
    ANXIETY = "anxiety"
    DETERMINATION = "determination"


class CredibilityFactor(Enum):
    """Factors affecting content credibility."""
    SOURCE_RELIABILITY = "source_reliability"
    FACT_CHECKABLE = "fact_checkable"
    BIAS_LEVEL = "bias_level"
    EMOTIONAL_MANIPULATION = "emotional_manipulation"
    EVIDENCE_QUALITY = "evidence_quality"
    LANGUAGE_QUALITY = "language_quality"


@dataclass
class EmotionalProfile:
    """Emotional analysis results."""
    primary_emotion: EmotionalDimension
    emotion_scores: Dict[EmotionalDimension, float] = field(default_factory=dict)
    emotional_intensity: float = 0.0
    emotional_stability: float = 0.0
    manipulation_likelihood: float = 0.0


@dataclass
class CredibilityAssessment:
    """Content credibility analysis."""
    overall_score: float
    factor_scores: Dict[CredibilityFactor, float] = field(default_factory=dict)
    reliability_indicators: List[str] = field(default_factory=list)
    warning_flags: List[str] = field(default_factory=list)
    fact_check_suggestions: List[str] = field(default_factory=list)


@dataclass
class ViralPotential:
    """Viral content prediction analysis."""
    viral_score: float
    engagement_prediction: Dict[str, float] = field(default_factory=dict)
    sharing_likelihood: float = 0.0
    discussion_potential: float = 0.0
    timing_optimization: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CulturalContext:
    """Cultural context and sensitivity analysis."""
    cultural_sensitivity_score: float
    cultural_references: List[str] = field(default_factory=list)
    potential_misunderstandings: List[str] = field(default_factory=list)
    localization_suggestions: List[str] = field(default_factory=list)
    religious_considerations: List[str] = field(default_factory=list)


@dataclass
class ContentInsights:
    """Comprehensive content analysis results."""
    emotional_profile: EmotionalProfile
    credibility_assessment: CredibilityAssessment
    viral_potential: ViralPotential
    cultural_context: CulturalContext
    analysis_timestamp: datetime = field(default_factory=datetime.now)
    processing_time_ms: float = 0.0
    confidence_score: float = 0.0


class AdvancedAIAnalyzer:
    """Advanced AI-powered content analysis system."""
    
    def __init__(self):
        """Initialize the advanced analyzer."""
        self.openai_client = openai
        self.analysis_cache: Dict[str, ContentInsights] = {}
        self.cache_ttl = 3600  # 1 hour cache
        
        # Analysis prompts
        self.prompts = {
            'emotional_analysis': """
Analyze the emotional dimensions of this Arabic/English news content. Provide scores (0-1) for each emotion:
- anger: How much anger or outrage does this content express or evoke?
- fear: How much fear, worry, or concern does this content contain?
- hope: How much hope, optimism, or positive outlook is present?
- sadness: How much sadness, grief, or melancholy is expressed?
- joy: How much happiness, celebration, or positive emotion is present?
- urgency: How urgent or time-sensitive is this content?
- anxiety: How much anxiety or stress does this content create?
- determination: How much resolve, determination, or call-to-action is present?

Also assess:
- emotional_intensity (0-1): Overall emotional strength
- emotional_stability (0-1): How balanced vs extreme the emotions are
- manipulation_likelihood (0-1): Likelihood this is designed to manipulate emotions

Content: {content}

Respond in JSON format with numerical scores and brief reasoning.
""",
            
            'credibility_analysis': """
Assess the credibility and reliability of this news content. Analyze these factors (0-1 scores):
- source_reliability: How reliable does the source appear?
- fact_checkable: How verifiable are the claims made?
- bias_level: How biased or neutral is the presentation? (0=very biased, 1=neutral)
- emotional_manipulation: How much does this use emotion over facts?
- evidence_quality: Quality of evidence or sources cited
- language_quality: Professional vs sensationalized language

Identify:
- reliability_indicators: Positive credibility signals
- warning_flags: Potential credibility issues
- fact_check_suggestions: Claims that should be verified

Content: {content}

Respond in JSON format with scores, indicators, flags, and suggestions.
""",
            
            'viral_prediction': """
Predict the viral potential and engagement likelihood of this content. Analyze:
- viral_score (0-1): Overall likelihood to go viral
- engagement_prediction: Expected likes, shares, comments (relative scores 0-1)
- sharing_likelihood (0-1): How likely people are to share this
- discussion_potential (0-1): How likely to generate discussion
- timing_optimization: Best times/contexts for posting

Consider factors like:
- Emotional impact and relatability
- Controversy or debate potential
- Visual appeal (if media present)
- Trending topic relevance
- Cultural significance

Content: {content}

Respond in JSON format with predictions and reasoning.
""",
            
            'cultural_analysis': """
Analyze the cultural context and sensitivity of this Arabic/Syrian news content:
- cultural_sensitivity_score (0-1): How culturally appropriate/sensitive is this?
- cultural_references: Specific cultural, religious, or regional references
- potential_misunderstandings: What might be misunderstood by different audiences?
- localization_suggestions: How to adapt for different cultural contexts
- religious_considerations: Any religious sensitivities or considerations

Consider:
- Syrian/Arab cultural context
- Religious sensitivities (Islam, Christianity, etc.)
- Regional political sensitivities
- Language nuances and cultural idioms
- Cross-cultural communication challenges

Content: {content}

Respond in JSON format with analysis and suggestions.
"""
        }
        
        logger.info("🧠 Advanced AI Content Analyzer initialized")
        
    async def analyze_comprehensive(self, content: str, content_type: str = "news") -> ContentInsights:
        """
        Perform comprehensive multi-dimensional content analysis.
        
        Args:
            content: Text content to analyze
            content_type: Type of content (news, social, etc.)
            
        Returns:
            ContentInsights with complete analysis
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = self._generate_cache_key(content)
        if cache_key in self.analysis_cache:
            cached_result = self.analysis_cache[cache_key]
            if (datetime.now() - cached_result.analysis_timestamp).seconds < self.cache_ttl:
                logger.debug("🔄 Using cached advanced analysis result")
                return cached_result
                
        logger.info("🧠 Starting comprehensive AI content analysis")
        
        try:
            # Run all analyses in parallel for efficiency
            analysis_tasks = [
                self._analyze_emotional_dimensions(content),
                self._assess_credibility(content),
                self._predict_viral_potential(content),
                self._analyze_cultural_context(content)
            ]
            
            emotional_profile, credibility_assessment, viral_potential, cultural_context = await asyncio.gather(
                *analysis_tasks, return_exceptions=True
            )
            
            # Handle any exceptions in individual analyses
            if isinstance(emotional_profile, Exception):
                logger.error(f"Emotional analysis failed: {emotional_profile}")
                emotional_profile = self._create_fallback_emotional_profile()
                
            if isinstance(credibility_assessment, Exception):
                logger.error(f"Credibility analysis failed: {credibility_assessment}")
                credibility_assessment = self._create_fallback_credibility_assessment()
                
            if isinstance(viral_potential, Exception):
                logger.error(f"Viral prediction failed: {viral_potential}")
                viral_potential = self._create_fallback_viral_potential()
                
            if isinstance(cultural_context, Exception):
                logger.error(f"Cultural analysis failed: {cultural_context}")
                cultural_context = self._create_fallback_cultural_context()
                
            # Calculate overall confidence score
            confidence_score = self._calculate_confidence_score(
                emotional_profile, credibility_assessment, viral_potential, cultural_context
            )
            
            # Create comprehensive insights
            insights = ContentInsights(
                emotional_profile=emotional_profile,
                credibility_assessment=credibility_assessment,
                viral_potential=viral_potential,
                cultural_context=cultural_context,
                analysis_timestamp=datetime.now(),
                processing_time_ms=(time.time() - start_time) * 1000,
                confidence_score=confidence_score
            )
            
            # Cache the result
            self.analysis_cache[cache_key] = insights
            
            logger.info(
                f"✅ Advanced analysis completed in {insights.processing_time_ms:.2f}ms "
                f"(confidence: {confidence_score:.2f})"
            )
            
            return insights
            
        except Exception as e:
            logger.error(f"❌ Advanced content analysis failed: {e}")
            return self._create_fallback_insights(content, time.time() - start_time)
            
    async def _analyze_emotional_dimensions(self, content: str) -> EmotionalProfile:
        """Analyze emotional dimensions using AI."""
        try:
            prompt = self.prompts['emotional_analysis'].format(content=content[:2000])
            
            response = await self.openai_client.ChatCompletion.acreate(
                model=config.get("openai.model", "gpt-4-turbo-preview"),
                messages=[
                    {"role": "system", "content": "You are an expert in emotional analysis and psychology, specializing in Arabic and Middle Eastern content."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Parse emotion scores
            emotion_scores = {}
            for emotion in EmotionalDimension:
                emotion_scores[emotion] = result.get(emotion.value, 0.0)
                
            # Find primary emotion
            primary_emotion = max(emotion_scores.items(), key=lambda x: x[1])[0]
            
            return EmotionalProfile(
                primary_emotion=primary_emotion,
                emotion_scores=emotion_scores,
                emotional_intensity=result.get('emotional_intensity', 0.0),
                emotional_stability=result.get('emotional_stability', 0.0),
                manipulation_likelihood=result.get('manipulation_likelihood', 0.0)
            )
            
        except Exception as e:
            logger.error(f"Emotional analysis failed: {e}")
            return self._create_fallback_emotional_profile()
            
    async def _assess_credibility(self, content: str) -> CredibilityAssessment:
        """Assess content credibility using AI."""
        try:
            prompt = self.prompts['credibility_analysis'].format(content=content[:2000])
            
            response = await self.openai_client.ChatCompletion.acreate(
                model=config.get("openai.model", "gpt-4-turbo-preview"),
                messages=[
                    {"role": "system", "content": "You are an expert fact-checker and media literacy specialist with deep knowledge of Middle Eastern news sources."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.2
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Parse factor scores
            factor_scores = {}
            for factor in CredibilityFactor:
                factor_scores[factor] = result.get(factor.value, 0.5)
                
            # Calculate overall score
            overall_score = sum(factor_scores.values()) / len(factor_scores)
            
            return CredibilityAssessment(
                overall_score=overall_score,
                factor_scores=factor_scores,
                reliability_indicators=result.get('reliability_indicators', []),
                warning_flags=result.get('warning_flags', []),
                fact_check_suggestions=result.get('fact_check_suggestions', [])
            )
            
        except Exception as e:
            logger.error(f"Credibility analysis failed: {e}")
            return self._create_fallback_credibility_assessment()
            
    async def _predict_viral_potential(self, content: str) -> ViralPotential:
        """Predict viral potential using AI."""
        try:
            prompt = self.prompts['viral_prediction'].format(content=content[:2000])
            
            response = await self.openai_client.ChatCompletion.acreate(
                model=config.get("openai.model", "gpt-4-turbo-preview"),
                messages=[
                    {"role": "system", "content": "You are a social media expert specializing in viral content prediction and engagement optimization."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.4
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return ViralPotential(
                viral_score=result.get('viral_score', 0.0),
                engagement_prediction=result.get('engagement_prediction', {}),
                sharing_likelihood=result.get('sharing_likelihood', 0.0),
                discussion_potential=result.get('discussion_potential', 0.0),
                timing_optimization=result.get('timing_optimization', {})
            )
            
        except Exception as e:
            logger.error(f"Viral prediction failed: {e}")
            return self._create_fallback_viral_potential()
            
    async def _analyze_cultural_context(self, content: str) -> CulturalContext:
        """Analyze cultural context and sensitivity."""
        try:
            prompt = self.prompts['cultural_analysis'].format(content=content[:2000])
            
            response = await self.openai_client.ChatCompletion.acreate(
                model=config.get("openai.model", "gpt-4-turbo-preview"),
                messages=[
                    {"role": "system", "content": "You are a cultural expert specializing in Middle Eastern, Arab, and Syrian culture with deep understanding of cross-cultural communication."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return CulturalContext(
                cultural_sensitivity_score=result.get('cultural_sensitivity_score', 0.5),
                cultural_references=result.get('cultural_references', []),
                potential_misunderstandings=result.get('potential_misunderstandings', []),
                localization_suggestions=result.get('localization_suggestions', []),
                religious_considerations=result.get('religious_considerations', [])
            )
            
        except Exception as e:
            logger.error(f"Cultural analysis failed: {e}")
            return self._create_fallback_cultural_context()
            
    def _generate_cache_key(self, content: str) -> str:
        """Generate cache key for content."""
        import hashlib
        return hashlib.md5(content.encode()).hexdigest()
        
    def _calculate_confidence_score(self, emotional_profile: EmotionalProfile, 
                                   credibility_assessment: CredibilityAssessment,
                                   viral_potential: ViralPotential,
                                   cultural_context: CulturalContext) -> float:
        """Calculate overall confidence score for the analysis."""
        # Factors that increase confidence
        factors = []
        
        # Emotional analysis confidence
        if emotional_profile.emotional_intensity > 0.1:
            factors.append(0.8)
        else:
            factors.append(0.6)
            
        # Credibility analysis confidence
        if len(credibility_assessment.reliability_indicators) > 0:
            factors.append(0.9)
        else:
            factors.append(0.7)
            
        # Viral prediction confidence
        if viral_potential.viral_score > 0.1:
            factors.append(0.8)
        else:
            factors.append(0.6)
            
        # Cultural analysis confidence
        if len(cultural_context.cultural_references) > 0:
            factors.append(0.9)
        else:
            factors.append(0.7)
            
        return sum(factors) / len(factors)
        
    # Fallback methods for error handling
    def _create_fallback_emotional_profile(self) -> EmotionalProfile:
        """Create fallback emotional profile."""
        return EmotionalProfile(
            primary_emotion=EmotionalDimension.URGENCY,
            emotion_scores={emotion: 0.1 for emotion in EmotionalDimension},
            emotional_intensity=0.1,
            emotional_stability=0.5,
            manipulation_likelihood=0.1
        )
        
    def _create_fallback_credibility_assessment(self) -> CredibilityAssessment:
        """Create fallback credibility assessment."""
        return CredibilityAssessment(
            overall_score=0.5,
            factor_scores={factor: 0.5 for factor in CredibilityFactor},
            reliability_indicators=["Analysis unavailable"],
            warning_flags=["Could not verify credibility"],
            fact_check_suggestions=["Manual fact-checking recommended"]
        )
        
    def _create_fallback_viral_potential(self) -> ViralPotential:
        """Create fallback viral potential."""
        return ViralPotential(
            viral_score=0.3,
            engagement_prediction={"likes": 0.3, "shares": 0.2, "comments": 0.4},
            sharing_likelihood=0.3,
            discussion_potential=0.4,
            timing_optimization={"best_time": "evening", "confidence": 0.3}
        )
        
    def _create_fallback_cultural_context(self) -> CulturalContext:
        """Create fallback cultural context."""
        return CulturalContext(
            cultural_sensitivity_score=0.7,
            cultural_references=["Analysis unavailable"],
            potential_misunderstandings=["Could not analyze cultural context"],
            localization_suggestions=["Manual review recommended"],
            religious_considerations=["Review for religious sensitivity"]
        )
        
    def _create_fallback_insights(self, content: str, processing_time: float) -> ContentInsights:
        """Create fallback insights when analysis fails."""
        return ContentInsights(
            emotional_profile=self._create_fallback_emotional_profile(),
            credibility_assessment=self._create_fallback_credibility_assessment(),
            viral_potential=self._create_fallback_viral_potential(),
            cultural_context=self._create_fallback_cultural_context(),
            analysis_timestamp=datetime.now(),
            processing_time_ms=processing_time * 1000,
            confidence_score=0.3
        )
        
    async def get_analysis_summary(self, insights: ContentInsights) -> Dict[str, Any]:
        """Get human-readable summary of analysis results."""
        return {
            "emotional_summary": {
                "primary_emotion": insights.emotional_profile.primary_emotion.value,
                "intensity": f"{insights.emotional_profile.emotional_intensity:.1%}",
                "stability": "stable" if insights.emotional_profile.emotional_stability > 0.7 else "volatile",
                "manipulation_risk": "high" if insights.emotional_profile.manipulation_likelihood > 0.7 else "low"
            },
            "credibility_summary": {
                "overall_score": f"{insights.credibility_assessment.overall_score:.1%}",
                "reliability": "high" if insights.credibility_assessment.overall_score > 0.7 else "moderate" if insights.credibility_assessment.overall_score > 0.4 else "low",
                "warning_count": len(insights.credibility_assessment.warning_flags),
                "fact_check_needed": len(insights.credibility_assessment.fact_check_suggestions) > 0
            },
            "viral_summary": {
                "viral_potential": f"{insights.viral_potential.viral_score:.1%}",
                "sharing_likelihood": f"{insights.viral_potential.sharing_likelihood:.1%}",
                "discussion_potential": f"{insights.viral_potential.discussion_potential:.1%}",
                "engagement_forecast": "high" if insights.viral_potential.viral_score > 0.7 else "moderate"
            },
            "cultural_summary": {
                "sensitivity_score": f"{insights.cultural_context.cultural_sensitivity_score:.1%}",
                "cultural_references": len(insights.cultural_context.cultural_references),
                "potential_issues": len(insights.cultural_context.potential_misunderstandings),
                "localization_needed": len(insights.cultural_context.localization_suggestions) > 0
            },
            "meta": {
                "analysis_confidence": f"{insights.confidence_score:.1%}",
                "processing_time": f"{insights.processing_time_ms:.0f}ms",
                "timestamp": insights.analysis_timestamp.isoformat()
            }
        } 