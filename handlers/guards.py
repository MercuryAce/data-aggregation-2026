import os
import time

from flask import abort, current_app, jsonify, render_template, session
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from services.cache_store import CacheMissError

# Cached / DB pages: session click-spam off by default.
# Set REQUEST_GUARD_COOLDOWN=5 to restore per-route cooldowns.
_DEFAULT_GUARD_COOLDOWN = int(os.getenv("REQUEST_GUARD_COOLDOWN", "0"))
# Legacy/CG-path pages (may still hit ApiCache / upstream-shaped workloads)
_PAGE_RATE_LIMIT = os.getenv("PAGE_RATE_LIMIT", "60 per minute")
# MySQL-backed views — protect the app/DB only, not CoinGecko quotas
_VIEWS_RATE_LIMIT = os.getenv("VIEWS_RATE_LIMIT", "120 per minute")


def rate_limit(limiter, limit_str, *, kind: str = "page"):
    """Apply flask-limiter.

    ``kind="page"`` uses ``PAGE_RATE_LIMIT`` (CG / ApiCache routes).
    ``kind="views"`` uses ``VIEWS_RATE_LIMIT`` (MySQL-backed list pages).
    Explicit env values always win; otherwise the per-route ``limit_str`` is used.
    """
    if kind == "views":
        env_val = os.getenv("VIEWS_RATE_LIMIT")
        default_env = _VIEWS_RATE_LIMIT
    else:
        env_val = os.getenv("PAGE_RATE_LIMIT")
        default_env = _PAGE_RATE_LIMIT

    # Prefer explicit env when set; else fall back to decorator argument.
    if env_val is not None and env_val.strip():
        effective = env_val.strip()
    else:
        effective = limit_str or default_env

    def decorator(f):
        if not limiter:
            return f
        return limiter.limit(effective)(f)

    return decorator


def allow_request(key, cooldown=None):
    if cooldown is None:
        cooldown = _DEFAULT_GUARD_COOLDOWN
    if cooldown <= 0:
        return True
    now = time.time()
    last = session.get(key, 0)
    if now - last < cooldown:
        return False
    session[key] = now
    return True


def guard_request(key: str, cooldown: int | None = None):
    if cooldown is None:
        cooldown = _DEFAULT_GUARD_COOLDOWN
    # Explicit cooldown=N in callers is ignored when global env is 0,
    # unless REQUEST_GUARD_COOLDOWN is unset and they pass a value —
    # prefer env as the master switch for the cached architecture.
    env = os.getenv("REQUEST_GUARD_COOLDOWN")
    if env is not None:
        cooldown = int(env)
    if not allow_request(key, cooldown=cooldown):
        abort(429)


def only_cache_success(response):
    """Do not store 4xx/5xx in flask-caching."""
    try:
        return getattr(response, "status_code", 200) == 200
    except Exception:
        return False


def guarded_render(template_name: str, fetch_context):
    try:
        context = fetch_context()
        if context is None:
            abort(404)
        return render_template(template_name, **context, error=None)

    except HTTPException:
        raise

    except CacheMissError as e:
        current_app.logger.warning("Cache miss: %s", e)
        abort(503)

    except SQLAlchemyError:
        current_app.logger.exception("Cache database error")
        abort(503)

    except Exception:
        current_app.logger.exception("Unexpected error rendering %s", template_name)
        abort(500)


def guarded_json(fetch_data, *, not_found_message="Resource not found."):
    try:
        return jsonify(fetch_data())

    except HTTPException:
        raise

    except CacheMissError as e:
        current_app.logger.warning("Cache miss: %s", e)
        return jsonify({"error": "Data not available yet. Please try again shortly."}), 503

    except SQLAlchemyError:
        current_app.logger.exception("Cache database error")
        return jsonify({"error": "Data store temporarily unavailable."}), 503

    except Exception:
        current_app.logger.exception("Unexpected JSON route error")
        return jsonify({"error": "Something went wrong while processing your request."}), 500
