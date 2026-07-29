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
from scripts.sync_cmc import sync_listings as sync_cmc_listings
from scripts.sync_cmc import sync_map as sync_cmc_map
from scripts.sync_defillama import (
    sync_chains,
    sync_current_prices,
    sync_dexs,
    sync_fees,
    sync_historical_chain_tvl,
    sync_historical_chain_tvl_by_chain,
    sync_pools,
    sync_protocol,
    sync_protocols,
    sync_stablecoins,
)
from scripts.sync_messari import (
    sync_asset_details,
    sync_assets,
)
from scripts.sync_alphavantage import (
    sync_crypto_daily,
    sync_etf,
    sync_fx,
    sync_metals,
    sync_news,
)
from services import id_map


def _run_sync(func, *args, **kwargs):
    try:
        with app.app_context():
            func(*args, **kwargs)
            logger.info(f"Synced {func.__name__}")
    except Exception as e:
        logger.error(f"Error syncing {func.__name__}: {e}")
        raise e


@celery.task(name="tasks.sync_tasks.sync_markets")
def sync_markets_task(**kwargs):
    _run_sync(sync_markets, **kwargs)


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
    limit = kwargs.get("limit", 30)
    _run_sync(sync_top_coin_details, limit=limit)


@celery.task(name="tasks.sync_tasks.sync_ohlc")
def sync_ohlc_task(**kwargs):
    _run_sync(sync_ohlc, **kwargs)


@celery.task(name="tasks.sync_tasks.sync_search")
def sync_search_task():
    _run_sync(sync_popular_searches)


@celery.task(name="tasks.sync_tasks.sync_cmc_listings")
def sync_cmc_listings_task(**kwargs):
    start = kwargs.get("start", 1)
    limit = kwargs.get("limit", 500)
    _run_sync(sync_cmc_listings, start=start, limit=limit)


@celery.task(name="tasks.sync_tasks.sync_cmc_map")
def sync_cmc_map_task(**kwargs):
    _run_sync(sync_cmc_map, **kwargs)


@celery.task(name="tasks.sync_tasks.sync_asset_id_map")
def sync_asset_id_map_task():
    _run_sync(id_map.build_id_map)


@celery.task(name="tasks.sync_tasks.sync_defillama_protocols")
def sync_defillama_protocols_task():
    _run_sync(sync_protocols)
    _run_sync(sync_protocol, "aave")
    _run_sync(sync_chains)


@celery.task(name="tasks.sync_tasks.sync_defillama_historical_tvl")
def sync_defillama_historical_tvl_task(**kwargs):
    chain = kwargs.get("chain", "Ethereum")
    _run_sync(sync_historical_chain_tvl)
    _run_sync(sync_historical_chain_tvl_by_chain, chain)


@celery.task(name="tasks.sync_tasks.sync_defillama_markets")
def sync_defillama_markets_task():
    _run_sync(sync_stablecoins)
    _run_sync(sync_pools)
    _run_sync(sync_dexs)
    _run_sync(sync_fees)


@celery.task(name="tasks.sync_tasks.sync_defillama_prices")
def sync_defillama_prices_task(**kwargs):
    coins = kwargs.get("coins", "coingecko:bitcoin,coingecko:ethereum")
    _run_sync(sync_current_prices, coins)


@celery.task(name="tasks.sync_tasks.sync_messari")
def sync_messari_task(**kwargs):
    limit = kwargs.get("limit", 20)
    slugs = kwargs.get("slugs", "bitcoin,ethereum")
    _run_sync(sync_assets, limit=limit, page=1)
    _run_sync(sync_asset_details, slugs)


@celery.task(name="tasks.sync_tasks.sync_av_news")
def sync_av_news_task(**kwargs):
    topics = kwargs.get("topics", "blockchain")
    tickers = kwargs.get("tickers", "CRYPTO:BTC,CRYPTO:ETH")
    limit = kwargs.get("limit", 50)
    _run_sync(sync_news, topics=topics, tickers=tickers, limit=limit)


@celery.task(name="tasks.sync_tasks.sync_av_etf")
def sync_av_etf_task(**kwargs):
    etfs = kwargs.get("etfs", "IBIT,FBTC,GLD,SLV")
    _run_sync(sync_etf, etfs=etfs)


@celery.task(name="tasks.sync_tasks.sync_av_fx")
def sync_av_fx_task(**kwargs):
    pairs = kwargs.get("pairs", "BTC/USD,ETH/USD,USD/EUR,USD/JPY,USD/GBP")
    _run_sync(sync_fx, pairs=pairs)


@celery.task(name="tasks.sync_tasks.sync_av_crypto_daily")
def sync_av_crypto_daily_task(**kwargs):
    symbols = kwargs.get("symbols", "BTC,ETH")
    market = kwargs.get("market", "USD")
    _run_sync(sync_crypto_daily, symbols=symbols, market=market)


@celery.task(name="tasks.sync_tasks.sync_av_metals")
def sync_av_metals_task(**kwargs):
    symbols = kwargs.get("symbols", "GOLD,SILVER")
    _run_sync(sync_metals, symbols=symbols)
