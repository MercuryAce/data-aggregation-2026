"""Unified market mash-up across CG, CMC, DefiLlama, and Messari."""

from __future__ import annotations

from datetime import datetime, timezone

from services import (
    cache_keys,
    cache_store,
    cmc_cache_keys,
    coingecko_service,
    defillama_cache_keys,
    id_map,
    messari_cache_keys,
)
from services.cache_store import CacheMissError
from utils.time_format import human_age

MARKETS_PER_PAGE = 250
MAX_MARKET_PAGES = 10


def _max_dt(*values: datetime | None) -> datetime:
    present = [v for v in values if v is not None]
    if not present:
        return datetime.now(timezone.utc)
    return max(present)


def _cmc_listings(limit: int = 500) -> tuple[list[dict], datetime | None]:
    # Prefer the standard sync key used by sync_cmc (start=1, limit=500)
    for start, lim in ((1, limit), (1, 500), (1, 2500), (1, 100)):
        entry = cache_store.get(cmc_cache_keys.listings_key(start, lim, "USD"))
        if entry is not None:
            payload = entry.payload
            rows = payload.get("data") if isinstance(payload, dict) else payload
            return list(rows or []), entry.fetched_at
    return [], None


def _cg_markets_page(page: int) -> tuple[list[dict], datetime | None]:
    entry = cache_store.get(cache_keys.markets_key("usd", MARKETS_PER_PAGE, page))
    if entry is None:
        return [], None
    return list(entry.payload or []), entry.fetched_at


def _cg_markets_all(pages: int = MAX_MARKET_PAGES) -> tuple[list[dict], datetime | None]:
    coins: list[dict] = []
    fetched_at: datetime | None = None
    for page in range(1, pages + 1):
        rows, at = _cg_markets_page(page)
        if not rows:
            break
        coins.extend(rows)
        fetched_at = _max_dt(fetched_at, at)
    return coins, fetched_at


