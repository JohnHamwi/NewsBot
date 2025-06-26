"""
Comprehensive tests for Advanced AI Content Analysis System.
Tests emotional analysis, credibility assessment, viral prediction, and cultural context analysis.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.services.advanced_content_analyzer import (
    AdvancedContentAnalyzer,
    EmotionalDimension,
    EmotionalProfile,
    CredibilityAssessment,
    ViralPotential,
    CulturalContext,
    ContentInsights
)
from src.services.enhanced_ai_service import EnhancedAIService, ContentOptimization


class TestAdvancedContentAnalyzer:
    """Test suite for AdvancedContentAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance for testing."""
        return AdvancedContentAnalyzer()
        
    @pytest.fixture
    def sample_news_content(self):
        """Sample Arabic news content for testing."""
        return """
        عاجل: تطورات مهمة في الوضع السوري اليوم. أعلنت الحكومة السورية عن خطة جديدة لإعادة الإعمار 
        في المناطق المحررة. هذه الخطة تشمل بناء المدارس والمستشفيات وتحسين البنية التحتية.
        المواطنون يعبرون عن أملهم في مستقبل أفضل للبلاد.
        """
        
    @pytest.mark.asyncio
    async def test_comprehensive_analysis_success(self, analyzer, sample_news_content):
        """Test successful comprehensive content analysis."""
        with patch('openai.ChatCompletion.acreate', new_callable=AsyncMock) as mock_openai:
            # Mock all OpenAI responses
            mock_openai.side_effect = [
                # Emotional analysis response
                Mock(choices=[Mock(message=Mock(content='{"anger": 0.2, "fear": 0.3, "hope": 0.8, "sadness": 0.1, "joy": 0.6, "urgency": 0.7, "anxiety": 0.2, "determination": 0.9, "emotional_intensity": 0.7, "emotional_stability": 0.8, "manipulation_likelihood": 0.1}'))]),
                # Credibility analysis response
                Mock(choices=[Mock(message=Mock(content='{"overall_score": 0.8, "reliability_indicators": ["Professional language", "Factual tone"], "warning_flags": [], "fact_check_suggestions": ["Verify reconstruction details"]}'))]),
                # Viral prediction response
                Mock(choices=[Mock(message=Mock(content='{"viral_score": 0.6, "engagement_prediction": {"likes": 0.7, "shares": 0.5, "comments": 0.8}, "sharing_likelihood": 0.6, "discussion_potential": 0.8}'))]),
                # Cultural analysis response
                Mock(choices=[Mock(message=Mock(content='{"cultural_sensitivity_score": 0.9, "cultural_references": ["Syrian government", "liberated areas"], "potential_misunderstandings": [], "localization_suggestions": ["Add context for international readers"]}'))])
            ]
            
            insights = await analyzer.analyze_comprehensive(sample_news_content)
            
            # Verify insights structure
            assert isinstance(insights, ContentInsights)
            assert isinstance(insights.emotional_profile, EmotionalProfile)
            assert isinstance(insights.credibility_assessment, CredibilityAssessment)
            assert isinstance(insights.viral_potential, ViralPotential)
            assert isinstance(insights.cultural_context, CulturalContext)
            
            # Verify emotional analysis
            assert insights.emotional_profile.primary_emotion == EmotionalDimension.DETERMINATION
            assert insights.emotional_profile.emotional_intensity == 0.7
            assert insights.emotional_profile.manipulation_likelihood == 0.1
            
            # Verify credibility assessment
            assert insights.credibility_assessment.overall_score == 0.8
            assert "Professional language" in insights.credibility_assessment.reliability_indicators
            
            # Verify viral potential
            assert insights.viral_potential.viral_score == 0.6
            assert insights.viral_potential.discussion_potential == 0.8
            
            # Verify cultural context
            assert insights.cultural_context.cultural_sensitivity_score == 0.9
            assert "Syrian government" in insights.cultural_context.cultural_references
            
            # Verify metadata
            assert insights.confidence_score > 0
            assert insights.processing_time_ms > 0
            assert isinstance(insights.analysis_timestamp, datetime)
            
    @pytest.mark.asyncio
    async def test_emotional_analysis_fallback(self, analyzer, sample_news_content):
        """Test emotional analysis with fallback when AI fails."""
        with patch('openai.ChatCompletion.acreate', new_callable=AsyncMock) as mock_openai:
            # Mock AI failure for emotional analysis
            mock_openai.side_effect = [
                Exception("OpenAI API error"),
                # Other analyses succeed
                Mock(choices=[Mock(message=Mock(content='{"overall_score": 0.5, "reliability_indicators": [], "warning_flags": [], "fact_check_suggestions": []}'))]),
                Mock(choices=[Mock(message=Mock(content='{"viral_score": 0.3, "engagement_prediction": {}, "sharing_likelihood": 0.3, "discussion_potential": 0.4}'))]),
                Mock(choices=[Mock(message=Mock(content='{"cultural_sensitivity_score": 0.7, "cultural_references": [], "potential_misunderstandings": [], "localization_suggestions": []}'))])
            ]
            
            insights = await analyzer.analyze_comprehensive(sample_news_content)
            
            # Should use fallback emotional profile
            assert insights.emotional_profile.primary_emotion == EmotionalDimension.URGENCY
            assert insights.emotional_profile.emotional_intensity == 0.3
            assert insights.confidence_score > 0  # Should still have confidence
            
    @pytest.mark.asyncio
    async def test_caching_functionality(self, analyzer, sample_news_content):
        """Test content analysis caching."""
        with patch('openai.ChatCompletion.acreate', new_callable=AsyncMock) as mock_openai:
            mock_openai.side_effect = [
                Mock(choices=[Mock(message=Mock(content='{"anger": 0.2, "fear": 0.3, "hope": 0.8, "sadness": 0.1, "joy": 0.6, "urgency": 0.7, "anxiety": 0.2, "determination": 0.9, "emotional_intensity": 0.7, "emotional_stability": 0.8, "manipulation_likelihood": 0.1}'))]),
                Mock(choices=[Mock(message=Mock(content='{"overall_score": 0.8, "reliability_indicators": [], "warning_flags": [], "fact_check_suggestions": []}'))]),
                Mock(choices=[Mock(message=Mock(content='{"viral_score": 0.6, "engagement_prediction": {}, "sharing_likelihood": 0.6, "discussion_potential": 0.8}'))]),
                Mock(choices=[Mock(message=Mock(content='{"cultural_sensitivity_score": 0.9, "cultural_references": [], "potential_misunderstandings": [], "localization_suggestions": []}'))])
            ]
            
            # First analysis
            insights1 = await analyzer.analyze_comprehensive(sample_news_content)
            
            # Second analysis (should use cache)
            insights2 = await analyzer.analyze_comprehensive(sample_news_content)
            
            # Should be same object from cache
            assert insights1.analysis_timestamp == insights2.analysis_timestamp
            assert mock_openai.call_count == 4  # Only called once for all analyses


class TestEnhancedAIService:
    """Test suite for EnhancedAIService."""
    
    @pytest.fixture
    def enhanced_ai_service(self):
        """Create enhanced AI service for testing."""
        with patch('src.services.enhanced_ai_service.AIService'):
            return EnhancedAIService()
            
    @pytest.fixture
    def sample_content(self):
        """Sample content for testing."""
        return "This is a test news article about important developments in Syria. The situation is improving with new reconstruction efforts."
        
    @pytest.mark.asyncio
    async def test_analyze_and_optimize_content(self, enhanced_ai_service, sample_content):
        """Test comprehensive content analysis and optimization."""
        with patch.object(enhanced_ai_service.content_analyzer, 'analyze_comprehensive') as mock_analyze:
            # Mock insights
            mock_insights = ContentInsights(
                emotional_profile=EmotionalProfile(
                    primary_emotion=EmotionalDimension.HOPE,
                    emotion_scores={EmotionalDimension.HOPE: 0.8},
                    emotional_intensity=0.7,
                    emotional_stability=0.8,
                    manipulation_likelihood=0.1
                ),
                credibility_assessment=CredibilityAssessment(
                    overall_score=0.8,
                    reliability_indicators=["Professional language"],
                    warning_flags=[],
                    fact_check_suggestions=["Verify details"]
                ),
                viral_potential=ViralPotential(
                    viral_score=0.6,
                    engagement_prediction={"likes": 0.7, "shares": 0.5},
                    sharing_likelihood=0.6,
                    discussion_potential=0.8
                ),
                cultural_context=CulturalContext(
                    cultural_sensitivity_score=0.9,
                    cultural_references=["Syrian context"],
                    potential_misunderstandings=[],
                    localization_suggestions=[]
                ),
                confidence_score=0.8,
                processing_time_ms=150.0
            )
            
            mock_analyze.return_value = mock_insights
            
            # Test analysis
            result = await enhanced_ai_service.analyze_and_optimize_content(sample_content)
            
            # Verify result structure
            assert "advanced_insights" in result
            assert "structure_analysis" in result
            assert "seo_insights" in result
            assert "optimization" in result
            assert "summary" in result
            assert "processing_time_ms" in result
            
            # Verify insights
            assert result["advanced_insights"] == mock_insights
            
    @pytest.mark.asyncio
    async def test_structure_analysis(self, enhanced_ai_service):
        """Test content structure analysis."""
        test_content = """
        This is a test article. It has multiple sentences. 
        
        This is a second paragraph. It also has multiple sentences for testing.
        The content structure should be analyzed properly.
        """
        
        structure = await enhanced_ai_service._analyze_content_structure(test_content)
        
        # Verify structure metrics
        assert structure["word_count"] > 0
        assert structure["sentence_count"] > 0
        assert structure["paragraph_count"] > 0
        assert "avg_sentence_length" in structure
        assert "structure_score" in structure
        assert "readability" in structure
        assert structure["readability"] in ["high", "medium", "low"]


class TestContentOptimization:
    """Test suite for ContentOptimization class."""
    
    @pytest.fixture
    def sample_insights(self):
        """Create sample insights for testing."""
        return ContentInsights(
            emotional_profile=EmotionalProfile(
                primary_emotion=EmotionalDimension.URGENCY,
                emotion_scores={EmotionalDimension.URGENCY: 0.9},
                emotional_intensity=0.8,
                emotional_stability=0.6,
                manipulation_likelihood=0.3
            ),
            credibility_assessment=CredibilityAssessment(
                overall_score=0.5,
                reliability_indicators=["Some indicators"],
                warning_flags=["Warning 1", "Warning 2", "Warning 3"],
                fact_check_suggestions=["Check this", "Verify that"]
            ),
            viral_potential=ViralPotential(
                viral_score=0.3,
                engagement_prediction={"likes": 0.4, "shares": 0.2},
                sharing_likelihood=0.3,
                discussion_potential=0.9
            ),
            cultural_context=CulturalContext(
                cultural_sensitivity_score=0.8,
                cultural_references=["Reference 1"],
                potential_misunderstandings=["Misunderstanding 1"],
                localization_suggestions=["Suggestion 1"]
            ),
            confidence_score=0.7,
            processing_time_ms=100.0
        )
        
    def test_optimization_recommendations_generation(self, sample_insights):
        """Test optimization recommendations generation."""
        optimization = ContentOptimization(sample_insights, "Sample content")
        recommendations = optimization.recommendations
        
        # Should generate recommendations for all categories
        assert "emotional_optimization" in recommendations
        assert "credibility_enhancement" in recommendations
        assert "viral_potential_boost" in recommendations
        assert "cultural_adaptation" in recommendations
        assert "timing_optimization" in recommendations
        assert "engagement_strategies" in recommendations
        
        # Should have credibility recommendations due to low score
        assert len(recommendations["credibility_enhancement"]) > 0
        
        # Should have viral boost recommendations due to low viral score
        assert len(recommendations["viral_potential_boost"]) > 0
        
        # Should have cultural adaptation recommendations due to misunderstandings
        assert len(recommendations["cultural_adaptation"]) > 0
        
        # Should have engagement strategies due to high discussion potential
        assert len(recommendations["engagement_strategies"]) > 0
        
        # Should have timing optimization for urgent content
        assert len(recommendations["timing_optimization"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
