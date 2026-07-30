"""OKX public REST client stub (spot ticker). Wire when OKX_API_KEY is ready."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config

BASE_URL = (Config.OKX_BASE_URL or "https://www.okx.com").rstrip("/")
REQUEST_TIMEOUT = Config.OKX_REQUEST_TIMEOUT

headers = {"accept": "application/json"}


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


class OkxAPIError(Exception):
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
        raise OkxAPIError(
            response.status_code, response.text[:200] or response.reason, response.url
        )
    body = response.json()
    if str(body.get("code", "0")) != "0":
        raise OkxAPIError(response.status_code, str(body.get("msg") or body), response.url)
    return body.get("data") or []


def get_ticker(inst_id: str) -> dict | None:
    """Spot ticker for instrument id, e.g. BTC-USDT."""
    rows = _call("/api/v5/market/ticker", {"instId": inst_id})
    return rows[0] if rows else None
