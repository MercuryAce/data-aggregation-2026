"""T5: Messari routes — assets, exchanges, timeseries wiring."""

from __future__ import annotations

from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc)


def test_asset_detail_loads_url_slug(client, no_request_guard, monkeypatch, app):
    from app import cache

    cache.clear()
    details_calls = []

    def fake_details(slugs):
        details_calls.append(slugs)
        return {"data": [{"slug": slugs}]}, _now()

    monkeypatch.setattr("blueprints.messari.get_asset_details", fake_details)

    response = client.get("/messari/asset/solana")
    assert response.status_code == 200
    assert details_calls == ["solana"]
    assert b"solana" in response.data


def test_index_loads_assets_and_details(client, no_request_guard, monkeypatch, app):
    from app import cache

    cache.clear()

    monkeypatch.setattr(
        "blueprints.messari.get_assets",
        lambda limit=20, page=1: ({"data": [{"slug": "bitcoin"}]}, _now()),
    )
    monkeypatch.setattr(
        "blueprints.messari.get_asset_details",
        lambda slugs: ({"data": [{"slug": "bitcoin"}]}, _now()),
    )

    response = client.get("/messari/")
    assert response.status_code == 200
    assert b"bitcoin" in response.data
    assert b"Assets" in response.data


def test_exchanges_and_timeseries_routes(client, no_request_guard, monkeypatch, app):
    from app import cache

    cache.clear()
    monkeypatch.setattr(
        "blueprints.messari.get_exchanges",
        lambda limit=100, page=1: ({"data": [{"id": "binance"}]}, _now()),
    )
    monkeypatch.setattr(
        "blueprints.messari.get_exchange",
        lambda exchange_id: ({"id": exchange_id}, _now()),
    )
    monkeypatch.setattr(
        "blueprints.messari.get_asset_timeseries",
        lambda slug, metric, granularity: (
            {"points": [[1, 2]]},
            _now(),
        ),
    )

    assert client.get("/messari/exchanges").status_code == 200
    assert b"binance" in client.get("/messari/exchanges").data
    assert client.get("/messari/exchange/binance").status_code == 200
    ts = client.get("/messari/asset/bitcoin/timeseries/price/1d")
    assert ts.status_code == 200
    assert b"points" in ts.data
