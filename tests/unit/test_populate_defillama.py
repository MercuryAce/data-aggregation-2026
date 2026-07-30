"""DefiLlama → market_coins price patch."""

from __future__ import annotations

from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc)


def test_patch_market_prices(app, monkeypatch):
    from models import MarketCoin, db
    from services import populate_defillama

    with app.app_context():
        db.session.add(
            MarketCoin(
                cg_id="bitcoin",
                symbol="btc",
                name="Bitcoin",
                market_cap_rank=1,
                current_price=1.0,
                market_cap=1e12,
                synced_at=_now(),
                source="coingecko",
            )
        )
        db.session.commit()

        monkeypatch.setattr(
            populate_defillama,
            "fetch_prices_by_quote_keys",
            lambda keys: {"coingecko:bitcoin": 111111.0},
        )
        monkeypatch.setattr(populate_defillama, "append_price_ticks", lambda ticks: len(ticks))

        n = populate_defillama.patch_market_prices()
        assert n == 1
        coin = db.session.get(MarketCoin, "bitcoin")
        assert coin.current_price == 111111.0
        assert coin.market_cap == 1e12  # untouched
        assert coin.market_cap_rank == 1
        assert coin.source == "defillama"
        assert coin.metrics_synced_at is not None


def test_patch_uses_contract_quote_key(app, monkeypatch):
    from models import MarketCoin, db
    from services import populate_defillama

    with app.app_context():
        db.session.add(
            MarketCoin(
                cg_id="usd-coin",
                symbol="usdc",
                name="USDC",
                market_cap_rank=5,
                current_price=1.0,
                platforms={
                    "ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                },
                primary_chain="ethereum",
                contract_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                synced_at=_now(),
                source="coingecko",
            )
        )
        db.session.commit()

        seen = {}

        def fake_fetch(keys):
            seen["keys"] = list(keys)
            return {
                "ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48": 1.001,
            }

        monkeypatch.setattr(populate_defillama, "fetch_prices_by_quote_keys", fake_fetch)
        monkeypatch.setattr(populate_defillama, "append_price_ticks", lambda ticks: len(ticks))

        n = populate_defillama.patch_market_prices()
        assert n == 1
        assert seen["keys"] == [
            "ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        ]
        assert db.session.get(MarketCoin, "usd-coin").current_price == 1.001


def test_fetch_prices_batches(app, monkeypatch):
    from services import populate_defillama

    calls = []

    def fake_current(coins: str):
        calls.append(coins)
        parts = coins.split(",")
        return {
            "coins": {
                p: {"price": 10.0 + i, "symbol": "X"}
                for i, p in enumerate(parts)
            }
        }

    monkeypatch.setattr(
        populate_defillama.defillama_client,
        "get_current_prices",
        fake_current,
    )
    monkeypatch.setattr(populate_defillama, "BATCH_SIZE", 2)

    prices = populate_defillama.fetch_prices_for_cg_ids(["a", "b", "c"])
    assert prices == {"a": 10.0, "b": 11.0, "c": 10.0}
    assert len(calls) == 2
    assert calls[0] == "coingecko:a,coingecko:b"
    assert calls[1] == "coingecko:c"
