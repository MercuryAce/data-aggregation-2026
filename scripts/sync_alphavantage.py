#!/usr/bin/env python3
"""Fetch Alpha Vantage data and write it to the ApiCache store."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app
from clients import av_client
from services import av_cache_keys, cache_store

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SOURCE = "alphavantage"
REQUEST_GAP_SECONDS = 13  # stay under free-tier ~5 req/min

TTL_NEWS = 60 * 60
TTL_QUOTE = 15 * 60
TTL_FX = 15 * 60
TTL_SPOT = 15 * 60
TTL_ETF_PROFILE = 24 * 60 * 60
TTL_DC_DAILY = 6 * 60 * 60

DEFAULT_ETFS = "IBIT,FBTC,GLD,SLV"
DEFAULT_PAIRS = "BTC/USD,ETH/USD,USD/EUR,USD/JPY,USD/GBP"
DEFAULT_CRYPTO_SYMBOLS = "BTC,ETH"
DEFAULT_METALS = "GOLD,SILVER"
DEFAULT_NEWS_TOPICS = "blockchain"
DEFAULT_NEWS_TICKERS = "CRYPTO:BTC,CRYPTO:ETH"


def _set(key: str, data, ttl_seconds: int) -> None:
    cache_store.set(key, data, ttl_seconds=ttl_seconds, source=SOURCE)
    logger.info("Synced %s", key)


def _throttle() -> None:
    time.sleep(REQUEST_GAP_SECONDS)


def sync_news(
    topics: str = DEFAULT_NEWS_TOPICS,
    tickers: str | None = None,
    limit: int = 50,
) -> None:
    data = av_client.get_news_sentiment(topics=topics, limit=limit)
    _set(av_cache_keys.news_key(topics, limit), data, TTL_NEWS)
    if tickers:
        _throttle()
        ticker_data = av_client.get_news_sentiment(tickers=tickers, limit=limit)
        _set(av_cache_keys.news_tickers_key(tickers, limit), ticker_data, TTL_NEWS)


def sync_etf(etfs: str = DEFAULT_ETFS) -> None:
    symbols = [s.strip().upper() for s in etfs.split(",") if s.strip()]
    for i, symbol in enumerate(symbols):
        if i:
            _throttle()
        profile = av_client.get_etf_profile(symbol)
        _set(av_cache_keys.etf_profile_key(symbol), profile, TTL_ETF_PROFILE)
        _throttle()
        quote = av_client.get_global_quote(symbol)
        _set(av_cache_keys.quote_key(symbol), quote, TTL_QUOTE)


def sync_fx(pairs: str = DEFAULT_PAIRS) -> None:
    pair_list = [p.strip() for p in pairs.split(",") if p.strip()]
    for i, pair in enumerate(pair_list):
        if "/" not in pair:
            logger.error("Invalid FX pair %r (expected FROM/TO)", pair)
            continue
        from_ccy, to_ccy = (part.strip().upper() for part in pair.split("/", 1))
        if i:
            _throttle()
        data = av_client.get_currency_exchange_rate(from_ccy, to_ccy)
        _set(av_cache_keys.fx_key(from_ccy, to_ccy), data, TTL_FX)


def sync_crypto_daily(
    symbols: str = DEFAULT_CRYPTO_SYMBOLS,
    market: str = "USD",
) -> None:
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    for i, symbol in enumerate(symbol_list):
        if i:
            _throttle()
        data = av_client.get_digital_currency_daily(symbol, market=market)
        _set(
            av_cache_keys.digital_currency_daily_key(symbol, market),
            data,
            TTL_DC_DAILY,
        )


def sync_metals(symbols: str = DEFAULT_METALS) -> None:
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    for i, symbol in enumerate(symbol_list):
        if i:
            _throttle()
        data = av_client.get_gold_silver_spot(symbol)
        _set(av_cache_keys.spot_key(symbol), data, TTL_SPOT)


def sync_all(
    etfs: str = DEFAULT_ETFS,
    pairs: str = DEFAULT_PAIRS,
    symbols: str = DEFAULT_CRYPTO_SYMBOLS,
    metals: str = DEFAULT_METALS,
    topics: str = DEFAULT_NEWS_TOPICS,
    tickers: str = DEFAULT_NEWS_TICKERS,
    limit: int = 50,
    market: str = "USD",
) -> None:
    sync_news(topics=topics, tickers=tickers, limit=limit)
    _throttle()
    sync_etf(etfs=etfs)
    _throttle()
    sync_fx(pairs=pairs)
    _throttle()
    sync_crypto_daily(symbols=symbols, market=market)
    _throttle()
    sync_metals(symbols=metals)


TASKS = {
    "news": sync_news,
    "etf": sync_etf,
    "fx": sync_fx,
    "crypto_daily": sync_crypto_daily,
    "metals": sync_metals,
    "all": sync_all,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Alpha Vantage data into ApiCache.")
    parser.add_argument(
        "--tasks",
        required=True,
        help="Comma-separated: news,etf,fx,crypto_daily,metals,all",
    )
    parser.add_argument("--etfs", type=str, default=DEFAULT_ETFS)
    parser.add_argument("--pairs", type=str, default=DEFAULT_PAIRS)
    parser.add_argument("--symbols", type=str, default=DEFAULT_CRYPTO_SYMBOLS)
    parser.add_argument("--metals", type=str, default=DEFAULT_METALS)
    parser.add_argument("--topics", type=str, default=DEFAULT_NEWS_TOPICS)
    parser.add_argument("--tickers", type=str, default=DEFAULT_NEWS_TICKERS)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--market", type=str, default="USD")
    parser.add_argument(
        "--no-throttle",
        action="store_true",
        help="Skip inter-request sleeps (tests / premium keys)",
    )
    args = parser.parse_args()

    if args.no_throttle:
        global REQUEST_GAP_SECONDS
        REQUEST_GAP_SECONDS = 0

    task_names = [name.strip() for name in args.tasks.split(",") if name.strip()]
    unknown = [name for name in task_names if name not in TASKS]
    if unknown:
        logger.error("Unknown task(s): %s", ", ".join(unknown))
        return 1

    with app.app_context():
        failed = 0
        for name in task_names:
            logger.info("Running task: %s", name)
            try:
                if name == "news":
                    sync_news(
                        topics=args.topics,
                        tickers=args.tickers,
                        limit=args.limit,
                    )
                elif name == "etf":
                    sync_etf(etfs=args.etfs)
                elif name == "fx":
                    sync_fx(pairs=args.pairs)
                elif name == "crypto_daily":
                    sync_crypto_daily(symbols=args.symbols, market=args.market)
                elif name == "metals":
                    sync_metals(symbols=args.metals)
                elif name == "all":
                    sync_all(
                        etfs=args.etfs,
                        pairs=args.pairs,
                        symbols=args.symbols,
                        metals=args.metals,
                        topics=args.topics,
                        tickers=args.tickers,
                        limit=args.limit,
                        market=args.market,
                    )
            except av_client.AvAPIError as exc:
                failed += 1
                logger.error("Task %s failed: %s", name, exc)
            except Exception as exc:
                failed += 1
                logger.exception("Task %s failed: %s", name, exc)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
