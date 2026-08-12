import os

from dotenv import load_dotenv
from flask import Flask, Response, request
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from blueprints.coingecko import init_cg_blueprint
from blueprints.views import init_views_blueprint
from models import MarketCoin, db
import markdown
from config import Config

from handlers.errors import register_error_handlers
from utils.formatters import compact_number, compact_usd
from utils.seo import build_sitemap_xml, canonical_url, sitemap_lastmod
from sqlalchemy import text

load_dotenv()

if os.environ.get("FLASK_ENV") == "production" and not Config.SITE_URL:
    raise RuntimeError("SITE_URL environment variable is required in production.")
    
app = Flask(__name__)

cache = Cache(app, config={
    "CACHE_TYPE": os.environ.get("CACHE_TYPE", "simple"),
    "CACHE_DEFAULT_TIMEOUT": int(os.environ.get("CACHE_DEFAULT_TIMEOUT", 60)),
})

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[
        os.environ.get("RATELIMIT_DAILY", "334 per day"),
        os.environ.get("RATELIMIT_HOURLY", "52 per hour"),
    ],
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
)

@app.route("/robots.txt")
def robots():
    site = Config.SITE_URL
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        "User-agent: GPTBot\n"
        "Disallow: /\n"
        "\n"
        "User-agent: ChatGPT-User\n"
        "Disallow: /\n"
        "\n"
        f"Sitemap: {site}/sitemap.xml\n"
    )
    return Response(body, mimetype="text/plain")

@app.route("/sitemap.xml")
@cache.memoize(timeout=Config.SITEMAP_CACHE_SECONDS)
def sitemap():
    limit = Config.SITEMAP_COIN_LIMIT
    entries: list[tuple[str, str, str, str | None]] = [
        ("/", "hourly", "1.0", None),
        ("/exchanges", "daily", "0.8", None),
        ("/trending", "hourly", "0.8", None),
        ("/categories", "daily", "0.7", None),
        ("/news", "hourly", "0.7", None),
    ]

    coins = (
        db.session.query(MarketCoin.cg_id, MarketCoin.synced_at, MarketCoin.metrics_synced_at)
        .filter(MarketCoin.market_cap_rank.isnot(None))
        .order_by(MarketCoin.market_cap_rank.asc())
        .limit(limit)
        .all()
    )
    for cg_id, synced_at, metrics_synced_at in coins:
        lastmod = max(filter(None, [metrics_synced_at, synced_at]), default=None)
        entries.append((f"/coin/{cg_id}", "hourly", "0.7", sitemap_lastmod(lastmod)))
        entries.append((f"/coin/analysis/{cg_id}", "daily", "0.8", sitemap_lastmod(lastmod)))

    xml = build_sitemap_xml(Config.SITE_URL, entries)
    return Response(xml, mimetype="application/xml")


@app.context_processor
def seo_context():
    default_image = Config.SEO_DEFAULT_IMAGE or f"{Config.SITE_URL}/static/img/logo.png"
    return {
        "site_url": Config.SITE_URL,
        "site_name": Config.SITE_NAME,
        "site_description": Config.SITE_DESCRIPTION,
        "site_robots": Config.SITE_ROBOTS,
        "canonical_url": canonical_url(Config.SITE_URL, request),
        "og_image": default_image,
    }

secret_key = os.environ.get("SECRET_KEY")

if not secret_key and os.environ.get("FLASK_ENV") == "production":
    raise RuntimeError("SECRET_KEY environment variable is required in production.")

app.config["SECRET_KEY"] = secret_key or os.environ.get("DEV_SECRET_KEY")

# === Database Configuration ===
# DATABASE_URI in .env (MySQL preferred; sqlite fallback for local/dev only).
os.makedirs(app.instance_path, exist_ok=True)
default_db_path = os.path.join(app.instance_path, "cache.db")
database_uri = os.environ.get("DATABASE_URI") or f"sqlite:///{default_db_path}"
app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
if database_uri.startswith("sqlite"):
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "connect_args": {"check_same_thread": False},
    }
elif database_uri.startswith("mysql"):
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 28000,
    }

db.init_app(app)
with app.app_context():
    db.create_all()
    from services.schema import ensure_market_coin_identity_columns

    ensure_market_coin_identity_columns()
    if database_uri.startswith("sqlite"):
        db.session.execute(text("PRAGMA journal_mode=WAL"))
        db.session.execute(text("PRAGMA synchronous=NORMAL"))
        db.session.commit()

def init_markdown(app):
    @app.template_filter('markdown')
    def markdownify(text):
        if not text:
            return ''
        return markdown.markdown(
            text,
            extensions=['tables', 'fenced_code', 'nl2br', 'codehilite'],
        )

init_markdown(app)


@app.template_filter("compact_number")
def compact_number_filter(value, decimals=1):
    return compact_number(value, decimals)


@app.template_filter("compact_usd")
def compact_usd_filter(value, decimals=1):
    return compact_usd(value, decimals)


views_bp = init_views_blueprint(cache, limiter)
app.register_blueprint(views_bp)

cg_bp = init_cg_blueprint(cache, limiter)
app.register_blueprint(cg_bp)

register_error_handlers(app)

if __name__ == '__main__':
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    )
