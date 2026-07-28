"""T2 (partial): CoinGecko cache key builders."""

from services import cache_keys as keys


def test_markets_and_coin_keys():
    assert keys.markets_key("usd", 250, 1) == "markets_usd_250_1"
    assert keys.coin_key("bitcoin", "usd") == "coin_bitcoin_usd"
    assert keys.ohlc_key("bitcoin", 30, "usd") == "ohlc_bitcoin_30_usd"


def test_search_key_normalises_query():
    assert keys.search_key("  BitCoin  ") == "search_bitcoin"
    assert keys.search_key("a" * 80) == "search_" + ("a" * 55)


def test_static_and_collection_keys():
    assert keys.trending_key() == "trending"
    assert keys.global_key() == "global"
    assert keys.categories_key() == "categories_market_cap_desc"
    assert keys.exchanges_key(100, 2) == "exchanges_100_2"
    assert keys.exchange_details_key("binance") == "exchange_details_binance"
