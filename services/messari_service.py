from datetime import datetime

from services import cache_store, messari_cache_keys
from services.cache_store import CacheMissError


def _cached(key: str) -> tuple[dict | list, datetime]:
    entry = cache_store.get(key)
    if entry is None:
        raise CacheMissError(f"Cache miss for key: {key}")
    return entry.payload, entry.fetched_at


def get_assets(limit=20, page=1):
    return _cached(messari_cache_keys.assets_key(limit, page))


def get_asset_details(slugs):
    return _cached(messari_cache_keys.asset_details_key(slugs))


def get_asset_metrics_catalog():
    return _cached(messari_cache_keys.asset_metrics_catalog_key())


def get_asset_timeseries(slug, metric, granularity):
    return _cached(messari_cache_keys.timeseries_key(slug, metric, granularity))


def get_exchanges(limit=100, page=1):
    return _cached(messari_cache_keys.exchanges_key(limit, page))


def get_exchange(exchange_id):
    return _cached(messari_cache_keys.exchange_key(exchange_id))