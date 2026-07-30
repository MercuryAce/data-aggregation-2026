"""Venue pair maps + asset_quotes populate."""

from __future__ import annotations

from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc)


def test_venue_pair_maps():
    from services.venue_pairs import (
        binance_pair_for_symbol,
        kraken_pair_for_symbol,
        okx_pair_for_symbol,
    )

    assert binance_pair_for_symbol("btc") == "BTCUSDT"
    assert kraken_pair_for_symbol("btc") == "XBTUSD"
    assert okx_pair_for_symbol("eth") == "ETH-USDT"


def test_patch_venue_quotes(app, monkeypatch):
    from models import AssetQuote, MarketCoin, db
    from services import populate_quotes

    with app.app_context():
        db.session.add(
            MarketCoin(
                cg_id="bitcoin",
                symbol="btc",
                name="Bitcoin",
                market_cap_rank=1,
                synced_at=_now(),
                source="coingecko",
            )
        )
        db.session.commit()

        monkeypatch.setattr(
            populate_quotes.binance_client,
            "get_book_tickers",
            lambda symbols: [
                {"symbol": "BTCUSDT", "bidPrice": "100.0", "askPrice": "101.0"}
            ],
        )
        monkeypatch.setattr(
            populate_quotes.kraken_client,
            "get_ticker",
            lambda pair: {"XXBTZUSD": {"a": ["102.0"], "b": ["99.0"], "c": ["100.5"]}},
        )
        monkeypatch.setattr(
            populate_quotes.okx_client,
            "get_ticker",
            lambda inst_id: {"bidPx": "99.5", "askPx": "100.5", "last": "100.0"},
        )

        n = populate_quotes.patch_venue_quotes(limit=5)
        assert n >= 2
        bn = db.session.get(AssetQuote, ("bitcoin", "binance"))
        assert bn is not None
        assert bn.bid == 100.0
        assert bn.ask == 101.0
        assert bn.kind == "exchange"
        kr = db.session.get(AssetQuote, ("bitcoin", "kraken"))
        assert kr is not None
        assert kr.bid == 99.0


def test_quotes_for_coin_spread(app):
    from models import AssetQuote, db
    from services.populate_quotes import quotes_for_coin

    with app.app_context():
        now = _now()
        db.session.add_all(
            [
                AssetQuote(
                    cg_id="bitcoin",
                    venue="coingecko",
                    kind="oracle",
                    last=100.0,
                    synced_at=now,
                ),
                AssetQuote(
                    cg_id="bitcoin",
                    venue="defillama",
                    kind="oracle",
                    last=102.0,
                    synced_at=now,
                ),
                AssetQuote(
                    cg_id="bitcoin",
                    venue="binance",
                    kind="exchange",
                    pair="BTCUSDT",
                    bid=99.0,
                    ask=101.0,
                    last=100.0,
                    synced_at=now,
                ),
            ]
        )
        db.session.commit()
        bundle = quotes_for_coin("bitcoin")
        assert bundle["oracle_spread"]["abs"] == 2.0
        assert len(bundle["exchanges"]) == 1
