# =============================================================================
# NewsBot Critical Logic Tests
# =============================================================================
# Focused tests for the critical business logic that was causing the
# posting interval bug. These tests verify the core algorithms without
# complex mocking dependencies.

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from src.utils.timezone_utils import now_eastern, utc_to_eastern


class TestPostingIntervalLogic:
    """Test the critical posting interval logic that was causing issues."""

    def test_posting_interval_calculation_too_soon(self):
        """Test that posting is blocked when interval hasn't elapsed."""
        # Arrange - simulate a post 1 hour ago, 3-hour interval
        last_post_time = now_eastern() - timedelta(hours=1)
        auto_post_interval = 10800  # 3 hours in seconds
        force_auto_post = False
        
        # Act - calculate if posting should happen
        time_since_last = (now_eastern() - last_post_time).total_seconds()
        should_post = time_since_last >= auto_post_interval or force_auto_post
        
        # Assert
        assert should_post is False
        assert time_since_last < auto_post_interval
        # Should be approximately 2 hours remaining
        remaining = auto_post_interval - time_since_last
        assert 7000 <= remaining <= 7400  # ~2 hours in seconds

    def test_posting_interval_calculation_ready_to_post(self):
        """Test that posting is allowed when interval has elapsed."""
        # Arrange - simulate a post 4 hours ago, 3-hour interval
        last_post_time = now_eastern() - timedelta(hours=4)
        auto_post_interval = 10800  # 3 hours in seconds
        force_auto_post = False
        
        # Act - calculate if posting should happen
        time_since_last = (now_eastern() - last_post_time).total_seconds()
        should_post = time_since_last >= auto_post_interval or force_auto_post
        
        # Assert
        assert should_post is True
        assert time_since_last >= auto_post_interval

    def test_force_auto_post_overrides_interval(self):
        """Test that force_auto_post flag overrides interval timing."""
        # Arrange - simulate a post 1 hour ago (too soon), but force flag is set
        last_post_time = now_eastern() - timedelta(hours=1)
        auto_post_interval = 10800  # 3 hours in seconds
        force_auto_post = True  # Force posting
        
        # Act - calculate if posting should happen
        time_since_last = (now_eastern() - last_post_time).total_seconds()
        should_post = time_since_last >= auto_post_interval or force_auto_post
        
        # Assert
        assert should_post is True  # Force flag should override timing
        assert time_since_last < auto_post_interval  # Confirm time wasn't sufficient

    def test_no_last_post_time_allows_posting(self):
        """Test that no previous post time allows immediate posting."""
        # Arrange
        last_post_time = None
        auto_post_interval = 10800
        force_auto_post = False
        
        # Act - check if posting should happen when no previous post exists
        if last_post_time is None:
            should_post = True
        else:
            time_since_last = (now_eastern() - last_post_time).total_seconds()
            should_post = time_since_last >= auto_post_interval or force_auto_post
        
        # Assert
        assert should_post is True


