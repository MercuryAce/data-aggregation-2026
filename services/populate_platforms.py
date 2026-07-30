"""Sync generic chain/contract identity onto market_coins from CoinGecko.

Column names stay provider-agnostic (`platforms`, `primary_chain`,
`contract_address`, `external_ids`). Quote-provider keys (e.g. DefiLlama)
are derived at patch time from these fields.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from clients import cg_client
from models import MarketCoin, db
from services.asset_identity import (
    merge_external_ids,
    normalize_platforms,
    pick_primary_chain,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def apply_platforms_to_coin(coin: MarketCoin, platforms_raw) -> bool:
    """Set platforms / primary_chain / contract_address on a coin. Returns True if changed."""
    platforms = normalize_platforms(platforms_raw)
    primary = pick_primary_chain(platforms)
    contract = platforms.get(primary) if primary else None

    changed = (
        (coin.platforms or {}) != platforms
        or coin.primary_chain != primary
        or coin.contract_address != contract
    )
    coin.platforms = platforms or None
    coin.primary_chain = primary
    coin.contract_address = contract
    coin.external_ids = merge_external_ids(coin.external_ids, coingecko=coin.cg_id)
    return changed


def populate_platforms() -> int:
    """One CG ``/coins/list?include_platform=true`` call; update matching market_coins."""
    payload = cg_client.get_coins_list(include_platform=True)
    if not isinstance(payload, list):
        logger.warning("CoinGecko coins/list returned unexpected payload")
        return 0

    by_id = {
        row["id"]: row
        for row in payload
        if isinstance(row, dict) and row.get("id")
    }
    coins = db.session.query(MarketCoin).all()
    if not coins:
        logger.warning("market_coins empty — run CG markets populate first")
        return 0

    now = _utcnow()
    updated = 0
    for coin in coins:
        entry = by_id.get(coin.cg_id)
        if entry is None:
            continue
        apply_platforms_to_coin(coin, entry.get("platforms"))
        coin.structure_synced_at = now
        updated += 1

    db.session.commit()
    logger.info("Synced platforms onto market_coins (%s rows)", updated)
    return updated
