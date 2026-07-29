import os

# Redis for broker + results
broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

imports = ("tasks.sync_tasks",)

timezone = "UTC"
enable_utc = True

task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]

# Avoid pile-up if a sync run takes longer than the interval
task_acks_late = True
worker_prefetch_multiplier = 1

# Markets: CG structure ~30m, CMC metrics ~12m (Basic ~15k credits/mo)
beat_schedule = {
    "populate-markets-structure": {
        "task": "tasks.sync_tasks.populate_markets_structure",
        "schedule": 30 * 60,          # CG rank / identity / supplies
        "kwargs": {"pages": 4, "per_page": 250},
    },
    "patch-market-metrics-cmc": {
        "task": "tasks.sync_tasks.patch_market_metrics_cmc",
        "schedule": 12 * 60,          # live price / mcap / volume on market_coins
        "kwargs": {"start": 1, "limit": 500},
    },
    "sync-cmc-listings": {
        "task": "tasks.sync_tasks.sync_cmc_listings",
        "schedule": 12 * 60,          # ApiCache mirror (same cadence as MySQL patch)
        "kwargs": {"start": 1, "limit": 500},
    },
    "sync-cmc-map": {
        "task": "tasks.sync_tasks.sync_cmc_map",
        "schedule": 24 * 60 * 60,     # daily ID map source
    },
    "sync-asset-id-map": {
        "task": "tasks.sync_tasks.sync_asset_id_map",
        "schedule": 6 * 60 * 60,
    },
    # MySQL view tables (pages read these; avoid duplicate ApiCache CG hits)
    "populate-trending": {
        "task": "tasks.sync_tasks.populate_trending",
        "schedule": 60 * 60,          # ~1h — trending churns
    },
    "populate-exchanges": {
        "task": "tasks.sync_tasks.populate_exchanges",
        "schedule": 24 * 60 * 60,     # daily
    },
    "populate-categories": {
        "task": "tasks.sync_tasks.populate_categories",
        "schedule": 24 * 60 * 60,     # daily
    },
    # ApiCache warmers for secondary routes (lazy-fill covers misses)
    "sync-exchange-details": {
        "task": "tasks.sync_tasks.sync_exchange_details",
        "schedule": 24 * 60 * 60,
        "kwargs": {"limit": 20},
    },
    "sync-top-coins": {
        "task": "tasks.sync_tasks.sync_top_coins",
        "schedule": 24 * 60 * 60,     # daily prewarm; misses live-fill
        "kwargs": {"limit": 15},
    },
    "sync-ohlc": {
        "task": "tasks.sync_tasks.sync_ohlc",
        "schedule": 24 * 60 * 60,
        "kwargs": {"limit": 10, "days": 30},
    },
    "sync-search": {
        "task": "tasks.sync_tasks.sync_search",
        "schedule": 24 * 60 * 60,
    },
    "sync-defillama-protocols": {
        "task": "tasks.sync_tasks.sync_defillama_protocols",
        "schedule": 60 * 60,
    },
    "sync-defillama-historical-tvl": {
        "task": "tasks.sync_tasks.sync_defillama_historical_tvl",
        "schedule": 4 * 60 * 60,
        "kwargs": {"chain": "Ethereum"},
    },
    "sync-defillama-markets": {
        "task": "tasks.sync_tasks.sync_defillama_markets",
        "schedule": 2 * 60 * 60,
    },
    "sync-defillama-prices": {
        "task": "tasks.sync_tasks.sync_defillama_prices",
        "schedule": 5 * 60,
        "kwargs": {
            "coins": "coingecko:bitcoin,coingecko:ethereum,coingecko:solana",
        },
    },
    "sync-messari": {
        "task": "tasks.sync_tasks.sync_messari",
        "schedule": 60 * 60,
        "kwargs": {"limit": 20, "slugs": "bitcoin,ethereum"},
    },
    # Alpha Vantage — sparse for free-tier ~5 req/min / ~25 req/day
    "sync-av-news": {
        "task": "tasks.sync_tasks.sync_av_news",
        "schedule": 60 * 60,
        "kwargs": {
            "topics": "blockchain",
            "tickers": "CRYPTO:BTC,CRYPTO:ETH",
            "limit": 50,
        },
    },
    "sync-av-fx": {
        "task": "tasks.sync_tasks.sync_av_fx",
        "schedule": 30 * 60,
        "kwargs": {"pairs": "BTC/USD,ETH/USD,USD/EUR"},
    },
    "sync-av-metals": {
        "task": "tasks.sync_tasks.sync_av_metals",
        "schedule": 30 * 60,
        "kwargs": {"symbols": "GOLD,SILVER"},
    },
    "sync-av-etf": {
        "task": "tasks.sync_tasks.sync_av_etf",
        "schedule": 24 * 60 * 60,
        "kwargs": {"etfs": "IBIT,FBTC,GLD,SLV"},
    },
    "sync-av-crypto-daily": {
        "task": "tasks.sync_tasks.sync_av_crypto_daily",
        "schedule": 6 * 60 * 60,
        "kwargs": {"symbols": "BTC,ETH", "market": "USD"},
    },
}
