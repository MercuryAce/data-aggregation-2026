"""T2: ApiCache store — set/get/miss/upsert/staleness."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from models import ApiCache, db
from services import cache_store


def test_get_missing_key_returns_none(app):
    assert cache_store.get("missing_key") is None


def test_set_then_get_returns_payload_and_fetched_at(app):
    cache_store.set("k1", {"ok": True}, ttl_seconds=60, source="test")

    entry = cache_store.get("k1")
    assert entry is not None
    assert entry.payload == {"ok": True}
    assert entry.fetched_at.tzinfo is not None


def test_set_upserts_existing_key(app):
    cache_store.set("k1", {"v": 1}, source="test")
    cache_store.set("k1", {"v": 2}, source="test")

    entry = cache_store.get("k1")
    assert entry is not None
    assert entry.payload == {"v": 2}


def test_set_stores_list_payload(app):
    cache_store.set("list_key", [{"id": "bitcoin"}], ttl_seconds=30)

    entry = cache_store.get("list_key")
    assert entry is not None
    assert entry.payload == [{"id": "bitcoin"}]


def test_is_stale_missing_key(app):
    assert cache_store.is_stale("nope") is True


def test_is_stale_false_when_unexpired(app):
    cache_store.set("fresh", {"a": 1}, ttl_seconds=3600)
    assert cache_store.is_stale("fresh") is False


def test_is_stale_true_when_expired(app):
    cache_store.set("old", {"a": 1}, ttl_seconds=60)

    row = db.session.get(ApiCache, "old")
    assert row is not None
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.session.commit()

    assert cache_store.is_stale("old") is True


def test_is_stale_false_when_no_ttl(app):
    cache_store.set("forever", {"a": 1}, ttl_seconds=None)
    assert cache_store.is_stale("forever") is False


def test_age_minutes(app):
    fetched_at = datetime.now(timezone.utc) - timedelta(minutes=12, seconds=30)
    assert cache_store.age_minutes(fetched_at) == 12


def test_get_still_returns_expired_entry(app):
    """Expiry is for is_stale(); get() does not hide expired rows."""
    cache_store.set("expired_but_present", {"x": 1}, ttl_seconds=1)

    row = db.session.get(ApiCache, "expired_but_present")
    assert row is not None
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    db.session.commit()

    entry = cache_store.get("expired_but_present")
    assert entry is not None
    assert entry.payload == {"x": 1}
