from flask_caching import logger
from celery_app import celery
from app import app
from scripts.sync_coingecko import (
    sync_markets,
    sync_trending,
    sync_categories,
    sync_exchanges,
    sync_top_coin_details,
    sync_ohlc,
    sync_popular_searches,
)
from scripts.sync_defillama import (
    sync_historical_chain_tvl,
    sync_historical_chain_tvl_by_chain,
    sync_protocol,
    sync_protocols,
)


def _run_sync(func, *args, **kwargs):
    try:
        with app.app_context():
            func(*args, **kwargs)
            logger.info(f"Synced {func.__name__}")
    except Exception as e:
        logger.error(f"Error syncing {func.__name__}: {e}")
        raise e


@celery.task(name="tasks.sync_tasks.sync_markets")
def sync_markets_task():
    _run_sync(sync_markets)


@celery.task(name="tasks.sync_tasks.sync_trending")
def sync_trending_task():
    _run_sync(sync_trending)


@celery.task(name="tasks.sync_tasks.sync_categories")
def sync_categories_task():
    _run_sync(sync_categories)


@celery.task(name="tasks.sync_tasks.sync_trending_categories")
def sync_trending_categories_task():
    _run_sync(sync_trending)
    _run_sync(sync_categories)


@celery.task(name="tasks.sync_tasks.sync_exchanges")
def sync_exchanges_task():
    _run_sync(sync_exchanges)


@celery.task(name="tasks.sync_tasks.sync_top_coin_details")
def sync_top_coin_details_task(**kwargs):
    _run_sync(sync_top_coin_details, **kwargs)


@celery.task(name="tasks.sync_tasks.sync_top_coins")
def sync_top_coins_task(**kwargs):
    # Beat schedule uses this name; default limit in script is 30.
    # kwargs passes limit=250 for market coverage — map to top coin details.
    limit = kwargs.get("limit", 30)
    _run_sync(sync_top_coin_details, limit=limit)


@celery.task(name="tasks.sync_tasks.sync_ohlc")
def sync_ohlc_task(**kwargs):
    _run_sync(sync_ohlc, **kwargs)


@celery.task(name="tasks.sync_tasks.sync_search")
def sync_search_task():
    _run_sync(sync_popular_searches)


@celery.task(name="tasks.sync_tasks.sync_defillama_protocols")
def sync_defillama_protocols_task():
    _run_sync(sync_protocols)
    _run_sync(sync_protocol, "aave")


@celery.task(name="tasks.sync_tasks.sync_defillama_historical_tvl")
def sync_defillama_historical_tvl_task(**kwargs):
    chain = kwargs.get("chain", "Ethereum")
    _run_sync(sync_historical_chain_tvl)
    _run_sync(sync_historical_chain_tvl_by_chain, chain)
