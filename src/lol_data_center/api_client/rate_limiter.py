"""Async token bucket rate limiter for Riot API.

The Riot API has rate limits of 100 requests per 2 minutes (120 seconds).
This rate limiter uses a token bucket algorithm to ensure we stay within limits.
"""

import asyncio
import time
from dataclasses import dataclass, field

from lol_data_center.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimiter:
    """Async token bucket rate limiter.

    Attributes:
        max_tokens: Maximum number of tokens (requests) in the bucket
        refill_rate: Tokens added per second
        tokens: Current available tokens
        last_refill: Timestamp of last token refill
    """

    max_tokens: int = 100
    refill_period_seconds: float = 120.0
    tokens: float = field(init=False)
    last_refill: float = field(init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    def __post_init__(self) -> None:
        """Initialize tokens to max."""
        self.tokens = float(self.max_tokens)
        self.last_refill = time.monotonic()

    @property
    def refill_rate(self) -> float:
        """Tokens per second."""
        return self.max_tokens / self.refill_period_seconds

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now

    async def acquire(self, tokens: int = 1) -> float:
        """Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire (default 1)

        Returns:
            Time waited in seconds
        """
        async with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                logger.debug(
                    "Rate limiter acquired tokens",
                    tokens_acquired=tokens,
                    tokens_remaining=self.tokens,
                )
                return 0.0

            # Calculate wait time
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.refill_rate

            logger.info(
                "Rate limiter waiting for tokens",
                tokens_needed=tokens_needed,
                wait_seconds=round(wait_time, 2),
                tokens_remaining=self.tokens,
            )

            await asyncio.sleep(wait_time)
            self._refill()
            self.tokens -= tokens

            return wait_time

    def available_tokens(self) -> float:
        """Get current available tokens (without acquiring lock)."""
        # Note: This is approximate since we don't refill here
        return self.tokens

    async def wait_until_ready(self) -> None:
        """Wait until at least one token is available."""
        await self.acquire(1)
        # Give back the token since we just wanted to wait
        async with self._lock:
            self.tokens = min(self.max_tokens, self.tokens + 1)
