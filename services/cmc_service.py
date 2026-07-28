from datetime import datetime

from services import cache_store, cmc_cache_keys
from services.cache_store import CacheMissError


def _cached(key: str) -> tuple[dict | list, datetime]:
    entry = cache_store.get(key)
    if entry is None:
        raise CacheMissError(f"Cache miss for key: {key}")
    return entry.payload, entry.fetched_at


def get_listings(start=1, limit=100, convert="USD"):
    return _cached(cmc_cache_keys.listings_key(start, limit, convert))


def get_quotes(ids: str, convert="USD"):
    return _cached(cmc_cache_keys.quotes_key(ids, convert))


def get_map(listing_status="active", limit=5000):
    return _cached(cmc_cache_keys.map_key(listing_status, limit))
