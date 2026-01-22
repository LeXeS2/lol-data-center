"""Tests for the rate limiter."""

from __future__ import annotations

import asyncio
import time

import pytest

from lol_data_center.api_client.rate_limiter import RateLimiter


class TestRateLimiter:
    """Tests for the RateLimiter class."""

    @pytest.mark.asyncio
    async def test_acquire_when_tokens_available(self) -> None:
        """Test acquiring tokens when tokens are available."""
        limiter = RateLimiter(max_tokens=10, refill_period_seconds=60)

        wait_time = await limiter.acquire(1)

        assert wait_time == 0.0
        assert limiter.tokens == 9.0

    @pytest.mark.asyncio
    async def test_acquire_multiple_tokens(self) -> None:
        """Test acquiring multiple tokens at once."""
        limiter = RateLimiter(max_tokens=10, refill_period_seconds=60)

        await limiter.acquire(5)

        assert limiter.tokens == 5.0

    @pytest.mark.asyncio
    async def test_acquire_waits_when_no_tokens(self) -> None:
        """Test that acquire waits when no tokens are available."""
        limiter = RateLimiter(max_tokens=2, refill_period_seconds=2)

        # Use all tokens
        await limiter.acquire(2)

        # Next acquire should wait
        start = time.monotonic()
        await limiter.acquire(1)
        elapsed = time.monotonic() - start

        # Should have waited ~1 second (for 1 token at 2 tokens/2 seconds = 1/sec)
        assert elapsed >= 0.9  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_tokens_refill_over_time(self) -> None:
        """Test that tokens refill over time."""
        limiter = RateLimiter(max_tokens=10, refill_period_seconds=1)

        # Use half the tokens
        await limiter.acquire(5)
        assert limiter.tokens == 5.0

        # Wait for refill
        await asyncio.sleep(0.5)

        # Trigger refill by acquiring
        await limiter.acquire(1)

        # Should have more tokens now (5 + refilled - 1)
        assert limiter.tokens > 4.0

    @pytest.mark.asyncio
    async def test_tokens_dont_exceed_max(self) -> None:
        """Test that tokens don't exceed maximum."""
        limiter = RateLimiter(max_tokens=10, refill_period_seconds=1)

        # Wait longer than refill period
        await asyncio.sleep(0.2)

        # This triggers refill but should cap at max
        await limiter.acquire(0)

        assert limiter.tokens <= limiter.max_tokens

    @pytest.mark.asyncio
    async def test_concurrent_access(self) -> None:
        """Test thread safety with concurrent access."""
        limiter = RateLimiter(max_tokens=10, refill_period_seconds=60)

        async def acquire_one() -> None:
            await limiter.acquire(1)

        # Run multiple concurrent acquires
        await asyncio.gather(*[acquire_one() for _ in range(5)])

        # Should have used 5 tokens
        assert round(limiter.tokens, 4) == 5.0

    def test_refill_rate_calculation(self) -> None:
        """Test refill rate calculation."""
        limiter = RateLimiter(max_tokens=100, refill_period_seconds=120)

        # 100 tokens / 120 seconds = 0.833... tokens/second
        assert limiter.refill_rate == pytest.approx(100 / 120)

    @pytest.mark.asyncio
    async def test_available_tokens(self) -> None:
        """Test available_tokens method."""
        limiter = RateLimiter(max_tokens=10, refill_period_seconds=60)

        await limiter.acquire(3)

        # Note: This is approximate since we don't refill
        assert limiter.available_tokens() == pytest.approx(7.0, abs=0.1)
