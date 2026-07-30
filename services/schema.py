"""Lightweight MySQL/SQLite column migrations for existing databases.

``db.create_all()`` does not add columns to tables that already exist.
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text

from models import db

logger = logging.getLogger(__name__)

# Generic identity columns on market_coins (provider-agnostic names).
MARKET_COIN_IDENTITY_COLUMNS: dict[str, str] = {
    "platforms": "JSON",
    "primary_chain": "VARCHAR(64)",
    "contract_address": "VARCHAR(128)",
    "external_ids": "JSON",
    "structure_synced_at": "DATETIME",
    "metrics_synced_at": "DATETIME",
}


def ensure_market_coin_identity_columns() -> list[str]:
    """ADD missing identity columns on market_coins. Returns names added."""
    inspector = inspect(db.engine)
    if "market_coins" not in inspector.get_table_names():
        return []

    existing = {col["name"] for col in inspector.get_columns("market_coins")}
    added: list[str] = []
    dialect = db.engine.dialect.name

    for name, sql_type in MARKET_COIN_IDENTITY_COLUMNS.items():
        if name in existing:
            continue
        # SQLite accepts generic types; MySQL uses the mapped types above.
        col_type = sql_type
        if dialect == "sqlite" and sql_type == "JSON":
            col_type = "TEXT"
        db.session.execute(
            text(f"ALTER TABLE market_coins ADD COLUMN {name} {col_type}")
        )
        added.append(name)

    if added:
        db.session.commit()
        logger.info("Added market_coins columns: %s", ", ".join(added))
        # Optional index for contract lookups (MySQL / SQLite 3.37+)
        if "contract_address" in added:
            try:
                db.session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_market_coins_contract_address "
                        "ON market_coins (contract_address)"
                    )
                )
                db.session.commit()
            except Exception:
                db.session.rollback()
                logger.debug("contract_address index skipped", exc_info=True)
    return added
