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

# Tiered schedule — aligned with API quota, not every 10 minutes for everything
beat_schedule = {
    "sync-markets-global": {
        "task": "tasks.sync_tasks.sync_markets",
        "schedule": 30 * 60,          # every 30 min (~1,440 calls/month for 2 endpoints)
    },
    "sync-trending-categories": {
        "task": "tasks.sync_tasks.sync_trending_categories",
        "schedule": 60 * 60,          # hourly
    },
    "sync-exchanges": {
        "task": "tasks.sync_tasks.sync_exchanges",
        "schedule": 4 * 60 * 60,      # every 4 hours
    },
    "sync-top-coins": {
        "task": "tasks.sync_tasks.sync_top_coins",
        "schedule": 2 * 60 * 60,      # every 2 hours
        "kwargs": {"limit": 250},     # match index page (250 coins)
    },
    "sync-ohlc": {
        "task": "tasks.sync_tasks.sync_ohlc",
        "schedule": 6 * 60 * 60,      # every 6 hours
        "kwargs": {"limit": 20, "days": 30},
    },
    "sync-search": {
        "task": "tasks.sync_tasks.sync_search",
        "schedule": 4 * 60 * 60,
    },
    "sync-defillama-protocols": {
        "task": "tasks.sync_tasks.sync_defillama_protocols",
        "schedule": 60 * 60,          # hourly — protocols list + aave detail
    },
    "sync-defillama-historical-tvl": {
        "task": "tasks.sync_tasks.sync_defillama_historical_tvl",
        "schedule": 4 * 60 * 60,      # every 4 hours
        "kwargs": {"chain": "Ethereum"},
    },
}