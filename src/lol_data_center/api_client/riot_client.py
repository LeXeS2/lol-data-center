"""Async Riot API client with rate limiting and validation."""

from __future__ import annotations

import asyncio
from enum import Enum

import aiohttp

from lol_data_center.api_client.rate_limiter import RateLimiter
from lol_data_center.api_client.validation import ValidationError, validate_response
from lol_data_center.config import get_settings
from lol_data_center.logging_config import get_logger
from lol_data_center.schemas.riot_api import (
    AccountDto,
    LeagueEntryDto,
    MatchDto,
    SummonerDto,
    TimelineDto,
)

logger = get_logger(__name__)


class Region(str, Enum):
    """Riot API regional routing values."""

    # Regional routing (for account-v1, match-v5)
    AMERICAS = "americas"
    ASIA = "asia"
    EUROPE = "europe"
    SEA = "sea"


class Platform(str, Enum):
    """Riot API platform routing values."""

    # Platform routing (for summoner-v4, etc.)
    BR1 = "br1"
    EUN1 = "eun1"
    EUW1 = "euw1"
    JP1 = "jp1"
    KR = "kr"
    LA1 = "la1"
    LA2 = "la2"
    NA1 = "na1"
    OC1 = "oc1"
    PH2 = "ph2"
    RU = "ru"
    SG2 = "sg2"
    TH2 = "th2"
    TR1 = "tr1"
    TW2 = "tw2"
    VN2 = "vn2"


# Mapping from region to platforms
REGION_TO_PLATFORMS: dict[Region, list[Platform]] = {
    Region.AMERICAS: [Platform.NA1, Platform.BR1, Platform.LA1, Platform.LA2, Platform.OC1],
    Region.ASIA: [Platform.KR, Platform.JP1],
    Region.EUROPE: [Platform.EUW1, Platform.EUN1, Platform.TR1, Platform.RU],
    Region.SEA: [Platform.PH2, Platform.SG2, Platform.TH2, Platform.TW2, Platform.VN2],
}


class RiotApiError(Exception):
    """Exception for Riot API errors."""

    def __init__(self, status_code: int, message: str, url: str) -> None:
        super().__init__(f"Riot API error {status_code}: {message}")
        self.status_code = status_code
        self.url = url


