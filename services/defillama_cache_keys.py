"""DefiLlama cache keys."""


def protocols_key() -> str:
    return "defillama_protocols"


def protocol_key(protocol: str) -> str:
    return f"defillama_protocol_{protocol}"


def historical_chain_tvl_key() -> str:
    return "defillama_historical_chain_tvl"


def historical_chain_tvl_by_chain_key(chain: str) -> str:
    return f"defillama_historical_chain_tvl_by_chain_{chain}"


def chains_key() -> str:
    return "defillama_chains"


def current_prices_key(coins: str) -> str:
    return f"defillama_prices_current_{coins.replace(':', '_').replace(',', '_')}"


def historical_prices_key(timestamp, coins: str) -> str:
    return (
        f"defillama_prices_hist_{timestamp}_"
        f"{coins.replace(':', '_').replace(',', '_')}"
    )


def stablecoins_key() -> str:
    return "defillama_stablecoins"


def stablecoin_key(asset_id) -> str:
    return f"defillama_stablecoin_{asset_id}"


def stablecoin_charts_all_key() -> str:
    return "defillama_stablecoin_charts_all"


def stablecoin_charts_chain_key(chain: str) -> str:
    return f"defillama_stablecoin_charts_{chain}"


def stablecoin_chains_key() -> str:
    return "defillama_stablecoin_chains"


def stablecoin_prices_key() -> str:
    return "defillama_stablecoin_prices"


def pools_key() -> str:
    return "defillama_pools"


def pool_chart_key(pool: str) -> str:
    return f"defillama_pool_chart_{pool}"


def bridges_key() -> str:
    return "defillama_bridges"


def bridge_key(bridge_id) -> str:
    return f"defillama_bridge_{bridge_id}"


def bridge_volume_key(chain: str) -> str:
    return f"defillama_bridge_volume_{chain}"


def dexs_key() -> str:
    return "defillama_dexs"


def dexs_by_chain_key(chain: str) -> str:
    return f"defillama_dexs_{chain}"


def dex_summary_key(protocol: str) -> str:
    return f"defillama_dex_summary_{protocol}"


def options_key() -> str:
    return "defillama_options"


def fees_key() -> str:
    return "defillama_fees"


def fees_by_chain_key(chain: str) -> str:
    return f"defillama_fees_{chain}"


def fees_by_protocol_key(protocol: str) -> str:
    return f"defillama_fees_protocol_{protocol}"
