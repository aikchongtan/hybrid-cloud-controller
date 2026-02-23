"""Unit tests for pricing scheduler."""

import asyncio
import time
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from packages.pricing_service import scheduler


@pytest.fixture
def mock_fetcher():
    """Mock the fetcher module."""
    with patch("packages.pricing_service.scheduler.fetcher") as mock:
        yield mock


@pytest.fixture
def sample_pricing_data():
    """Sample pricing data for testing."""
    return {
        "ec2_pricing": {"t3.micro": Decimal("0.0104")},
        "ebs_pricing": {"gp3": Decimal("0.08")},
        "s3_pricing": {"STANDARD": Decimal("0.023")},
        "data_transfer_pricing": {"internet_egress": Decimal("0.09")},
    }


def test_scheduler_initialization():
    """Test scheduler can be initialized."""
    sched = scheduler.PricingScheduler()
    assert not sched._running
    assert sched._thread is None


def test_get_scheduler_returns_singleton():
    """Test get_scheduler returns the same instance."""
    # Reset global instance
    scheduler._scheduler_instance = None
    
    sched1 = scheduler.get_scheduler()
    sched2 = scheduler.get_scheduler()
    
    assert sched1 is sched2


def test_schedule_daily_fetch_starts_scheduler():
    """Test schedule_daily_fetch starts the scheduler thread."""
    sched = scheduler.PricingScheduler()
    
    try:
        sched.schedule_daily_fetch()
        
        assert sched._running
        assert sched._thread is not None
        assert sched._thread.is_alive()
    finally:
        sched.stop()


def test_schedule_daily_fetch_prevents_double_start():
    """Test schedule_daily_fetch doesn't start twice."""
    sched = scheduler.PricingScheduler()
    
    try:
        sched.schedule_daily_fetch()
        first_thread = sched._thread
        
        # Try to start again
        sched.schedule_daily_fetch()
        
        # Should be the same thread
        assert sched._thread is first_thread
    finally:
        sched.stop()


def test_stop_scheduler():
    """Test stopping the scheduler."""
    sched = scheduler.PricingScheduler()
    
    sched.schedule_daily_fetch()
    assert sched._running
    
    sched.stop()
    
    assert not sched._running
    # Give thread time to stop
    time.sleep(0.1)


def test_stop_scheduler_when_not_running():
    """Test stopping scheduler when it's not running doesn't error."""
    sched = scheduler.PricingScheduler()
    
    # Should not raise an error
    sched.stop()
    assert not sched._running


def test_execute_fetch_success(mock_fetcher, sample_pricing_data):
    """Test execute_fetch succeeds on first attempt."""
    mock_fetcher.fetch_pricing_data.return_value = sample_pricing_data
    
    result = asyncio.run(scheduler.execute_fetch())
    
    assert result["success"] is True
    assert result["data"] == sample_pricing_data
    assert result["error"] is None
    assert result["attempts"] == 1
    assert result["cached_used"] is False


def test_execute_fetch_retries_on_failure(mock_fetcher, sample_pricing_data):
    """Test execute_fetch retries with exponential backoff."""
    # Fail twice, then succeed
    mock_fetcher.fetch_pricing_data.side_effect = [
        Exception("API Error 1"),
        Exception("API Error 2"),
        sample_pricing_data,
    ]
    
    # Mock sleep to avoid waiting
    async def mock_sleep(delay):
        pass
    
    with patch("asyncio.sleep", side_effect=mock_sleep):
        result = asyncio.run(scheduler.execute_fetch())
    
    assert result["success"] is True
    assert result["data"] == sample_pricing_data
    assert result["attempts"] == 3
    assert result["cached_used"] is False
    assert mock_fetcher.fetch_pricing_data.call_count == 3


def test_execute_fetch_uses_cache_after_max_retries(mock_fetcher, sample_pricing_data):
    """Test execute_fetch uses cached data after all retries fail."""
    # Always fail
    mock_fetcher.fetch_pricing_data.side_effect = Exception("API Error")
    mock_fetcher.get_current_pricing.return_value = sample_pricing_data
    
    # Mock sleep to avoid waiting
    async def mock_sleep(delay):
        pass
    
    with patch("asyncio.sleep", side_effect=mock_sleep):
        result = asyncio.run(scheduler.execute_fetch())
    
    assert result["success"] is False
    assert result["data"] == sample_pricing_data
    assert result["error"] is not None
    assert result["attempts"] == 7  # max_retries + 1
    assert result["cached_used"] is True


def test_execute_fetch_no_cache_available(mock_fetcher):
    """Test execute_fetch when no cached data is available."""
    # Always fail
    mock_fetcher.fetch_pricing_data.side_effect = Exception("API Error")
    mock_fetcher.get_current_pricing.return_value = None
    
    # Mock sleep to avoid waiting
    async def mock_sleep(delay):
        pass
    
    with patch("asyncio.sleep", side_effect=mock_sleep):
        result = asyncio.run(scheduler.execute_fetch())
    
    assert result["success"] is False
    assert result["data"] is None
    assert "no cached data" in result["error"].lower()
    assert result["attempts"] == 7
    assert result["cached_used"] is False


def test_execute_fetch_cache_retrieval_fails(mock_fetcher):
    """Test execute_fetch when cache retrieval itself fails."""
    # Always fail
    mock_fetcher.fetch_pricing_data.side_effect = Exception("API Error")
    mock_fetcher.get_current_pricing.side_effect = Exception("Database Error")
    
    # Mock sleep to avoid waiting
    async def mock_sleep(delay):
        pass
    
    with patch("asyncio.sleep", side_effect=mock_sleep):
        result = asyncio.run(scheduler.execute_fetch())
    
    assert result["success"] is False
    assert result["data"] is None
    assert "cache retrieval failed" in result["error"].lower()
    assert result["attempts"] == 7


def test_execute_fetch_exponential_backoff_delays():
    """Test that execute_fetch uses exponential backoff delays."""
    with patch("packages.pricing_service.scheduler.fetcher") as mock_fetcher:
        # Fail 3 times
        mock_fetcher.fetch_pricing_data.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            Exception("Error 3"),
            {"ec2_pricing": {}},  # Success on 4th attempt
        ]
        
        sleep_calls = []
        
        async def mock_sleep(delay):
            sleep_calls.append(delay)
        
        with patch("asyncio.sleep", side_effect=mock_sleep):
            result = asyncio.run(scheduler.execute_fetch())
        
        # Should have called sleep 3 times with exponential backoff
        assert len(sleep_calls) == 3
        assert sleep_calls[0] == 60  # 1 minute
        assert sleep_calls[1] == 120  # 2 minutes
        assert sleep_calls[2] == 240  # 4 minutes


def test_convenience_functions():
    """Test convenience functions for starting/stopping scheduler."""
    # Reset global instance
    scheduler._scheduler_instance = None
    
    try:
        # Start scheduler
        scheduler.schedule_daily_fetch()
        
        sched = scheduler.get_scheduler()
        assert sched._running
        
        # Stop scheduler
        scheduler.stop_scheduler()
        assert not sched._running
    finally:
        # Cleanup
        if scheduler._scheduler_instance:
            scheduler._scheduler_instance.stop()