class RiotApiClient:
    """Async client for the Riot Games API.

    This client handles:
    - Rate limiting (100 requests / 2 minutes)
    - Response validation
    - Error handling
    """

    def __init__(
        self,
        api_key: str | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        """Initialize the Riot API client.

        Args:
            api_key: Riot API key (defaults to settings)
            rate_limiter: Custom rate limiter (defaults to standard limits)
        """
        settings = get_settings()
        self._api_key = api_key or settings.riot_api_key
        self._rate_limiter = rate_limiter or RateLimiter(
            max_tokens=settings.rate_limit_requests,
            refill_period_seconds=settings.rate_limit_window_seconds,
        )
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"X-Riot-Token": self._api_key},
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> RiotApiClient:
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: BaseException | None,
        exc_val: BaseException | None,
        exc_tb: BaseException | None,
    ) -> None:
        """Async context manager exit."""
        await self.close()

    def _build_url(self, routing: str, endpoint: str) -> str:
        """Build the full API URL.

        Args:
            routing: Region or platform routing value
            endpoint: API endpoint path

        Returns:
            Full URL
        """
        return f"https://{routing}.api.riotgames.com{endpoint}"

    async def _request(
        self,
        routing: str,
        endpoint: str,
        method: str = "GET",
        params: dict[str, object] | None = None,
    ) -> object:
        """Make a rate-limited request to the Riot API.

        Args:
            routing: Region or platform routing value
            endpoint: API endpoint path
            method: HTTP method
            params: Query parameters

        Returns:
            JSON response data

        Raises:
            RiotApiError: If the API returns an error
        """
        url = self._build_url(routing, endpoint)
        session = await self._get_session()

        acquired = False
        attempt = 0

        while True:
            if not acquired:
                # Wait for rate limit only on first attempt; retries follow Riot's Retry-After
                await self._rate_limiter.acquire()
                acquired = True

            logger.debug(
                "Making Riot API request",
                url=url,
                method=method,
                params=params,
                attempt=attempt,
            )

            async with session.request(method, url, params=params) as response:
                response_text = await response.text()

                if response.status == 429:
                    # Riot says too many requests; respect Retry-After then retry
                    retry_after = int(response.headers.get("Retry-After", 120))
                    logger.warning(
                        "Rate limited by Riot API; retrying after delay",
                        retry_after=retry_after,
                        url=url,
                        attempt=attempt,
                    )
                    attempt += 1
                    await asyncio.sleep(retry_after)
                    # Retry without getting another token from our limiter
                    continue

                if response.status == 404:
                    raise RiotApiError(404, "Not found", url)

                if response.status != 200:
                    logger.error(
                        "Riot API error",
                        status_code=response.status,
                        url=url,
                        response=response_text[:500],
                    )
                    raise RiotApiError(response.status, response_text, url)

                try:
                    return await response.json()
                except Exception as e:
                    logger.error(
                        "Failed to parse JSON response",
                        url=url,
                        error=str(e),
                        response=response_text[:500],
                    )
                    raise RiotApiError(
                        response.status,
                        f"Invalid JSON response: {e}",
                        url,
                    ) from e

    # Account-V1 endpoints

    async def get_account_by_riot_id(
        self,
        game_name: str,
        tag_line: str,
        region: Region = Region.EUROPE,
    ) -> AccountDto:
        """Get account by Riot ID.

        Args:
            game_name: Game name part of Riot ID
            tag_line: Tag line part of Riot ID
            region: Regional routing value

        Returns:
            Account data
        """
        endpoint = f"/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        data = await self._request(region.value, endpoint)
        return await validate_response(
            AccountDto,
            data,
            "account-v1/by-riot-id",
            self._build_url(region.value, endpoint),
        )

    async def get_account_by_puuid(
        self,
        puuid: str,
        region: Region = Region.EUROPE,
    ) -> AccountDto:
        """Get account by PUUID.

        Args:
            puuid: Player Universal Unique Identifier
            region: Regional routing value

        Returns:
            Account data
        """
        endpoint = f"/riot/account/v1/accounts/by-puuid/{puuid}"
        data = await self._request(region.value, endpoint)
        return await validate_response(
            AccountDto,
            data,
            "account-v1/by-puuid",
            self._build_url(region.value, endpoint),
        )

    # Summoner-V4 endpoints

    async def get_summoner_by_puuid(
        self,
        puuid: str,
        platform: Platform = Platform.EUW1,
    ) -> SummonerDto:
        """Get summoner by PUUID.

        Args:
            puuid: Player Universal Unique Identifier
            platform: Platform routing value

        Returns:
            Summoner data
        """
        endpoint = f"/lol/summoner/v4/summoners/by-puuid/{puuid}"
        data = await self._request(platform.value, endpoint)
        return await validate_response(
            SummonerDto,
            data,
            "summoner-v4/by-puuid",
            self._build_url(platform.value, endpoint),
        )

    # League-V4 endpoints

    async def get_summoner_league(
        self,
        puuid: str,
        platform: Platform = Platform.EUW1,
    ) -> list[LeagueEntryDto]:
        """Get league entries for a summoner.

        Args:
            puuid: Encrypted PUUID
            platform: Platform routing value

        Returns:
            List of league entries (one per queue type: RANKED_SOLO_5x5, RANKED_FLEX_SR, etc.)
        """
        endpoint = f"/lol/league/v4/entries/by-puuid/{puuid}"
        data = await self._request(platform.value, endpoint)

        # The API returns a list of league entries
        if not isinstance(data, list):
            raise ValidationError(
                message="Expected list of league entries",
                endpoint="league-v4/by-puuid",
                url=self._build_url(platform.value, endpoint),
                response_body=str(data),
            )

        # Validate each entry
        entries = []
        for entry_data in data:
            entry = await validate_response(
                LeagueEntryDto,
                entry_data,
                "league-v4/by-puuid",
                self._build_url(platform.value, endpoint),
            )
            entries.append(entry)

        return entries

    # Match-V5 endpoints

    async def get_match_ids(
        self,
        puuid: str,
        region: Region = Region.EUROPE,
        start: int = 0,
        count: int = 20,
        queue: int | None = None,
        match_type: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[str]:
        """Get list of match IDs for a player.

        Args:
            puuid: Player Universal Unique Identifier
            region: Regional routing value
            start: Start index for pagination
            count: Number of match IDs to return (max 100)
            queue: Queue ID filter
            match_type: Match type filter (ranked, normal, etc.)
            start_time: Start time filter (epoch seconds)
            end_time: End time filter (epoch seconds)

        Returns:
            List of match IDs
        """
        endpoint = f"/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params: dict[str, object] = {"start": start, "count": min(count, 100)}

        if queue is not None:
            params["queue"] = queue
        if match_type is not None:
            params["type"] = match_type
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time

        data = await self._request(region.value, endpoint, params=params)

        # The API returns a plain list, not an object
        if not isinstance(data, list):
            raise ValidationError(
                message="Expected list of match IDs",
                endpoint="match-v5/ids",
                url=self._build_url(region.value, endpoint),
                response_body=str(data),
            )

        return data

    async def fetch_all_match_ids(
        self,
        puuid: str,
        region: Region = Region.EUROPE,
        queue: int | None = None,
        match_type: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[str]:
        """Fetch all available match IDs for a player using pagination.

        This method automatically handles pagination by making multiple requests
        with incrementing start indices until all matches are retrieved.

        Args:
            puuid: Player Universal Unique Identifier
            region: Regional routing value
            queue: Queue ID filter
            match_type: Match type filter (ranked, normal, etc.)
            start_time: Start time filter (epoch seconds)
            end_time: End time filter (epoch seconds)

        Returns:
            Complete list of all match IDs for the player
        """
        all_match_ids: list[str] = []
        start = 0
        page_size = 100  # Use maximum allowed by Riot API

        logger.info(
            "Starting match ID pagination",
            puuid=puuid,
            region=region.value,
        )

        while True:
            # Fetch page
            match_ids = await self.get_match_ids(
                puuid=puuid,
                region=region,
                start=start,
                count=page_size,
                queue=queue,
                match_type=match_type,
                start_time=start_time,
                end_time=end_time,
            )

            # No more matches
            if not match_ids:
                logger.info(
                    "Pagination complete - no more matches",
                    puuid=puuid,
                    total_matches=len(all_match_ids),
                )
                break

            all_match_ids.extend(match_ids)

            logger.debug(
                "Fetched match ID page",
                page_start=start,
                page_size=len(match_ids),
                total_so_far=len(all_match_ids),
            )

            # Fewer results than requested = last page
            if len(match_ids) < page_size:
                logger.info(
                    "Pagination complete - last page",
                    puuid=puuid,
                    total_matches=len(all_match_ids),
                )
                break

            start += len(match_ids)

        return all_match_ids

    async def get_match(
        self,
        match_id: str,
        region: Region = Region.EUROPE,
    ) -> MatchDto:
        """Get match details by match ID.

        Args:
            match_id: Match ID (format: REGION_GAMEID)
            region: Regional routing value

        Returns:
            Match data
        """
        endpoint = f"/lol/match/v5/matches/{match_id}"
        data = await self._request(region.value, endpoint)
        return await validate_response(
            MatchDto,
            data,
            "match-v5/match",
            self._build_url(region.value, endpoint),
        )

    async def get_match_timeline(
        self,
        match_id: str,
        region: Region = Region.EUROPE,
    ) -> TimelineDto:
        """Get match timeline by match ID.

        Args:
            match_id: Match ID (format: REGION_GAMEID)
            region: Regional routing value

        Returns:
            Timeline data with frames and events
        """
        endpoint = f"/lol/match/v5/matches/{match_id}/timeline"
        data = await self._request(region.value, endpoint)
        return await validate_response(
            TimelineDto,
            data,
            "match-v5/timeline",
            self._build_url(region.value, endpoint),
        )


def get_region_for_platform(platform: Platform) -> Region:
    """Get the regional routing value for a platform.

    Args:
        platform: Platform routing value

    Returns:
        Corresponding region
    """
    for region, platforms in REGION_TO_PLATFORMS.items():
        if platform in platforms:
            return region
    return Region.EUROPE  # Default fallback
