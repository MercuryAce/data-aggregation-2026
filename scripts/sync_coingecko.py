#!/usr/bin/env python3
"""Fetch CoinGecko data and write it to the ApiCache store."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app
from clients import cg_client
from services import cache_keys, cache_store
from services.timeseries_store import append_price_ticks

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TTL_MARKETS = 60 * 60
TTL_WARM = 60 * 60
TTL_COLD = 4 * 60 * 60
TTL_COIN = 2 * 60 * 60
TTL_OHLC = 6 * 60 * 60


def sync_markets(vs_currency="usd", limit=250, page=1, pages=1) -> None:
    """Sync one or more markets pages (pages>1 walks page..page+pages-1)."""
    page_count = max(1, int(pages or 1))
    start_page = max(1, int(page or 1))
    all_ticks: list[dict] = []

    for offset in range(page_count):
        current = start_page + offset
        markets = cg_client.get_market_data(
            vs_currency=vs_currency,
            limit=limit,
            page=current,
        )
        cache_store.set(
            cache_keys.markets_key(vs_currency, limit, current),
            markets,
            ttl_seconds=TTL_MARKETS,
        )
        logger.info(
            "Synced %s (%s rows)",
            cache_keys.markets_key(vs_currency, limit, current),
            len(markets) if isinstance(markets, list) else "?",
        )
        for coin in markets or []:
            if not isinstance(coin, dict):
                continue
            price = coin.get("current_price")
            if price is None or not coin.get("id"):
                continue
            all_ticks.append(
                {
                    "asset_id": coin["id"],
                    "source": "coingecko",
                    "price": float(price),
                    "volume": coin.get("total_volume"),
                    "meta": {"symbol": coin.get("symbol")},
                }
            )
        if not markets or (isinstance(markets, list) and len(markets) < limit):
            break

    global_data = cg_client.get_global()
    cache_store.set(cache_keys.global_key(), global_data, ttl_seconds=TTL_MARKETS)
    logger.info("Synced %s", cache_keys.global_key())
    append_price_ticks(all_ticks)


def sync_trending() -> None:
    data = cg_client.get_trending()
    cache_store.set(cache_keys.trending_key(), data, ttl_seconds=TTL_WARM)
    logger.info("Synced %s", cache_keys.trending_key())


def sync_categories(order="market_cap_desc") -> None:
    data = cg_client.get_categories(order=order)
    cache_store.set(cache_keys.categories_key(order), data, ttl_seconds=TTL_WARM)
    logger.info("Synced %s", cache_keys.categories_key(order))


def sync_exchanges(per_page=100, page=1) -> None:
    data = cg_client.get_exchanges(per_page=per_page, page=page)
    cache_store.set(
        cache_keys.exchanges_key(per_page, page),
        data,
        ttl_seconds=TTL_COLD,
    )
    logger.info("Synced %s", cache_keys.exchanges_key(per_page, page))


def sync_exchange_details(limit=20, per_page=100, page=1) -> None:
    """Warm ApiCache for exchange detail pages (top N by trust rank)."""
    from models import Exchange, db

    ids: list[str] = []
    rows = (
        db.session.query(Exchange)
        .order_by(Exchange.trust_score_rank.asc())
        .limit(limit)
        .all()
    )
    if rows:
        ids = [row.exchange_id for row in rows if row.exchange_id]
    else:
        listing = cg_client.get_exchanges(per_page=min(limit, per_page), page=page) or []
        ids = [row.get("id") for row in listing if isinstance(row, dict) and row.get("id")]
        ids = ids[:limit]

    for exchange_id in ids:
        data = cg_client.get_exchange_details(exchange_id)
        cache_store.set(
            cache_keys.exchange_details_key(exchange_id),
            data,
            ttl_seconds=TTL_COLD,
        )
        logger.info("Synced %s", cache_keys.exchange_details_key(exchange_id))


def sync_top_coin_details(limit=30, vs_currency="usd") -> None:
    markets = cg_client.get_market_data(vs_currency=vs_currency, limit=limit, page=1)
    for coin in markets:
        coin_id = coin["id"]
        details = cg_client.get_coin_details(coin_id, vs_currency=vs_currency)
        cache_store.set(
            cache_keys.coin_key(coin_id, vs_currency),
            details,
            ttl_seconds=TTL_COIN,
        )
        logger.info("Synced %s", cache_keys.coin_key(coin_id, vs_currency))


def sync_ohlc(limit=20, days=30, vs_currency="usd") -> None:
    markets = cg_client.get_market_data(vs_currency=vs_currency, limit=limit, page=1)
    for coin in markets:
        coin_id = coin["id"]
        data = cg_client.get_ohlc(coin_id, days=days, vs_currency=vs_currency)
        cache_store.set(
            cache_keys.ohlc_key(coin_id, days, vs_currency),
            data,
            ttl_seconds=TTL_OHLC,
        )
        logger.info("Synced %s", cache_keys.ohlc_key(coin_id, days, vs_currency))


def sync_popular_searches(queries: list[str] | None = None) -> None:
    for query in queries or ("bitcoin", "ethereum", "solana"):
        data = cg_client.get_search(query)
        cache_store.set(cache_keys.search_key(query), data, ttl_seconds=TTL_COLD)
        logger.info("Synced %s", cache_keys.search_key(query))


TASKS = {
    "markets": sync_markets,
    "trending": sync_trending,
    "categories": sync_categories,
    "exchanges": sync_exchanges,
    "exchange-details": sync_exchange_details,
    "top-coins": sync_top_coin_details,
    "ohlc": sync_ohlc,
    "search": sync_popular_searches,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync CoinGecko data into ApiCache.")
    parser.add_argument(
        "--tasks",
        required=True,
        help="Comma-separated tasks: markets,trending,categories,exchanges,exchange-details,top-coins,ohlc,search",
    )
    parser.add_argument("--pages", type=int, default=1, help="Markets page count")
    parser.add_argument("--limit", type=int, default=250)
    args = parser.parse_args()

    task_names = [name.strip() for name in args.tasks.split(",") if name.strip()]
    unknown = [name for name in task_names if name not in TASKS]
    if unknown:
        logger.error("Unknown task(s): %s", ", ".join(unknown))
        return 1

    with app.app_context():
        for name in task_names:
            logger.info("Running task: %s", name)
            if name == "markets":
                sync_markets(limit=args.limit, pages=args.pages)
            elif name == "top-coins":
                sync_top_coin_details(limit=args.limit if args.limit != 250 else 30)
            elif name == "ohlc":
                sync_ohlc(limit=args.limit if args.limit != 250 else 20)
            elif name == "exchange-details":
                sync_exchange_details(limit=args.limit if args.limit != 250 else 20)
            else:
                TASKS[name]()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
