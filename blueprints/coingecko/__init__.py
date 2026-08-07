from flask import Blueprint, abort, jsonify, request, render_template
from flask_caching import Cache

from handlers.guards import (
    only_cache_success,
    guard_request,
    guarded_json,
    guarded_render,
    rate_limit,
)
from models import db, MarketCoin
from services.cache_store import CacheMissError
from services.coingecko_service import (
    get_coin_details,
    get_exchange_details,
    get_ohlc,
    get_search,
)
from services.analysis_client import fetch_analysis

cg_bp = Blueprint("cg", __name__, url_prefix="")


def init_cg_blueprint(cache: Cache, limiter=None):
    """Secondary CG routes (coin detail, search, news, exchange detail, OHLC).

    Market / Exchanges / Trending / Categories live on the views blueprint.
    """

    @cg_bp.route("/coin/<coin_id>")
    @cache.cached(timeout=30, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def coin(coin_id):
        guard_request(f"coin_last_hit_{coin_id}", cooldown=3)

        def fetch_context():
            coin_data, fetched_at = get_coin_details(coin_id)
            quotes = None
            try:
                from services.populate_quotes import quotes_for_coin

                quotes = quotes_for_coin(coin_id)
            except Exception:
                quotes = None
            return {
                "coin": coin_data,
                "last_updated": fetched_at,
                "quotes": quotes,
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

    @cg_bp.route("/coin/analysis/<coin_id>")
    @cache.cached(timeout=60, query_string=True, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def coin_analysis(coin_id):
        guard_request(f"coin_analysis_last_hit_{coin_id}", cooldown=3)
        def fetch_context():
            row = db.session.get(MarketCoin, coin_id)
            if row is None:
                raise CacheMissError(f"unknown coin: {coin_id}")
            return {
                "coin": row.to_market_dict(),
                "coin_id": coin_id,
                "vs": request.args.get("vs", "gold"),
                "window": request.args.get("window", 90, type=int),
                "analysis": fetch_analysis(
                    coin_id, 
                    vs=request.args.get("vs", "gold"), 
                    window=request.args.get("window", 90, type=int)
                )
            }
        return guarded_render("analysis.html", fetch_context)

    return cg_bp
