import os

from dotenv import load_dotenv
from flask import Flask, send_from_directory
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from blueprints.coingecko import init_cg_blueprint
from models import db
import markdown

from handlers.errors import register_error_handlers
from utils.formatters import compact_number, compact_usd

load_dotenv()

# from models import db
app = Flask(__name__)
@app.route('/robots.txt')
def robots():
    return send_from_directory(app.static_folder, 'robots.txt')

secret_key = os.environ.get("SECRET_KEY")

if not secret_key and os.environ.get("FLASK_ENV") == "production":
    raise RuntimeError("SECRET_KEY environment variable is required in production.")

app.config["SECRET_KEY"] = secret_key or os.environ.get("DEV_SECRET_KEY")

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

# === Database Configuration ===
os.makedirs(app.instance_path, exist_ok=True)
default_db_path = os.path.join(app.instance_path, "cache.db")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URI",
    f"sqlite:///{default_db_path}",
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# Create db instance
db.init_app(app)
with app.app_context():
    db.create_all()

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


cg_bp = init_cg_blueprint(cache, limiter)
app.register_blueprint(cg_bp)

register_error_handlers(app)

if __name__ == '__main__':
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    )
