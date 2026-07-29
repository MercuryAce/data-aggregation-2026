"""Alpha Vantage client query construction + soft-error handling."""

from __future__ import annotations

import pytest

from clients import av_client


def test_get_news_sentiment_builds_query(monkeypatch):
    captured = {}

    def fake_call(params=None):
        captured["params"] = params
        return {"feed": []}

    monkeypatch.setattr(av_client, "_call", fake_call)
    result = av_client.get_news_sentiment(topics="blockchain", limit=25)
    assert result == {"feed": []}
    assert captured["params"]["function"] == "NEWS_SENTIMENT"
    assert captured["params"]["topics"] == "blockchain"
    assert captured["params"]["limit"] == 25
    assert captured["params"]["sort"] == "LATEST"


def test_get_etf_profile_builds_query(monkeypatch):
    captured = {}

    def fake_call(params=None):
        captured["params"] = params
        return {"symbol": "IBIT"}

    monkeypatch.setattr(av_client, "_call", fake_call)
    av_client.get_etf_profile("IBIT")
    assert captured["params"] == {"function": "ETF_PROFILE", "symbol": "IBIT"}


def test_get_global_quote_builds_query(monkeypatch):
    captured = {}

    def fake_call(params=None):
        captured["params"] = params
        return {"Global Quote": {}}

    monkeypatch.setattr(av_client, "_call", fake_call)
    av_client.get_global_quote("GLD")
    assert captured["params"]["function"] == "GLOBAL_QUOTE"
    assert captured["params"]["symbol"] == "GLD"


def test_get_currency_exchange_rate_builds_query(monkeypatch):
    captured = {}

    def fake_call(params=None):
        captured["params"] = params
        return {}

    monkeypatch.setattr(av_client, "_call", fake_call)
    av_client.get_currency_exchange_rate("BTC", "USD")
    assert captured["params"]["function"] == "CURRENCY_EXCHANGE_RATE"
    assert captured["params"]["from_currency"] == "BTC"
    assert captured["params"]["to_currency"] == "USD"


def test_get_digital_currency_daily_builds_query(monkeypatch):
    captured = {}

    def fake_call(params=None):
        captured["params"] = params
        return {}

    monkeypatch.setattr(av_client, "_call", fake_call)
    av_client.get_digital_currency_daily("ETH", market="USD")
    assert captured["params"]["function"] == "DIGITAL_CURRENCY_DAILY"
    assert captured["params"]["symbol"] == "ETH"
    assert captured["params"]["market"] == "USD"


def test_get_gold_silver_spot_builds_query(monkeypatch):
    captured = {}

    def fake_call(params=None):
        captured["params"] = params
        return {}

    monkeypatch.setattr(av_client, "_call", fake_call)
    av_client.get_gold_silver_spot("GOLD")
    assert captured["params"] == {"function": "GOLD_SILVER_SPOT", "symbol": "GOLD"}


def test_call_raises_on_soft_error_note(monkeypatch):
    class FakeResponse:
        ok = True
        url = "https://www.alphavantage.co/query?function=GLOBAL_QUOTE"
        text = ""

        def json(self):
            return {"Note": "Thank you for using Alpha Vantage! Our standard API rate limit is 25 requests per day."}

    monkeypatch.setattr(
        av_client.session,
        "get",
        lambda *args, **kwargs: FakeResponse(),
    )
    with pytest.raises(av_client.AvAPIError) as exc:
        av_client._call({"function": "GLOBAL_QUOTE", "symbol": "IBM"})
    assert "rate limit" in exc.value.message.lower() or "Note" in str(exc.value)


def test_call_raises_on_error_message(monkeypatch):
    class FakeResponse:
        ok = True
        url = "https://www.alphavantage.co/query"
        text = ""

        def json(self):
            return {"Error Message": "Invalid API call"}

    monkeypatch.setattr(
        av_client.session,
        "get",
        lambda *args, **kwargs: FakeResponse(),
    )
    with pytest.raises(av_client.AvAPIError) as exc:
        av_client._call({"function": "BAD"})
    assert "Invalid API call" in exc.value.message
