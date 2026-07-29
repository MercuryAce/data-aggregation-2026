"""Ensure test DB rebind never targets the production cache file."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from tests.conftest import rebind_db


def test_app_fixture_uses_temp_db_not_instance(app):
    uri = str(app.config["SQLALCHEMY_DATABASE_URI"])
    assert "test_cache.db" in uri
    assert "/instance/cache.db" not in uri

    from models import db

    with app.app_context():
        assert "test_cache.db" in str(db.engine.url)


def test_rebind_drop_all_leaves_other_db_intact(tmp_path, monkeypatch):
    """drop_all after rebind must only affect the rebound URI."""
    prod = tmp_path / "prod.db"
    test = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URI", f"sqlite:///{prod}")

    from app import app as flask_app
    from models import ApiCache, db

    with flask_app.app_context():
        rebind_db(flask_app, f"sqlite:///{prod}")
        db.create_all()
        db.session.add(
            ApiCache(
                key="keep-me",
                payload={"ok": True},
                fetched_at=datetime.now(timezone.utc),
                source="test",
            )
        )
        db.session.commit()

        rebind_db(flask_app, f"sqlite:///{test}")
        assert str(test) in str(db.engine.url)
        db.drop_all()
        db.create_all()

        # Restore a disposable bind so later tests in this process stay isolated.
        rebind_db(flask_app, f"sqlite:///{tmp_path / 'cleanup.db'}")
        db.create_all()

    con = sqlite3.connect(prod)
    tables = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='api_cache'"
    ).fetchall()
    assert tables, "other DB tables must survive rebound drop_all"
    assert con.execute("SELECT COUNT(*) FROM api_cache").fetchone()[0] == 1
    assert con.execute("SELECT key FROM api_cache").fetchone()[0] == "keep-me"
