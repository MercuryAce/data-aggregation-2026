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
from services.timeseries_store import append_price_ticks

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TTL_SECONDS = 60 * 60
SOURCE = "defillama"
DEFAULT_PROTOCOL = "aave"
DEFAULT_CHAIN = "Ethereum"
DEFAULT_COINS = "ethereum:0x0000000000000000000000000000000000000000"
DEFAULT_BRIDGE_ID = "1"


def _set(key: str, data) -> None:
    cache_store.set(key, data, ttl_seconds=TTL_SECONDS, source=SOURCE)
    logger.info("Synced %s", key)


def sync_protocols() -> None:
    _set(defillama_cache_keys.protocols_key(), defillama_client.get_protocols())


def sync_protocol(protocol: str = DEFAULT_PROTOCOL) -> None:
    _set(
        defillama_cache_keys.protocol_key(protocol),
        defillama_client.get_protocol(protocol),
    )


def sync_historical_chain_tvl() -> None:
    _set(
        defillama_cache_keys.historical_chain_tvl_key(),
        defillama_client.get_historical_chain_tvl(),
    )


def sync_historical_chain_tvl_by_chain(chain: str = DEFAULT_CHAIN) -> None:
    _set(
        defillama_cache_keys.historical_chain_tvl_by_chain_key(chain),
        defillama_client.get_historical_chain_tvl_by_chain(chain),
    )


def sync_chains() -> None:
    _set(defillama_cache_keys.chains_key(), defillama_client.get_chains())


def sync_current_prices(coins: str = DEFAULT_COINS) -> None:
    data = defillama_client.get_current_prices(coins)
    _set(defillama_cache_keys.current_prices_key(coins), data)
    ticks = []
    coin_map = (data or {}).get("coins") if isinstance(data, dict) else None
    if isinstance(coin_map, dict):
        for coin_key, info in coin_map.items():
            if not isinstance(info, dict) or info.get("price") is None:
                continue
            asset_id = coin_key
            if coin_key.startswith("coingecko:"):
                asset_id = coin_key.split(":", 1)[1]
            ticks.append(
                {
                    "asset_id": asset_id,
                    "source": SOURCE,
                    "price": float(info["price"]),
                    "meta": {"defillama_key": coin_key},
                }
            )
    append_price_ticks(ticks)


def sync_stablecoins() -> None:
    _set(defillama_cache_keys.stablecoins_key(), defillama_client.get_stablecoins())


def sync_stablecoin_charts_all() -> None:
    _set(
        defillama_cache_keys.stablecoin_charts_all_key(),
        defillama_client.get_stablecoin_charts_all(),
    )


def sync_stablecoin_chains() -> None:
    _set(
        defillama_cache_keys.stablecoin_chains_key(),
        defillama_client.get_stablecoin_chains(),
    )


def sync_stablecoin_prices() -> None:
    _set(
        defillama_cache_keys.stablecoin_prices_key(),
        defillama_client.get_stablecoin_prices(),
    )


def sync_pools() -> None:
    _set(defillama_cache_keys.pools_key(), defillama_client.get_pools())


def sync_bridges() -> None:
    _set(defillama_cache_keys.bridges_key(), defillama_client.get_bridges())


def sync_bridge(bridge_id: str = DEFAULT_BRIDGE_ID) -> None:
    _set(
        defillama_cache_keys.bridge_key(bridge_id),
        defillama_client.get_bridge(bridge_id),
    )


def sync_bridge_volume(chain: str = DEFAULT_CHAIN) -> None:
    _set(
        defillama_cache_keys.bridge_volume_key(chain),
        defillama_client.get_bridge_volume(chain),
    )


def sync_dexs() -> None:
    _set(defillama_cache_keys.dexs_key(), defillama_client.get_dexs())


def sync_dexs_by_chain(chain: str = DEFAULT_CHAIN) -> None:
    _set(
        defillama_cache_keys.dexs_by_chain_key(chain),
        defillama_client.get_dexs_by_chain(chain),
    )


def sync_fees() -> None:
    _set(defillama_cache_keys.fees_key(), defillama_client.get_fees())


def sync_fees_by_chain(chain: str = DEFAULT_CHAIN) -> None:
    _set(
        defillama_cache_keys.fees_by_chain_key(chain),
        defillama_client.get_fees_by_chain(chain),
    )


def sync_options() -> None:
    _set(defillama_cache_keys.options_key(), defillama_client.get_options())


TASKS = {
    "protocols": sync_protocols,
    "protocol": sync_protocol,
    "historical_chain_tvl": sync_historical_chain_tvl,
    "historical_chain_tvl_by_chain": sync_historical_chain_tvl_by_chain,
    "chains": sync_chains,
    "current_prices": sync_current_prices,
    "stablecoins": sync_stablecoins,
    "stablecoin_charts_all": sync_stablecoin_charts_all,
    "stablecoin_chains": sync_stablecoin_chains,
    "stablecoin_prices": sync_stablecoin_prices,
    "pools": sync_pools,
    # "bridges": sync_bridges,
    # "bridge": sync_bridge,
    # "bridge_volume": sync_bridge_volume,
    "dexs": sync_dexs,
    "dexs_by_chain": sync_dexs_by_chain,
    "fees": sync_fees,
    "fees_by_chain": sync_fees_by_chain,
    "options": sync_options,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync DefiLlama data into ApiCache.")
    parser.add_argument(
        "--tasks",
        required=True,
        help="Comma-separated task names (see TASKS in this script)",
    )
    parser.add_argument("--protocol", type=str, default=DEFAULT_PROTOCOL)
    parser.add_argument("--chain", type=str, default=DEFAULT_CHAIN)
    parser.add_argument("--coins", type=str, default=DEFAULT_COINS)
    parser.add_argument("--bridge-id", type=str, default=DEFAULT_BRIDGE_ID)
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
            if name == "protocol":
                sync_protocol(args.protocol)
            elif name == "historical_chain_tvl_by_chain":
                sync_historical_chain_tvl_by_chain(args.chain)
            elif name == "current_prices":
                sync_current_prices(args.coins)
            elif name == "bridge":
                sync_bridge(args.bridge_id)
            elif name == "bridge_volume":
                sync_bridge_volume(args.chain)
            elif name == "dexs_by_chain":
                sync_dexs_by_chain(args.chain)
            elif name == "fees_by_chain":
                sync_fees_by_chain(args.chain)
            else:
                TASKS[name]()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
