"""Tests for RiotApiClient 429 Retry-After handling."""

from __future__ import annotations

import asyncio
from types import TracebackType

import pytest
from pytest import MonkeyPatch

from lol_data_center.api_client.riot_client import Region, RiotApiClient


class _StubLimiter:
    def __init__(self) -> None:
        self.acquires = 0

    async def acquire(self) -> None:
        self.acquires += 1


class _FakeResponse:
    def __init__(
        self,
        status: int,
        json_body: object | None,
        text_body: str = "",
        headers: dict | None = None,
    ) -> None:
        self.status = status
        self._json_body = json_body
        self._text_body = text_body
        self.headers = headers or {}

    async def __aenter__(self) -> _FakeResponse:
        return self

    async def __aexit__(
        self,
        exc_type: BaseException | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        return False

    async def text(self) -> str:
        return self._text_body

    async def json(self) -> object | None:
        return self._json_body


class _FakeSession:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        # Will pop(0) for each request
        self._responses = list(responses)

    def request(self, method: str, url: str, params: dict | None = None) -> _FakeResponse:
        # aiohttp returns a context manager for async with
        if not self._responses:
            raise AssertionError("No more fake responses queued")
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_request_retries_on_429_then_succeeds(monkeypatch: MonkeyPatch) -> None:
    limiter = _StubLimiter()
    client = RiotApiClient(api_key="test", rate_limiter=limiter)

    # Prepare: 429 with Retry-After: 0, then 200 with list json
    r1 = _FakeResponse(429, json_body=None, text_body="Too Many", headers={"Retry-After": "0"})
    r2 = _FakeResponse(200, json_body=["MATCH_1", "MATCH_2"], text_body="OK")
    fake_session = _FakeSession([r1, r2])

    async def _fake_get_session() -> _FakeSession:
        return fake_session

    # Patch client's session getter
    monkeypatch.setattr(client, "_get_session", _fake_get_session)

    # Patch sleep to avoid delays and capture calls
    sleep_calls: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)

    result = await client.get_match_ids(puuid="puuid", region=Region.EUROPE, start=0, count=5)

    # Should have retried once and returned the JSON from second response
    assert result == ["MATCH_1", "MATCH_2"]
    # Rate limiter acquire only once for initial attempt
    assert limiter.acquires == 1
    # Sleep called with Retry-After value
    assert sleep_calls == [0]


@pytest.mark.asyncio
async def test_request_uses_default_retry_after_when_header_missing(
    monkeypatch: MonkeyPatch,
) -> None:
    limiter = _StubLimiter()
    client = RiotApiClient(api_key="test", rate_limiter=limiter)

    # 429 without Retry-After header, then 200
    r1 = _FakeResponse(429, json_body=None, text_body="Too Many", headers={})
    r2 = _FakeResponse(200, json_body=["A"], text_body="OK")
    fake_session = _FakeSession([r1, r2])

    async def _fake_get_session() -> _FakeSession:
        return fake_session

    monkeypatch.setattr(client, "_get_session", _fake_get_session)

    sleep_values: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        sleep_values.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)

    result = await client.get_match_ids(puuid="puuid", region=Region.ASIA, start=0, count=1)

    assert result == ["A"]
    assert limiter.acquires == 1
    # Default value 120 seconds
    assert sleep_values == [120]
