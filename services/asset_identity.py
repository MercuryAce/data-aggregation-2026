"""Provider-agnostic asset identity helpers (chains, contracts, quote keys)."""

from __future__ import annotations

# Prefer these CG platforms when choosing a primary contract.
PRIMARY_CHAIN_PREFERENCE = (
    "ethereum",
    "solana",
    "base",
    "binance-smart-chain",
    "arbitrum-one",
    "polygon-pos",
    "avalanche",
    "optimistic-ethereum",
    "tron",
    "fantom",
    "cronos",
    "celo",
    "moonbeam",
    "linea",
    "scroll",
    "zksync",
    "sui",
    "aptos",
    "near-protocol",
)

# CoinGecko platform id → DefiLlama coins API chain prefix.
# Extend when adding quote providers; keep CG ids as the source of truth in `platforms`.
CG_PLATFORM_TO_DEFILLAMA = {
    "ethereum": "ethereum",
    "binance-smart-chain": "bsc",
    "polygon-pos": "polygon",
    "arbitrum-one": "arbitrum",
    "optimistic-ethereum": "optimism",
    "avalanche": "avax",
    "base": "base",
    "solana": "solana",
    "tron": "tron",
    "fantom": "fantom",
    "cronos": "cronos",
    "celo": "celo",
    "moonbeam": "moonbeam",
    "linea": "linea",
    "scroll": "scroll",
    "zksync": "era",
    "polygon-zkevm": "polygon_zkevm",
    "manta-pacific": "manta",
    "blast": "blast",
    "mode": "mode",
    "gnosis": "xdai",
    "xdai": "xdai",
}


def normalize_platforms(raw) -> dict[str, str]:
    """Return {platform: address} with empty addresses dropped."""
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for chain, addr in raw.items():
        if not chain or addr is None:
            continue
        text = str(addr).strip()
        if text:
            out[str(chain)] = text
    return out


def pick_primary_chain(platforms: dict[str, str]) -> str | None:
    if not platforms:
        return None
    for chain in PRIMARY_CHAIN_PREFERENCE:
        if chain in platforms:
            return chain
    return next(iter(platforms.keys()), None)


def merge_external_ids(existing, **updates) -> dict:
    base = dict(existing) if isinstance(existing, dict) else {}
    for key, value in updates.items():
        if value is None or value == "":
            continue
        base[key] = value
    return base


def defillama_quote_key(cg_id: str, platforms: dict[str, str] | None = None) -> str:
    """Build a DefiLlama `coins` API id from generic platforms + cg_id fallback."""
    platforms = platforms or {}
    chain = pick_primary_chain(platforms)
    if chain:
        llama_chain = CG_PLATFORM_TO_DEFILLAMA.get(chain)
        addr = platforms.get(chain)
        if llama_chain and addr:
            return f"{llama_chain}:{addr}"
    return f"coingecko:{cg_id}"
