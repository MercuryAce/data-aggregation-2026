from flask import Blueprint
from flask_caching import Cache

from handlers.guards import guard_request, guarded_render, rate_limit
from services.defillama_service import (
    get_historical_chain_tvl,
    get_historical_chain_tvl_by_chain,
    get_protocol,
    get_protocols,
)

defillama_bp = Blueprint("defillama", __name__, url_prefix="/defillama")


def init_defillama_blueprint(cache: Cache, limiter=None):
    @defillama_bp.route("/protocols")
    @cache.cached(timeout=120)
    @rate_limit(limiter, "5 per minute")
    def protocols():
        guard_request("defillama_protocols_last_hit", cooldown=5)

        def fetch_context():
            payload, fetched_at = get_protocols()
            return {
                "protocols": payload,
                "last_updated": fetched_at,
            }

        return guarded_render("defillama/protocols.html", fetch_context)

    @defillama_bp.route("/protocol/<protocol>")
    @cache.cached(timeout=120)
    @rate_limit(limiter, "5 per minute")
    def protocol_detail(protocol):
        guard_request(f"defillama_protocol_last_hit_{protocol}", cooldown=3)

        def fetch_context():
            payload, fetched_at = get_protocol(protocol)
            return {
                "protocol": protocol,
                "details": payload,
                "last_updated": fetched_at,
            }

        return guarded_render("defillama/protocol.html", fetch_context)

    @defillama_bp.route("/historical-chain-tvl")
    @cache.cached(timeout=120)
    @rate_limit(limiter, "5 per minute")
    def historical_chain_tvl():
        guard_request("defillama_historical_chain_tvl_last_hit", cooldown=5)

        def fetch_context():
            payload, fetched_at = get_historical_chain_tvl()
            return {
                "details": payload,
                "last_updated": fetched_at,
            }

        return guarded_render("defillama/historical_chain_tvl.html", fetch_context)

    @defillama_bp.route("/historical-chain-tvl/<chain>")
    @cache.cached(timeout=120)
    @rate_limit(limiter, "5 per minute")
    def historical_chain_tvl_by_chain(chain):
        guard_request(
            f"defillama_historical_chain_tvl_by_chain_last_hit_{chain}",
            cooldown=3,
        )

        def fetch_context():
            payload, fetched_at = get_historical_chain_tvl_by_chain(chain)
            return {
                "chain": chain,
                "details": payload,
                "last_updated": fetched_at,
            }

        return guarded_render(
            "defillama/historical_chain_tvl_by_chain.html",
            fetch_context,
        )

    return defillama_bp
