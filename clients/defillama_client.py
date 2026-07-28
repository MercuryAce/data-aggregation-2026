"""DefiLlama HTTP client — mirrors DefiLlamaRequestController route surface.

Hosts follow the public Llama API layout:
  api | coins | stablecoins | yields | bridges
"""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config

API_KEY = Config.DEFILLAMA_API_KEY
API_KEY_HEADER = Config.DEFILLAMA_API_KEY_HEADER
REQUEST_TIMEOUT = Config.DEFILLAMA_REQUEST_TIMEOUT

# Prefer explicit host base; fall back to api.llama.fi domain derivation.
_BASE = Config.DEFILLAMA_BASE_URL.rstrip("/")
if "://" in _BASE:
    _SCHEME, _REST = _BASE.split("://", 1)
    _HOST = _REST.split("/", 1)[0]
    # api.llama.fi -> llama.fi
    DOMAIN = ".".join(_HOST.split(".")[-2:]) if _HOST.count(".") >= 1 else "llama.fi"
    SCHEME = _SCHEME
else:
    DOMAIN = "llama.fi"
    SCHEME = "https"

headers = {"accept": "application/json"}
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


def _url(server: str, path: str) -> str:
    return f"{SCHEME}://{server}.{DOMAIN}/{path.lstrip('/')}"


def _call(server: str, path: str, params: dict | None = None):
    response = session.get(
        _url(server, path),
        params=params or {},
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


# ---------------------- TVL / Protocols (api) ---------------------- #

def get_protocols():
    return _call("api", "protocols")


def get_protocol(protocol: str):
    return _call("api", f"protocol/{protocol}")


def get_historical_chain_tvl():
    return _call("api", "v2/historicalChainTvl")


def get_historical_chain_tvl_by_chain(chain: str):
    return _call("api", f"v2/historicalChainTvl/{chain}")


def get_chains():
    return _call("api", "v2/chains")


# ---------------------- Coins (coins) ---------------------- #

def get_current_prices(coins: str):
    return _call("coins", f"prices/current/{coins}")


def get_historical_prices(timestamp: int | str, coins: str):
    return _call("coins", f"prices/historical/{timestamp}/{coins}")


def get_batch_historical(**params):
    return _call("coins", "batchHistorical", params)


def get_price_chart(coins: str, **params):
    return _call("coins", f"chart/{coins}", params)


def get_price_percentage(coins: str, **params):
    return _call("coins", f"percentage/{coins}", params)


def get_first_price(coins: str):
    return _call("coins", f"prices/first/{coins}")


def get_block(chain: str, timestamp: int | str):
    return _call("coins", f"block/{chain}/{timestamp}")


# ---------------------- Stablecoins ---------------------- #

def get_stablecoins(include_prices: bool | None = None):
    params = {}
    if include_prices is not None:
        params["includePrices"] = str(include_prices).lower()
    return _call("stablecoins", "stablecoins", params)


def get_stablecoin_charts_all(stablecoin: int | str | None = None):
    params = {}
    if stablecoin is not None:
        params["stablecoin"] = stablecoin
    return _call("stablecoins", "stablecoincharts/all", params)


def get_stablecoin_charts_by_chain(chain: str, stablecoin: int | str | None = None):
    params = {}
    if stablecoin is not None:
        params["stablecoin"] = stablecoin
    return _call("stablecoins", f"stablecoincharts/{chain}", params)


def get_stablecoin(asset_id: int | str):
    return _call("stablecoins", f"stablecoin/{asset_id}")


def get_stablecoin_chains():
    return _call("stablecoins", "stablecoinchains")


def get_stablecoin_prices():
    return _call("stablecoins", "stablecoinprices")


# ---------------------- Yields ---------------------- #

def get_pools():
    return _call("yields", "pools")


def get_pool_chart(pool: str):
    return _call("yields", f"chart/{pool}")


# ---------------------- Bridges ---------------------- #

def get_bridges(include_chains: bool | None = None):
    params = {}
    if include_chains is not None:
        params["includeChains"] = str(include_chains).lower()
    return _call("bridges", "bridges", params)


def get_bridge(bridge_id: int | str):
    return _call("bridges", f"bridge/{bridge_id}")


def get_bridge_volume(chain: str, **params):
    return _call("bridges", f"bridgevolume/{chain}", params)


def get_bridge_day_stats(timestamp: int | str, chain: str, **params):
    return _call("bridges", f"bridgedaystats/{timestamp}/{chain}", params)


def get_bridge_transactions(bridge_id: int | str, **params):
    return _call("bridges", f"transactions/{bridge_id}", params)


# ---------------------- DEX volumes / options (api) ---------------------- #

def get_dexs(**params):
    return _call("api", "overview/dexs", params)


def get_dexs_by_chain(chain: str, **params):
    return _call("api", f"overview/dexs/{chain}", params)


def get_dex_summary(protocol: str, **params):
    return _call("api", f"summary/dexs/{protocol}", params)


def get_options(**params):
    return _call("api", "overview/options", params)


def get_options_by_chain(chain: str, **params):
    return _call("api", f"overview/options/{chain}", params)


def get_options_summary(protocol: str, **params):
    return _call("api", f"summary/options/{protocol}", params)


# ---------------------- Fees (api) ---------------------- #

def get_fees(**params):
    return _call("api", "overview/fees", params)


def get_fees_by_chain(chain: str, **params):
    return _call("api", f"overview/fees/{chain}", params)


def get_fees_by_protocol(protocol: str, **params):
    return _call("api", f"summary/fees/{protocol}", params)
