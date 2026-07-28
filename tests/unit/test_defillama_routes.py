"""T5 (partial): DefiLlama routes — cache dependencies."""

from __future__ import annotations

from datetime import datetime, timezone


def test_protocols_loads_cache(client, no_request_guard, monkeypatch, app):
    from app import cache

    cache.clear()
    protocols_calls = []

    def fake_protocols():
        protocols_calls.append(1)
        return [{"id": "1", "name": "Protocol 1"}], datetime.now(timezone.utc)

    monkeypatch.setattr("blueprints.defillama.get_protocols", fake_protocols)

    response = client.get("/defillama/protocols")

    assert response.status_code == 200
    assert protocols_calls == [1]
    assert b"Protocol 1" in response.data


def test_protocol_loads_cache(client, no_request_guard, monkeypatch, app):
    from app import cache

    cache.clear()
    protocol_calls = []

    def fake_protocol(protocol: str):
        protocol_calls.append(protocol)
        return {"id": "1", "name": "Protocol 1"}, datetime.now(timezone.utc)

    monkeypatch.setattr("blueprints.defillama.get_protocol", fake_protocol)

    response = client.get("/defillama/protocol/aave")

    assert response.status_code == 200
    assert protocol_calls == ["aave"]
    assert b"Protocol 1" in response.data


def test_historical_chain_tvl_loads_cache(client, no_request_guard, monkeypatch, app):
    from app import cache

    cache.clear()
    calls = []

    def fake_historical_chain_tvl():
        calls.append(1)
        return [{"date": 1, "tvl": 100}], datetime.now(timezone.utc)

    monkeypatch.setattr(
        "blueprints.defillama.get_historical_chain_tvl",
        fake_historical_chain_tvl,
    )

    response = client.get("/defillama/historical-chain-tvl")

    assert response.status_code == 200
    assert calls == [1]
    assert b"100" in response.data


def test_historical_chain_tvl_by_chain_loads_cache(
    client, no_request_guard, monkeypatch, app
):
    from app import cache

    cache.clear()
    calls = []

    def fake_historical_chain_tvl_by_chain(chain: str):
        calls.append(chain)
        return [{"date": 1, "tvl": 50}], datetime.now(timezone.utc)

    monkeypatch.setattr(
        "blueprints.defillama.get_historical_chain_tvl_by_chain",
        fake_historical_chain_tvl_by_chain,
    )

    response = client.get("/defillama/historical-chain-tvl/Ethereum")

    assert response.status_code == 200
    assert calls == ["Ethereum"]
    assert b"50" in response.data
