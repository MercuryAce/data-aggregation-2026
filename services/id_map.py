"""Cross-source asset identity map (CG / CMC / Messari / DefiLlama)."""

from __future__ import annotations

from services import cache_keys, cache_store, cmc_service
from services.cache_store import CacheMissError

ID_MAP_KEY = "asset_id_map"
ID_MAP_TTL = 24 * 60 * 60


def _empty_map() -> dict:
    return {
        "by_cg_id": {},
        "by_cmc_slug": {},
        "by_symbol": {},
        "by_messari_slug": {},
    }


def get_id_map() -> dict:
    entry = cache_store.get(ID_MAP_KEY)
    if entry is None:
        return _empty_map()
    payload = entry.payload
    if not isinstance(payload, dict):
        return _empty_map()
    return payload


def save_id_map(payload: dict) -> None:
    cache_store.set(ID_MAP_KEY, payload, ttl_seconds=ID_MAP_TTL, source="mashup")


def build_id_map() -> dict:
    """Rebuild map from CMC map + CG markets pages when available."""
    mapping = _empty_map()

    # CMC map: slug / symbol / id
    try:
        cmc_map, _ = cmc_service.get_map()
        rows = cmc_map.get("data") if isinstance(cmc_map, dict) else cmc_map
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            slug = (row.get("slug") or "").lower()
            symbol = (row.get("symbol") or "").upper()
            cmc_id = row.get("id")
            entry = {
                "cmc_id": cmc_id,
                "cmc_slug": slug,
                "symbol": symbol,
                "name": row.get("name"),
                "messari_slug": slug,
            }
            if slug:
                mapping["by_cmc_slug"][slug] = entry
                mapping["by_messari_slug"][slug] = entry
            if symbol:
                mapping["by_symbol"].setdefault(symbol, entry)
    except CacheMissError:
        pass

    # CG markets: join by symbol (and slug==id when possible)
    for page in range(1, 11):
        try:
            entry = cache_store.get(cache_keys.markets_key("usd", 250, page))
        except Exception:
            entry = None
        if entry is None:
            continue
        for coin in entry.payload or []:
            if not isinstance(coin, dict):
                continue
            cg_id = coin.get("id")
            symbol = (coin.get("symbol") or "").upper()
            if not cg_id:
                continue
            base = mapping["by_symbol"].get(symbol) or mapping["by_cmc_slug"].get(cg_id) or {}
            platforms = coin.get("platforms") or {}
            contracts = []
            if isinstance(platforms, dict):
                for chain, addr in platforms.items():
                    if addr:
                        contracts.append(f"{chain}:{addr}")
            row = {
                **base,
                "cg_id": cg_id,
                "symbol": symbol or base.get("symbol"),
                "name": coin.get("name") or base.get("name"),
                "image": coin.get("image"),
                "contracts": contracts,
                "messari_slug": base.get("messari_slug") or cg_id,
                "cmc_slug": base.get("cmc_slug"),
                "cmc_id": base.get("cmc_id"),
                "defillama_coin": f"coingecko:{cg_id}",
            }
            mapping["by_cg_id"][cg_id] = row
            if row.get("cmc_slug"):
                mapping["by_cmc_slug"][row["cmc_slug"]] = row
            if symbol:
                mapping["by_symbol"][symbol] = row
            if row.get("messari_slug"):
                mapping["by_messari_slug"][row["messari_slug"]] = row

    save_id_map(mapping)
    return mapping


def resolve_cg(cg_id: str) -> dict:
    mapping = get_id_map()
    return mapping.get("by_cg_id", {}).get(cg_id) or {"cg_id": cg_id}


def resolve_symbol(symbol: str) -> dict:
    mapping = get_id_map()
    return mapping.get("by_symbol", {}).get((symbol or "").upper()) or {}
