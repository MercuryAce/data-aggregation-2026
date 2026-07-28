"""Unified market mash-up service."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from services import cache_keys, cache_store, cmc_cache_keys, market_service
from services.cache_store import CacheMissError


def _now():
    return datetime.now(timezone.utc)


def test_unified_markets_prefers_cmc_price(app):
    cache_store.set(
        cmc_cache_keys.listings_key(1, 500, "USD"),
        {
            "data": [
                {
                    "id": 1,
                    "name": "Bitcoin",
                    "symbol": "BTC",
                    "slug": "bitcoin",
                    "cmc_rank": 1,
                    "quote": {"USD": {"price": 99999.0, "percent_change_24h": 1.5, "market_cap": 1e12, "volume_24h": 1e9}},
                }
            ]
        },
        source="cmc",
    )
    cache_store.set(
        cache_keys.markets_key("usd", 250, 1),
        [
            {
                "id": "bitcoin",
                "symbol": "btc",
                "name": "Bitcoin",
                "image": "https://example/btc.png",
                "current_price": 1.0,
                "market_cap_rank": 1,
                "price_change_percentage_24h": 0.1,
                "market_cap": 1,
                "total_volume": 1,
            }
        ],
        source="coingecko",
    )

    rows, meta = market_service.get_unified_markets(page=1, per_page=250, max_pages=1)
    assert rows[0]["current_price"] == 99999.0
    assert rows[0]["price_source"] == "cmc"
    assert rows[0]["image"] == "https://example/btc.png"
    assert meta["price_source"] == "cmc"


def test_unified_markets_falls_back_to_cg(app):
    cache_store.set(
        cache_keys.markets_key("usd", 250, 1),
        [
            {
                "id": "ethereum",
                "symbol": "eth",
                "name": "Ethereum",
                "current_price": 3000.0,
                "market_cap_rank": 2,
            }
        ],
        source="coingecko",
    )

    rows, meta = market_service.get_unified_markets(page=1, per_page=250, max_pages=1)
    assert rows[0]["id"] == "ethereum"
    assert rows[0]["current_price"] == 3000.0
    assert rows[0]["price_source"] == "coingecko"
    assert meta["price_source"] == "coingecko"


def test_unified_markets_miss_raises(app):
    with pytest.raises(CacheMissError):
        market_service.get_unified_markets(page=1, per_page=250, max_pages=1)


def test_live_prices_from_cmc(app):
    cache_store.set(
        cmc_cache_keys.listings_key(1, 500, "USD"),
        {
            "data": [
                {
                    "id": 1,
                    "symbol": "BTC",
                    "slug": "bitcoin",
                    "quote": {"USD": {"price": 50.0, "percent_change_24h": 2.0}},
                }
            ]
        },
        source="cmc",
    )
    payload = market_service.get_live_prices(["bitcoin"])
    assert payload["prices"]["bitcoin"]["price"] == 50.0
    assert payload["prices"]["bitcoin"]["source"] == "cmc"
