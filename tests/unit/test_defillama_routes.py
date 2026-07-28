"""T5 (partial): DefiLlama routes — service wiring."""

from __future__ import annotations

from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc)


def test_index_renders(client, no_request_guard, app):
    from app import cache

    cache.clear()
    response = client.get("/defillama/")
    assert response.status_code == 200
    assert b"DefiLlama" in response.data


def test_protocols_loads_cache(client, no_request_guard, monkeypatch, app):
    from app import cache

    cache.clear()

    monkeypatch.setattr(
        "blueprints.defillama.svc.get_protocols",
        lambda: ([{"name": "Protocol 1"}], _now()),
    )

    response = client.get("/defillama/protocols")
    assert response.status_code == 200
    assert b"Protocol 1" in response.data


def test_protocol_and_chains_routes(client, no_request_guard, monkeypatch, app):
    from app import cache

    cache.clear()
    monkeypatch.setattr(
        "blueprints.defillama.svc.get_protocol",
        lambda protocol: ({"name": protocol}, _now()),
    )
    monkeypatch.setattr(
        "blueprints.defillama.svc.get_chains",
        lambda: ([{"name": "Ethereum"}], _now()),
    )

    assert client.get("/defillama/protocol/aave").status_code == 200
    assert b"aave" in client.get("/defillama/protocol/aave").data
    assert client.get("/defillama/v2/chains").status_code == 200
    assert b"Ethereum" in client.get("/defillama/chains").data


def test_dexs_fees_bridges_routes(client, no_request_guard, monkeypatch, app):
    from app import cache

    cache.clear()
    monkeypatch.setattr(
        "blueprints.defillama.svc.get_dexs", lambda: ({"total24h": 11}, _now())
    )
    monkeypatch.setattr(
        "blueprints.defillama.svc.get_fees", lambda: ({"total24h": 22}, _now())
    )
    monkeypatch.setattr(
        "blueprints.defillama.svc.get_bridges",
        lambda: ({"bridges": [{"name": "Portal"}]}, _now()),
    )

    assert b"11" in client.get("/defillama/overview/dexs").data
    assert b"22" in client.get("/defillama/fees").data
    assert b"Portal" in client.get("/defillama/bridges").data
