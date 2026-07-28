import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config

API_KEY = Config.MESSARI_API_KEY
API_KEY_HEADER = Config.MESSARI_API_KEY_HEADER
BASE_URL = Config.MESSARI_BASE_URL
REQUEST_TIMEOUT = Config.MESSARI_REQUEST_TIMEOUT

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


def get_assets(limit=20, page=1, **params):
    query = {"limit": limit, "page": page, **params}
    return _call(f"{BASE_URL}/metrics/v2/assets", query)


def get_asset_details(slugs, **params):
    query = {"assets": slugs, **params}
    return _call(f"{BASE_URL}/metrics/v2/assets/details", query)


def get_asset_metrics_catalog(**params):
    return _call(f"{BASE_URL}/metrics/v2/assets/metrics", params)


def get_asset_timeseries(slug, metric, granularity, **params):
    url = (
        f"{BASE_URL}/metrics/v2/assets/{slug}/metrics/{metric}"
        f"/time-series/{granularity}"
    )
    return _call(url, params)


def get_exchanges(limit=100, page=1, **params):
    query = {"limit": limit, "page": page, **params}
    return _call(f"{BASE_URL}/metrics/v1/exchanges", query)


def get_exchange(exchange_id, **params):
    return _call(f"{BASE_URL}/metrics/v1/exchanges/{exchange_id}", params)


class MessariAPIError(Exception):
    """Raised when Messari returns a non-success HTTP response."""

    def __init__(self, status_code: int, message: str, url: str):
        self.status_code = status_code
        self.message = message
        self.url = url
        super().__init__(f"{status_code} {message} ({url})")


def _call(url: str, params: dict | None = None):
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
        detail = body.get("error") or body.get("message") or response.text[:200]
    except Exception:
        detail = response.text[:200] or response.reason

    raise MessariAPIError(response.status_code, str(detail), response.url)
