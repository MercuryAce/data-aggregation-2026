"""T1: CoinGecko HTTP client — URL/query/headers (mocked)."""

from __future__ import annotations

import pytest
import responses
from requests.exceptions import HTTPError

from clients import cg_client

BASE = cg_client.BASE_URL


@responses.activate
def test_get_market_data_builds_query():
    responses.add(
        responses.GET,
        f"{BASE}/coins/markets",
        json=[{"id": "bitcoin"}],
        status=200,
    )

    result = cg_client.get_market_data(vs_currency="usd", limit=10, page=2)

    assert result == [{"id": "bitcoin"}]
    url = responses.calls[0].request.url
    assert "vs_currency=usd" in url
    assert "per_page=10" in url
    assert "page=2" in url


@responses.activate
def test_get_coin_details_path_includes_id():
    responses.add(
        responses.GET,
        f"{BASE}/coins/bitcoin",
        json={"id": "bitcoin"},
        status=200,
    )

    assert cg_client.get_coin_details("bitcoin")["id"] == "bitcoin"


@responses.activate
def test_get_global_and_trending():
    responses.add(responses.GET, f"{BASE}/global", json={"data": {}}, status=200)
    responses.add(
        responses.GET,
        f"{BASE}/search/trending",
        json={"coins": []},
        status=200,
    )

    assert cg_client.get_global() == {"data": {}}
    assert cg_client.get_trending() == {"coins": []}


@responses.activate
def test_get_ohlc_builds_query():
    responses.add(
        responses.GET,
        f"{BASE}/coins/ethereum/ohlc",
        json=[[1, 2, 3, 4, 5]],
        status=200,
    )

    result = cg_client.get_ohlc("ethereum", days=7, vs_currency="usd")
    assert result == [[1, 2, 3, 4, 5]]
    url = responses.calls[0].request.url
    assert "days=7" in url
    assert "vs_currency=usd" in url


@responses.activate
def test_get_search_and_exchanges():
    responses.add(
        responses.GET,
        f"{BASE}/search",
        json={"coins": []},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/exchanges",
        json=[{"id": "binance"}],
        status=200,
    )

    assert cg_client.get_search("btc") == {"coins": []}
    assert "query=btc" in responses.calls[0].request.url

    assert cg_client.get_exchanges(per_page=50, page=1)[0]["id"] == "binance"
    assert "per_page=50" in responses.calls[1].request.url


@responses.activate
def test_http_error_raises():
    responses.add(responses.GET, f"{BASE}/global", json={"error": "no"}, status=404)

    with pytest.raises(HTTPError):
        cg_client.get_global()


@responses.activate
def test_accept_header_sent():
    responses.add(responses.GET, f"{BASE}/ping", json={}, status=200)

    cg_client.ping()
    assert responses.calls[0].request.headers.get("accept") == "application/json"
