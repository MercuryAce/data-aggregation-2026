"""T2 (partial): Messari cache key builders are pure and deterministic."""

from services import messari_cache_keys as keys


def test_assets_key():
    assert keys.assets_key(20, 1) == "messari_assets_20_1"
    assert keys.assets_key(limit=50, page=2) == "messari_assets_50_2"


def test_asset_details_key_replaces_commas():
    assert keys.asset_details_key("bitcoin,ethereum") == "messari_details_bitcoin_ethereum"
    assert keys.asset_details_key("solana") == "messari_details_solana"


def test_timeseries_and_exchange_keys():
    assert keys.timeseries_key("bitcoin", "price", "1d") == "messari_ts_bitcoin_price_1d"
    assert keys.exchanges_key(100, 1) == "messari_exchanges_100_1"
    assert keys.exchange_key("binance") == "messari_exchange_binance"
    assert keys.asset_metrics_catalog_key() == "messari_metrics_catalog"
