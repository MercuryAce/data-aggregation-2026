"""Cache key builders for CoinMarketCap snapshots."""


def listings_key(start=1, limit=100, convert="USD") -> str:
    return f"cmc_listings_{convert}_{start}_{limit}"


def quotes_key(ids: str, convert="USD") -> str:
    return f"cmc_quotes_{convert}_{ids.replace(',', '_')}"


def map_key(listing_status="active", limit=5000) -> str:
    return f"cmc_map_{listing_status}_{limit}"
