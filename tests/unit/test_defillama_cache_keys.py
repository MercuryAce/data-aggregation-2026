"""T2 (partial): DefiLlama cache key builders."""

from services import defillama_cache_keys as keys


def test_protocols_key():
    assert keys.protocols_key() == "defillama_protocols"


def test_protocol_key():
    assert keys.protocol_key("aave") == "defillama_protocol_aave"


def test_historical_chain_tvl_key():
    assert keys.historical_chain_tvl_key() == "defillama_historical_chain_tvl"


def test_historical_chain_tvl_by_chain_key():
    assert (
        keys.historical_chain_tvl_by_chain_key("Ethereum")
        == "defillama_historical_chain_tvl_by_chain_Ethereum"
    )
