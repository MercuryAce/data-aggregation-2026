"""Populate + views blueprint smoke tests (no live CG when monkeypatched)."""

from __future__ import annotations

from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc)


def test_ensure_markets_skips_when_populated(app, monkeypatch):
    from models import MarketCoin, GlobalStats, db
    from services import populate_coingecko as populate

    calls = {"markets": 0, "global": 0}

    with app.app_context():
        db.session.add(
            MarketCoin(
                cg_id="bitcoin",
                symbol="btc",
                name="Bitcoin",
                market_cap_rank=1,
                synced_at=_now(),
            )
        )
        db.session.add(
            GlobalStats(
                id=1,
                active_cryptocurrencies=1,
                markets=1,
                synced_at=_now(),
                payload={"active_cryptocurrencies": 1, "markets": 1},
            )
        )
        db.session.commit()

        monkeypatch.setattr(
            populate,
            "populate_markets",
            lambda **kwargs: calls.__setitem__("markets", calls["markets"] + 1),
        )
        monkeypatch.setattr(
            populate,
            "populate_global",
            lambda: calls.__setitem__("global", calls["global"] + 1),
        )

        populate.ensure_markets(force=False)
        assert calls == {"markets": 0, "global": 0}


def test_populate_markets_upserts(app, monkeypatch):
    from models import MarketCoin, db
    from services import populate_coingecko as populate

    monkeypatch.setattr(
        populate.cg_client,
        "get_market_data",
        lambda **kwargs: [
            {
                "id": "bitcoin",
                "symbol": "btc",
                "name": "Bitcoin",
                "market_cap_rank": 1,
                "image": "http://x",
                "current_price": 100.0,
                "price_change_percentage_24h": 1.5,
                "market_cap": 1e12,
                "total_volume": 1e10,
                "high_24h": 110,
                "low_24h": 90,
                "fully_diluted_valuation": 1e12,
                "total_supply": 21e6,
                "circulating_supply": 19e6,
            }
        ],
    )

    with app.app_context():
        n = populate.populate_markets(pages=1, per_page=1)
        assert n == 1
        row = db.session.get(MarketCoin, "bitcoin")
        assert row is not None
        assert row.name == "Bitcoin"
        assert row.current_price == 100.0


def test_views_index_reads_mysql(client, no_request_guard, monkeypatch, app):
    from app import cache
    from models import MarketCoin, GlobalStats, db

    cache.clear()
    with app.app_context():
        db.session.add(
            MarketCoin(
                cg_id="bitcoin",
                symbol="btc",
                name="Bitcoin",
                market_cap_rank=1,
                current_price=50,
                synced_at=_now(),
            )
        )
        db.session.add(
            GlobalStats(
                id=1,
                active_cryptocurrencies=10,
                markets=20,
                market_cap_change_percentage_24h_usd=1.0,
                volume_change_percentage_24h_usd=2.0,
                payload={
                    "active_cryptocurrencies": 10,
                    "markets": 20,
                    "market_cap_change_percentage_24h_usd": 1.0,
                    "volume_change_percentage_24h_usd": 2.0,
                },
                synced_at=_now(),
            )
        )
        db.session.commit()

    monkeypatch.setattr(
        "blueprints.views.populate.ensure_markets",
        lambda force=False: None,
    )

    response = client.get("/")
    assert response.status_code == 200
    assert b"Bitcoin" in response.data


def test_views_trending_reads_snapshot(client, no_request_guard, monkeypatch, app):
    from app import cache
    from models import TrendingSnapshot, db

    cache.clear()
    payload = {
        "coins": [{"item": {"id": "solana", "name": "Solana", "symbol": "sol", "thumb": "", "market_cap_rank": 5, "data": {"price": 1, "price_change_percentage_24h": {"usd": 1}, "market_cap": "1", "sparkline": ""}}}],
        "nfts": [],
        "categories": [],
    }
    with app.app_context():
        db.session.merge(
            TrendingSnapshot(id="latest", payload=payload, synced_at=_now())
        )
        db.session.commit()

    monkeypatch.setattr(
        "blueprints.views.populate.ensure_trending",
        lambda force=False: None,
    )

    response = client.get("/trending")
    assert response.status_code == 200
    assert b"Solana" in response.data


def test_market_prices_api(client, no_request_guard, app):
    from models import MarketCoin, db

    with app.app_context():
        db.session.add(
            MarketCoin(
                cg_id="bitcoin",
                symbol="btc",
                name="Bitcoin",
                market_cap_rank=1,
                current_price=42.5,
                price_change_percentage_24h=1.25,
                market_cap=1e12,
                total_volume=1e9,
                synced_at=_now(),
                source="cmc",
            )
        )
        db.session.commit()

    response = client.get("/api/markets/prices?ids=bitcoin")
    assert response.status_code == 200
    data = response.get_json()
    assert "bitcoin" in data["prices"]
    assert data["prices"]["bitcoin"]["price"] == 42.5
    assert data["prices"]["bitcoin"]["price_display"].startswith("$")

    by_page = client.get("/api/markets/prices?page=1")
    assert by_page.status_code == 200
    assert "bitcoin" in by_page.get_json()["prices"]
