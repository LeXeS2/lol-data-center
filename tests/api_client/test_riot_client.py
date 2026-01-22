"""Tests for RiotApiClient."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from lol_data_center.api_client.riot_client import Region, RiotApiClient


class TestFetchAllMatchIds:
    """Tests for RiotApiClient.fetch_all_match_ids method."""

    @pytest.mark.asyncio
    async def test_fetch_all_match_ids_single_page(self) -> None:
        """Test fetching all match IDs when results fit in one page."""
        client = RiotApiClient(api_key="test-key")

        # Mock get_match_ids to return less than page size
        match_ids = [f"EUW1_MATCH_{i}" for i in range(50)]
        client.get_match_ids = AsyncMock(return_value=match_ids)

        result = await client.fetch_all_match_ids(
            puuid="test-puuid",
            region=Region.EUROPE,
        )

        assert result == match_ids
        assert len(result) == 50
        # Should only call once since we got less than 100 results
        client.get_match_ids.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_all_match_ids_multiple_pages(self) -> None:
        """Test fetching all match IDs across multiple pages."""
        client = RiotApiClient(api_key="test-key")

        # Mock get_match_ids to return multiple pages
        page_1 = [f"EUW1_MATCH_{i}" for i in range(100)]
        page_2 = [f"EUW1_MATCH_{i}" for i in range(100, 200)]
        page_3 = [f"EUW1_MATCH_{i}" for i in range(200, 250)]

        client.get_match_ids = AsyncMock(side_effect=[page_1, page_2, page_3])

        result = await client.fetch_all_match_ids(
            puuid="test-puuid",
            region=Region.EUROPE,
        )

        assert len(result) == 250
        assert result == page_1 + page_2 + page_3
        # Should call 3 times
        assert client.get_match_ids.call_count == 3

        # Verify pagination parameters
        calls = client.get_match_ids.call_args_list
        assert calls[0].kwargs["start"] == 0
        assert calls[0].kwargs["count"] == 100
        assert calls[1].kwargs["start"] == 100
        assert calls[1].kwargs["count"] == 100
        assert calls[2].kwargs["start"] == 200
        assert calls[2].kwargs["count"] == 100

    @pytest.mark.asyncio
    async def test_fetch_all_match_ids_empty_result(self) -> None:
        """Test fetching all match IDs when player has no matches."""
        client = RiotApiClient(api_key="test-key")

        # Mock get_match_ids to return empty list
        client.get_match_ids = AsyncMock(return_value=[])

        result = await client.fetch_all_match_ids(
            puuid="test-puuid",
            region=Region.EUROPE,
        )

        assert result == []
        client.get_match_ids.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_all_match_ids_exact_page_boundary(self) -> None:
        """Test fetching when results are exactly at page boundary (100)."""
        client = RiotApiClient(api_key="test-key")

        # First call returns exactly 100, second returns empty
        page_1 = [f"EUW1_MATCH_{i}" for i in range(100)]

        client.get_match_ids = AsyncMock(side_effect=[page_1, []])

        result = await client.fetch_all_match_ids(
            puuid="test-puuid",
            region=Region.EUROPE,
        )

        assert len(result) == 100
        assert result == page_1
        # Should call twice (second call gets empty, stops)
        assert client.get_match_ids.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_all_match_ids_with_filters(self) -> None:
        """Test fetching all match IDs with optional filters."""
        client = RiotApiClient(api_key="test-key")

        match_ids = [f"EUW1_MATCH_{i}" for i in range(30)]
        client.get_match_ids = AsyncMock(return_value=match_ids)

        result = await client.fetch_all_match_ids(
            puuid="test-puuid",
            region=Region.EUROPE,
            queue=420,  # Ranked Solo/Duo
            match_type="ranked",
            start_time=1704067200,
            end_time=1704153600,
        )

        assert result == match_ids

        # Verify filters were passed through
        call_kwargs = client.get_match_ids.call_args.kwargs
        assert call_kwargs["queue"] == 420
        assert call_kwargs["match_type"] == "ranked"
        assert call_kwargs["start_time"] == 1704067200
        assert call_kwargs["end_time"] == 1704153600

    @pytest.mark.asyncio
    async def test_fetch_all_match_ids_large_history(self) -> None:
        """Test fetching all match IDs for player with large match history."""
        client = RiotApiClient(api_key="test-key")

        # Simulate 10 full pages + 1 partial page (1050 matches total)
        pages = []
        for i in range(10):
            pages.append([f"EUW1_MATCH_{j}" for j in range(i * 100, (i + 1) * 100)])
        pages.append([f"EUW1_MATCH_{j}" for j in range(1000, 1050)])

        client.get_match_ids = AsyncMock(side_effect=pages)

        result = await client.fetch_all_match_ids(
            puuid="test-puuid",
            region=Region.EUROPE,
        )

        assert len(result) == 1050
        assert client.get_match_ids.call_count == 11

        # Verify last call
        last_call = client.get_match_ids.call_args_list[-1]
        assert last_call.kwargs["start"] == 1000
        assert last_call.kwargs["count"] == 100

    @pytest.mark.asyncio
    async def test_fetch_all_match_ids_pagination_consistency(self) -> None:
        """Test that pagination maintains correct start indices."""
        client = RiotApiClient(api_key="test-key")

        # 3 pages: 100, 100, 47
        pages = [
            [f"MATCH_{i}" for i in range(100)],
            [f"MATCH_{i}" for i in range(100, 200)],
            [f"MATCH_{i}" for i in range(200, 247)],
        ]

        client.get_match_ids = AsyncMock(side_effect=pages)

        result = await client.fetch_all_match_ids(
            puuid="test-puuid",
            region=Region.ASIA,
        )

        assert len(result) == 247

        # Verify all calls had correct parameters
        calls = client.get_match_ids.call_args_list
        assert len(calls) == 3

        assert calls[0].kwargs["puuid"] == "test-puuid"
        assert calls[0].kwargs["region"] == Region.ASIA
        assert calls[0].kwargs["start"] == 0

        assert calls[1].kwargs["start"] == 100
        assert calls[2].kwargs["start"] == 200


class TestGetMatchTimeline:
    """Tests for RiotApiClient.get_match_timeline method."""

    @pytest.mark.asyncio
    async def test_get_match_timeline_success(self) -> None:
        """Test successfully fetching match timeline."""
        from lol_data_center.schemas.riot_api import MatchMetadataDto, MatchTimelineDto

        client = RiotApiClient(api_key="test-key")

        # Mock the _request method to return timeline data
        timeline_data = {
            "metadata": {
                "dataVersion": "2",
                "matchId": "EUW1_12345678",
                "participants": ["puuid1", "puuid2"],
            },
            "info": {
                "frameInterval": 60000,
                "frames": [
                    {"timestamp": 0, "events": []},
                    {"timestamp": 60000, "events": [{"type": "CHAMPION_KILL"}]},
                ],
            },
        }

        client._request = AsyncMock(return_value=timeline_data)

        result = await client.get_match_timeline("EUW1_12345678", Region.EUROPE)

        assert isinstance(result, MatchTimelineDto)
        assert isinstance(result.metadata, MatchMetadataDto)
        assert result.metadata.match_id == "EUW1_12345678"
        assert "frameInterval" in result.info
        assert "frames" in result.info
        assert len(result.info["frames"]) == 2

        # Verify the request was made correctly
        client._request.assert_called_once_with(
            "europe",
            "/lol/match/v5/matches/EUW1_12345678/timeline",
        )

    @pytest.mark.asyncio
    async def test_get_match_timeline_different_region(self) -> None:
        """Test fetching match timeline from different region."""
        client = RiotApiClient(api_key="test-key")

        timeline_data = {
            "metadata": {
                "dataVersion": "2",
                "matchId": "NA1_987654321",
                "participants": ["puuid1"],
            },
            "info": {
                "frameInterval": 60000,
                "frames": [],
            },
        }

        client._request = AsyncMock(return_value=timeline_data)

        result = await client.get_match_timeline("NA1_987654321", Region.AMERICAS)

        assert result.metadata.match_id == "NA1_987654321"

        # Verify correct region was used
        client._request.assert_called_once_with(
            "americas",
            "/lol/match/v5/matches/NA1_987654321/timeline",
        )

