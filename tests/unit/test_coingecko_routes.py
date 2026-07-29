"""CoinGecko secondary routes (coin / search / OHLC) — views blueprint owns list pages."""

from __future__ import annotations

from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc)


def _capture_render(monkeypatch):
    captured = {}

    def fake_guarded_render(template_name, fetch_context):
        captured["template"] = template_name
        captured["context"] = fetch_context()
        return "ok", 200

    monkeypatch.setattr("blueprints.coingecko.guarded_render", fake_guarded_render)
    return captured


def test_coin_detail_uses_url_id(client, no_request_guard, monkeypatch, app):
    from app import cache

    cache.clear()
    captured = _capture_render(monkeypatch)
    calls = []

    def fake_coin_details(coin_id, vs_currency="usd"):
        calls.append(coin_id)
        return {"id": coin_id, "name": "Ethereum"}, _now()

    monkeypatch.setattr(
        "blueprints.coingecko.get_coin_details",
        fake_coin_details,
    )

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


def test_news_page_renders(client, no_request_guard, app):
    from app import cache

    cache.clear()
    response = client.get("/news")
    assert response.status_code == 200
    assert b"cryptopanic.com/widgets/news" in response.data
