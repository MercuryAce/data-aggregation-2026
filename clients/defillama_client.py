import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config

API_KEY = Config.DEFILLAMA_API_KEY
API_KEY_HEADER = Config.DEFILLAMA_API_KEY_HEADER
BASE_URL = Config.DEFILLAMA_BASE_URL.rstrip("/")
REQUEST_TIMEOUT = Config.DEFILLAMA_REQUEST_TIMEOUT

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


# ---------------------- Public API Functions ---------------------- #

def get_protocols():
    return _call(f"{BASE_URL}/protocols")


def get_protocol(protocol: str):
    return _call(f"{BASE_URL}/protocol/{protocol}")


def get_historical_chain_tvl():
    """All-chains historical TVL: GET /v2/historicalChainTvl"""
    return _call(f"{BASE_URL}/v2/historicalChainTvl")


def get_historical_chain_tvl_by_chain(chain: str):
    """Per-chain historical TVL: GET /v2/historicalChainTvl/{chain}"""
    return _call(f"{BASE_URL}/v2/historicalChainTvl/{chain}")


# ---------------------- Private Helper ---------------------- #

def _call(url: str, params: dict | None = None):
    response = session.get(
        url,
        params=params or {},
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()
