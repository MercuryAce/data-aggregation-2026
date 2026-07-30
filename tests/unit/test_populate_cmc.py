"""CMC → market_coins metrics patch."""

from __future__ import annotations

from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc)


def test_patch_market_metrics_matches_slug(app, monkeypatch):
    from models import MarketCoin, db
    from services import populate_cmc

    with app.app_context():
        db.session.add(
            MarketCoin(
                cg_id="bitcoin",
                symbol="btc",
                name="Bitcoin",
                market_cap_rank=1,
                current_price=1.0,
                synced_at=_now(),
                source="coingecko",
            )
        )
        db.session.commit()

        monkeypatch.setattr(
            populate_cmc,
            "fetch_listings",
            lambda **kwargs: [
                {
                    "id": 1,
                    "slug": "bitcoin",
                    "symbol": "BTC",
                    "circulating_supply": 19e6,
                    "total_supply": 21e6,
                    "quote": {
                        "USD": {
                            "price": 99999.0,
                            "percent_change_24h": 2.5,
                            "market_cap": 1e12,
                            "volume_24h": 2e10,
                            "fully_diluted_market_cap": 1.1e12,
                        }
                    },
                }
            ],
        )

        n = populate_cmc.patch_market_metrics(limit=100)
        assert n == 1
        coin = db.session.get(MarketCoin, "bitcoin")
        assert coin.current_price == 99999.0
        assert coin.price_change_percentage_24h == 2.5
        assert coin.market_cap == 1e12
        assert coin.total_volume == 2e10
        assert coin.market_cap_rank == 1  # rank untouched
        assert coin.source == "cmc"
        assert coin.metrics_synced_at is not None
        assert (coin.external_ids or {}).get("cmc") == 1
        assert (coin.external_ids or {}).get("cmc_slug") == "bitcoin"


def test_patch_skips_ambiguous_symbol(app, monkeypatch):
    from models import MarketCoin, db
    from services import populate_cmc

    with app.app_context():
        db.session.add_all(
            [
                MarketCoin(
                    cg_id="token-a",
                    symbol="xyz",
                    name="A",
                    market_cap_rank=1,
                    current_price=1,
                    synced_at=_now(),
                ),
                MarketCoin(
                    cg_id="token-b",
                    symbol="xyz",
                    name="B",
                    market_cap_rank=2,
                    current_price=2,
                    synced_at=_now(),
                ),
            ]
        )
        db.session.commit()

        monkeypatch.setattr(
            populate_cmc,
            "fetch_listings",
            lambda **kwargs: [
                {
                    "slug": "other",
                    "symbol": "XYZ",
                    "quote": {"USD": {"price": 50.0, "percent_change_24h": 1}},
                }
            ],
        )

        assert populate_cmc.patch_market_metrics() == 0
        assert db.session.get(MarketCoin, "token-a").current_price == 1
