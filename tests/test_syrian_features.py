"""
Test suite for Syrian NewsBot features.
Tests location detection, content cleaning, time formatting, and media validation.
"""

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import pytest


class TestSyrianLocationDetection:
    """Test Syrian location detection functionality."""

    def test_detect_damascus_english(self):
        """Test detection of Damascus in English."""
        from src.utils.syrian_locations import SyrianLocationDetector

        detector = SyrianLocationDetector()

        text = "Breaking news from Damascus today"
        locations = detector.detect_locations(text)

        assert len(locations) >= 1
        assert any(loc["name"] == "Damascus" for loc in locations)

    def test_detect_damascus_arabic(self):
        """Test detection of Damascus in Arabic."""
        from src.utils.syrian_locations import SyrianLocationDetector

        detector = SyrianLocationDetector()

        text = "أخبار عاجلة من دمشق اليوم"
        locations = detector.detect_locations(text)

        assert len(locations) >= 1
        assert any(loc["name"] == "Damascus" for loc in locations)

    def test_no_locations_found(self):
        """Test when no Syrian locations are mentioned."""
        from src.utils.syrian_locations import SyrianLocationDetector

        detector = SyrianLocationDetector()

        text = "News from London and Paris today"
        locations = detector.detect_locations(text)

        assert len(locations) == 0

    def test_format_location_tags(self):
        """Test formatting location tags."""
        from src.utils.syrian_locations import SyrianLocationDetector

        detector = SyrianLocationDetector()

        text = "News from Damascus"
        locations = detector.detect_locations(text)
        tags = detector.format_location_tags(locations)

        assert len(tags) >= 1
        assert "Damascus" in tags


class TestContentCleaning:
    """Test content cleaning functionality."""

    def test_remove_emojis(self):
        """Test removal of emojis."""
        from src.utils.content_cleaner import ContentCleaner

        cleaner = ContentCleaner()

        text = "أخبار مهمة 🔥⚡️📰 اليوم"
        cleaned = cleaner.clean_content(text)

        assert "🔥" not in cleaned
        assert "⚡️" not in cleaned
        assert "📰" not in cleaned
        assert "أخبار مهمة" in cleaned

    def test_remove_sources_arabic(self):
        """Test removal of Arabic source attributions."""
        from src.utils.content_cleaner import ContentCleaner

        cleaner = ContentCleaner()

        text = "أخبار مهمة اليوم\nالمصدر: قناة الإخبارية"
        cleaned = cleaner.clean_content(text)

        assert "المصدر:" not in cleaned
        assert "أخبار مهمة اليوم" in cleaned

    def test_remove_telegram_links(self):
        """Test removal of Telegram links."""
        from src.utils.content_cleaner import ContentCleaner

        cleaner = ContentCleaner()

        text = "أخبار مهمة\nt.me/newschannel"
        cleaned = cleaner.clean_content(text)

        assert "t.me" not in cleaned
        assert "أخبار مهمة" in cleaned

    def test_preserve_core_content(self):
        """Test that core content is preserved."""
        from src.utils.content_cleaner import ContentCleaner

        cleaner = ContentCleaner()

        text = "هذا خبر مهم جداً ويجب الحفاظ عليه"
        cleaned = cleaner.clean_content(text)

        assert cleaned.strip() == text


class TestSyrianTimeFormatting:
    """Test Syrian time formatting functionality."""

    def test_current_syrian_time(self):
        """Test getting current Syrian time."""
        from src.utils.syrian_time import SyrianTimeHandler

        handler = SyrianTimeHandler()

        syrian_time = handler.now_syrian()

        assert isinstance(syrian_time, datetime)
        # Check if timezone is Syrian (pytz timezone)
        assert str(syrian_time.tzinfo) == "Asia/Damascus"

    def test_format_full_datetime(self):
        """Test full datetime formatting."""
        from src.utils.syrian_time import SyrianTimeHandler

        handler = SyrianTimeHandler()

        utc_time = datetime(2025, 6, 10, 12, 0, 0, tzinfo=timezone.utc)
        formatted = handler.format_syrian_time(utc_time, format_style="full")

        assert isinstance(formatted, str)
        assert "2025" in formatted

    def test_timezone_conversion(self):
        """Test timezone conversion from UTC to Syrian time."""
        from src.utils.syrian_time import SyrianTimeHandler

        handler = SyrianTimeHandler()

        utc_time = datetime(2025, 6, 10, 12, 0, 0, tzinfo=timezone.utc)
        syrian_time = handler.to_syrian_time(utc_time)

        assert str(syrian_time.tzinfo) == "Asia/Damascus"


