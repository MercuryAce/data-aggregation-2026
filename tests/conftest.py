"""Shared fixtures for CryptoDash unit tests (no live network)."""

from __future__ import annotations

import pytest


def rebind_db(flask_app, uri: str) -> None:
    """Point Flask-SQLAlchemy at ``uri`` and rebuild engines.

    Updating ``SQLALCHEMY_DATABASE_URI`` alone does not rebind. Without this,
    ``db.drop_all()`` would wipe the previously bound database (often
    ``instance/cache.db``).
    """
    from models import db

    flask_app.config["SQLALCHEMY_DATABASE_URI"] = uri
    db.session.remove()

    engines = db._app_engines.setdefault(flask_app, {})
    for engine in list(engines.values()):
        engine.dispose()
    engines.clear()

    options = db._engine_options.copy()
    options.update(flask_app.config.get("SQLALCHEMY_ENGINE_OPTIONS") or {})
    options["url"] = uri
    echo = flask_app.config.get("SQLALCHEMY_ECHO", False)
    options.setdefault("echo", echo)
    options.setdefault("echo_pool", echo)
    db._apply_driver_defaults(options, flask_app)
    engines[None] = db._make_engine(None, options, flask_app)


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Flask app bound to an isolated temp SQLite file (never instance/cache.db)."""
    db_path = tmp_path / "test_cache.db"
    test_uri = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URI", test_uri)
    monkeypatch.setenv("CACHE_TYPE", "SimpleCache")
    monkeypatch.setenv("RATELIMIT_STORAGE_URI", "memory://")

    from app import app as flask_app
    from app import cache, limiter
    from models import db

    flask_app.config.update(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )

    limiter.enabled = False

    with flask_app.app_context():
        rebind_db(flask_app, test_uri)
        assert "test_cache.db" in str(db.engine.url)
        assert "instance/cache.db" not in str(db.engine.url)
        db.drop_all()
        db.create_all()
        cache.clear()
        yield flask_app
        assert "test_cache.db" in str(db.engine.url)
        db.session.remove()
        db.drop_all()
        cache.clear()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def no_request_guard(monkeypatch):
    """Bypass session click-spam cooldown used by blueprint routes."""
    monkeypatch.setattr("handlers.guards.allow_request", lambda *args, **kwargs: True)
