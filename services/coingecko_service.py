from datetime import datetime

from services import cache_keys, cache_store
from services.cache_store import CacheMissError


def _cached(key: str) -> tuple[dict | list, datetime]:
    entry = cache_store.get(key)
    if entry is None:
        raise CacheMissError(f"Cache miss for key: {key}")
    return entry.payload, entry.fetched_at


def get_coins_list(include_platform=False) -> tuple[dict | list, datetime]:
    return _cached(cache_keys.coin_list_key(include_platform))


def get_market_data(vs_currency="usd", limit=250, page=1):
    return _cached(cache_keys.markets_key(vs_currency, limit, page))


def get_coin_details(coin_id, vs_currency="usd"):
    return _cached(cache_keys.coin_key(coin_id, vs_currency))


def get_coin_tickers(coin_id):
    return _cached(cache_keys.coin_tickers_key(coin_id))


def get_coin_history(coin_id, date, localization=False):
    return _cached(cache_keys.coin_history_key(coin_id, date, localization))


def get_market_chart(coin_id, days=30, vs_currency="usd"):
    return _cached(cache_keys.market_chart_key(coin_id, days, vs_currency))


def get_market_chart_range(coin_id, from_ts, to_ts, vs_currency="usd"):
    return _cached(cache_keys.market_chart_range_key(coin_id, from_ts, to_ts, vs_currency))


def get_ohlc(coin_id, days=30, vs_currency="usd"):
    return _cached(cache_keys.ohlc_key(coin_id, days, vs_currency))


def get_ohlc_range(coin_id, from_ts, to_ts, vs_currency="usd", interval="daily"):
    return _cached(cache_keys.ohlc_range_key(coin_id, from_ts, to_ts, vs_currency, interval))


def get_categories(order="market_cap_desc"):
    return _cached(cache_keys.categories_key(order))


def get_categories_list():
    return _cached(cache_keys.categories_list_key())


def get_simple_price(ids, vs_currencies="usd"):
    return _cached(cache_keys.simple_price_key(ids, vs_currencies))


def get_supported_vs_currencies():
    return _cached(cache_keys.supported_vs_currencies_key())


def get_exchanges(per_page=100, page=1):
    return _cached(cache_keys.exchanges_key(per_page, page))


def get_exchanges_list():
    return _cached(cache_keys.exchanges_list_key())


def get_exchange_details(exchange_id):
    return _cached(cache_keys.exchange_details_key(exchange_id))


def get_search(query):
    if not query:
        raise CacheMissError("Query is required")
    return _cached(cache_keys.search_key(query))


def get_trending():
    return _cached(cache_keys.trending_key())


def get_global():
    return _cached(cache_keys.global_key())


def get_global_market_cap_chart(days=30, vs_currency="usd"):
    return _cached(cache_keys.global_market_cap_chart_key(days, vs_currency))
