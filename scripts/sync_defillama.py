#!/usr/bin/env python3
"""Fetch DefiLlama data and write it to the ApiCache store."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app
from clients import defillama_client
from services import cache_store, defillama_cache_keys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TTL_SECONDS = 60 * 60
SOURCE = "defillama"
DEFAULT_PROTOCOL = "aave"
DEFAULT_CHAIN = "Ethereum"


def sync_protocols() -> None:
    data = defillama_client.get_protocols()
    key = defillama_cache_keys.protocols_key()
    cache_store.set(key, data, ttl_seconds=TTL_SECONDS, source=SOURCE)
    logger.info("Synced %s", key)


def sync_protocol(protocol: str = DEFAULT_PROTOCOL) -> None:
    data = defillama_client.get_protocol(protocol)
    key = defillama_cache_keys.protocol_key(protocol)
    cache_store.set(key, data, ttl_seconds=TTL_SECONDS, source=SOURCE)
    logger.info("Synced %s", key)


def sync_historical_chain_tvl() -> None:
    data = defillama_client.get_historical_chain_tvl()
    key = defillama_cache_keys.historical_chain_tvl_key()
    cache_store.set(key, data, ttl_seconds=TTL_SECONDS, source=SOURCE)
    logger.info("Synced %s", key)


def sync_historical_chain_tvl_by_chain(chain: str = DEFAULT_CHAIN) -> None:
    data = defillama_client.get_historical_chain_tvl_by_chain(chain)
    key = defillama_cache_keys.historical_chain_tvl_by_chain_key(chain)
    cache_store.set(key, data, ttl_seconds=TTL_SECONDS, source=SOURCE)
    logger.info("Synced %s", key)


TASKS = {
    "protocols": sync_protocols,
    "protocol": sync_protocol,
    "historical_chain_tvl": sync_historical_chain_tvl,
    "historical_chain_tvl_by_chain": sync_historical_chain_tvl_by_chain,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync DefiLlama data into ApiCache.")
    parser.add_argument(
        "--tasks",
        required=True,
        help=(
            "Comma-separated: protocols,protocol,"
            "historical_chain_tvl,historical_chain_tvl_by_chain"
        ),
    )
    parser.add_argument(
        "--protocol",
        type=str,
        default=DEFAULT_PROTOCOL,
        help=f"Protocol slug for protocol sync (default: {DEFAULT_PROTOCOL})",
    )
    parser.add_argument(
        "--chain",
        type=str,
        default=DEFAULT_CHAIN,
        help=f"Chain name for per-chain historical TVL (default: {DEFAULT_CHAIN})",
    )
    args = parser.parse_args()

    task_names = [
        name.strip().replace("-", "_")
        for name in args.tasks.split(",")
        if name.strip()
    ]
    unknown = [name for name in task_names if name not in TASKS]
    if unknown:
        logger.error("Unknown task(s): %s", ", ".join(unknown))
        return 1

    with app.app_context():
        for name in task_names:
            logger.info("Running task: %s", name)
            if name == "protocols":
                sync_protocols()
            elif name == "protocol":
                sync_protocol(args.protocol)
            elif name == "historical_chain_tvl":
                sync_historical_chain_tvl()
            elif name == "historical_chain_tvl_by_chain":
                sync_historical_chain_tvl_by_chain(args.chain)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