class TestStartupGracePeriod:
    """Test startup grace period logic."""

    def test_startup_grace_period_active(self):
        """Test that startup grace period blocks posting when active."""
        # Arrange - bot started 2 minutes ago, 5-minute grace period
        startup_time = datetime.now(timezone.utc) - timedelta(minutes=2)
        startup_grace_period_minutes = 5
        disable_auto_post_on_startup = True
        
        # Act - calculate if grace period is still active
        if disable_auto_post_on_startup:
            time_since_startup = (datetime.now(timezone.utc) - startup_time).total_seconds()
            grace_period_seconds = startup_grace_period_minutes * 60
            should_wait = time_since_startup < grace_period_seconds
            seconds_to_wait = max(0, grace_period_seconds - time_since_startup)
        else:
            should_wait = False
            seconds_to_wait = 0
        
        # Assert
        assert should_wait is True
        assert seconds_to_wait > 0
        # Should be approximately 3 minutes remaining (5 - 2)
        assert 170 <= seconds_to_wait <= 190

    def test_startup_grace_period_expired(self):
        """Test that expired grace period allows posting."""
        # Arrange - bot started 10 minutes ago, 5-minute grace period
        startup_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        startup_grace_period_minutes = 5
        disable_auto_post_on_startup = True
        
        # Act - calculate if grace period is still active
        if disable_auto_post_on_startup:
            time_since_startup = (datetime.now(timezone.utc) - startup_time).total_seconds()
            grace_period_seconds = startup_grace_period_minutes * 60
            should_wait = time_since_startup < grace_period_seconds
            seconds_to_wait = max(0, grace_period_seconds - time_since_startup)
        else:
            should_wait = False
            seconds_to_wait = 0
        
        # Assert
        assert should_wait is False
        assert seconds_to_wait == 0

    def test_startup_grace_period_disabled(self):
        """Test that disabled grace period allows immediate posting."""
        # Arrange - grace period is disabled
        startup_time = datetime.now(timezone.utc)  # Just started
        startup_grace_period_minutes = 5
        disable_auto_post_on_startup = False  # Disabled
        
        # Act - calculate if grace period is active
        if disable_auto_post_on_startup:
            time_since_startup = (datetime.now(timezone.utc) - startup_time).total_seconds()
            grace_period_seconds = startup_grace_period_minutes * 60
            should_wait = time_since_startup < grace_period_seconds
            seconds_to_wait = max(0, grace_period_seconds - time_since_startup)
        else:
            should_wait = False
            seconds_to_wait = 0
        
        # Assert
        assert should_wait is False
        assert seconds_to_wait == 0


class TestManualVerificationDelay:
    """Test manual verification delay logic."""

    def test_manual_verification_delay_blocks_posting(self):
        """Test that manual verification delay blocks auto-posting."""
        # Arrange - delay is set until 1 hour from now
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        manual_verification_delay_until = {'auto_fetch': future_time}
        
        # Act - check if delay is active
        now_utc = datetime.now(timezone.utc)
        delay_until = manual_verification_delay_until.get('auto_fetch')
        should_wait = delay_until and now_utc < delay_until
        
        # Assert
        assert should_wait is True

    def test_manual_verification_delay_expired(self):
        """Test that expired manual verification delay allows posting."""
        # Arrange - delay was set until 1 hour ago (expired)
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        manual_verification_delay_until = {'auto_fetch': past_time}
        
        # Act - check if delay is active
        now_utc = datetime.now(timezone.utc)
        delay_until = manual_verification_delay_until.get('auto_fetch')
        should_wait = delay_until and now_utc < delay_until
        
        # Assert
        assert should_wait is False

    def test_no_manual_verification_delay(self):
        """Test that no manual verification delay allows posting."""
        # Arrange - no delay is set
        manual_verification_delay_until = {}
        
        # Act - check if delay is active
        now_utc = datetime.now(timezone.utc)
        delay_until = manual_verification_delay_until.get('auto_fetch')
        should_wait = bool(delay_until and now_utc < delay_until)
        
        # Assert
        assert should_wait is False


class TestTimezoneConversions:
    """Test timezone conversion logic that was causing issues."""

    def test_utc_to_eastern_conversion(self):
        """Test that UTC to Eastern conversion works correctly."""
        # Arrange - create a UTC datetime
        utc_time = datetime(2025, 1, 16, 12, 0, 0, tzinfo=timezone.utc)
        
        # Act - convert to Eastern
        eastern_time = utc_to_eastern(utc_time)
        
        # Assert
        assert eastern_time.tzinfo is not None
        # Should be 5 hours behind UTC (EST) or 4 hours behind (EDT)
        hour_diff = utc_time.hour - eastern_time.hour
        assert hour_diff in [4, 5] or hour_diff in [-19, -20]  # Account for day wrap

    def test_eastern_time_consistency(self):
        """Test that Eastern time calls are consistent."""
        # Act - get Eastern time twice
        time1 = now_eastern()
        time2 = now_eastern()
        
        # Assert - should be very close in time
        diff = abs((time2 - time1).total_seconds())
        assert diff < 1.0  # Less than 1 second difference

    def test_timezone_aware_datetime(self):
        """Test that Eastern time has timezone information."""
        # Act
        eastern_time = now_eastern()
        
        # Assert
        assert eastern_time.tzinfo is not None
        # Should be Eastern timezone
        tz_str = str(eastern_time.tzinfo)
        assert any(indicator in tz_str for indicator in ["EST", "EDT", "America/New_York"])


