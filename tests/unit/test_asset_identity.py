"""Generic asset identity helpers."""

from __future__ import annotations

from services.asset_identity import (
    defillama_quote_key,
    merge_external_ids,
    normalize_platforms,
    pick_primary_chain,
)


def test_normalize_and_primary():
    platforms = normalize_platforms(
        {
            "solana": "So111",
            "ethereum": "0xA0b8",
            "binance-smart-chain": "",
        }
    )
    assert platforms == {"solana": "So111", "ethereum": "0xA0b8"}
    assert pick_primary_chain(platforms) == "ethereum"


def test_defillama_quote_key_prefers_contract():
    key = defillama_quote_key(
        "usd-coin",
        {"ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"},
    )
    assert key == "ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"


def test_defillama_quote_key_maps_bsc_and_fallback():
    assert (
        defillama_quote_key("binancecoin", {"binance-smart-chain": "0xbb4"})
        == "bsc:0xbb4"
    )
    assert defillama_quote_key("bitcoin", {}) == "coingecko:bitcoin"


def test_merge_external_ids():
    merged = merge_external_ids({"coingecko": "btc"}, cmc=1, cmc_slug="bitcoin")
    assert merged == {"coingecko": "btc", "cmc": 1, "cmc_slug": "bitcoin"}
