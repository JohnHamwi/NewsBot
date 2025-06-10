"""
Test suite for the RateLimiter class.
"""

import pytest
import asyncio
import time
from src.utils.rate_limiter import RateLimiter, RateLimiterManager, rate_limited

@pytest.mark.asyncio
async def test_rate_limiter_basic():
    """Test basic rate limiting functionality."""
    # Create a rate limiter with 10 calls per second
    limiter = RateLimiter("test", calls_per_second=10, burst_limit=5)
    
    # First 5 calls should be immediate (burst)
    start_time = time.time()
    for i in range(5):
        wait_time = await limiter.acquire()
        assert wait_time == 0.0, f"Expected no wait for call {i+1}"
    
    # Next call should have to wait
    wait_time = await limiter.acquire()
    assert wait_time > 0.0, "Expected to wait for 6th call"
    
    # Check stats
    stats = limiter.get_stats()
    assert stats["total_calls"] == 6
    assert stats["waited_calls"] == 1
    assert stats["wait_percentage"] > 0

@pytest.mark.asyncio
async def test_rate_limiter_refill():
    """Test token refill over time."""
    # Create a rate limiter with 2 calls per second
    limiter = RateLimiter("test", calls_per_second=2, burst_limit=2)
    
    # Use up the burst
    await limiter.acquire()
    await limiter.acquire()
    
    # Wait for a token to be refilled (0.5 seconds)
    await asyncio.sleep(0.6)
    
    # Next call should be immediate
    start_time = time.time()
    wait_time = await limiter.acquire()
    assert wait_time == 0.0, "Expected no wait after token refill"

@pytest.mark.asyncio
async def test_rate_limiter_manager():
    """Test rate limiter manager."""
    # Create manager
    manager = RateLimiterManager()
    
    # Should have default limiters
    assert "telegram" in manager.limiters
    assert "discord" in manager.limiters
    assert "default" in manager.limiters
    
    # Add a custom limiter
    manager.add_limiter("custom", calls_per_second=5, burst_limit=3)
    assert "custom" in manager.limiters
    
    # Use the custom limiter
    for i in range(3):
        wait_time = await manager.acquire("custom")
        assert wait_time == 0.0, f"Expected no wait for call {i+1}"
    
    # Next call should have to wait
    wait_time = await manager.acquire("custom")
    assert wait_time > 0.0, "Expected to wait after burst"
    
    # Test getting a non-existent limiter (should use default)
    limiter = manager.get_limiter("nonexistent")
    assert limiter is manager.limiters["default"]
    
    # Test stats
    stats = manager.get_all_stats()
    assert "custom" in stats
    assert stats["custom"]["total_calls"] == 4
    assert stats["custom"]["waited_calls"] == 1

@pytest.mark.asyncio
async def test_rate_limited_decorator():
    """Test rate_limited decorator."""
    # Create a global manager and add a test limiter
    from src.utils.rate_limiter import rate_limiter_manager
    rate_limiter_manager.add_limiter("test_decorator", calls_per_second=2, burst_limit=2)
    
    # Create a decorated function
    @rate_limited("test_decorator")
    async def test_function():
        return "result"
    
    # First two calls should be quick
    start_time = time.time()
    for i in range(2):
        result = await test_function()
        assert result == "result"
    end_time = time.time()
    assert end_time - start_time < 0.1, "First two calls should be quick"
    
    # Third call should be rate limited
    start_time = time.time()
    result = await test_function()
    end_time = time.time()
    assert result == "result"
    assert end_time - start_time >= 0.4, "Third call should be rate limited"
    
    # Get stats to verify calls were made
    stats = rate_limiter_manager.get_limiter("test_decorator").get_stats()
    assert stats["total_calls"] == 3
    assert stats["waited_calls"] >= 1 