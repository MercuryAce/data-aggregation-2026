from flask import Blueprint
from flask_caching import Cache

from handlers.guards import only_cache_success, guard_request, guarded_render, rate_limit
from services.messari_service import (
    get_asset_details,
    get_asset_metrics_catalog,
    get_asset_timeseries,
    get_assets,
    get_exchange,
    get_exchanges,
)

DEFAULT_DETAIL_SLUGS = "bitcoin,ethereum"
DEFAULT_ASSETS_LIMIT = 20
DEFAULT_EXCHANGES_LIMIT = 100

messari_bp = Blueprint("messari", __name__, url_prefix="/messari")


def init_messari_blueprint(cache: Cache, limiter=None):
    @messari_bp.route("/")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def index():
        guard_request("messari_index_last_hit", cooldown=5)

        def fetch_context():
            assets_payload, assets_at = get_assets(
                limit=DEFAULT_ASSETS_LIMIT, page=1
            )
            details_payload, details_at = get_asset_details(DEFAULT_DETAIL_SLUGS)
            return {
                "assets": assets_payload,
                "details": details_payload,
                "last_updated": max(assets_at, details_at),
            }

        return guarded_render("messari/index.html", fetch_context)

    @messari_bp.route("/assets")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def assets():
        guard_request("messari_assets_last_hit", cooldown=5)

        def fetch_context():
            payload, fetched_at = get_assets(limit=DEFAULT_ASSETS_LIMIT, page=1)
            return {"assets": payload, "last_updated": fetched_at}

        return guarded_render("messari/assets.html", fetch_context)

    @messari_bp.route("/asset/<slug>")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def asset_detail(slug):
        guard_request(f"messari_asset_last_hit_{slug}", cooldown=3)

        def fetch_context():
            details_payload, fetched_at = get_asset_details(slug)
            return {
                "slug": slug,
                "details": details_payload,
                "last_updated": fetched_at,
            }

        return guarded_render("messari/asset.html", fetch_context)

    @messari_bp.route("/asset/<slug>/timeseries/<metric>/<granularity>")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def asset_timeseries(slug, metric, granularity):
        guard_request(
            f"messari_ts_last_hit_{slug}_{metric}_{granularity}",
            cooldown=3,
        )

        def fetch_context():
            payload, fetched_at = get_asset_timeseries(slug, metric, granularity)
            return {
                "slug": slug,
                "metric": metric,
                "granularity": granularity,
                "timeseries": payload,
                "last_updated": fetched_at,
            }

        return guarded_render("messari/timeseries.html", fetch_context)

    @messari_bp.route("/metrics")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def metrics_catalog():
        guard_request("messari_metrics_last_hit", cooldown=5)

        def fetch_context():
            payload, fetched_at = get_asset_metrics_catalog()
            return {"metrics": payload, "last_updated": fetched_at}

        return guarded_render("messari/metrics.html", fetch_context)

    @messari_bp.route("/exchanges")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def exchanges():
        guard_request("messari_exchanges_last_hit", cooldown=5)

        def fetch_context():
            payload, fetched_at = get_exchanges(
                limit=DEFAULT_EXCHANGES_LIMIT, page=1
            )
            return {"exchanges": payload, "last_updated": fetched_at}

        return guarded_render("messari/exchanges.html", fetch_context)

    @messari_bp.route("/exchange/<exchange_id>")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def exchange_detail(exchange_id):
        guard_request(f"messari_exchange_last_hit_{exchange_id}", cooldown=3)

        def fetch_context():
            payload, fetched_at = get_exchange(exchange_id)
            return {
                "exchange_id": exchange_id,
                "exchange": payload,
                "last_updated": fetched_at,
            }

        return guarded_render("messari/exchange.html", fetch_context)

    return messari_bp
