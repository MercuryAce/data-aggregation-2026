"""T1: Messari HTTP client — URL/query/headers and error mapping (mocked)."""

from __future__ import annotations

import json

import pytest
import responses
from requests.exceptions import HTTPError

from clients import messari_client


BASE = messari_client.BASE_URL


@responses.activate
def test_get_assets_builds_query_and_returns_json():
    payload = {"data": [{"slug": "bitcoin"}]}
    responses.add(
        responses.GET,
        f"{BASE}/metrics/v2/assets",
        json=payload,
        status=200,
    )

    result = messari_client.get_assets(limit=10, page=2)

    assert result == payload
    assert len(responses.calls) == 1
    request = responses.calls[0].request
    assert "limit=10" in request.url
    assert "page=2" in request.url
    assert request.headers.get("accept") == "application/json"


@responses.activate
def test_get_asset_details_passes_assets_param():
    responses.add(
        responses.GET,
        f"{BASE}/metrics/v2/assets/details",
        json={"data": []},
        status=200,
    )

    messari_client.get_asset_details("solana")

    assert "assets=solana" in responses.calls[0].request.url


@responses.activate
def test_get_asset_timeseries_path_includes_slug_metric_granularity():
    responses.add(
        responses.GET,
        f"{BASE}/metrics/v2/assets/bitcoin/metrics/price/time-series/1d",
        json={"data": []},
        status=200,
    )

    result = messari_client.get_asset_timeseries("bitcoin", "price", "1d")

    assert result == {"data": []}
    assert len(responses.calls) == 1


@responses.activate
def test_get_exchanges_builds_limit_and_page():
    responses.add(
        responses.GET,
        f"{BASE}/metrics/v1/exchanges",
        json={"data": []},
        status=200,
    )

    messari_client.get_exchanges(limit=50, page=3)

    url = responses.calls[0].request.url
    assert "limit=50" in url
    assert "page=3" in url


@responses.activate
def test_get_exchange_path_includes_id():
    responses.add(
        responses.GET,
        f"{BASE}/metrics/v1/exchanges/binance",
        json={"data": {"id": "binance"}},
        status=200,
    )

    result = messari_client.get_exchange("binance")

    assert result["data"]["id"] == "binance"


@responses.activate
def test_http_error_raises():
    responses.add(
        responses.GET,
        f"{BASE}/metrics/v2/assets",
        json={"error": "nope"},
        status=404,
    )

    with pytest.raises(HTTPError):
        messari_client.get_assets()


@responses.activate
def test_api_key_header_sent_when_configured(monkeypatch):
    monkeypatch.setattr(messari_client, "API_KEY", "test-key")
    monkeypatch.setattr(
        messari_client,
        "headers",
        {
            "accept": "application/json",
            messari_client.API_KEY_HEADER: "test-key",
        },
    )
    responses.add(
        responses.GET,
        f"{BASE}/metrics/v2/assets/metrics",
        json={},
        status=200,
    )

    messari_client.get_asset_metrics_catalog()

    assert (
        responses.calls[0].request.headers.get(messari_client.API_KEY_HEADER)
        == "test-key"
    )