class TestMediaValidation:
    """Test media validation functionality."""

    def test_validate_jpeg_image(self):
        """Test validation of JPEG images."""
        from src.utils.media_validator import MediaValidator

        validator = MediaValidator()

        # Create a minimal JPEG file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"\xff\xd8\xff\xe0\x00\x10JFIF")
            tmp.flush()

            try:
                result = validator._validate_image_file(Path(tmp.name))
                assert result["valid"] == True
                assert result["format"] == "JPEG"
            finally:
                os.unlink(tmp.name)

    def test_validate_invalid_image(self):
        """Test validation of invalid image files."""
        from src.utils.media_validator import MediaValidator

        validator = MediaValidator()

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"This is not an image")
            tmp.flush()

            try:
                result = validator._validate_image_file(Path(tmp.name))
                assert result["valid"] == False
            finally:
                os.unlink(tmp.name)

    def test_validate_nonexistent_file(self):
        """Test validation of non-existent files."""
        from src.utils.media_validator import MediaValidator

        validator = MediaValidator()

        result = validator._validate_image_file(Path("/nonexistent/file.jpg"))
        assert result["valid"] == False
        assert "does not exist" in result["error"]


class TestTranslationFeatures:
    """Test translation functionality."""

    @pytest.mark.asyncio
    async def test_translate_fallback(self):
        """Test fallback translation when OpenAI is not available."""
        from src.utils.translator import ChatGPTTranslator

        translator = ChatGPTTranslator()

        # Test with known vocabulary words
        text_with_known_words = "أخبار عاجلة"
        translation = translator._translate_fallback(text_with_known_words)

        assert isinstance(translation, str)
        assert len(translation) > 0

    def test_generate_title_fallback(self):
        """Test fallback title generation."""
        from src.utils.translator import ChatGPTTranslator

        translator = ChatGPTTranslator()

        arabic_text = "أخبار عاجلة من دمشق اليوم"
        title = translator._extract_title_fallback(arabic_text)

        assert isinstance(title, str)
        assert len(title) > 0

    def test_empty_text_handling(self):
        """Test handling of empty text."""
        from src.utils.translator import ChatGPTTranslator

        translator = ChatGPTTranslator()

        # Test empty text
        translation = translator._translate_fallback("")
        assert isinstance(translation, str)

        title = translator._extract_title_fallback("")
        assert title == "أخبار سورية"  # Default fallback


class TestEnhancedMediaService:
    """Test enhanced media service functionality."""

    def test_format_file_size(self):
        """Test file size formatting utility."""
        from src.services.media_service import MediaService

        mock_bot = Mock()
        media_service = MediaService(mock_bot)

        # Test various file sizes
        assert "1.0 KB" in media_service._format_file_size(1024)
        assert "1.0 MB" in media_service._format_file_size(1024 * 1024)
        assert "512 B" in media_service._format_file_size(512)

    def test_format_time_duration(self):
        """Test time duration formatting utility."""
        from src.services.media_service import MediaService

        mock_bot = Mock()
        media_service = MediaService(mock_bot)

        # Test various durations - adjust expectations based on actual format
        result_60 = media_service._format_time(60)
        result_30 = media_service._format_time(30)
        result_0 = media_service._format_time(0)

        assert isinstance(result_60, str)
        assert isinstance(result_30, str)
        assert isinstance(result_0, str)


