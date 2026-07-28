"""MongoDB Atlas time-series store for price ticks.

Best-effort: if MONGODB_URI is unset or Mongo is unreachable, callers no-op.
Supports Atlas X.509 via MONGODB_TLS_CERT_FILE (tlsCertificateKeyFile).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import Config

logger = logging.getLogger(__name__)

COLLECTION = "price_ticks"
ROOT = Path(__file__).resolve().parents[1]

_client = None
_db = None


def is_configured() -> bool:
    return bool(Config.MONGODB_URI)


def _resolve_cert_path() -> str | None:
    raw = (Config.MONGODB_TLS_CERT_FILE or "").strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        logger.warning("MongoDB TLS cert not found: %s", path)
        return None
    return str(path)


def _client_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "serverSelectionTimeoutMS": 8000,
        "tls": True,
    }
    cert = _resolve_cert_path()
    if cert:
        kwargs["tlsCertificateKeyFile"] = cert
    return kwargs


def get_client():
    """Return a shared MongoClient, or None if URI unset / connect fails."""
    global _client, _db
    if not Config.MONGODB_URI:
        return None
    if _client is not None:
        return _client
    try:
        from pymongo import MongoClient

        _client = MongoClient(Config.MONGODB_URI, **_client_kwargs())
        _client.admin.command("ping")
        _db = _client[Config.MONGODB_DB]
        _ensure_timeseries(_db)
        return _client
    except Exception as exc:
        logger.warning("MongoDB unavailable: %s", exc)
        _client = None
        _db = None
        return None


def get_db():
    if get_client() is None:
        return None
    return _db


def _ensure_timeseries(db) -> None:
    names = set(db.list_collection_names())
    if COLLECTION in names:
        return
    try:
        db.create_collection(
            COLLECTION,
            timeseries={
                "timeField": "timestamp",
                "metaField": "meta",
                "granularity": "minutes",
            },
        )
        logger.info("Created time-series collection %s", COLLECTION)
    except Exception as exc:
        # Race or already exists
        logger.debug("create_collection %s: %s", COLLECTION, exc)


def append_price_ticks(ticks: list[dict[str, Any]]) -> int:
    """Insert price ticks. Each tick needs asset_id, source, price.

    Returns number of documents written (0 if Mongo disabled/unavailable).
    """
    if not ticks:
        return 0
    db = get_db()
    if db is None:
        return 0

    now = datetime.now(timezone.utc)
    docs = []
    for tick in ticks:
        price = tick.get("price")
        if price is None:
            continue
        asset_id = str(tick.get("asset_id") or "").strip()
        if not asset_id:
            continue
        meta = dict(tick.get("meta") or {})
        meta["asset_id"] = asset_id
        meta["source"] = tick.get("source") or "unknown"
        doc: dict[str, Any] = {
            "timestamp": tick.get("timestamp") or now,
            "meta": meta,
            "price": float(price),
        }
        if tick.get("volume") is not None:
            doc["volume"] = float(tick["volume"])
        if tick.get("tvl") is not None:
            doc["tvl"] = float(tick["tvl"])
        docs.append(doc)

    if not docs:
        return 0
    try:
        result = db[COLLECTION].insert_many(docs, ordered=False)
        return len(result.inserted_ids)
    except Exception as exc:
        logger.warning("Failed to append price ticks: %s", exc)
        return 0


def get_price_history(
    asset_id: str,
    *,
    source: str | None = None,
    since: datetime | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Return ticks newest-last for charting. Empty if Mongo unavailable."""
    db = get_db()
    if db is None:
        return []

    query: dict[str, Any] = {"meta.asset_id": asset_id}
    if source:
        query["meta.source"] = source
    if since is not None:
        query["timestamp"] = {"$gte": since}

    try:
        cursor = (
            db[COLLECTION]
            .find(query, {"_id": 0})
            .sort("timestamp", 1)
            .limit(limit)
        )
        return list(cursor)
    except Exception as exc:
        logger.warning("Failed to read price history for %s: %s", asset_id, exc)
        return []


def reset_client_for_tests() -> None:
    """Drop cached client (tests only)."""
    global _client, _db
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
    _client = None
    _db = None
