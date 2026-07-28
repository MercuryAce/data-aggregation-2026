#!/usr/bin/env python3
"""Fetch Messari data and write it to the ApiCache store."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app
from clients import messari_client
from services import cache_store, messari_cache_keys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TTL_SECONDS = 60 * 60
SOURCE = "messari"
DEFAULT_SLUGS = "bitcoin,ethereum"


def sync_assets(limit=20, page=1) -> None:
    data = messari_client.get_assets(limit=limit, page=page)
    key = messari_cache_keys.assets_key(limit, page)
    cache_store.set(key, data, ttl_seconds=TTL_SECONDS, source=SOURCE)
    logger.info("Synced %s", key)


def sync_asset_details(slugs: str = DEFAULT_SLUGS) -> None:
    data = messari_client.get_asset_details(slugs)
    key = messari_cache_keys.asset_details_key(slugs)
    cache_store.set(key, data, ttl_seconds=TTL_SECONDS, source=SOURCE)
    logger.info("Synced %s", key)


def sync_asset_metrics_catalog() -> None:
    data = messari_client.get_asset_metrics_catalog()
    key = messari_cache_keys.asset_metrics_catalog_key()
    cache_store.set(key, data, ttl_seconds=TTL_SECONDS, source=SOURCE)
    logger.info("Synced %s", key)


def sync_asset_timeseries(
    slug: str = "bitcoin",
    metric: str = "price",
    granularity: str = "1d",
    **params,
) -> None:
    data = messari_client.get_asset_timeseries(slug, metric, granularity, **params)
    key = messari_cache_keys.timeseries_key(slug, metric, granularity)
    cache_store.set(key, data, ttl_seconds=TTL_SECONDS, source=SOURCE)
    logger.info("Synced %s", key)


def sync_exchanges(limit=100, page=1) -> None:
    data = messari_client.get_exchanges(limit=limit, page=page)
    key = messari_cache_keys.exchanges_key(limit, page)
    cache_store.set(key, data, ttl_seconds=TTL_SECONDS, source=SOURCE)
    logger.info("Synced %s", key)


def sync_exchange(exchange_id: str) -> None:
    data = messari_client.get_exchange(exchange_id)
    key = messari_cache_keys.exchange_key(exchange_id)
    cache_store.set(key, data, ttl_seconds=TTL_SECONDS, source=SOURCE)
    logger.info("Synced %s", key)


TASKS = {
    "assets": sync_assets,
    "asset_details": sync_asset_details,
    "asset_metrics_catalog": sync_asset_metrics_catalog,
    "asset_timeseries": sync_asset_timeseries,
    "exchanges": sync_exchanges,
    "exchange": sync_exchange,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Messari data into ApiCache.")
    parser.add_argument(
        "--tasks",
        required=True,
        help="Comma-separated: assets,asset_details,asset_metrics_catalog,asset_timeseries,exchanges",
    )
    parser.add_argument("--limit", type=int, default=20, help="Asset list page size")
    parser.add_argument("--page", type=int, default=1, help="Asset list page number")
    parser.add_argument(
        "--slugs",
        type=str,
        default=DEFAULT_SLUGS,
        help="Comma-separated asset slugs for asset_details sync",
    )
    parser.add_argument("--timeseries-slug", type=str, default="bitcoin")
    parser.add_argument("--metric", type=str, default="price")
    parser.add_argument("--granularity", type=str, default="1d")
    parser.add_argument("--exchange-id", type=str, default="binance")
    args = parser.parse_args()

    task_names = [name.strip() for name in args.tasks.split(",") if name.strip()]
    unknown = [name for name in task_names if name not in TASKS]
    if unknown:
        logger.error("Unknown task(s): %s", ", ".join(unknown))
        return 1

    with app.app_context():
        failed = 0
        for name in task_names:
            logger.info("Running task: %s", name)
            try:
                if name == "assets":
                    sync_assets(limit=args.limit, page=args.page)
                elif name == "asset_details":
                    sync_asset_details(slugs=args.slugs)
                elif name == "exchanges":
                    sync_exchanges(limit=args.limit, page=args.page)
                elif name == "exchange":
                    sync_exchange(args.exchange_id)
                elif name == "asset_timeseries":
                    sync_asset_timeseries(
                        slug=args.timeseries_slug,
                        metric=args.metric,
                        granularity=args.granularity,
                    )
                else:
                    TASKS[name]()
            except messari_client.MessariAPIError as exc:
                failed += 1
                if exc.status_code in (401, 403):
                    logger.error(
                        "Task %s skipped — Messari auth/plan error: %s",
                        name,
                        exc.message,
                    )
                else:
                    logger.error("Task %s failed: %s", name, exc)
            except Exception as exc:
                failed += 1
                logger.exception("Task %s failed: %s", name, exc)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
