"""DefiLlama cache keys."""


def protocols_key() -> str:
    return "defillama_protocols"


def protocol_key(protocol: str) -> str:
    return f"defillama_protocol_{protocol}"


def historical_chain_tvl_key() -> str:
    return "defillama_historical_chain_tvl"


def historical_chain_tvl_by_chain_key(chain: str) -> str:
    return f"defillama_historical_chain_tvl_by_chain_{chain}"
