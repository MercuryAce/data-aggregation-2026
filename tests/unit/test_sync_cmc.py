"""CMC cache keys + sync smoke."""

from __future__ import annotations

from services import cmc_cache_keys
from scripts import sync_cmc


def test_cmc_cache_keys():
    assert cmc_cache_keys.listings_key(1, 500, "USD") == "cmc_listings_USD_1_500"
    assert cmc_cache_keys.map_key() == "cmc_map_active_5000"


def test_sync_listings(monkeypatch, app):
    calls = {"set": []}

    def fake_listings(**kwargs):
        return {
            "data": [
                {
                    "id": 1,
                    "slug": "bitcoin",
                    "symbol": "BTC",
                    "quote": {"USD": {"price": 1.23, "volume_24h": 9}},
                }
            ]
        }

    monkeypatch.setattr("scripts.sync_cmc.cmc_client.get_listings_latest", fake_listings)
    monkeypatch.setattr(
        "scripts.sync_cmc.cache_store.set",
        lambda key, data, ttl_seconds=None, source="cmc": calls["set"].append(key),
    )
    monkeypatch.setattr("scripts.sync_cmc.append_price_ticks", lambda ticks: len(ticks))

    with app.app_context():
        sync_cmc.sync_listings(start=1, limit=100)

    assert calls["set"]
    assert "cmc_listings_USD_1_100" in calls["set"][0] or calls["set"][0].startswith("cmc_listings")
