"""Patch live prices on MySQL market_coins from DefiLlama.

Builds quote keys from generic ``platforms`` / ``contract_address`` when
present; falls back to ``coingecko:{cg_id}``. Updates price only.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from clients import defillama_client
from models import MarketCoin, db
from services.asset_identity import defillama_quote_key, normalize_platforms
from services.timeseries_store import append_price_ticks

logger = logging.getLogger(__name__)

SOURCE = "defillama"
# Keep URL paths short; DefiLlama accepts many coins per call.
BATCH_SIZE = 80


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _chunked(items: list[str], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def quote_key_for_coin(coin: MarketCoin) -> str:
    platforms = normalize_platforms(coin.platforms)
    return defillama_quote_key(coin.cg_id, platforms)


def fetch_prices_by_quote_keys(keys: list[str]) -> dict[str, float]:
    """Return {quote_key: price} from DefiLlama current prices."""
    prices: dict[str, float] = {}
    for batch in _chunked(keys, BATCH_SIZE):
        payload = defillama_client.get_current_prices(",".join(batch))
        coin_map = (payload or {}).get("coins") if isinstance(payload, dict) else None
        if not isinstance(coin_map, dict):
            continue
        for key, info in coin_map.items():
            if not isinstance(info, dict) or info.get("price") is None:
                continue
            try:
                prices[key] = float(info["price"])
            except (TypeError, ValueError):
                continue
    return prices


def fetch_prices_for_cg_ids(cg_ids: list[str]) -> dict[str, float]:
    """Legacy helper: coingecko:{id} only. Prefer patch_market_prices."""
    keys = [f"coingecko:{cg_id}" for cg_id in cg_ids]
    by_key = fetch_prices_by_quote_keys(keys)
    out: dict[str, float] = {}
    for key, price in by_key.items():
        if key.startswith("coingecko:"):
            out[key.split(":", 1)[1]] = price
    return out


def patch_market_prices(*, limit: int | None = None) -> int:
    """UPDATE current_price on existing market_coins from DefiLlama.

    ``limit`` caps by market_cap_rank order (None = all rows).
    """
    query = db.session.query(MarketCoin).order_by(MarketCoin.market_cap_rank.asc())
    if limit is not None and limit > 0:
        query = query.limit(limit)
    coins = query.all()
    if not coins:
        logger.warning("market_coins empty — run CG populate first")
        return 0

    key_to_cg: dict[str, str] = {}
    for coin in coins:
        key = quote_key_for_coin(coin)
        # First writer wins if two assets share a contract (rare).
        key_to_cg.setdefault(key, coin.cg_id)

    by_id = {c.cg_id: c for c in coins}
    by_key = fetch_prices_by_quote_keys(list(key_to_cg.keys()))
    if not by_key:
        logger.warning("DefiLlama returned no prices")
        return 0

    now = _utcnow()
    updated = 0
    ticks = []
    for key, price in by_key.items():
        cg_id = key_to_cg.get(key)
        if cg_id is None and key.startswith("coingecko:"):
            cg_id = key.split(":", 1)[1]
        coin = by_id.get(cg_id) if cg_id else None
        if coin is None:
            continue
        coin.current_price = price
        coin.source = SOURCE
        coin.synced_at = now
        coin.metrics_synced_at = now
        updated += 1
        ticks.append(
            {
                "asset_id": cg_id,
                "source": SOURCE,
                "price": price,
                "timestamp": now,
                "meta": {"quote_key": key},
            }
        )

    db.session.commit()
    append_price_ticks(ticks)
    logger.info("Patched market_coins prices from DefiLlama (%s rows)", updated)
    return updated
