#!/usr/bin/env python3
"""
Test script for NewsBot enhancements

This script tests the new features:
1. Syrian Location Detection
2. Content Cleaning (remove sources, emojis, links, hashtags)
3. Syrian Time Localization
4. Media Validation
"""

import asyncio
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.syrian_locations import detect_syrian_locations, format_syrian_location_tags
from src.utils.content_cleaner import clean_news_content, get_content_cleaning_stats
from src.utils.syrian_time import format_syrian_time, now_syrian, get_syrian_timezone_info
from src.utils.media_validator import validate_media_url


def test_syrian_locations():
    """Test Syrian location detection."""
    print("🔍 Testing Syrian Location Detection...")
    
    test_texts = [
        "Breaking news from Damascus and Aleppo today",
        "Situation in حلب and دمشق remains tense",
        "Reports from Idlib Governorate and Daraa",
        "No Syrian locations mentioned here",
        "Fighting continues in Homs, Latakia, and Deir ez-Zor",
        "الوضع في إدلب ودرعا"
    ]
    
    for i, text in enumerate(test_texts, 1):
        print(f"\nTest {i}: {text}")
        locations = detect_syrian_locations(text)
        if locations:
            print(f"  Detected: {[loc['name'] for loc in locations]}")
            tags = format_syrian_location_tags(text)
            print(f"  Tags: {tags}")
        else:
            print("  No locations detected")
    
    print("✅ Syrian location detection test completed\n")


def test_content_cleaning():
    """Test content cleaning functionality."""
    print("🧹 Testing Content Cleaning...")
    
    test_texts = [
        "🔥 Breaking news from Damascus! Source: @SyrianNews #Syria #Damascus https://t.me/channel",
        "المصدر: قناة الإخبارية 📺 عاجل من حلب 🚨 #سوريا",
        "According to Reuters, situation in Aleppo... via: @NewsChannel",
        "Forwarded from Syrian Updates\nJoin our channel: t.me/updates",
        "Normal news text without any sources or emojis",
        "🎯 نقلاً عن: وكالة الأنباء السورية 📰 الخبر: وضع متوتر في دمشق #عاجل"
    ]
    
    for i, text in enumerate(test_texts, 1):
        print(f"\nTest {i}:")
        print(f"  Original: {text}")
        cleaned = clean_news_content(text)
        print(f"  Cleaned:  {cleaned}")
        
        stats = get_content_cleaning_stats(text, cleaned)
        print(f"  Stats: {stats['reduction_percentage']}% reduction, "
              f"{stats['emojis_removed']} emojis, {stats['urls_removed']} URLs, "
              f"{stats['hashtags_removed']} hashtags removed")
    
    print("✅ Content cleaning test completed\n")


def test_syrian_time():
    """Test Syrian time functionality."""
    print("🕐 Testing Syrian Time Localization...")
    
    # Test current Syrian time
    current_syrian = now_syrian()
    print(f"Current Syrian time: {format_syrian_time(current_syrian)}")
    print(f"Short format: {format_syrian_time(current_syrian, format_style='short')}")
    print(f"Time only: {format_syrian_time(current_syrian, format_style='time_only')}")
    
    # Test timezone info
    tz_info = get_syrian_timezone_info()
    print(f"Timezone info: {tz_info}")
    
    # Test with different timestamps
    test_time = datetime(2024, 1, 15, 14, 30, 0)
    print(f"Test time in Syrian timezone: {format_syrian_time(test_time)}")
    
    print("✅ Syrian time test completed\n")


async def test_media_validation():
    """Test media validation functionality."""
    print("📷 Testing Media Validation...")
    
    # Test URLs (these are example URLs - replace with real ones for actual testing)
    test_urls = [
        "https://example.com/image.jpg",  # This will fail as it's not a real image
        "https://httpbin.org/image/jpeg",  # This should work
        "https://httpbin.org/image/png",   # This should work
        "https://example.com/video.mp4",   # This will fail
        "https://invalid-url.com/fake.jpg"  # This will fail
    ]
    
    print("Note: Using test URLs - some may fail due to network/availability")
    
    for i, url in enumerate(test_urls, 1):
        print(f"\nTest {i}: {url}")
        try:
            result = await validate_media_url(url)
            print(f"  Valid: {result['valid']}")
            print(f"  Type: {result['type']}")
            if result['error']:
                print(f"  Error: {result['error']}")
            if result['validation_details']:
                details = result['validation_details']
                print(f"  Details: {details.get('format', 'Unknown')} - {details.get('file_size', 0)} bytes")
        except Exception as e:
            print(f"  Exception: {str(e)}")
    
    print("✅ Media validation test completed\n")


def test_integration():
    """Test integration of all features."""
    print("🔗 Testing Feature Integration...")
    
    # Simulate a typical Syrian news message
    sample_message = """
    🔥 عاجل من دمشق: تطورات جديدة في الوضع الأمني
    
    المصدر: قناة الإخبارية السورية
    التوقيت: الساعة 15:30
    
    تشهد العاصمة دمشق وريف دمشق حالة من الهدوء النسبي بعد الأحداث الأخيرة في حلب وإدلب.
    
    #سوريا #دمشق #عاجل
    @SyrianNewsChannel
    https://t.me/syriannews/12345
    """
    
    print("Original message:")
    print(sample_message)
    print("\n" + "="*50 + "\n")
    
    # Clean content
    cleaned = clean_news_content(sample_message)
    print("After content cleaning:")
    print(cleaned)
    print()
    
    # Detect locations
    locations = detect_syrian_locations(cleaned)
    location_tags = format_syrian_location_tags(cleaned)
    print(f"Detected locations: {[loc['name'] for loc in locations]}")
    print(f"Location tags: {location_tags}")
    print()
    
    # Syrian time
    current_time = now_syrian()
    print(f"Current Syrian time: {format_syrian_time(current_time, format_style='short')}")
    
    print("✅ Integration test completed\n")


async def main():
    """Run all tests."""
    print("🚀 Starting NewsBot Enhancement Tests\n")
    
    test_syrian_locations()
    test_content_cleaning()
    test_syrian_time()
    await test_media_validation()
    test_integration()
    
    print("🎉 All tests completed!")


if __name__ == "__main__":
    asyncio.run(main()) 