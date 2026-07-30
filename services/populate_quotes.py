"""Populate asset_quotes: oracle mids + venue bid/ask (display only)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from clients import av_client, binance_client, cg_client, cmc_client, defillama_client
from clients import kraken_client, okx_client
from models import AssetQuote, MarketCoin, db
from services.asset_identity import defillama_quote_key, normalize_platforms
from services.venue_pairs import (
    binance_pair_for_symbol,
    kraken_pair_for_symbol,
    okx_pair_for_symbol,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _upsert_quote(
    *,
    cg_id: str,
    venue: str,
    kind: str,
    pair: str | None,
    bid: float | None,
    ask: float | None,
    last: float | None,
    meta: dict | None = None,
    now: datetime | None = None,
) -> None:
    now = now or _utcnow()
    row = db.session.get(AssetQuote, (cg_id, venue)) or AssetQuote(
        cg_id=cg_id, venue=venue
    )
    row.kind = kind
    row.pair = pair
    row.bid = bid
    row.ask = ask
    row.last = last
    row.meta = meta
    row.synced_at = now
    db.session.merge(row)


def _top_coins(limit: int) -> list[MarketCoin]:
    return (
        db.session.query(MarketCoin)
        .order_by(MarketCoin.market_cap_rank.asc())
        .limit(limit)
        .all()
    )


def patch_oracle_quotes(*, limit: int = 20) -> int:
    """Store CG / CMC / DefiLlama / Alpha Vantage mids for top assets."""
    coins = _top_coins(limit)
    if not coins:
        return 0
    now = _utcnow()
    updated = 0

    # CoinGecko: one markets page is enough for top 20–250
    try:
        cg_rows = cg_client.get_market_data(vs_currency="usd", limit=max(limit, 50), page=1)
        by_id = {r.get("id"): r for r in (cg_rows or []) if isinstance(r, dict)}
    except Exception:
        logger.exception("CG markets failed for oracle spread")
        by_id = {}

    for coin in coins:
        price = None
        row = by_id.get(coin.cg_id)
        if row and row.get("current_price") is not None:
            try:
                price = float(row["current_price"])
            except (TypeError, ValueError):
                price = None
        if price is None and coin.current_price is not None:
            price = float(coin.current_price)
        if price is not None:
            _upsert_quote(
                cg_id=coin.cg_id,
                venue="coingecko",
                kind="oracle",
                pair=None,
                bid=None,
                ask=None,
                last=price,
                now=now,
            )
            updated += 1

    # DefiLlama batch
    try:
        key_to_cg = {}
        for coin in coins:
            key = defillama_quote_key(coin.cg_id, normalize_platforms(coin.platforms))
            key_to_cg.setdefault(key, coin.cg_id)
        if key_to_cg:
            payload = defillama_client.get_current_prices(",".join(key_to_cg.keys()))
            coin_map = (payload or {}).get("coins") if isinstance(payload, dict) else {}
            for key, info in (coin_map or {}).items():
                if not isinstance(info, dict) or info.get("price") is None:
                    continue
                cg_id = key_to_cg.get(key)
                if not cg_id and key.startswith("coingecko:"):
                    cg_id = key.split(":", 1)[1]
                if not cg_id:
                    continue
                _upsert_quote(
                    cg_id=cg_id,
                    venue="defillama",
                    kind="oracle",
                    pair=key,
                    bid=None,
                    ask=None,
                    last=float(info["price"]),
                    now=now,
                )
                updated += 1
    except Exception:
        logger.exception("DefiLlama oracle spread failed")

    # CMC listings (credit cost) — best-effort match by slug/symbol
    try:
        listings = cmc_client.get_listings_latest(start=1, limit=min(200, max(limit, 50)))
        rows = listings.get("data") if isinstance(listings, dict) else []
        by_slug = {(r.get("slug") or "").lower(): r for r in rows or []}
        by_symbol: dict[str, list] = {}
        for r in rows or []:
            sym = (r.get("symbol") or "").upper()
            if sym:
                by_symbol.setdefault(sym, []).append(r)
        for coin in coins:
            item = by_slug.get(coin.cg_id)
            if item is None:
                matches = by_symbol.get((coin.symbol or "").upper()) or []
                item = matches[0] if len(matches) == 1 else None
            if item is None:
                continue
            usd = (item.get("quote") or {}).get("USD") or {}
            if usd.get("price") is None:
                continue
            _upsert_quote(
                cg_id=coin.cg_id,
                venue="cmc",
                kind="oracle",
                pair=None,
                bid=None,
                ask=None,
                last=float(usd["price"]),
                meta={"cmc_id": item.get("id"), "cmc_slug": item.get("slug")},
                now=now,
            )
            updated += 1
    except Exception:
        logger.exception("CMC oracle spread failed")

    # Alpha Vantage: BTC (+ ETH if free tier allows) — 1 req/sec, sparse
    import time

    av_symbols = [("bitcoin", "BTC"), ("ethereum", "ETH")]
    for i, (cg_id, fx) in enumerate(av_symbols):
        if not any(c.cg_id == cg_id for c in coins):
            continue
        if i:
            time.sleep(1.1)
        try:
            payload = av_client.get_currency_exchange_rate(
                from_currency=fx, to_currency="USD"
            )
            block = (payload or {}).get("Realtime Currency Exchange Rate") or {}
            rate = block.get("5. Exchange Rate")
            bid = block.get("8. Bid Price")
            ask = block.get("9. Ask Price")
            if rate is None:
                continue
            _upsert_quote(
                cg_id=cg_id,
                venue="alphavantage",
                kind="oracle",
                pair=f"{fx}/USD",
                bid=float(bid) if bid else None,
                ask=float(ask) if ask else None,
                last=float(rate),
                now=now,
            )
            updated += 1
        except Exception:
            logger.exception("Alpha Vantage oracle failed for %s", cg_id)

    db.session.commit()
    logger.info("Oracle quotes upserted (~%s writes)", updated)
    return updated


def patch_venue_quotes(*, limit: int = 20, include_okx: bool = True) -> int:
    """Store Binance / Kraken (/ OKX) bid/ask for mapped top symbols."""
    coins = _top_coins(limit)
    if not coins:
        return 0
    now = _utcnow()
    updated = 0

    # Binance: batch bookTicker when possible
    binance_jobs = []
    for coin in coins:
        pair = binance_pair_for_symbol(coin.symbol)
        if pair:
            binance_jobs.append((coin, pair))
    try:
        symbols = [p for _, p in binance_jobs]
        tickers = binance_client.get_book_tickers(symbols) if symbols else []
        by_sym = {
            (t.get("symbol") or "").upper(): t
            for t in tickers
            if isinstance(t, dict)
        }
        for coin, pair in binance_jobs:
            t = by_sym.get(pair.upper())
            if not t:
                continue
            bid = float(t["bidPrice"]) if t.get("bidPrice") is not None else None
            ask = float(t["askPrice"]) if t.get("askPrice") is not None else None
            mid = (bid + ask) / 2.0 if bid is not None and ask is not None else None
            _upsert_quote(
                cg_id=coin.cg_id,
                venue="binance",
                kind="exchange",
                pair=pair,
                bid=bid,
                ask=ask,
                last=mid,
                now=now,
            )
            updated += 1
    except Exception:
        logger.exception("Binance venue quotes failed; trying per-symbol")
        for coin, pair in binance_jobs:
            try:
                t = binance_client.get_book_ticker(pair)
                bid = float(t["bidPrice"]) if t.get("bidPrice") is not None else None
                ask = float(t["askPrice"]) if t.get("askPrice") is not None else None
                mid = (bid + ask) / 2.0 if bid is not None and ask is not None else None
                _upsert_quote(
                    cg_id=coin.cg_id,
                    venue="binance",
                    kind="exchange",
                    pair=pair,
                    bid=bid,
                    ask=ask,
                    last=mid,
                    now=now,
                )
                updated += 1
            except Exception:
                logger.debug("Binance miss %s", pair, exc_info=True)

    # Kraken: one pair per request (small N)
    for coin in coins:
        pair = kraken_pair_for_symbol(coin.symbol)
        if not pair:
            continue
        try:
            result = kraken_client.get_ticker(pair)
            bid, ask, last = kraken_client.parse_bid_ask(result)
            mid = last
            if mid is None and bid is not None and ask is not None:
                mid = (bid + ask) / 2.0
            _upsert_quote(
                cg_id=coin.cg_id,
                venue="kraken",
                kind="exchange",
                pair=pair,
                bid=bid,
                ask=ask,
                last=mid,
                now=now,
            )
            updated += 1
        except Exception:
            logger.debug("Kraken miss %s", pair, exc_info=True)

    if include_okx:
        for coin in coins:
            pair = okx_pair_for_symbol(coin.symbol)
            if not pair:
                continue
            try:
                t = okx_client.get_ticker(pair)
                if not t:
                    continue
                bid = float(t["bidPx"]) if t.get("bidPx") not in (None, "") else None
                ask = float(t["askPx"]) if t.get("askPx") not in (None, "") else None
                last = float(t["last"]) if t.get("last") not in (None, "") else None
                _upsert_quote(
                    cg_id=coin.cg_id,
                    venue="okx",
                    kind="exchange",
                    pair=pair,
                    bid=bid,
                    ask=ask,
                    last=last,
                    now=now,
                )
                updated += 1
            except Exception:
                logger.debug("OKX miss %s", pair, exc_info=True)

    db.session.commit()
    logger.info("Venue quotes upserted (~%s writes)", updated)
    return updated


def quotes_for_coin(cg_id: str) -> dict:
    """Bundle quotes + spread summary for templates / API."""
    rows = (
        db.session.query(AssetQuote)
        .filter(AssetQuote.cg_id == cg_id)
        .order_by(AssetQuote.kind.asc(), AssetQuote.venue.asc())
        .all()
    )
    oracles = [r.to_dict() for r in rows if r.kind == "oracle"]
    exchanges = [r.to_dict() for r in rows if r.kind == "exchange"]

    def _spread(items: list[dict]) -> dict | None:
        mids = [i.get("mid") or i.get("last") for i in items]
        mids = [m for m in mids if m is not None]
        if len(mids) < 2:
            return None
        lo, hi = min(mids), max(mids)
        return {
            "low": lo,
            "high": hi,
            "abs": hi - lo,
            "pct": ((hi - lo) / lo * 100.0) if lo else None,
            "n": len(mids),
        }

    return {
        "oracles": oracles,
        "exchanges": exchanges,
        "oracle_spread": _spread(oracles),
        "venue_spread": _spread(exchanges),
    }
