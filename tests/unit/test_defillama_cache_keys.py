"""T2 (partial): DefiLlama cache key builders."""

from services import defillama_cache_keys as keys


def test_core_keys():
    assert keys.protocols_key() == "defillama_protocols"
    assert keys.protocol_key("aave") == "defillama_protocol_aave"
    assert keys.historical_chain_tvl_key() == "defillama_historical_chain_tvl"
    assert (
        keys.historical_chain_tvl_by_chain_key("Ethereum")
        == "defillama_historical_chain_tvl_by_chain_Ethereum"
    )
    assert keys.chains_key() == "defillama_chains"


def test_market_keys():
    assert keys.stablecoins_key() == "defillama_stablecoins"
    assert keys.pools_key() == "defillama_pools"
    assert keys.bridges_key() == "defillama_bridges"
    assert keys.dexs_key() == "defillama_dexs"
    assert keys.fees_key() == "defillama_fees"
    assert keys.dexs_by_chain_key("Ethereum") == "defillama_dexs_Ethereum"
