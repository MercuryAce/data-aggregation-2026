"""Alpha Vantage API client (single /query endpoint, function= routing)."""

from __future__ import annotations

import re

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config

API_KEY = Config.ALPHAVANTAGE_API_KEY
BASE_URL = (Config.ALPHAVANTAGE_BASE_URL or "https://www.alphavantage.co/query").rstrip(
    "/"
)
REQUEST_TIMEOUT = Config.ALPHAVANTAGE_REQUEST_TIMEOUT

SOFT_ERROR_KEYS = ("Note", "Information", "Error Message")
_APIKEY_QUERY_RE = re.compile(r"([?&]apikey=)[^&\s]+", re.IGNORECASE)


def redact_secrets(text: str) -> str:
    """Strip API keys from URLs and AV soft-error copy before logging."""
    if not text:
        return text
    out = _APIKEY_QUERY_RE.sub(r"\1***", text)
    if API_KEY:
        out = out.replace(API_KEY, "***")
    return out


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


class AvAPIError(Exception):
    """Raised when Alpha Vantage returns an HTTP or soft-error response."""

    def __init__(self, status_code: int, message: str, url: str):
        self.status_code = status_code
        self.message = redact_secrets(message)
        self.url = redact_secrets(url)
        super().__init__(f"{status_code} {self.message} ({self.url})")

    @property
    def is_rate_limit(self) -> bool:
        text = (self.message or "").lower()
        return "rate limit" in text or "25 requests per day" in text


def _call(params: dict | None = None):
    query = dict(params or {})
    if API_KEY:
        query["apikey"] = API_KEY

    response = session.get(BASE_URL, params=query, timeout=REQUEST_TIMEOUT)
    safe_url = redact_secrets(response.url)
    if not response.ok:
        detail = ""
        try:
            body = response.json()
            detail = (
                body.get("Error Message")
                or body.get("Information")
                or body.get("Note")
                or response.text[:200]
            )
        except Exception:
            detail = response.text[:200] or response.reason
        raise AvAPIError(response.status_code, str(detail), safe_url)

    data = response.json()
    if isinstance(data, dict):
        for key in SOFT_ERROR_KEYS:
            if key in data and data[key]:
                raise AvAPIError(200, str(data[key]), safe_url)
    return data


def get_news_sentiment(
    tickers=None,
    topics=None,
    time_from=None,
    time_to=None,
    sort="LATEST",
    limit=50,
    **params,
):
    query = {"function": "NEWS_SENTIMENT", "sort": sort, "limit": limit, **params}
    if tickers is not None:
        query["tickers"] = tickers
    if topics is not None:
        query["topics"] = topics
    if time_from is not None:
        query["time_from"] = time_from
    if time_to is not None:
        query["time_to"] = time_to
    return _call(query)


def get_etf_profile(symbol, **params):
    return _call({"function": "ETF_PROFILE", "symbol": symbol, **params})


def get_global_quote(symbol, **params):
    return _call({"function": "GLOBAL_QUOTE", "symbol": symbol, **params})


def get_currency_exchange_rate(from_currency, to_currency, **params):
    return _call(
        {
            "function": "CURRENCY_EXCHANGE_RATE",
            "from_currency": from_currency,
            "to_currency": to_currency,
            **params,
        }
    )


def get_digital_currency_daily(symbol, market="USD", **params):
    return _call(
        {
            "function": "DIGITAL_CURRENCY_DAILY",
            "symbol": symbol,
            "market": market,
            **params,
        }
    )


def get_gold_silver_spot(symbol, **params):
    return _call({"function": "GOLD_SILVER_SPOT", "symbol": symbol, **params})