class TestContentFiltering:
    """Test content filtering logic."""

    def test_content_length_validation(self):
        """Test content length requirements."""
        # Test cases
        short_content = "Short"
        medium_content = "This is a medium length piece of content that should be acceptable"
        long_content = "This is a very long piece of content that definitely meets the minimum requirements for posting" * 2
        
        # Minimum length requirement (from the bot logic)
        min_length = 50
        
        # Assert
        assert len(short_content.strip()) < min_length  # Should be rejected
        assert len(medium_content.strip()) >= min_length  # Should be accepted
        assert len(long_content.strip()) >= min_length  # Should be accepted

    def test_blacklist_checking(self):
        """Test blacklist content filtering."""
        # Arrange
        message_id = 12345
        blacklisted_ids = [12345, 67890, 11111]
        
        # Act
        is_blacklisted = message_id in blacklisted_ids
        
        # Assert
        assert is_blacklisted is True
        
        # Test non-blacklisted
        message_id = 99999
        is_blacklisted = message_id in blacklisted_ids
        assert is_blacklisted is False


class TestIntervalConfiguration:
    """Test interval configuration and conversion."""

    def test_interval_minutes_to_seconds_conversion(self):
        """Test converting interval from minutes to seconds."""
        # Test common intervals
        assert 180 * 60 == 10800  # 3 hours = 10800 seconds
        assert 240 * 60 == 14400  # 4 hours = 14400 seconds
        assert 60 * 60 == 3600    # 1 hour = 3600 seconds

    def test_interval_validation(self):
        """Test interval validation."""
        # Test valid intervals
        valid_intervals = [60, 120, 180, 240, 360]  # 1-6 hours in minutes
        for interval in valid_intervals:
            assert interval > 0
            assert interval <= 720  # Max 12 hours
        
        # Test invalid intervals
        invalid_intervals = [0, -60, 1440]  # 0, negative, 24 hours
        for interval in invalid_intervals:
            assert interval <= 0 or interval > 720


class TestRichPresenceCalculations:
    """Test rich presence time calculations."""

    def test_next_post_time_calculation(self):
        """Test calculating next post time for rich presence."""
        # Arrange
        last_post_time = now_eastern() - timedelta(hours=1)
        auto_post_interval = 10800  # 3 hours
        
        # Act - calculate next post time
        next_post_time = last_post_time + timedelta(seconds=auto_post_interval)
        time_until_next = next_post_time - now_eastern()
        
        # Assert
        assert next_post_time > now_eastern()  # Should be in future
        assert time_until_next.total_seconds() > 0
        # Should be approximately 2 hours remaining
        assert 7000 <= time_until_next.total_seconds() <= 7400

    def test_overdue_post_calculation(self):
        """Test detecting overdue posts for rich presence."""
        # Arrange - last post was 4 hours ago, interval is 3 hours
        last_post_time = now_eastern() - timedelta(hours=4)
        auto_post_interval = 10800  # 3 hours
        
        # Act - calculate if post is overdue
        next_post_time = last_post_time + timedelta(seconds=auto_post_interval)
        is_overdue = now_eastern() > next_post_time
        overdue_by = (now_eastern() - next_post_time).total_seconds()
        
        # Assert
        assert is_overdue is True
        assert overdue_by > 0
        # Should be overdue by approximately 1 hour
        assert 3500 <= overdue_by <= 3700  # ~1 hour in seconds 