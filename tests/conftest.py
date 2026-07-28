"""Shared fixtures for CryptoDash unit tests (no live network)."""

from __future__ import annotations

import pytest


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Flask app configured for isolated testing (in-memory SQLite, no cooldowns)."""
    db_path = tmp_path / "test_cache.db"
    monkeypatch.setenv("DATABASE_URI", f"sqlite:///{db_path}")
    monkeypatch.setenv("CACHE_TYPE", "SimpleCache")
    monkeypatch.setenv("RATELIMIT_STORAGE_URI", "memory://")

    # Import after env overrides so app config can pick them up where applicable.
    from app import app as flask_app
    from app import cache, limiter
    from models import db

    flask_app.config.update(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )

    # Disable per-IP rate limits during tests.
    limiter.enabled = False

    with flask_app.app_context():
        db.drop_all()
        db.create_all()
        cache.clear()
        yield flask_app
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
