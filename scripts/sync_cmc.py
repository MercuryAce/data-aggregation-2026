#!/usr/bin/env python3
"""Fetch CoinMarketCap data into ApiCache (and optional Mongo ticks)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app
from clients import cmc_client
from services import cache_store, cmc_cache_keys
from services.timeseries_store import append_price_ticks

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TTL_LISTINGS = 2 * 60
TTL_MAP = 24 * 60 * 60
SOURCE = "cmc"
PAGE_SIZE = 200  # 1 CMC credit per 200 coins returned


def _usd_quote(item: dict) -> dict:
    quote = item.get("quote") or {}
    return quote.get("USD") or quote.get("usd") or {}


def sync_listings(start=1, limit=500, convert="USD") -> None:
    """Fetch listings in pages of 100 and store one combined snapshot."""
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

    key = cmc_cache_keys.listings_key(start, limit, convert)
    cache_store.set(
        key,
        {"data": collected},
        ttl_seconds=TTL_LISTINGS,
        source=SOURCE,
    )
    logger.info("Synced %s (%s rows)", key, len(collected))

    ticks = []
    for item in collected:
        usd = _usd_quote(item)
        price = usd.get("price")
        if price is None:
            continue
        slug = (item.get("slug") or item.get("symbol") or str(item.get("id"))).lower()
        ticks.append(
            {
                "asset_id": slug,
                "source": SOURCE,
                "price": float(price),
                "volume": usd.get("volume_24h"),
                "meta": {
                    "cmc_id": item.get("id"),
                    "symbol": item.get("symbol"),
                },
            }
        )
    append_price_ticks(ticks)


def sync_map(listing_status="active", limit=5000) -> None:
    payload = cmc_client.get_cryptocurrency_map(
        listing_status=listing_status,
        limit=limit,
    )
    key = cmc_cache_keys.map_key(listing_status, limit)
    cache_store.set(key, payload, ttl_seconds=TTL_MAP, source=SOURCE)
    logger.info("Synced %s", key)


TASKS = {
    "listings": sync_listings,
    "map": sync_map,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync CMC data into ApiCache.")
    parser.add_argument(
        "--tasks",
        required=True,
        help="Comma-separated tasks: listings,map",
    )
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()

    task_names = [name.strip() for name in args.tasks.split(",") if name.strip()]
    unknown = [name for name in task_names if name not in TASKS]
    if unknown:
        logger.error("Unknown task(s): %s", ", ".join(unknown))
        return 1

    with app.app_context():
        for name in task_names:
            logger.info("Running task: %s", name)
            if name == "listings":
                sync_listings(start=args.start, limit=args.limit)
            else:
                TASKS[name]()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
