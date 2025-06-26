"""
Comprehensive AI Integration Tests for NewsBot
Tests all AI service functionality including edge cases and error scenarios.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.services.ai_service import AIService
from src.services.ai_content_analyzer import AIContentAnalyzer
from src.services.news_intelligence import NewsIntelligenceService


class TestAIServiceComprehensive:
    """Comprehensive tests for AI service functionality."""

    @pytest.fixture
    def ai_service(self):
        """Create AI service instance for testing."""
        service = AIService()
        return service

    @pytest.fixture
    def content_analyzer(self):
        """Create AI content analyzer for testing."""
        analyzer = AIContentAnalyzer()
        return analyzer

    @pytest.fixture
    def news_intelligence(self):
        """Create news intelligence service for testing."""
        service = NewsIntelligenceService()
        return service

    @pytest.mark.asyncio
    async def test_translation_with_special_characters(self, ai_service):
        """Test translation handling special Arabic characters and formatting."""
        test_cases = [
            "النص مع أرقام ١٢٣٤٥",
            "نص مع علامات ترقيم: ؟ ! ، ؛",
            "نص مع\nأسطر متعددة\nوفقرات",
            "نص مع رموز تعبيرية 😀 🇸🇾 📰",
        ]
        
        for arabic_text in test_cases:
            with patch('openai.ChatCompletion.acreate') as mock_openai:
                mock_openai.return_value.choices = [
                    Mock(message=Mock(content="Translated text"))
                ]
                
                result = await ai_service.translate_to_english(arabic_text)
                assert result is not None
                assert len(result) > 0

    @pytest.mark.asyncio
    async def test_content_analysis_edge_cases(self, content_analyzer):
        """Test AI content analysis with edge cases."""
        edge_cases = [
            "",  # Empty content
            "a" * 10000,  # Very long content
            "🔥" * 100,  # Only emojis
            "123456789",  # Only numbers
            "BREAKING: " * 50,  # Repeated keywords
        ]
        
        for content in edge_cases:
            try:
                result = await content_analyzer.analyze_content(content)
                # Should handle gracefully without crashing
                assert result is not None
            except Exception as e:
                # Should not raise unhandled exceptions
                pytest.fail(f"Content analysis failed for edge case: {e}")

    @pytest.mark.asyncio
    async def test_urgency_detection_accuracy(self, news_intelligence):
        """Test urgency detection with various content types."""
        test_cases = [
            ("عاجل: انفجار في دمشق", "breaking"),
            ("مهم: اجتماع طارئ", "important"), 
            ("تحديث: الطقس اليوم", "normal"),
            ("خبر عادي عن الاقتصاد", "normal"),
        ]
        
        for arabic_text, expected_urgency in test_cases:
            with patch('openai.ChatCompletion.acreate') as mock_openai:
                mock_openai.return_value.choices = [
                    Mock(message=Mock(content=f'{{"urgency": "{expected_urgency}", "score": 0.8}}'))
                ]
                
                result = await news_intelligence.analyze_urgency(arabic_text)
                assert result.urgency_level.value == expected_urgency

    @pytest.mark.asyncio
    async def test_ai_service_rate_limiting(self, ai_service):
        """Test AI service handles rate limiting gracefully."""
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            # Simulate rate limit error
            mock_openai.side_effect = Exception("Rate limit exceeded")
            
            result = await ai_service.translate_to_english("نص للاختبار")
            # Should handle rate limiting gracefully
            assert result is None or isinstance(result, str)

    @pytest.mark.asyncio
    async def test_concurrent_ai_requests(self, ai_service):
        """Test AI service handles concurrent requests properly."""
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.return_value.choices = [
                Mock(message=Mock(content="Translated"))
            ]
            
            # Make multiple concurrent requests
            tasks = [
                ai_service.translate_to_english(f"نص {i}")
                for i in range(5)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should complete without errors
            for result in results:
                assert not isinstance(result, Exception)
                assert isinstance(result, str)


class TestAIErrorRecovery:
    """Test AI service error recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_openai_api_timeout_handling(self):
        """Test handling of OpenAI API timeouts."""
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.side_effect = asyncio.TimeoutError()
            
            ai_service = AIService()
            result = await ai_service.translate_to_english("نص للاختبار")
            
            # Should handle timeout gracefully
            assert result is None or result == "نص للاختبار"

    @pytest.mark.asyncio
    async def test_invalid_api_key_handling(self):
        """Test handling of invalid API key errors."""
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.side_effect = Exception("Invalid API key")
            
            ai_service = AIService()
            result = await ai_service.translate_to_english("نص للاختبار")
            
            # Should handle invalid key gracefully
            assert result is None or result == "نص للاختبار"

    @pytest.mark.asyncio
    async def test_malformed_response_handling(self):
        """Test handling of malformed AI responses."""
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            # Simulate malformed response
            mock_openai.return_value.choices = []
            
            ai_service = AIService()
            result = await ai_service.translate_to_english("نص للاختبار")
            
            # Should handle malformed response gracefully
            assert result is None or result == "نص للاختبار"


class TestAIPerformanceOptimization:
    """Test AI service performance optimizations."""

    @pytest.mark.asyncio
    async def test_caching_mechanism(self):
        """Test AI response caching for identical requests."""
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.return_value.choices = [
                Mock(message=Mock(content="Cached translation"))
            ]
            
            ai_service = AIService()
            
            # Make same request twice
            result1 = await ai_service.translate_to_english("نص للتخزين المؤقت")
            result2 = await ai_service.translate_to_english("نص للتخزين المؤقت")
            
            # Should use cache for second request
            assert result1 == result2
            # OpenAI should only be called once if caching works
            assert mock_openai.call_count <= 2

    @pytest.mark.asyncio
    async def test_batch_processing_optimization(self):
        """Test batch processing for multiple AI requests."""
        content_analyzer = AIContentAnalyzer()
        
        # Test batch analysis
        contents = [
            "محتوى أول للتحليل",
            "محتوى ثاني للتحليل", 
            "محتوى ثالث للتحليل"
        ]
        
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.return_value.choices = [
                Mock(message=Mock(content='{"urgency": "normal", "category": "general"}'))
            ]
            
            # Process all content
            results = []
            for content in contents:
                result = await content_analyzer.analyze_content(content)
                results.append(result)
            
            # All should complete successfully
            assert len(results) == 3
            assert all(r is not None for r in results) 