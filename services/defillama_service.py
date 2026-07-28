from datetime import datetime

from services import cache_store, defillama_cache_keys
from services.cache_store import CacheMissError


def _cached(key: str) -> tuple[dict | list, datetime]:
    entry = cache_store.get(key)
    if entry is None:
        raise CacheMissError(f"Cache miss for key: {key}")
    return entry.payload, entry.fetched_at


def get_protocols():
    return _cached(defillama_cache_keys.protocols_key())


def get_protocol(protocol: str):
    return _cached(defillama_cache_keys.protocol_key(protocol))


def get_historical_chain_tvl():
    return _cached(defillama_cache_keys.historical_chain_tvl_key())


def get_historical_chain_tvl_by_chain(chain: str):
    return _cached(defillama_cache_keys.historical_chain_tvl_by_chain_key(chain))


def get_chains():
    return _cached(defillama_cache_keys.chains_key())


def get_current_prices(coins: str):
    return _cached(defillama_cache_keys.current_prices_key(coins))


def get_historical_prices(timestamp, coins: str):
    return _cached(defillama_cache_keys.historical_prices_key(timestamp, coins))


def get_stablecoins():
    return _cached(defillama_cache_keys.stablecoins_key())


def get_stablecoin(asset_id):
    return _cached(defillama_cache_keys.stablecoin_key(asset_id))


def get_stablecoin_charts_all():
    return _cached(defillama_cache_keys.stablecoin_charts_all_key())


def get_stablecoin_charts_by_chain(chain: str):
    return _cached(defillama_cache_keys.stablecoin_charts_chain_key(chain))


def get_stablecoin_chains():
    return _cached(defillama_cache_keys.stablecoin_chains_key())


def get_stablecoin_prices():
    return _cached(defillama_cache_keys.stablecoin_prices_key())


def get_pools():
    return _cached(defillama_cache_keys.pools_key())


def get_pool_chart(pool: str):
    return _cached(defillama_cache_keys.pool_chart_key(pool))


def get_bridges():
    return _cached(defillama_cache_keys.bridges_key())


def get_bridge(bridge_id):
    return _cached(defillama_cache_keys.bridge_key(bridge_id))


def get_bridge_volume(chain: str):
    return _cached(defillama_cache_keys.bridge_volume_key(chain))


def get_dexs():
    return _cached(defillama_cache_keys.dexs_key())


def get_dexs_by_chain(chain: str):
    return _cached(defillama_cache_keys.dexs_by_chain_key(chain))


def get_dex_summary(protocol: str):
    return _cached(defillama_cache_keys.dex_summary_key(protocol))


def get_options():
    return _cached(defillama_cache_keys.options_key())


def get_fees():
    return _cached(defillama_cache_keys.fees_key())


def get_fees_by_chain(chain: str):
    return _cached(defillama_cache_keys.fees_by_chain_key(chain))


def get_fees_by_protocol(protocol: str):
    return _cached(defillama_cache_keys.fees_by_protocol_key(protocol))
