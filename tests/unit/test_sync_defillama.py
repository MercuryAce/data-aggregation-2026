"""T4: DefiLlama sync script — CLI flags must reach sync helpers."""

from __future__ import annotations

import scripts.sync_defillama as sync_defillama


def test_protocols_task_uses_cli_flags(app, monkeypatch):
    calls = []
    monkeypatch.setitem(
        sync_defillama.TASKS,
        "protocols",
        lambda: calls.append({"protocols": True}),
    )
    monkeypatch.setattr("sys.argv", ["sync_defillama.py", "--tasks", "protocols"])

    assert sync_defillama.main() == 0
    assert calls == [{"protocols": True}]


def test_protocol_task_uses_cli_flags(app, monkeypatch):
    calls = []
    monkeypatch.setattr(
        sync_defillama,
        "sync_protocol",
        lambda protocol: calls.append({"protocol": protocol}),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["sync_defillama.py", "--tasks", "protocol", "--protocol", "aave"],
    )

    assert sync_defillama.main() == 0
    assert calls == [{"protocol": "aave"}]


def test_historical_chain_tvl_task_needs_no_chain(app, monkeypatch):
    calls = []
    monkeypatch.setitem(
        sync_defillama.TASKS,
        "historical_chain_tvl",
        lambda: calls.append({"all_chains": True}),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["sync_defillama.py", "--tasks", "historical-chain-tvl"],
    )

    assert sync_defillama.main() == 0
    assert calls == [{"all_chains": True}]


def test_historical_chain_tvl_by_chain_task_uses_cli_flags(app, monkeypatch):
    calls = []
    monkeypatch.setattr(
        sync_defillama,
        "sync_historical_chain_tvl_by_chain",
        lambda chain: calls.append({"chain": chain}),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "sync_defillama.py",
            "--tasks",
            "historical_chain_tvl_by_chain",
            "--chain",
            "Ethereum",
        ],
    )

    assert sync_defillama.main() == 0
    assert calls == [{"chain": "Ethereum"}]


def test_sync_protocols_writes_cache(app, monkeypatch):
    monkeypatch.setattr(
        sync_defillama.defillama_client,
        "get_protocols",
        lambda: [{"id": "1", "name": "Protocol 1"}],
    )

    sync_defillama.sync_protocols()

    from services import cache_store, defillama_cache_keys

    entry = cache_store.get(defillama_cache_keys.protocols_key())
    assert entry is not None
    assert entry.payload[0]["name"] == "Protocol 1"
