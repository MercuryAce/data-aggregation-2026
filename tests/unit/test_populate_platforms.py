"""CoinGecko → market_coins platform/contract sync."""

from __future__ import annotations

from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc)


def test_populate_platforms(app, monkeypatch):
    from models import MarketCoin, db
    from services import populate_platforms

    with app.app_context():
        db.session.add(
            MarketCoin(
                cg_id="usd-coin",
                symbol="usdc",
                name="USDC",
                market_cap_rank=5,
                synced_at=_now(),
                source="coingecko",
            )
        )
        db.session.commit()

        monkeypatch.setattr(
            populate_platforms.cg_client,
            "get_coins_list",
            lambda include_platform=False: [
                {
                    "id": "usd-coin",
                    "symbol": "usdc",
                    "name": "USDC",
                    "platforms": {
                        "ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                        "solana": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    },
                }
            ],
        )

        n = populate_platforms.populate_platforms()
        assert n == 1
        coin = db.session.get(MarketCoin, "usd-coin")
        assert coin.primary_chain == "ethereum"
        assert coin.contract_address.startswith("0xA0b8")
        assert "solana" in (coin.platforms or {})
        assert (coin.external_ids or {}).get("coingecko") == "usd-coin"
        assert coin.structure_synced_at is not None
