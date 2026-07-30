"""Kraken public REST client (Ticker bid/ask prototype)."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config

API_KEY = Config.KRAKEN_API_KEY
BASE_URL = (Config.KRAKEN_BASE_URL or "https://api.kraken.com").rstrip("/")
REQUEST_TIMEOUT = Config.KRAKEN_REQUEST_TIMEOUT

headers = {"accept": "application/json"}
# Public ticker needs no auth; key reserved for private signed routes later.


def _build_session():
    session = requests.Session()
    retries = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


session = _build_session()


class KrakenAPIError(Exception):
    def __init__(self, status_code: int, message: str, url: str):
        self.status_code = status_code
        self.message = message
        self.url = url
        super().__init__(f"{status_code} {message} ({url})")


def _call(path: str, params: dict | None = None):
    url = f"{BASE_URL}/{path.lstrip('/')}"
    response = session.get(
        url, params=params or {}, headers=headers, timeout=REQUEST_TIMEOUT
    )
    if not response.ok:
        raise KrakenAPIError(
            response.status_code, response.text[:200] or response.reason, response.url
        )
    body = response.json()
    errors = body.get("error") or []
    if errors:
        raise KrakenAPIError(response.status_code, "; ".join(errors), response.url)
    return body.get("result") or {}


def get_ticker(pair: str) -> dict:
    """Return Kraken ticker result map for one pair (e.g. XBTUSD)."""
    return _call("/0/public/Ticker", {"pair": pair})


def parse_bid_ask(ticker_result: dict) -> tuple[float | None, float | None, float | None]:
    """Extract bid, ask, last from a Kraken ticker result dict (one pair entry)."""
    if not ticker_result:
        return None, None, None
    # Result is { "XXBTZUSD": { "a": [...], "b": [...], "c": [...] }, ... }
    entry = next(iter(ticker_result.values()))
    if not isinstance(entry, dict):
        return None, None, None

    def _first(arr):
        if isinstance(arr, (list, tuple)) and arr:
            try:
                return float(arr[0])
            except (TypeError, ValueError):
                return None
        return None

    ask = _first(entry.get("a"))
    bid = _first(entry.get("b"))
    last = _first(entry.get("c"))
    return bid, ask, last