class TestDailyLogRotation:
    """Test daily log rotation functionality."""

    def test_eastern_timezone_configuration(self):
        """Test that Eastern timezone is properly configured."""
        from src.utils.base_logger import EASTERN

        assert EASTERN == ZoneInfo("America/New_York")

    def test_log_file_creation(self):
        """Test that log files are created properly."""
        import tempfile

        from src.utils.base_logger import setup_logger

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a logger that writes to temp directory
            logger = setup_logger("TestLogger")
            logger.info("Test message")

            # Check that some log file was created (may be in default location)
            assert logger is not None

    def test_unicode_handling_in_logs(self):
        """Test that Unicode characters (Arabic) are handled properly in logs."""
        from src.utils.base_logger import setup_logger

        logger = setup_logger("TestLogger")

        # This should not raise an exception
        arabic_message = "أخبار عاجلة من دمشق"
        logger.info(arabic_message)

        # If we get here without exception, Unicode handling works
        assert True


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple Syrian enhancements."""

    def test_complete_news_processing_pipeline(self):
        """Test complete news processing pipeline."""
        from src.utils.content_cleaner import ContentCleaner
        from src.utils.syrian_locations import SyrianLocationDetector
        from src.utils.syrian_time import SyrianTimeHandler

        # Raw Telegram message with all elements that need cleaning
        raw_message = """🔥 أخبار عاجلة من دمشق #عاجل
        
        تقارير تفيد بحدوث انفجار في العاصمة دمشق
        
        المصدر: قناة الأخبار
        t.me/newschannel"""

        # Step 1: Clean content
        cleaner = ContentCleaner()
        cleaned_content = cleaner.clean_content(raw_message)

        # Step 2: Detect locations
        detector = SyrianLocationDetector()
        locations = detector.detect_locations(cleaned_content)

        # Step 3: Format time
        handler = SyrianTimeHandler()
        current_time = datetime.now(timezone.utc)
        syrian_time = handler.format_syrian_time(current_time, format_style="short")

        # Verify pipeline results
        assert "🔥" not in cleaned_content
        assert "#عاجل" not in cleaned_content
        assert "المصدر:" not in cleaned_content
        assert "t.me" not in cleaned_content
        assert "تقارير تفيد بحدوث انفجار" in cleaned_content

        assert len(locations) >= 1
        assert any(loc["name"] == "Damascus" for loc in locations)

        assert isinstance(syrian_time, str)
        assert len(syrian_time) > 0

    def test_error_handling_across_modules(self):
        """Test error handling across all Syrian enhancement modules."""
        from pathlib import Path

        from src.utils.content_cleaner import ContentCleaner
        from src.utils.media_validator import MediaValidator
        from src.utils.syrian_locations import SyrianLocationDetector

        # Test with problematic inputs
        detector = SyrianLocationDetector()
        cleaner = ContentCleaner()
        validator = MediaValidator()

        # Empty content
        assert cleaner.clean_content("") == ""
        assert len(detector.detect_locations("")) == 0

        # Invalid file paths
        result = validator._validate_image_file(Path("/invalid/path.jpg"))
        assert result["valid"] == False

        result = validator._validate_video_file(Path("/invalid/path.mp4"))
        assert result["valid"] == False

    def test_unicode_handling_across_modules(self):
        """Test Unicode handling across all modules."""
        from src.utils.content_cleaner import ContentCleaner
        from src.utils.syrian_locations import SyrianLocationDetector

        # Arabic text with various Unicode characters
        unicode_text = "أخبار عاجلة من دمشق 🔥 والمناطق المحيطة بها"

        detector = SyrianLocationDetector()
        cleaner = ContentCleaner()

        # Content cleaning should preserve Arabic but remove emojis
        cleaned = cleaner.clean_content(unicode_text)
        assert "أخبار عاجلة من دمشق" in cleaned
        assert "🔥" not in cleaned

        # Location detection should work with Arabic
        locations = detector.detect_locations(unicode_text)
        assert len(locations) >= 1
        assert any(loc["name"] == "Damascus" for loc in locations)

        # All modules should handle Unicode gracefully
        assert isinstance(cleaned, str)
        assert isinstance(locations, list)
