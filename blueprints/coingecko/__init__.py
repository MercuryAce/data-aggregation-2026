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
    get_coin_details,
    get_exchange_details,
    get_exchanges,
    get_global,
    get_market_data,
    get_ohlc,
    get_search,
    get_trending,
)
from services import cache_keys, cache_store

cg_bp = Blueprint("cg", __name__, url_prefix="")

# Synced CoinGecko markets pages use this page size (see scripts/sync_coingecko.py).
MARKETS_PAGE_SIZE = 250
MAX_MARKET_PAGES = 10


def _markets_total_pages(vs_currency="usd", limit=MARKETS_PAGE_SIZE) -> int:
    total = 0
    for page in range(1, MAX_MARKET_PAGES + 1):
        if cache_store.get(cache_keys.markets_key(vs_currency, limit, page)) is None:
            break
        total = page
    return max(total, 1)


def init_cg_blueprint(cache: Cache, limiter=None):
    @cg_bp.route("/")
    @cache.cached(timeout=30, query_string=True, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def index():
        guard_request("index_last_hit", cooldown=5)
        page = request.args.get("page", default=1, type=int) or 1
        if page < 1:
            page = 1

        def fetch_context():
            coins, coins_at = get_market_data(
                vs_currency="usd",
                limit=MARKETS_PAGE_SIZE,
                page=page,
            )
            global_payload, global_at = get_global()
            total_pages = _markets_total_pages()
            return {
                "coins": coins,
                "global_stats": global_payload["data"],
                "last_updated": max(coins_at, global_at),
                "page": page,
                "per_page": MARKETS_PAGE_SIZE,
                "total": total_pages * MARKETS_PAGE_SIZE,
                "total_pages": total_pages,
            }

        return guarded_render("index.html", fetch_context)

    @cg_bp.route("/coin/<coin_id>")
    @cache.cached(timeout=30, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def coin(coin_id):
        guard_request(f"coin_last_hit_{coin_id}", cooldown=3)

        def fetch_context():
            coin_data, fetched_at = get_coin_details(coin_id)
            return {
                "coin": coin_data,
                "last_updated": fetched_at,
            }

        return guarded_render("coin.html", fetch_context)

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
