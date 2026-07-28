"""T3: service _cached layer — hit / miss / typed helpers."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from services import cache_keys, cache_store, coingecko_service, messari_service
from services.cache_store import CacheMissError
from services import defillama_cache_keys, defillama_service, messari_cache_keys


def test_coingecko_cached_hit(app):
    payload = [{"id": "bitcoin"}]
    cache_store.set(cache_keys.markets_key("usd", 250, 1), payload)

    data, fetched_at = coingecko_service.get_market_data(limit=250)
    assert data == payload
    assert isinstance(fetched_at, datetime)


def test_coingecko_cached_miss_raises(app):
    with pytest.raises(CacheMissError, match="Cache miss"):
        coingecko_service.get_market_data(limit=250)


def test_coingecko_get_global_requires_dict(app):
    cache_store.set(cache_keys.global_key(), [{"not": "an object"}])

    with pytest.raises(CacheMissError, match="not an object"):
        coingecko_service.get_global()


def test_coingecko_get_global_hit(app):
    payload = {"data": {"markets": 1}}
    cache_store.set(cache_keys.global_key(), payload)

    data, _ = coingecko_service.get_global()
    assert data == payload


def test_coingecko_search_empty_query_raises():
    with pytest.raises(CacheMissError, match="Query is required"):
        coingecko_service.get_search("")


def test_messari_cached_miss_raises(app):
    with pytest.raises(CacheMissError):
        messari_service.get_assets(limit=20, page=1)


def test_messari_cached_hit(app):
    key = messari_cache_keys.assets_key(20, 1)
    cache_store.set(key, {"data": []}, source="messari")

    data, fetched_at = messari_service.get_assets(20, 1)
    assert data == {"data": []}
    assert fetched_at.tzinfo is not None


def test_defillama_cached_hit(app):
    key = defillama_cache_keys.protocols_key()
    cache_store.set(key, [{"name": "aave"}], source="defillama")

    data, _ = defillama_service.get_protocols()
    assert data == [{"name": "aave"}]


def test_defillama_cached_miss_raises(app):
    with pytest.raises(CacheMissError):
        defillama_service.get_protocol("aave")
