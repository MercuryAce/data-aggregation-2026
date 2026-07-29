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
from services import populate_coingecko as populate

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
    parser = argparse.ArgumentParser(description="Populate MySQL view tables from CoinGecko.")
    parser.add_argument(
        "--tables",
        required=True,
        help="Comma-separated: markets,exchanges,trending,categories,all",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Refresh even when tables already have rows",
    )
    args = parser.parse_args()

    names = [n.strip() for n in args.tables.split(",") if n.strip()]
    unknown = [n for n in names if n not in TASKS]
    if unknown:
        logger.error("Unknown table(s): %s", ", ".join(unknown))
        return 1

    with app.app_context():
        for name in names:
            logger.info("Populating: %s (force=%s)", name, args.force)
            TASKS[name](args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
