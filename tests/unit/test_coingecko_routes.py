"""T5 (partial): CoinGecko routes — service wiring and status codes."""

from __future__ import annotations

from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc)


def _capture_render(monkeypatch):
    """Avoid brittle full-template fixtures; capture fetch_context output."""
    captured = {}

    def fake_guarded_render(template_name, fetch_context):
        captured["template"] = template_name
        captured["context"] = fetch_context()
        return "ok", 200

    monkeypatch.setattr("blueprints.coingecko.guarded_render", fake_guarded_render)
    return captured


def test_index_loads_markets_and_global(client, no_request_guard, monkeypatch, app):
    from app import cache

    cache.clear()
    captured = _capture_render(monkeypatch)

    markets = [{"id": "bitcoin", "name": "Bitcoin"}]
    global_payload = {"data": {"markets": 50, "active_cryptocurrencies": 100}}

    monkeypatch.setattr(
        "blueprints.coingecko.get_market_data",
        lambda limit=250, vs_currency="usd", page=1: (markets, _now()),
    )
    monkeypatch.setattr(
        "blueprints.coingecko.get_global",
        lambda: (global_payload, _now()),
    )

    response = client.get("/")
    assert response.status_code == 200
    assert captured["template"] == "index.html"
    assert captured["context"]["coins"] == markets
    assert captured["context"]["global_stats"] == global_payload["data"]


def test_coin_detail_uses_url_id(client, no_request_guard, monkeypatch, app):
    from app import cache

    cache.clear()
    captured = _capture_render(monkeypatch)
    calls = []

    def fake_coin_details(coin_id, vs_currency="usd"):
        calls.append(coin_id)
        return {"id": coin_id, "name": "Ethereum"}, _now()

    monkeypatch.setattr("blueprints.coingecko.get_coin_details", fake_coin_details)

    response = client.get("/coin/ethereum")
    assert response.status_code == 200
    assert calls == ["ethereum"]
    assert captured["context"]["coin"]["id"] == "ethereum"


def test_price_history_rejects_invalid_days(client, no_request_guard, app):
    from app import cache

    cache.clear()
    response = client.get("/api/price-history/bitcoin?days=11")
    assert response.status_code == 400


def test_price_history_returns_ohlc_json(client, no_request_guard, monkeypatch, app):
    from app import cache

    cache.clear()

    monkeypatch.setattr(
        "blueprints.coingecko.get_ohlc",
        lambda coin_id, days=30, vs_currency="usd": ([[1, 2, 3, 4, 5]], _now()),
    )

    response = client.get("/api/price-history/bitcoin?days=30")
    assert response.status_code == 200
    assert response.get_json() == [[1, 2, 3, 4, 5]]


def test_index_cache_miss_returns_503(client, no_request_guard, monkeypatch, app):
    from app import cache
    from services.cache_store import CacheMissError

    cache.clear()
    monkeypatch.setattr(
        "blueprints.coingecko.get_market_data",
        lambda **kwargs: (_ for _ in ()).throw(CacheMissError("missing")),
    )

    response = client.get("/")
    assert response.status_code == 503


def test_trending_loads_cache(client, no_request_guard, monkeypatch, app):
    from app import cache

    cache.clear()
    captured = _capture_render(monkeypatch)
    payload = {"coins": [{"item": {"id": "solana", "name": "Solana"}}]}

    monkeypatch.setattr(
        "blueprints.coingecko.get_trending",
        lambda: (payload, _now()),
    )

    response = client.get("/trending")
    assert response.status_code == 200
    assert captured["template"] == "trending.html"
    assert captured["context"]["trending"] == payload
