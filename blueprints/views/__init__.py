"""DB-read views blueprint — MySQL only; first-fill via populate_coingecko."""

from __future__ import annotations

from flask import Blueprint, request
from flask_caching import Cache

from handlers.guards import (
    guard_request,
    guarded_render,
    only_cache_success,
    rate_limit,
)
from models import Category, Exchange, GlobalStats, MarketCoin, TrendingSnapshot, db
from services import populate_coingecko as populate
from services.cache_store import CacheMissError

views_bp = Blueprint("views", __name__, url_prefix="")

MARKETS_PER_PAGE = 100


def init_views_blueprint(cache: Cache, limiter=None):
    # DB-backed pages: generous limits (app/DB protection only).
    # Override with VIEWS_RATE_LIMIT in .env (e.g. "120 per minute").
    view_limit = "120 per minute"

    @views_bp.route("/")
    @cache.cached(timeout=30, query_string=True, response_filter=only_cache_success)
    @rate_limit(limiter, view_limit, kind="views")
    def index():
        guard_request("index_last_hit")
        page = request.args.get("page", default=1, type=int) or 1
        if page < 1:
            page = 1

        def fetch_context():
            populate.ensure_markets()
            total = db.session.query(MarketCoin).count()
            if total == 0:
                raise CacheMissError("market_coins empty after ensure")
            total_pages = max(1, (total + MARKETS_PER_PAGE - 1) // MARKETS_PER_PAGE)
            if page > total_pages:
                page_num = total_pages
            else:
                page_num = page

            rows = (
                db.session.query(MarketCoin)
                .order_by(MarketCoin.market_cap_rank.asc())
                .offset((page_num - 1) * MARKETS_PER_PAGE)
                .limit(MARKETS_PER_PAGE)
                .all()
            )
            global_row = db.session.get(GlobalStats, 1)
            if global_row is None:
                raise CacheMissError("global_stats missing")

            last_updated = global_row.synced_at
            if rows:
                last_updated = max(last_updated, max(r.synced_at for r in rows))

            return {
                "coins": [r.to_market_dict() for r in rows],
                "global_stats": global_row.to_stats_dict(),
                "last_updated": last_updated,
                "page": page_num,
                "per_page": MARKETS_PER_PAGE,
                "total": total,
                "total_pages": total_pages,
            }

        return guarded_render("index.html", fetch_context)

    @views_bp.route("/exchanges")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, view_limit, kind="views")
    def exchanges():
        guard_request("exchanges_last_hit")

        def fetch_context():
            populate.ensure_exchanges()
            rows = (
                db.session.query(Exchange)
                .order_by(Exchange.trust_score_rank.asc())
                .all()
            )
            if not rows:
                raise CacheMissError("exchanges empty after ensure")
            return {
                "exchanges": [r.to_exchange_dict() for r in rows],
                "last_updated": max(r.synced_at for r in rows),
            }

        return guarded_render("exchanges.html", fetch_context)

    @views_bp.route("/trending")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, view_limit, kind="views")
    def trending():
        guard_request("trending_last_hit")

        def fetch_context():
            populate.ensure_trending()
            snap = db.session.get(TrendingSnapshot, "latest")
            if snap is None or not snap.payload:
                raise CacheMissError("trending snapshot missing")
            return {"trending": snap.payload, "last_updated": snap.synced_at}

        return guarded_render("trending.html", fetch_context)

    @views_bp.route("/categories")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, view_limit, kind="views")
    def categories():
        guard_request("categories_last_hit")

        def fetch_context():
            populate.ensure_categories()
            rows = (
                db.session.query(Category)
                .order_by(Category.market_cap.desc())
                .all()
            )
            if not rows:
                raise CacheMissError("categories empty after ensure")
            return {
                "categories": [r.to_category_dict() for r in rows],
                "last_updated": max(r.synced_at for r in rows),
            }

        return guarded_render("categories.html", fetch_context)

    return views_bp
