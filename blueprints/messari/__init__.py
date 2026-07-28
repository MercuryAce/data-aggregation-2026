from flask import Blueprint
from flask_caching import Cache

from handlers.guards import guard_request, guarded_render, rate_limit
from services.messari_service import get_asset_details

DEFAULT_DETAIL_SLUGS = "bitcoin,ethereum"

messari_bp = Blueprint("messari", __name__, url_prefix="/messari")


def init_messari_blueprint(cache: Cache, limiter=None):
    @messari_bp.route("/")
    @cache.cached(timeout=120)
    @rate_limit(limiter, "5 per minute")
    def index():
        guard_request("messari_index_last_hit", cooldown=5)

        def fetch_context():
            details_payload, details_at = get_asset_details(DEFAULT_DETAIL_SLUGS)
            return {
                "details": details_payload,
                "last_updated": details_at,
            }

        return guarded_render("messari/index.html", fetch_context)

    @messari_bp.route("/asset/<slug>")
    @cache.cached(timeout=120)
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

    return messari_bp
