#!/usr/bin/env python3
"""CLI to populate MySQL view tables from CoinGecko."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app
from services import populate_cmc, populate_coingecko as populate
from services import populate_defillama, populate_platforms, populate_quotes

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TASKS = {
    "markets": lambda force: populate.ensure_markets(force=force),
    "exchanges": lambda force: populate.ensure_exchanges(force=force),
    "trending": lambda force: populate.ensure_trending(force=force),
    "categories": lambda force: populate.ensure_categories(force=force),
    "all": lambda force: populate.ensure_all(force=force),
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Populate MySQL view tables (CG structure + optional price patches)."
    )
    parser.add_argument(
        "--tables",
        help="Comma-separated: markets,exchanges,trending,categories,all",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Refresh even when tables already have rows",
    )
    parser.add_argument(
        "--sync-platforms",
        action="store_true",
        help="Sync generic chain/contract columns from CoinGecko coins/list",
    )
    parser.add_argument(
        "--patch-cmc",
        action="store_true",
        help="UPDATE live price metrics from CMC onto existing market_coins",
    )
    parser.add_argument("--cmc-limit", type=int, default=500)
    parser.add_argument(
        "--patch-defillama",
        action="store_true",
        help="UPDATE current_price from DefiLlama onto existing market_coins",
    )
    parser.add_argument(
        "--defillama-limit",
        type=int,
        default=None,
        help="Cap DefiLlama patch to top N by market_cap_rank (default: all)",
    )
    parser.add_argument(
        "--patch-oracle-quotes",
        action="store_true",
        help="Upsert oracle mids (CG/CMC/DefiLlama) into asset_quotes",
    )
    parser.add_argument(
        "--patch-av-quotes",
        action="store_true",
        help="Upsert Alpha Vantage BTC mid (daily — free tier ~25 req/day)",
    )
    parser.add_argument(
        "--patch-venue-quotes",
        action="store_true",
        help="Upsert exchange bid/ask (Binance/Kraken/OKX) into asset_quotes",
    )
    parser.add_argument(
        "--quotes-limit",
        type=int,
        default=20,
        help="Top N by market_cap_rank for quote patches (default: 20)",
    )
    args = parser.parse_args()

    if (
        not args.tables
        and not args.patch_cmc
        and not args.patch_defillama
        and not args.sync_platforms
        and not args.patch_oracle_quotes
        and not args.patch_av_quotes
        and not args.patch_venue_quotes
    ):
        parser.error(
            "Provide --tables and/or --sync-platforms and/or --patch-cmc "
            "and/or --patch-defillama and/or --patch-oracle-quotes "
            "and/or --patch-av-quotes and/or --patch-venue-quotes"
        )

    with app.app_context():
        if args.tables:
            names = [n.strip() for n in args.tables.split(",") if n.strip()]
            unknown = [n for n in names if n not in TASKS]
            if unknown:
                logger.error("Unknown table(s): %s", ", ".join(unknown))
                return 1
            for name in names:
                logger.info("Populating: %s (force=%s)", name, args.force)
                TASKS[name](args.force)

        if args.sync_platforms:
            n = populate_platforms.populate_platforms()
            logger.info("Platform sync updated %s rows", n)

        if args.patch_cmc:
            n = populate_cmc.patch_market_metrics(limit=args.cmc_limit)
            logger.info("CMC metrics patch updated %s rows", n)

        if args.patch_defillama:
            n = populate_defillama.patch_market_prices(limit=args.defillama_limit)
            logger.info("DefiLlama price patch updated %s rows", n)

        if args.patch_oracle_quotes:
            n = populate_quotes.patch_oracle_quotes(limit=args.quotes_limit)
            logger.info("Oracle quotes upsert writes ~%s", n)

        if args.patch_av_quotes:
            n = populate_quotes.patch_alphavantage_quotes()
            logger.info("AV oracle quotes upsert writes ~%s", n)

        if args.patch_venue_quotes:
            n = populate_quotes.patch_venue_quotes(limit=args.quotes_limit)
            logger.info("Venue quotes upsert writes ~%s", n)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
