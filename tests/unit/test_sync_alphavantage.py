"""Alpha Vantage sync script — CLI flags and cache writes."""

from __future__ import annotations

import scripts.sync_alphavantage as sync_av
from services import av_cache_keys


def test_av_cache_keys():
    assert av_cache_keys.news_key("blockchain", 50) == "av_news_blockchain_50"
    assert (
        av_cache_keys.news_tickers_key("CRYPTO:BTC,CRYPTO:ETH", 50)
        == "av_news_tickers_CRYPTO-BTC_CRYPTO-ETH_50"
    )
    assert av_cache_keys.etf_profile_key("ibit") == "av_etf_profile_IBIT"
    assert av_cache_keys.quote_key("gld") == "av_quote_GLD"
    assert av_cache_keys.fx_key("btc", "usd") == "av_fx_BTC_USD"
    assert av_cache_keys.digital_currency_daily_key("btc") == "av_dc_daily_BTC_USD"
    assert av_cache_keys.spot_key("gold") == "av_spot_GOLD"


def test_metals_task_invokes_sync_metals(app, monkeypatch):
    calls = []

    monkeypatch.setattr(
        sync_av,
        "sync_metals",
        lambda symbols="GOLD,SILVER": calls.append(symbols),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["sync_alphavantage.py", "--tasks", "metals", "--metals", "GOLD,XAG"],
    )

    assert sync_av.main() == 0
    assert calls == ["GOLD,XAG"]


def test_fx_task_uses_cli_pairs(app, monkeypatch):
    calls = []

    monkeypatch.setattr(
        sync_av,
        "sync_fx",
        lambda pairs="BTC/USD": calls.append(pairs),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["sync_alphavantage.py", "--tasks", "fx", "--pairs", "ETH/USD,USD/EUR"],
    )

    assert sync_av.main() == 0
    assert calls == ["ETH/USD,USD/EUR"]


def test_unknown_task_returns_1(app, monkeypatch):
    monkeypatch.setattr("sys.argv", ["sync_alphavantage.py", "--tasks", "not-a-task"])
    assert sync_av.main() == 1


def test_sync_metals_writes_cache(app, monkeypatch):
    monkeypatch.setattr(sync_av, "REQUEST_GAP_SECONDS", 0)
    monkeypatch.setattr(
        sync_av.av_client,
        "get_gold_silver_spot",
        lambda symbol: {"symbol": symbol, "price": "2000"},
    )

    sync_av.sync_metals(symbols="GOLD,SILVER")

    from services import cache_store

    gold = cache_store.get(av_cache_keys.spot_key("GOLD"))
    silver = cache_store.get(av_cache_keys.spot_key("SILVER"))
    assert gold is not None
    assert gold.payload["symbol"] == "GOLD"
    assert silver is not None
    assert silver.payload["symbol"] == "SILVER"


def test_sync_fx_writes_cache(app, monkeypatch):
    monkeypatch.setattr(sync_av, "REQUEST_GAP_SECONDS", 0)

    def fake_fx(from_currency, to_currency):
        return {
            "Realtime Currency Exchange Rate": {
                "1. From_Currency Code": from_currency,
                "3. To_Currency Code": to_currency,
                "5. Exchange Rate": "1.0",
            }
        }

    monkeypatch.setattr(sync_av.av_client, "get_currency_exchange_rate", fake_fx)

    sync_av.sync_fx(pairs="BTC/USD")

    from services import cache_store

    entry = cache_store.get(av_cache_keys.fx_key("BTC", "USD"))
    assert entry is not None
    assert (
        entry.payload["Realtime Currency Exchange Rate"]["1. From_Currency Code"]
        == "BTC"
    )


def test_sync_news_writes_topic_and_ticker_keys(app, monkeypatch):
    monkeypatch.setattr(sync_av, "REQUEST_GAP_SECONDS", 0)
    calls = []

    def fake_news(**kwargs):
        calls.append(kwargs)
        return {"feed": [{"title": "x"}]}

    monkeypatch.setattr(sync_av.av_client, "get_news_sentiment", fake_news)

    sync_av.sync_news(topics="blockchain", tickers="CRYPTO:BTC", limit=10)

    from services import cache_store

    assert len(calls) == 2
    topic_entry = cache_store.get(av_cache_keys.news_key("blockchain", 10))
    ticker_entry = cache_store.get(av_cache_keys.news_tickers_key("CRYPTO:BTC", 10))
    assert topic_entry is not None
    assert ticker_entry is not None
