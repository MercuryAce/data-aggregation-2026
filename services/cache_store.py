from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from models import ApiCache, db


class CacheMissError(Exception):
    """Raised when a cache key is missing (sync has not populated it yet)."""


@dataclass(frozen=True)
class CacheEntry:
    payload: dict | list
    fetched_at: datetime


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@contextmanager
def _app_context():
    from flask import has_app_context

    if has_app_context():
        yield
        return

    from app import app

    with app.app_context():
        yield


def get(key: str) -> CacheEntry | None:
    """Return a cached entry or None if the key is missing."""
    with _app_context():
        row = db.session.get(ApiCache, key)
        if row is None:
            return None
        return CacheEntry(payload=row.payload, fetched_at=_as_utc(row.fetched_at))


def set(
    key: str,
    payload: dict | list,
    *,
    ttl_seconds: int | None = None,
    source: str = "coingecko",
) -> None:
    """Upsert a cache entry."""
    with _app_context():
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds) if ttl_seconds else None

        row = db.session.get(ApiCache, key)
        if row is None:
            row = ApiCache(key=key)
            db.session.add(row)

        row.payload = payload
        row.fetched_at = now
        row.expires_at = expires_at
        row.source = source
        db.session.commit()


def get_or_none(key: str) -> CacheEntry | None:
    """Alias for get()."""
    return get(key)


def age_minutes(fetched_at: datetime) -> int:
    """Return cache age in whole minutes."""
    now = datetime.now(timezone.utc)
    diff = now - _as_utc(fetched_at)
    return int(diff.total_seconds() // 60)


def is_stale(key: str) -> bool:
    """Return True if the key is missing or past its expiry time."""
    with _app_context():
        row = db.session.get(ApiCache, key)
        if row is None:
            return True
        if row.expires_at is None:
            return False
        return _as_utc(row.expires_at) < datetime.now(timezone.utc)
