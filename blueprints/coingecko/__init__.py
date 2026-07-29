from flask import Blueprint, abort, jsonify, request, render_template
from flask_caching import Cache

from handlers.guards import (
    only_cache_success,
    guard_request,
    guarded_json,
    guarded_render,
    rate_limit,
)
from services.coingecko_service import (
    get_categories,
    get_exchange_details,
    get_exchanges,
    get_global,
    get_ohlc,
    get_search,
    get_trending,
)
from services import market_service
from services.timeseries_store import get_price_history

cg_bp = Blueprint("cg", __name__, url_prefix="")


def init_cg_blueprint(cache: Cache, limiter=None):
    @cg_bp.route("/")
    @cache.cached(timeout=30, query_string=True, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def index():
        guard_request("index_last_hit", cooldown=5)
        page = request.args.get("page", default=1, type=int) or 1
        per_page = request.args.get("per_page", default=100, type=int) or 100
        per_page = min(max(per_page, 25), 250)

        def fetch_context():
            coins, meta = market_service.get_unified_markets(
                page=page,
                per_page=per_page,
                max_pages=10,
            )
            global_payload, global_at = get_global()
            last_updated = max(meta["last_updated"], global_at)
            return {
                "coins": coins,
                "global_stats": global_payload["data"],
                "last_updated": last_updated,
                "last_updated_age": meta.get("last_updated_age"),
                "price_source": meta.get("price_source"),
                "page": meta.get("page", page),
                "per_page": meta.get("per_page", per_page),
                "total": meta.get("total", len(coins)),
                "total_pages": meta.get("total_pages", 1),
            }

        return guarded_render("index.html", fetch_context)

    @cg_bp.route("/coin/<coin_id>")
    @cache.cached(timeout=30, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def coin(coin_id):
        guard_request(f"coin_last_hit_{coin_id}", cooldown=3)

        def fetch_context():
            coin_data, meta = market_service.get_unified_coin(coin_id)
            return {
                "coin": coin_data,
                "last_updated": meta["last_updated"],
                "last_updated_age": meta.get("last_updated_age"),
                "price_source": meta.get("price_source"),
            }

        return guarded_render("coin.html", fetch_context)

    @cg_bp.route("/api/live-prices")
    @rate_limit(limiter, "30 per minute")
    def live_prices():
        raw = request.args.get("ids", "", type=str)
        ids = [part.strip() for part in raw.split(",") if part.strip()]
        if not ids:
            return jsonify({"error": "ids query parameter required"}), 400
        if len(ids) > 100:
            return jsonify({"error": "Too many ids (max 100)"}), 400

        guard_request("live_prices_last_hit", cooldown=1)

        def fetch():
            payload = market_service.get_live_prices(ids)
            # JSON-serialize datetime
            last_updated = payload.get("last_updated")
            if last_updated is not None:
                payload = dict(payload)
                payload["last_updated"] = last_updated.isoformat()
            return payload

        return guarded_json(fetch)

    @cg_bp.route("/api/price-history/<coin_id>")
    @cache.cached(timeout=300, query_string=True, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def price_history(coin_id):
        allowed_days = {7, 30, 90, 365}
        days = request.args.get("days", default=30, type=int)
        if days not in allowed_days:
            return jsonify({"error": "Invalid days parameter."}), 400

        guard_request(f"price_history_last_hit_{coin_id}_{days}", cooldown=3)

        def fetch():
            # Prefer Mongo ticks when available; fall back to CG OHLC cache
            from datetime import datetime, timedelta, timezone

            since = datetime.now(timezone.utc) - timedelta(days=days)
            ticks = get_price_history(coin_id, since=since, limit=2000)
            if len(ticks) >= 2:
                # OHLC-compatible: [ts_ms, open, high, low, close] approx from ticks
                series = []
                for tick in ticks:
                    ts = tick.get("timestamp")
                    price = tick.get("price")
                    if ts is None or price is None:
                        continue
                    ts_ms = int(ts.timestamp() * 1000) if hasattr(ts, "timestamp") else ts
                    series.append([ts_ms, price, price, price, price])
                return series
            return get_ohlc(coin_id, days=days)[0]

        return guarded_json(fetch)

    @cg_bp.route("/trending")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def trending():
        guard_request("trending_last_hit", cooldown=5)

        def fetch_context():
            trending_data, fetched_at = get_trending()
            return {"trending": trending_data, "last_updated": fetched_at}

        return guarded_render("trending.html", fetch_context)

    @cg_bp.route("/categories")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def categories():
        guard_request("categories_last_hit", cooldown=5)

        def fetch_context():
            categories_data, fetched_at = get_categories()
            return {"categories": categories_data, "last_updated": fetched_at}

        return guarded_render("categories.html", fetch_context)

    @cg_bp.route("/search")
    @cache.cached(timeout=60, query_string=True, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def search():
        query = request.args.get("q", "", type=str).strip()
        if not query:
            abort(400)

        guard_request(f"search_last_hit_{query.lower()}", cooldown=3)

        def fetch_context():
            results, fetched_at = get_search(query)
            return {"query": query, "results": results, "last_updated": fetched_at}

        return guarded_render("search.html", fetch_context)

    @cg_bp.route("/exchanges")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def exchanges():
        guard_request("exchanges_last_hit", cooldown=5)

        def fetch_context():
            exchanges_data, fetched_at = get_exchanges()
            return {"exchanges": exchanges_data, "last_updated": fetched_at}

        return guarded_render("exchanges.html", fetch_context)

    @cg_bp.route("/exchange/<exchange_id>")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def exchange_detail(exchange_id):
        guard_request(f"exchange_last_hit_{exchange_id}", cooldown=3)

        def fetch_context():
            exchange, fetched_at = get_exchange_details(exchange_id)
            return {"exchange": exchange, "last_updated": fetched_at}

        return guarded_render("exchange.html", fetch_context)

    @cg_bp.route("/news")
    def news():
        return render_template("news.html")

    return cg_bp
