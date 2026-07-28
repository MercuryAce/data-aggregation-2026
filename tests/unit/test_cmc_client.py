"""CMC client query construction."""

from __future__ import annotations

from clients import cmc_client


def test_get_listings_latest_builds_query(monkeypatch):
    captured = {}

    def fake_call(path, params=None):
        captured["path"] = path
        captured["params"] = params
        return {"data": []}

    monkeypatch.setattr(cmc_client, "_call", fake_call)
    result = cmc_client.get_listings_latest(start=1, limit=50, convert="USD")
    assert result == {"data": []}
    assert captured["path"] == "cryptocurrency/listings/latest"
    assert captured["params"]["limit"] == 50
    assert captured["params"]["start"] == 1


def test_get_map_builds_query(monkeypatch):
    captured = {}

    def fake_call(path, params=None):
        captured["path"] = path
        captured["params"] = params
        return {"data": []}

    monkeypatch.setattr(cmc_client, "_call", fake_call)
    cmc_client.get_cryptocurrency_map(limit=100)
    assert captured["path"] == "cryptocurrency/map"
    assert captured["params"]["limit"] == 100
