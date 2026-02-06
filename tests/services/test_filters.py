"""Tests for match filters."""

import pytest

from lol_data_center.services.filters import (
    MINIMUM_GAME_DURATION_SECONDS,
    is_allowed_queue,
    is_valid_game_duration,
)


class TestIsAllowedQueue:
    """Tests for is_allowed_queue function."""

    @pytest.mark.parametrize(
        "queue_id,expected",
        [
            (400, True),  # Draft Pick
            (420, True),  # Ranked Solo/Duo
            (440, True),  # Ranked Flex
            (480, True),  # Swiftplay
            (450, False),  # ARAM
            (900, False),  # ARURF
            (0, False),  # Custom game
        ],
    )
    def test_is_allowed_queue(self, queue_id: int, expected: bool) -> None:
        """Test queue ID filtering."""
        assert is_allowed_queue(queue_id) == expected


class TestIsValidGameDuration:
    """Tests for is_valid_game_duration function."""

    def test_valid_duration_exactly_minimum(self) -> None:
        """Test that exactly minimum duration (600s / 10 min) is valid."""
        assert is_valid_game_duration(MINIMUM_GAME_DURATION_SECONDS) is True

    def test_valid_duration_above_minimum(self) -> None:
        """Test that durations above minimum are valid."""
        assert is_valid_game_duration(MINIMUM_GAME_DURATION_SECONDS + 1) is True
        assert is_valid_game_duration(1800) is True  # 30 minutes
        assert is_valid_game_duration(3600) is True  # 1 hour

    def test_invalid_duration_below_minimum(self) -> None:
        """Test that durations below minimum are invalid."""
        assert is_valid_game_duration(MINIMUM_GAME_DURATION_SECONDS - 1) is False
        assert is_valid_game_duration(599) is False  # 9:59
        assert is_valid_game_duration(300) is False  # 5 minutes (typical remake)
        assert is_valid_game_duration(180) is False  # 3 minutes
        assert is_valid_game_duration(0) is False  # Edge case

    def test_threshold_is_600_seconds(self) -> None:
        """Test that the threshold is set to 600 seconds (10 minutes)."""
        assert MINIMUM_GAME_DURATION_SECONDS == 600

    @pytest.mark.parametrize(
        "duration,expected",
        [
            (0, False),  # Immediate end
            (180, False),  # 3 minutes (remake time)
            (300, False),  # 5 minutes
            (599, False),  # Just under threshold
            (600, True),  # Exactly threshold
            (601, True),  # Just over threshold
            (900, True),  # 15 minutes (early surrender)
            (1200, True),  # 20 minutes (normal surrender)
            (1800, True),  # 30 minutes (typical game)
            (2400, True),  # 40 minutes (long game)
        ],
    )
    def test_duration_boundary_cases(self, duration: int, expected: bool) -> None:
        """Test various duration boundary cases."""
        assert is_valid_game_duration(duration) == expected
