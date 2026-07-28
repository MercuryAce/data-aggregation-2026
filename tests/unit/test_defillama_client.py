"""T1: DefiLlama HTTP client — URL/query/headers (mocked)."""

from __future__ import annotations

import pytest
import responses
from requests.exceptions import HTTPError

from clients import defillama_client

BASE = defillama_client.BASE_URL


@responses.activate
def test_get_protocols_builds_query_and_returns_json():
    payload = [{"id": "1", "name": "Protocol 1", "slug": "protocol-1"}]
    responses.add(
        responses.GET,
        f"{BASE}/protocols",
        json=payload,
        status=200,
    )
    result = defillama_client.get_protocols()
    assert result == payload
    assert len(responses.calls) == 1
    assert responses.calls[0].request.headers.get("accept") == "application/json"


@responses.activate
def test_get_protocol_path_includes_slug():
    payload = {"id": "1", "name": "Aave", "slug": "aave"}
    responses.add(
        responses.GET,
        f"{BASE}/protocol/aave",
        json=payload,
        status=200,
    )
    assert defillama_client.get_protocol("aave") == payload


@responses.activate
def test_get_historical_chain_tvl_all_chains():
    payload = [{"date": 1, "tvl": 100.0}]
    responses.add(
        responses.GET,
        f"{BASE}/v2/historicalChainTvl",
        json=payload,
        status=200,
    )
    assert defillama_client.get_historical_chain_tvl() == payload


@responses.activate
def test_get_historical_chain_tvl_by_chain():
    payload = [{"date": 1, "tvl": 50.0}]
    responses.add(
        responses.GET,
        f"{BASE}/v2/historicalChainTvl/Ethereum",
        json=payload,
        status=200,
    )
    assert defillama_client.get_historical_chain_tvl_by_chain("Ethereum") == payload


@responses.activate
def test_http_error_raises():
    responses.add(responses.GET, f"{BASE}/protocols", status=400)
    with pytest.raises(HTTPError):
        defillama_client.get_protocols()
