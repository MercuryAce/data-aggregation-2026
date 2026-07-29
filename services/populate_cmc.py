"""Patch live market metrics on MySQL market_coins from CoinMarketCap.

Does not change CoinGecko ranking / identity columns — only price-ish fields.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from clients import cmc_client
from models import MarketCoin, db

logger = logging.getLogger(__name__)

SOURCE = "cmc"
# CMC credits: 1 credit per 200 coins returned — prefer page size 200.
PAGE_SIZE = 200


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _usd_quote(item: dict) -> dict:
    quote = item.get("quote") or {}
    return quote.get("USD") or quote.get("usd") or {}


def fetch_listings(*, start: int = 1, limit: int = 500, convert: str = "USD") -> list[dict]:
    """Fetch listings in credit-efficient pages of 200."""
    collected: list[dict] = []
    remaining = limit
    cursor = start
    while remaining > 0:
        batch = min(PAGE_SIZE, remaining)
        payload = cmc_client.get_listings_latest(
            start=cursor,
            limit=batch,
            convert=convert,
        )
        rows = payload.get("data") or []
        if not rows:
            break
        collected.extend(rows)
        remaining -= len(rows)
        cursor += len(rows)
        if len(rows) < batch:
            break
    return collected


def _match_coin(
    item: dict,
    by_cg_id: dict[str, MarketCoin],
    by_symbol: dict[str, list[MarketCoin]],
) -> MarketCoin | None:
    slug = (item.get("slug") or "").lower()
    if slug and slug in by_cg_id:
        return by_cg_id[slug]

    symbol = (item.get("symbol") or "").upper()
    if not symbol:
        return None
    matches = by_symbol.get(symbol) or []
    if len(matches) == 1:
        return matches[0]
    return None


def patch_market_metrics(*, start: int = 1, limit: int = 500, convert: str = "USD") -> int:
    """UPDATE price / mcap / volume / % on existing market_coins. Returns rows patched."""
    listings = fetch_listings(start=start, limit=limit, convert=convert)
    if not listings:
        logger.warning("CMC listings empty — nothing to patch")
        return 0

    coins = db.session.query(MarketCoin).all()
    if not coins:
        logger.warning("market_coins empty — run CG populate first")
        return 0

    by_cg_id = {c.cg_id: c for c in coins}
    by_symbol: dict[str, list[MarketCoin]] = {}
    for coin in coins:
        sym = (coin.symbol or "").upper()
        if sym:
            by_symbol.setdefault(sym, []).append(coin)

    now = _utcnow()
    updated = 0
    for item in listings:
        coin = _match_coin(item, by_cg_id, by_symbol)
        if coin is None:
            continue

        usd = _usd_quote(item)
        price = usd.get("price")
        if price is not None:
            coin.current_price = float(price)

        change = usd.get("percent_change_24h")
        if change is not None:
            coin.price_change_percentage_24h = float(change)

        mcap = usd.get("market_cap")
        if mcap is not None:
            coin.market_cap = float(mcap)

        volume = usd.get("volume_24h")
        if volume is not None:
            coin.total_volume = float(volume)

        fdv = usd.get("fully_diluted_market_cap")
        if fdv is not None:
            coin.fully_diluted_valuation = float(fdv)

        if item.get("circulating_supply") is not None:
            coin.circulating_supply = float(item["circulating_supply"])
        if item.get("total_supply") is not None:
            coin.total_supply = float(item["total_supply"])

        coin.source = SOURCE
        coin.synced_at = now
        updated += 1

    db.session.commit()
    logger.info("Patched market_coins metrics from CMC (%s rows)", updated)
    return updated
