"""T4: CoinGecko sync script — CLI tasks and cache writes."""

from __future__ import annotations

import scripts.sync_coingecko as sync_coingecko


def test_markets_task_invokes_sync_markets(app, monkeypatch):
    calls = []

    monkeypatch.setitem(
        sync_coingecko.TASKS,
        "markets",
        lambda: calls.append("markets"),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["sync_coingecko.py", "--tasks", "markets"],
    )

    assert sync_coingecko.main() == 0
    assert calls == ["markets"]


def test_unknown_task_returns_error(app, monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["sync_coingecko.py", "--tasks", "not-a-task"],
    )

    assert sync_coingecko.main() == 1


def test_multiple_tasks_run_in_order(app, monkeypatch):
    calls = []

    monkeypatch.setitem(
        sync_coingecko.TASKS,
        "trending",
        lambda: calls.append("trending"),
    )
    monkeypatch.setitem(
        sync_coingecko.TASKS,
        "categories",
        lambda: calls.append("categories"),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["sync_coingecko.py", "--tasks", "trending,categories"],
    )

    assert sync_coingecko.main() == 0
    assert calls == ["trending", "categories"]


def test_sync_markets_writes_markets_and_global(app, monkeypatch):
    monkeypatch.setattr(
        sync_coingecko.cg_client,
        "get_market_data",
        lambda **kwargs: [{"id": "bitcoin"}],
    )
    monkeypatch.setattr(
        sync_coingecko.cg_client,
        "get_global",
        lambda: {"data": {"markets": 1}},
    )

    sync_coingecko.sync_markets(vs_currency="usd", limit=10, page=1)

    from services import cache_keys, cache_store

    markets = cache_store.get(cache_keys.markets_key("usd", 10, 1))
    global_entry = cache_store.get(cache_keys.global_key())
    assert markets is not None
    assert markets.payload[0]["id"] == "bitcoin"
    assert global_entry is not None
    assert global_entry.payload["data"]["markets"] == 1


def test_sync_trending_writes_cache(app, monkeypatch):
    monkeypatch.setattr(
        sync_coingecko.cg_client,
        "get_trending",
        lambda: {"coins": [{"item": {"id": "solana"}}]},
    )

    sync_coingecko.sync_trending()

    from services import cache_keys, cache_store

    entry = cache_store.get(cache_keys.trending_key())
    assert entry is not None
    assert entry.payload["coins"][0]["item"]["id"] == "solana"
