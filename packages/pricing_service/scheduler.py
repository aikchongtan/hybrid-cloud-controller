"""
Pricing data scheduler for Hybrid Cloud Controller.

This module provides scheduling functionality to fetch AWS pricing data
every 24 hours with retry logic and exponential backoff on failure.
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from packages.pricing_service import fetcher

logger = logging.getLogger("hybrid_cloud.pricing_service.scheduler")


class PricingScheduler:
    """Scheduler for periodic pricing data fetches."""

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def schedule_daily_fetch(self) -> None:
        """
        Schedule pricing fetch every 24 hours.

        Starts a background thread that executes pricing fetches at 24-hour intervals.
        The scheduler runs continuously until stopped.
        """
        if self._running:
            logger.warning("Scheduler is already running")
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._thread.start()
        logger.info("Pricing scheduler started - will fetch every 24 hours")

    def stop(self) -> None:
        """Stop the pricing scheduler."""
        if not self._running:
            return

        logger.info("Stopping pricing scheduler")
        self._running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def _run_scheduler(self) -> None:
        """
        Main scheduler loop.

        Executes pricing fetch immediately on start, then waits 24 hours
        between subsequent fetches.
        """
        while self._running:
            try:
                # Execute fetch with retry logic
                asyncio.run(execute_fetch())

                # Wait 24 hours before next fetch (unless stopped)
                if self._stop_event.wait(timeout=24 * 60 * 60):
                    # Stop event was set
                    break

            except Exception as e:
                logger.error(f"Unexpected error in scheduler loop: {e}", exc_info=True)
                # Wait a bit before retrying to avoid tight error loops
                if self._stop_event.wait(timeout=60):
                    break


async def execute_fetch() -> dict[str, any]:
    """
    Execute pricing fetch with retry and exponential backoff.

    Attempts to fetch pricing data from AWS Pricing API. On failure,
    retries with exponential backoff: 1 min, 2 min, 4 min, 8 min, etc.
    Maximum of 6 retry attempts (total ~63 minutes of retries).

    Returns:
        dict with keys:
            - success (bool): Whether fetch succeeded
            - data (dict): Pricing data if successful
            - error (str): Error message if failed
            - attempts (int): Number of attempts made
            - cached_used (bool): Whether cached data was used

    Raises:
        No exceptions - all errors are caught and returned in result dict
    """
    max_retries = 6
    base_delay = 60  # 1 minute in seconds

    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Attempting pricing fetch (attempt {attempt + 1}/{max_retries + 1})")

            # Fetch pricing data
            pricing_data = fetcher.fetch_pricing_data()

            logger.info("Pricing fetch succeeded")
            return {
                "success": True,
                "data": pricing_data,
                "error": None,
                "attempts": attempt + 1,
                "cached_used": False,
            }

        except Exception as e:
            logger.warning(
                f"Pricing fetch failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
            )

            # If this was the last attempt, use cached data
            if attempt >= max_retries:
                logger.error(
                    f"All {max_retries + 1} pricing fetch attempts failed, using cached data"
                )

                try:
                    cached_data = fetcher.get_current_pricing()
                    if cached_data:
                        logger.info("Using cached pricing data")
                        return {
                            "success": False,
                            "data": cached_data,
                            "error": str(e),
                            "attempts": attempt + 1,
                            "cached_used": True,
                        }
                    else:
                        logger.error("No cached pricing data available")
                        return {
                            "success": False,
                            "data": None,
                            "error": f"Fetch failed and no cached data: {e}",
                            "attempts": attempt + 1,
                            "cached_used": False,
                        }
                except Exception as cache_error:
                    logger.error(f"Failed to retrieve cached data: {cache_error}")
                    return {
                        "success": False,
                        "data": None,
                        "error": f"Fetch failed: {e}, Cache retrieval failed: {cache_error}",
                        "attempts": attempt + 1,
                        "cached_used": False,
                    }

            # Calculate exponential backoff delay: 1, 2, 4, 8, 16, 32 minutes
            delay = base_delay * (2**attempt)
            logger.info(f"Retrying in {delay} seconds ({delay // 60} minutes)")

            # Wait before retry
            await asyncio.sleep(delay)

    # Should never reach here, but just in case
    return {
        "success": False,
        "data": None,
        "error": "Unexpected scheduler state",
        "attempts": max_retries + 1,
        "cached_used": False,
    }


# Global scheduler instance
_scheduler_instance: Optional[PricingScheduler] = None


def get_scheduler() -> PricingScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = PricingScheduler()
    return _scheduler_instance


def schedule_daily_fetch() -> None:
    """
    Convenience function to start the global scheduler.

    This is the main entry point for starting the pricing scheduler.
    """
    scheduler = get_scheduler()
    scheduler.schedule_daily_fetch()


def stop_scheduler() -> None:
    """Stop the global scheduler."""
    global _scheduler_instance
    if _scheduler_instance:
        _scheduler_instance.stop()
