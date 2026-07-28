"""DefiLlama blueprint — routes aligned with DefiLlamaRequestController / llama.php."""

from flask import Blueprint
from flask_caching import Cache

from handlers.guards import only_cache_success, guard_request, guarded_render, rate_limit
from services import defillama_service as svc

defillama_bp = Blueprint("defillama", __name__, url_prefix="/defillama")


def _dump(title, fetch, *, subtitle=None, cooldown_key=None, cooldown=5):
    if cooldown_key:
        guard_request(cooldown_key, cooldown=cooldown)

    def fetch_context():
        payload, fetched_at = fetch()
        return {
            "title": title,
            "subtitle": subtitle,
            "payload": payload,
            "last_updated": fetched_at,
        }

    return guarded_render("defillama/dump.html", fetch_context)


def init_defillama_blueprint(cache: Cache, limiter=None):
    @defillama_bp.route("/")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def index():
        guard_request("defillama_index_last_hit", cooldown=5)
        return guarded_render("defillama/index.html", lambda: {})

    # --- TVL / Protocols ---
    @defillama_bp.route("/protocols")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def protocols():
        return _dump(
            "Protocols",
            svc.get_protocols,
            cooldown_key="defillama_protocols_last_hit",
        )

    @defillama_bp.route("/protocol/<protocol>")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def protocol_detail(protocol):
        return _dump(
            f"Protocol: {protocol}",
            lambda: svc.get_protocol(protocol),
            cooldown_key=f"defillama_protocol_last_hit_{protocol}",
            cooldown=3,
        )

    @defillama_bp.route("/v2/historicalChainTvl")
    @defillama_bp.route("/historical-chain-tvl")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def historical_chain_tvl():
        return _dump(
            "Historical chain TVL",
            svc.get_historical_chain_tvl,
            cooldown_key="defillama_historical_chain_tvl_last_hit",
        )

    @defillama_bp.route("/v2/historicalChainTvl/<chain>")
    @defillama_bp.route("/historical-chain-tvl/<chain>")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def historical_chain_tvl_by_chain(chain):
        return _dump(
            f"Historical chain TVL: {chain}",
            lambda: svc.get_historical_chain_tvl_by_chain(chain),
            cooldown_key=f"defillama_historical_tvl_{chain}",
            cooldown=3,
        )

    @defillama_bp.route("/v2/chains")
    @defillama_bp.route("/chains")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def chains():
        return _dump(
            "Chains",
            svc.get_chains,
            cooldown_key="defillama_chains_last_hit",
        )

    # --- Coins ---
    @defillama_bp.route("/prices/current/<path:coins>")
    @cache.cached(timeout=60, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def current_prices(coins):
        return _dump(
            "Current prices",
            lambda: svc.get_current_prices(coins),
            subtitle=coins,
            cooldown_key=f"defillama_prices_current_{coins}",
            cooldown=3,
        )

    @defillama_bp.route("/prices/historical/<timestamp>/<path:coins>")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def historical_prices(timestamp, coins):
        return _dump(
            "Historical prices",
            lambda: svc.get_historical_prices(timestamp, coins),
            subtitle=f"{timestamp} / {coins}",
            cooldown_key=f"defillama_prices_hist_{timestamp}",
            cooldown=3,
        )

    # --- Stablecoins ---
    @defillama_bp.route("/stablecoins")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def stablecoins():
        return _dump(
            "Stablecoins",
            svc.get_stablecoins,
            cooldown_key="defillama_stablecoins_last_hit",
        )

    @defillama_bp.route("/stablecoincharts/all")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def stablecoin_charts_all():
        return _dump(
            "Stablecoin charts (all)",
            svc.get_stablecoin_charts_all,
            cooldown_key="defillama_stablecoin_charts_all",
        )

    @defillama_bp.route("/stablecoincharts/<chain>")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def stablecoin_charts_chain(chain):
        return _dump(
            f"Stablecoin charts: {chain}",
            lambda: svc.get_stablecoin_charts_by_chain(chain),
            cooldown_key=f"defillama_stablecoin_charts_{chain}",
            cooldown=3,
        )

    @defillama_bp.route("/stablecoin/<asset_id>")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def stablecoin_detail(asset_id):
        return _dump(
            f"Stablecoin {asset_id}",
            lambda: svc.get_stablecoin(asset_id),
            cooldown_key=f"defillama_stablecoin_{asset_id}",
            cooldown=3,
        )

    @defillama_bp.route("/stablecoinchains")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def stablecoin_chains():
        return _dump(
            "Stablecoin chains",
            svc.get_stablecoin_chains,
            cooldown_key="defillama_stablecoin_chains",
        )

    @defillama_bp.route("/stablecoinprices")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def stablecoin_prices():
        return _dump(
            "Stablecoin prices",
            svc.get_stablecoin_prices,
            cooldown_key="defillama_stablecoin_prices",
        )

    # --- Yields ---
    @defillama_bp.route("/pools")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def pools():
        return _dump(
            "Yield pools",
            svc.get_pools,
            cooldown_key="defillama_pools_last_hit",
        )

    @defillama_bp.route("/chart/<pool>")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def pool_chart(pool):
        return _dump(
            f"Pool chart: {pool}",
            lambda: svc.get_pool_chart(pool),
            cooldown_key=f"defillama_pool_chart_{pool}",
            cooldown=3,
        )

    # --- Bridges ---
    @defillama_bp.route("/bridges")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def bridges():
        return _dump(
            "Bridges",
            svc.get_bridges,
            cooldown_key="defillama_bridges_last_hit",
        )

    @defillama_bp.route("/bridge/<bridge_id>")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def bridge_detail(bridge_id):
        return _dump(
            f"Bridge {bridge_id}",
            lambda: svc.get_bridge(bridge_id),
            cooldown_key=f"defillama_bridge_{bridge_id}",
            cooldown=3,
        )

    @defillama_bp.route("/bridgevolume/<chain>")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def bridge_volume(chain):
        return _dump(
            f"Bridge volume: {chain}",
            lambda: svc.get_bridge_volume(chain),
            cooldown_key=f"defillama_bridge_volume_{chain}",
            cooldown=3,
        )

    # --- DEX / options / fees ---
    @defillama_bp.route("/overview/dexs")
    @defillama_bp.route("/dexs")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def dexs():
        return _dump(
            "DEX volumes",
            svc.get_dexs,
            cooldown_key="defillama_dexs_last_hit",
        )

    @defillama_bp.route("/overview/dexs/<chain>")
    @defillama_bp.route("/dexs/<chain>")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def dexs_by_chain(chain):
        return _dump(
            f"DEX volumes: {chain}",
            lambda: svc.get_dexs_by_chain(chain),
            cooldown_key=f"defillama_dexs_{chain}",
            cooldown=3,
        )

    @defillama_bp.route("/summary/dexs/<protocol>")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def dex_summary(protocol):
        return _dump(
            f"DEX summary: {protocol}",
            lambda: svc.get_dex_summary(protocol),
            cooldown_key=f"defillama_dex_summary_{protocol}",
            cooldown=3,
        )

    @defillama_bp.route("/overview/options")
    @defillama_bp.route("/options")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def options():
        return _dump(
            "Options volumes",
            svc.get_options,
            cooldown_key="defillama_options_last_hit",
        )

    @defillama_bp.route("/overview/fees")
    @defillama_bp.route("/fees")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def fees():
        return _dump(
            "Fees",
            svc.get_fees,
            cooldown_key="defillama_fees_last_hit",
        )

    @defillama_bp.route("/overview/fees/<chain>")
    @defillama_bp.route("/fees/<chain>")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def fees_by_chain(chain):
        return _dump(
            f"Fees: {chain}",
            lambda: svc.get_fees_by_chain(chain),
            cooldown_key=f"defillama_fees_{chain}",
            cooldown=3,
        )

    @defillama_bp.route("/summary/fees/<protocol>")
    @cache.cached(timeout=120, response_filter=only_cache_success)
    @rate_limit(limiter, "5 per minute")
    def fees_by_protocol(protocol):
        return _dump(
            f"Fees: {protocol}",
            lambda: svc.get_fees_by_protocol(protocol),
            cooldown_key=f"defillama_fees_protocol_{protocol}",
            cooldown=3,
        )

    return defillama_bp
