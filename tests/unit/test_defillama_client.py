"""T1: DefiLlama HTTP client — multi-host URLs (mocked)."""

from __future__ import annotations

import pytest
import responses
from requests.exceptions import HTTPError

from clients import defillama_client as c


@responses.activate
def test_get_protocols_uses_api_host():
    url = c._url("api", "protocols")
    responses.add(responses.GET, url, json=[{"slug": "aave"}], status=200)
    assert c.get_protocols() == [{"slug": "aave"}]
    assert "api.llama.fi" in responses.calls[0].request.url


@responses.activate
def test_get_protocol_and_chains():
    responses.add(
        responses.GET, c._url("api", "protocol/aave"), json={"name": "Aave"}, status=200
    )
    responses.add(
        responses.GET, c._url("api", "v2/chains"), json=[{"name": "Ethereum"}], status=200
    )
    assert c.get_protocol("aave")["name"] == "Aave"
    assert c.get_chains()[0]["name"] == "Ethereum"


@responses.activate
def test_historical_tvl_endpoints():
    responses.add(
        responses.GET,
        c._url("api", "v2/historicalChainTvl"),
        json=[{"tvl": 1}],
        status=200,
    )
    responses.add(
        responses.GET,
        c._url("api", "v2/historicalChainTvl/Ethereum"),
        json=[{"tvl": 2}],
        status=200,
    )
    assert c.get_historical_chain_tvl()[0]["tvl"] == 1
    assert c.get_historical_chain_tvl_by_chain("Ethereum")[0]["tvl"] == 2


@responses.activate
def test_coins_stablecoins_yields_bridges_hosts():
    responses.add(
        responses.GET,
        c._url("coins", "prices/current/ethereum:0x0"),
        json={"coins": {}},
        status=200,
    )
    responses.add(
        responses.GET,
        c._url("stablecoins", "stablecoins"),
        json={"peggedAssets": []},
        status=200,
    )
    responses.add(
        responses.GET, c._url("yields", "pools"), json={"data": []}, status=200
    )
    responses.add(
        responses.GET, c._url("bridges", "bridges"), json={"bridges": []}, status=200
    )

    assert "coins" in c.get_current_prices("ethereum:0x0")
    assert c.get_stablecoins()["peggedAssets"] == []
    assert c.get_pools()["data"] == []
    assert c.get_bridges()["bridges"] == []


@responses.activate
def test_dexs_and_fees():
    responses.add(
        responses.GET, c._url("api", "overview/dexs"), json={"total24h": 1}, status=200
    )
    responses.add(
        responses.GET, c._url("api", "overview/fees"), json={"total24h": 2}, status=200
    )
    assert c.get_dexs()["total24h"] == 1
    assert c.get_fees()["total24h"] == 2


@responses.activate
def test_http_error_raises():
    responses.add(responses.GET, c._url("api", "protocols"), status=400)
    with pytest.raises(HTTPError):
        c.get_protocols()
