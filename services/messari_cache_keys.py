def assets_key(limit=20, page=1) -> str:
    return f"messari_assets_{limit}_{page}"

def asset_details_key(slugs: str) -> str:
    return f"messari_details_{slugs.replace(',', '_')}"


def asset_metrics_catalog_key() -> str:
    return "messari_metrics_catalog"


def exchanges_key(limit=100, page=1) -> str:
    return f"messari_exchanges_{limit}_{page}"

def exchange_key(exchange_id) -> str:
    return f"messari_exchange_{exchange_id}"

def timeseries_key(slug, metric, granularity) -> str:
    return f"messari_ts_{slug}_{metric}_{granularity}"