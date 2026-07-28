from flask import Blueprint
from flask_caching import Cache

from handlers.guards import only_cache_success, guard_request, guarded_json, guarded_render, rate_limit
from services.defillama_service import defillama_service

defillama_bp = Blueprint("defillama", __name__, url_prefix="")

def init_defillama_blueprint(cache: Cache, limiter=None):
    @defillama_bp.route("/")
    @cache.cached(timeout=300, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def index():
        pass