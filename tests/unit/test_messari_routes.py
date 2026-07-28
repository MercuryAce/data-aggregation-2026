"""T5 (partial): Messari routes — slug and cache dependencies."""

from __future__ import annotations

from datetime import datetime, timezone


def test_asset_detail_loads_url_slug(client, no_request_guard, monkeypatch, app):
    from app import cache

    cache.clear()
    details_calls = []

    def fake_details(slugs):
        details_calls.append(slugs)
        return {"data": [{"slug": slugs}]}, datetime.now(timezone.utc)

    monkeypatch.setattr("blueprints.messari.get_asset_details", fake_details)

    response = client.get("/messari/asset/solana")

    assert response.status_code == 200
    assert details_calls == ["solana"]
    assert b"solana" in response.data


def test_index_loads_default_detail_slugs(client, no_request_guard, monkeypatch, app):
    """Index only needs details cache — must not depend on assets sync."""
    from app import cache

    cache.clear()
    details_calls = []

    def fake_details(slugs):
        details_calls.append(slugs)
        return {"data": [{"slug": "bitcoin"}]}, datetime.now(timezone.utc)

    monkeypatch.setattr("blueprints.messari.get_asset_details", fake_details)

    response = client.get("/messari/")

    assert response.status_code == 200
    assert details_calls == ["bitcoin,ethereum"]
    assert b"bitcoin" in response.data
