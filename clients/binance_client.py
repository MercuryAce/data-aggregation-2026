"""Binance / Binance.US spot REST client (public bookTicker prototype)."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config

API_KEY = Config.BINANCE_API_KEY
API_KEY_HEADER = Config.BINANCE_API_KEY_HEADER or "X-MBX-APIKEY"
BASE_URL = (Config.BINANCE_BASE_URL or "https://api.binance.com").rstrip("/")
REQUEST_TIMEOUT = Config.BINANCE_REQUEST_TIMEOUT

headers = {"accept": "application/json"}
# Optional: some deployments rate-limit friendlier with a key present.
if API_KEY:
    headers[API_KEY_HEADER] = API_KEY


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


class BinanceAPIError(Exception):
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
    if response.ok:
        return response.json()
    detail = response.text[:200] or response.reason
    try:
        body = response.json()
        detail = body.get("msg") or body.get("message") or detail
    except Exception:
        pass
    raise BinanceAPIError(response.status_code, str(detail), response.url)


def get_book_ticker(symbol: str) -> dict:
    """Best bid/ask for a symbol, e.g. BTCUSDT."""
    return _call("/api/v3/ticker/bookTicker", {"symbol": symbol.upper()})


def get_book_tickers(symbols: list[str] | None = None) -> list[dict]:
    """All book tickers, or a subset when ``symbols`` is provided."""
    params = None
    if symbols:
        import json

        # Binance.US rejects spaces inside the symbols JSON array.
        params = {
            "symbols": json.dumps(
                [s.upper() for s in symbols], separators=(",", ":")
            )
        }
    payload = _call("/api/v3/ticker/bookTicker", params)
    if isinstance(payload, dict):
        return [payload]
    return payload or []
