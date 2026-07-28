from flask import render_template


def register_error_handlers(app):

    @app.errorhandler(400)
    def bad_request(error):
        return render_template(
            "errors/400.html",
            error=error,
        ), 400

    @app.errorhandler(404)
    def not_found(error):
        return render_template(
            "errors/404.html",
            error=error,
        ), 404

    @app.errorhandler(429)
    def too_many_requests(error):
        return render_template(
            "errors/429.html",
            error=error,
        ), 429

    @app.errorhandler(500)
    def internal_error(error):
        return render_template(
            "errors/5xx.html",
            code=500,
            title="Something went wrong",
            message="An unexpected error occurred. Please try again.",
            error=error,
        ), 500

    @app.errorhandler(502)
    def bad_gateway(error):
        return render_template(
            "errors/5xx.html",
            code=502,
            title="Crypto data service unavailable",
            message="The upstream crypto data service returned an error. Please try again shortly.",
            error=error,
        ), 502

    @app.errorhandler(503)
    def service_unavailable(error):
        return render_template(
            "errors/5xx.html",
            code=503,
            title="Data not ready yet",
            message=(
                "Market data has not been synced into the local cache. "
                "Run: python scripts/sync_coingecko.py --tasks markets"
            ),
            error=error,
        ), 503

    @app.errorhandler(504)
    def gateway_timeout(error):
        return render_template(
            "errors/5xx.html",
            code=504,
            title="Request timed out",
            message="The upstream service took too long to respond. Please try again.",
            error=error,
        ), 504