def _index_cmc_by_symbol(rows: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in rows:
        symbol = (row.get("symbol") or "").upper()
        if symbol and symbol not in out:
            out[symbol] = row
    return out


def _usd_quote(cmc_row: dict) -> dict:
    quote = cmc_row.get("quote") or {}
    return quote.get("USD") or quote.get("usd") or {}


def _mash_row(cg: dict | None, cmc: dict | None, mapping: dict | None = None) -> dict:
    mapping = mapping or {}
    cg = cg or {}
    cmc = cmc or {}
    usd = _usd_quote(cmc) if cmc else {}

    cg_id = cg.get("id") or mapping.get("cg_id")
    symbol = (cmc.get("symbol") or cg.get("symbol") or mapping.get("symbol") or "").lower()
    name = cmc.get("name") or cg.get("name") or mapping.get("name") or symbol

    price = usd.get("price")
    price_source = "cmc" if price is not None else None
    if price is None:
        price = cg.get("current_price")
        price_source = "coingecko" if price is not None else None

    change_24h = usd.get("percent_change_24h")
    if change_24h is None:
        change_24h = cg.get("price_change_percentage_24h")

    market_cap = usd.get("market_cap")
    if market_cap is None:
        market_cap = cg.get("market_cap")

    volume = usd.get("volume_24h")
    if volume is None:
        volume = cg.get("total_volume")

    rank = cmc.get("cmc_rank") or cg.get("market_cap_rank")

    return {
        "id": cg_id or (cmc.get("slug") or symbol),
        "cg_id": cg_id,
        "cmc_id": cmc.get("id") or mapping.get("cmc_id"),
        "cmc_slug": cmc.get("slug") or mapping.get("cmc_slug"),
        "symbol": symbol,
        "name": name,
        "image": cg.get("image") or mapping.get("image"),
        "market_cap_rank": rank,
        "current_price": price,
        "price_change_percentage_24h": change_24h,
        "market_cap": market_cap,
        "total_volume": volume,
        "high_24h": cg.get("high_24h"),
        "low_24h": cg.get("low_24h"),
        "fully_diluted_valuation": cg.get("fully_diluted_valuation")
        or usd.get("fully_diluted_market_cap"),
        "total_supply": cmc.get("total_supply") or cg.get("total_supply"),
        "circulating_supply": cmc.get("circulating_supply") or cg.get("circulating_supply"),
        "price_source": price_source,
        "defillama_coin": mapping.get("defillama_coin"),
        "messari_slug": mapping.get("messari_slug") or cmc.get("slug") or cg_id,
        "tvl": mapping.get("tvl"),
    }


def get_unified_markets(
    *,
    page: int = 1,
    per_page: int = 250,
    max_pages: int = MAX_MARKET_PAGES,
) -> tuple[list[dict], dict]:
    """Return mashed market rows for one UI page plus freshness meta."""
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = MARKETS_PER_PAGE

    cmc_rows, cmc_at = _cmc_listings(limit=per_page * max_pages)
    cg_rows, cg_at = _cg_markets_all(pages=max_pages)
    mapping = id_map.get_id_map()

    if not cmc_rows and not cg_rows:
        raise CacheMissError("No market snapshots available (run sync_cmc / sync_coingecko)")

    cmc_by_symbol = _index_cmc_by_symbol(cmc_rows)
    cg_by_symbol = {
        (c.get("symbol") or "").upper(): c for c in cg_rows if c.get("symbol")
    }
    cg_by_id = {c.get("id"): c for c in cg_rows if c.get("id")}

    # Prefer CMC ranking when present; otherwise CG order
    if cmc_rows:
        ordered = []
        seen = set()
        for cmc in cmc_rows:
            symbol = (cmc.get("symbol") or "").upper()
            slug = (cmc.get("slug") or "").lower()
            mapped = (
                mapping.get("by_cmc_slug", {}).get(slug)
                or mapping.get("by_symbol", {}).get(symbol)
                or {}
            )
            cg = None
            cg_id = mapped.get("cg_id")
            if cg_id and cg_id in cg_by_id:
                cg = cg_by_id[cg_id]
            elif symbol in cg_by_symbol:
                cg = cg_by_symbol[symbol]
            row = _mash_row(cg, cmc, mapped)
            key = row["id"]
            if key in seen:
                continue
            seen.add(key)
            ordered.append(row)
        # Append CG-only leftovers
        for cg in cg_rows:
            if cg.get("id") in seen:
                continue
            symbol = (cg.get("symbol") or "").upper()
            if symbol in seen:
                continue
            mapped = mapping.get("by_cg_id", {}).get(cg.get("id"), {})
            cmc = cmc_by_symbol.get(symbol)
            row = _mash_row(cg, cmc, mapped)
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            ordered.append(row)
    else:
        ordered = []
        for cg in cg_rows:
            mapped = mapping.get("by_cg_id", {}).get(cg.get("id"), {})
            symbol = (cg.get("symbol") or "").upper()
            ordered.append(_mash_row(cg, cmc_by_symbol.get(symbol), mapped))

    # Stable market-cap rank order (None ranks last)
    ordered.sort(
        key=lambda row: (
            row.get("market_cap_rank") is None,
            row.get("market_cap_rank") if row.get("market_cap_rank") is not None else 10**9,
            -(row.get("market_cap") or 0),
        )
    )

    total = len(ordered)
    start = (page - 1) * per_page
    end = start + per_page
    page_rows = ordered[start:end]

    fetched_at = _max_dt(cmc_at, cg_at)
    meta = {
        "last_updated": fetched_at,
        "last_updated_age": human_age(fetched_at),
        "cmc_updated": cmc_at,
        "cg_updated": cg_at,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": max(1, (total + per_page - 1) // per_page),
        "price_source": "cmc" if cmc_rows else "coingecko",
    }
    return page_rows, meta


def get_live_prices(ids: list[str]) -> dict:
    """Return mashed live prices for a list of cg ids / symbols / cmc slugs."""
    cmc_rows, cmc_at = _cmc_listings()
    cmc_by_symbol = _index_cmc_by_symbol(cmc_rows)
    cmc_by_slug = {
        (r.get("slug") or "").lower(): r for r in cmc_rows if r.get("slug")
    }
    mapping = id_map.get_id_map()
    out = {}
    for raw in ids:
        key = (raw or "").strip()
        if not key:
            continue
        mapped = (
            mapping.get("by_cg_id", {}).get(key)
            or mapping.get("by_cmc_slug", {}).get(key.lower())
            or mapping.get("by_symbol", {}).get(key.upper())
            or {}
        )
        symbol = (mapped.get("symbol") or key).upper()
        cmc = (
            cmc_by_slug.get((mapped.get("cmc_slug") or key).lower())
            or cmc_by_symbol.get(symbol)
        )
        usd = _usd_quote(cmc) if cmc else {}
        price = usd.get("price")
        source = "cmc"
        if price is None:
            # optional DefiLlama overlay for coingecko:id
            dl_key = mapped.get("defillama_coin") or f"coingecko:{key}"
            entry = cache_store.get(defillama_cache_keys.current_prices_key(dl_key))
            if entry and isinstance(entry.payload, dict):
                coins = entry.payload.get("coins") or entry.payload
                if isinstance(coins, dict):
                    info = coins.get(dl_key) or next(iter(coins.values()), None)
                    if isinstance(info, dict) and info.get("price") is not None:
                        price = info["price"]
                        source = "defillama"
        out[key] = {
            "price": price,
            "percent_change_24h": usd.get("percent_change_24h"),
            "source": source if price is not None else None,
        }

    return {
        "prices": out,
        "last_updated": cmc_at or datetime.now(timezone.utc),
        "last_updated_age": human_age(cmc_at or datetime.now(timezone.utc)),
    }


def get_unified_coin(coin_id: str) -> tuple[dict, dict]:
    """Mash CG coin detail with CMC quote and optional Messari/DefiLlama."""
    mapping = id_map.resolve_cg(coin_id)
    cmc_rows, cmc_at = _cmc_listings()
    symbol = (mapping.get("symbol") or "").upper()
    cmc = None
    for row in cmc_rows:
        if (row.get("slug") or "").lower() == (mapping.get("cmc_slug") or "").lower():
            cmc = row
            break
        if symbol and (row.get("symbol") or "").upper() == symbol:
            cmc = row
            break

    coin = None
    cg_at = None
    try:
        coin, cg_at = coingecko_service.get_coin_details(coin_id)
    except CacheMissError:
        raise CacheMissError(
            f"Coin detail not synced for {coin_id} (run sync_coingecko --tasks top-coins)"
        )

    usd = _usd_quote(cmc) if cmc else {}
    market_data = dict(coin.get("market_data") or {})
    if usd.get("price") is not None:
        market_data.setdefault("current_price", {})
        if isinstance(market_data["current_price"], dict):
            market_data["current_price"]["usd"] = usd["price"]
        market_data["price_change_percentage_24h"] = usd.get(
            "percent_change_24h",
            market_data.get("price_change_percentage_24h"),
        )
        if usd.get("market_cap") is not None:
            market_data.setdefault("market_cap", {})
            if isinstance(market_data["market_cap"], dict):
                market_data["market_cap"]["usd"] = usd["market_cap"]

    messari = None
    messari_at = None
    slug = mapping.get("messari_slug") or coin_id
    entry = cache_store.get(messari_cache_keys.asset_details_key(slug))
    if entry is not None:
        messari = entry.payload
        messari_at = entry.fetched_at

    tvl = None
    # protocols list may include gecko_id
    protocols_entry = cache_store.get(defillama_cache_keys.protocols_key())
    if protocols_entry and isinstance(protocols_entry.payload, list):
        for proto in protocols_entry.payload:
            if not isinstance(proto, dict):
                continue
            if proto.get("gecko_id") == coin_id or (proto.get("slug") or "") == coin_id:
                tvl = proto.get("tvl")
                break

    coin = dict(coin)
    coin["market_data"] = market_data
    coin["mashup"] = {
        "price_source": "cmc" if usd.get("price") is not None else "coingecko",
        "cmc": cmc,
        "messari": messari,
        "tvl": tvl,
        "mapping": mapping,
    }

    fetched_at = _max_dt(cg_at, cmc_at, messari_at)
    meta = {
        "last_updated": fetched_at,
        "last_updated_age": human_age(fetched_at),
        "price_source": coin["mashup"]["price_source"],
    }
    return coin, meta
