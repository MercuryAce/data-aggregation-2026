"""T4: Messari sync script — CLI flags must reach sync helpers."""

from __future__ import annotations

import scripts.sync_messari as sync_messari


def test_exchanges_task_uses_cli_limit_and_page(app, monkeypatch):
    calls = []

    monkeypatch.setattr(
        sync_messari,
        "sync_exchanges",
        lambda limit=100, page=1: calls.append({"limit": limit, "page": page}),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["sync_messari.py", "--tasks", "exchanges", "--limit", "50", "--page", "3"],
    )

    assert sync_messari.main() == 0
    assert calls == [{"limit": 50, "page": 3}]


def test_assets_task_uses_cli_limit_and_page(app, monkeypatch):
    calls = []

    monkeypatch.setattr(
        sync_messari,
        "sync_assets",
        lambda limit=20, page=1: calls.append({"limit": limit, "page": page}),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["sync_messari.py", "--tasks", "assets", "--limit", "15", "--page", "2"],
    )

    assert sync_messari.main() == 0
    assert calls == [{"limit": 15, "page": 2}]


def test_sync_exchanges_writes_cache_with_limit_page(app, monkeypatch):
    monkeypatch.setattr(
        sync_messari.messari_client,
        "get_exchanges",
        lambda limit=100, page=1: {"data": [{"id": "binance"}], "limit": limit, "page": page},
    )

    sync_messari.sync_exchanges(limit=50, page=2)

    from services import cache_store, messari_cache_keys

    entry = cache_store.get(messari_cache_keys.exchanges_key(50, 2))
    assert entry is not None
    assert entry.payload["limit"] == 50
    assert entry.payload["page"] == 2
