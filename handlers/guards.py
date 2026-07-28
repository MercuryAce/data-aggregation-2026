import time

from flask import abort, current_app, jsonify, render_template, session
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from services.cache_store import CacheMissError


def rate_limit(limiter, limit_str):
    def decorator(f):
        if not limiter:
            return f
        return limiter.limit(limit_str)(f)

    return decorator


def allow_request(key, cooldown=5):
    now = time.time()
    last = session.get(key, 0)
    if now - last < cooldown:
        return False
    session[key] = now
    return True


def guard_request(key: str, cooldown: int):
    if not allow_request(key, cooldown=cooldown):
        abort(429)


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
