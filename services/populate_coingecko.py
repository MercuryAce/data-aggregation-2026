"""Populate typed MySQL view tables from CoinGecko (first-fill + force refresh)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager

from clients import cg_client
from models import (
    Category,
    Exchange,
    GlobalStats,
    MarketCoin,
    SyncLock,
    TrendingCoin,
    TrendingSnapshot,
    db,
)
from services.asset_identity import merge_external_ids
from services.cache_store import CacheMissError

logger = logging.getLogger(__name__)

SOURCE = "coingecko"
LOCK_STALE_SECONDS = 120
MARKETS_PAGES = 4  # 4 * 250 = 1000 coins for prototype
MARKETS_PER_PAGE = 250


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _table_empty(model) -> bool:
    return db.session.query(model).first() is None


@contextmanager
def _sync_lock(name: str):
    """Acquire a named lock row; skip work if another fill is in progress."""
    now = _utcnow()
    lock = db.session.get(SyncLock, name)
    if lock is None:
        lock = SyncLock(name=name, status="idle")
        db.session.add(lock)
        db.session.commit()

    if lock.status == "running" and lock.locked_at:
        locked_at = lock.locked_at
        if locked_at.tzinfo is None:
            locked_at = locked_at.replace(tzinfo=timezone.utc)
        if now - locked_at < timedelta(seconds=LOCK_STALE_SECONDS):
            raise CacheMissError(f"Sync already in progress for {name}")

    lock.status = "running"
    lock.locked_at = now
    lock.message = None
    db.session.commit()
    try:
        yield
        lock.status = "idle"
        lock.message = "ok"
        lock.locked_at = _utcnow()
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        lock = db.session.get(SyncLock, name)
        if lock is not None:
            lock.status = "error"
            lock.message = str(exc)[:500]
            lock.locked_at = _utcnow()
            db.session.commit()
        raise


def populate_markets(*, pages: int = MARKETS_PAGES, per_page: int = MARKETS_PER_PAGE) -> int:
    now = _utcnow()
    collected: list[dict] = []
    for page in range(1, pages + 1):
        batch = cg_client.get_market_data(vs_currency="usd", limit=per_page, page=page)
        if not batch:
            break
        collected.extend(batch)

    for row in collected:
        cg_id = row.get("id")
        if not cg_id:
            continue
        coin = db.session.get(MarketCoin, cg_id) or MarketCoin(cg_id=cg_id)
        coin.market_cap_rank = row.get("market_cap_rank")
        coin.symbol = (row.get("symbol") or "").lower()
        coin.name = row.get("name") or cg_id
        coin.image = row.get("image")
        coin.current_price = row.get("current_price")
        coin.price_change_percentage_24h = row.get("price_change_percentage_24h")
        coin.market_cap = row.get("market_cap")
        coin.total_volume = row.get("total_volume")
        coin.high_24h = row.get("high_24h")
        coin.low_24h = row.get("low_24h")
        coin.fully_diluted_valuation = row.get("fully_diluted_valuation")
        coin.total_supply = row.get("total_supply")
        coin.circulating_supply = row.get("circulating_supply")
        coin.external_ids = merge_external_ids(coin.external_ids, coingecko=cg_id)
        coin.structure_synced_at = now
        coin.synced_at = now
        coin.source = SOURCE
        db.session.merge(coin)
    db.session.commit()
    logger.info("Populated market_coins (%s rows)", len(collected))
    return len(collected)


def populate_global() -> None:
    payload = cg_client.get_global()
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise CacheMissError("CoinGecko global payload missing data")

    row = db.session.get(GlobalStats, 1) or GlobalStats(id=1)
    row.active_cryptocurrencies = data.get("active_cryptocurrencies")
    row.markets = data.get("markets")
    row.market_cap_change_percentage_24h_usd = data.get(
        "market_cap_change_percentage_24h_usd"
    )
    # CG nests total volume change under total_volume; template expects volume_change_percentage_24h_usd
    vol_change = data.get("volume_change_percentage_24h_usd")
    if vol_change is None:
        # older/alternate shapes — leave None
        pass
    row.volume_change_percentage_24h_usd = vol_change or 0
    row.payload = data
    row.synced_at = _utcnow()
    row.source = SOURCE
    db.session.merge(row)
    db.session.commit()
    logger.info("Populated global_stats")


def populate_exchanges(*, per_page: int = 100, page: int = 1) -> int:
    rows = cg_client.get_exchanges(per_page=per_page, page=page) or []
    now = _utcnow()
    for row in rows:
        ex_id = row.get("id")
        if not ex_id:
            continue
        exchange = db.session.get(Exchange, ex_id) or Exchange(exchange_id=ex_id)
        exchange.name = row.get("name") or ex_id
        exchange.image = row.get("image")
        exchange.url = row.get("url")
        exchange.description = row.get("description")
        exchange.country = row.get("country")
        exchange.year_established = row.get("year_established")
        exchange.trust_score = row.get("trust_score")
        exchange.trust_score_rank = row.get("trust_score_rank")
        exchange.trade_volume_24h_btc = row.get("trade_volume_24h_btc")
        exchange.synced_at = now
        exchange.source = SOURCE
        db.session.merge(exchange)
    db.session.commit()
    logger.info("Populated exchanges (%s rows)", len(rows))
    return len(rows)


def populate_trending() -> None:
    payload = cg_client.get_trending() or {}
    now = _utcnow()

    snap = db.session.get(TrendingSnapshot, "latest") or TrendingSnapshot(id="latest")
    snap.payload = payload
    snap.synced_at = now
    snap.source = SOURCE
    db.session.merge(snap)

    for entry in payload.get("coins") or []:
        item = entry.get("item") if isinstance(entry, dict) else None
        if not isinstance(item, dict):
            continue
        cg_id = item.get("id")
        if not cg_id:
            continue
        coin = db.session.get(TrendingCoin, cg_id) or TrendingCoin(cg_id=cg_id)
        coin.score = entry.get("score") if isinstance(entry, dict) else item.get("score")
        coin.name = item.get("name") or cg_id
        coin.symbol = item.get("symbol") or ""
        coin.image = item.get("thumb") or item.get("small") or item.get("large")
        coin.market_cap_rank = item.get("market_cap_rank")
        coin.payload = entry
        coin.synced_at = now
        coin.source = SOURCE
        db.session.merge(coin)

    db.session.commit()
    logger.info("Populated trending snapshot + coins")


def populate_categories() -> int:
    rows = cg_client.get_categories(order="market_cap_desc") or []
    now = _utcnow()
    for row in rows:
        if not isinstance(row, dict):
            continue
        cat_id = row.get("id") or row.get("name")
        if not cat_id:
            continue
        cat = db.session.get(Category, cat_id) or Category(category_id=str(cat_id))
        cat.name = row.get("name") or str(cat_id)
        cat.content = row.get("content")
        cat.market_cap = row.get("market_cap")
        cat.market_cap_change_24h = row.get("market_cap_change_24h")
        cat.volume_24h = row.get("volume_24h")
        cat.top_3_coins = row.get("top_3_coins") or []
        cat.synced_at = now
        cat.source = SOURCE
        db.session.merge(cat)
    db.session.commit()
    logger.info("Populated categories (%s rows)", len(rows))
    return len(rows)


def ensure_markets(*, force: bool = False) -> None:
    if not force and not _table_empty(MarketCoin):
        return
    with _sync_lock("markets"):
        if not force and not _table_empty(MarketCoin):
            return
        populate_markets()
        populate_global()


def ensure_exchanges(*, force: bool = False) -> None:
    if not force and not _table_empty(Exchange):
        return
    with _sync_lock("exchanges"):
        if not force and not _table_empty(Exchange):
            return
        populate_exchanges()


def ensure_trending(*, force: bool = False) -> None:
    snap = db.session.get(TrendingSnapshot, "latest")
    if not force and snap is not None and snap.payload:
        return
    with _sync_lock("trending"):
        snap = db.session.get(TrendingSnapshot, "latest")
        if not force and snap is not None and snap.payload:
            return
        populate_trending()


def ensure_categories(*, force: bool = False) -> None:
    if not force and not _table_empty(Category):
        return
    with _sync_lock("categories"):
        if not force and not _table_empty(Category):
            return
        populate_categories()


def ensure_all(*, force: bool = False) -> None:
    ensure_markets(force=force)
    ensure_exchanges(force=force)
    ensure_trending(force=force)
    ensure_categories(force=force)
