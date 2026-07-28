"""CoinMarketCap Pro API client."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config

API_KEY = Config.CMC_API_KEY
API_KEY_HEADER = Config.CMC_API_KEY_HEADER or "X-CMC_PRO_API_KEY"
BASE_URL = Config.CMC_BASE_URL.rstrip("/")
REQUEST_TIMEOUT = Config.CMC_REQUEST_TIMEOUT

headers = {
    "accept": "application/json",
}
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


class CmcAPIError(Exception):
    """Raised when CMC returns a non-success HTTP response."""

    def __init__(self, status_code: int, message: str, url: str):
        self.status_code = status_code
        self.message = message
        self.url = url
        super().__init__(f"{status_code} {message} ({url})")


def _call(path: str, params: dict | None = None):
    url = f"{BASE_URL}/{path.lstrip('/')}"
    response = session.get(
        url,
        params=params or {},
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    if response.ok:
        return response.json()

    detail = ""
    try:
        body = response.json()
        status = body.get("status") or {}
        detail = status.get("error_message") or body.get("error") or response.text[:200]
    except Exception:
        detail = response.text[:200] or response.reason

    raise CmcAPIError(response.status_code, str(detail), response.url)


def get_listings_latest(
    start=1,
    limit=100,
    convert="USD",
    sort="market_cap",
    sort_dir="desc",
    **params,
):
    query = {
        "start": start,
        "limit": limit,
        "convert": convert,
        "sort": sort,
        "sort_dir": sort_dir,
        **params,
    }
    return _call("cryptocurrency/listings/latest", query)


def get_quotes_latest(symbol=None, id=None, slug=None, convert="USD", **params):
    query = {"convert": convert, **params}
    if symbol is not None:
        query["symbol"] = symbol
    if id is not None:
        query["id"] = id
    if slug is not None:
        query["slug"] = slug
    return _call("cryptocurrency/quotes/latest", query)


def get_cryptocurrency_map(listing_status="active", start=1, limit=5000, **params):
    query = {
        "listing_status": listing_status,
        "start": start,
        "limit": limit,
        **params,
    }
    return _call("cryptocurrency/map", query)
