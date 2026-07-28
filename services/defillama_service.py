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


def get_protocol(protocol: str) -> tuple[dict | list, datetime]:
    return _cached(defillama_cache_keys.protocol_key(protocol))


def get_historical_chain_tvl() -> tuple[dict | list, datetime]:
    return _cached(defillama_cache_keys.historical_chain_tvl_key())


def get_historical_chain_tvl_by_chain(chain: str) -> tuple[dict | list, datetime]:
    return _cached(defillama_cache_keys.historical_chain_tvl_by_chain_key(chain))
