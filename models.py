from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _utcnow():
    return datetime.now(timezone.utc)


class ApiCache(db.Model):
    __tablename__ = "api_cache"

    key = db.Column(db.String(255), primary_key=True)
    payload = db.Column(db.JSON, nullable=False)
    fetched_at = db.Column(db.DateTime, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    source = db.Column(db.String(255), nullable=False, default="coingecko")

    def __repr__(self):
        return f"<ApiCache {self.key} @ {self.fetched_at}>"


creator_asset = db.Table(
    "creator_asset",
    db.Column("creator_id", db.Integer, db.ForeignKey("creators.id"), primary_key=True),
    db.Column("asset_id", db.Integer, db.ForeignKey("assets.id"), primary_key=True),
    db.Column("created_at", db.DateTime, default=_utcnow),
)


class Creator(db.Model):
    __tablename__ = "creators"

    id = db.Column(db.Integer, primary_key=True)
    handle = db.Column(db.String(100), unique=True, nullable=False)
    platform = db.Column(db.String(50))
    profile_url = db.Column(db.String(300), nullable=False)
    followers = db.Column(db.String(50))
    posts = db.Column(db.String(50))
    engagements = db.Column(db.String(50))
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=_utcnow)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)

    assets = db.relationship("Asset", secondary=creator_asset, back_populates="creators")

    def __repr__(self):
        return f"<Creator {self.handle}>"


class Asset(db.Model):
    __tablename__ = "assets"

    id = db.Column(db.Integer, primary_key=True)
    coin_id = db.Column(db.String(200), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow)

    creators = db.relationship("Creator", secondary=creator_asset, back_populates="assets")

    def __repr__(self):
        return f"<Asset {self.coin_id}>"


# ---- Typed view tables (MySQL prototype) ----


class MarketCoin(db.Model):
    __tablename__ = "market_coins"

    cg_id = db.Column(db.String(200), primary_key=True)
    market_cap_rank = db.Column(db.Integer, index=True)
    symbol = db.Column(db.String(50), nullable=False, default="")
    name = db.Column(db.String(200), nullable=False, default="")
    image = db.Column(db.String(500))
    current_price = db.Column(db.Float)
    price_change_percentage_24h = db.Column(db.Float)
    market_cap = db.Column(db.Float)
    total_volume = db.Column(db.Float)
    high_24h = db.Column(db.Float)
    low_24h = db.Column(db.Float)
    fully_diluted_valuation = db.Column(db.Float)
    total_supply = db.Column(db.Float)
    circulating_supply = db.Column(db.Float)
    # Generic cross-provider identity (not named for a single oracle)
    platforms = db.Column(db.JSON)  # {chain: contract_address}
    primary_chain = db.Column(db.String(64))
    contract_address = db.Column(db.String(128), index=True)
    external_ids = db.Column(db.JSON)  # {"coingecko": "...", "cmc": 1, "cmc_slug": "..."}
    structure_synced_at = db.Column(db.DateTime)  # last rank/metadata refresh
    metrics_synced_at = db.Column(db.DateTime)  # last live price/metrics patch
    synced_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    source = db.Column(db.String(50), nullable=False, default="coingecko")

    def to_market_dict(self) -> dict:
        return {
            "id": self.cg_id,
            "market_cap_rank": self.market_cap_rank,
            "symbol": self.symbol,
            "name": self.name,
            "image": self.image,
            "current_price": self.current_price,
            "price_change_percentage_24h": self.price_change_percentage_24h,
            "market_cap": self.market_cap,
            "total_volume": self.total_volume,
            "high_24h": self.high_24h,
            "low_24h": self.low_24h,
            "fully_diluted_valuation": self.fully_diluted_valuation,
            "total_supply": self.total_supply,
            "circulating_supply": self.circulating_supply,
            "platforms": self.platforms or {},
            "primary_chain": self.primary_chain,
            "contract_address": self.contract_address,
            "external_ids": self.external_ids or {},
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
            "metrics_synced_at": (
                self.metrics_synced_at.isoformat() if self.metrics_synced_at else None
            ),
            "source": self.source,
        }


class GlobalStats(db.Model):
    __tablename__ = "global_stats"

    id = db.Column(db.Integer, primary_key=True)
    active_cryptocurrencies = db.Column(db.Integer)
    markets = db.Column(db.Integer)
    market_cap_change_percentage_24h_usd = db.Column(db.Float)
    volume_change_percentage_24h_usd = db.Column(db.Float)
    payload = db.Column(db.JSON)
    synced_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    source = db.Column(db.String(50), nullable=False, default="coingecko")

    def to_stats_dict(self) -> dict:
        if isinstance(self.payload, dict) and self.payload:
            return self.payload
        return {
            "active_cryptocurrencies": self.active_cryptocurrencies or 0,
            "markets": self.markets or 0,
            "market_cap_change_percentage_24h_usd": self.market_cap_change_percentage_24h_usd
            or 0,
            "volume_change_percentage_24h_usd": self.volume_change_percentage_24h_usd or 0,
        }


class Exchange(db.Model):
    __tablename__ = "exchanges"

    exchange_id = db.Column(db.String(200), primary_key=True)
    name = db.Column(db.String(200), nullable=False, default="")
    image = db.Column(db.String(500))
    url = db.Column(db.String(500))
    description = db.Column(db.Text)
    country = db.Column(db.String(100))
    year_established = db.Column(db.Integer)
    trust_score = db.Column(db.Integer, index=True)
    trust_score_rank = db.Column(db.Integer)
    trade_volume_24h_btc = db.Column(db.Float)
    synced_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    source = db.Column(db.String(50), nullable=False, default="coingecko")

    def to_exchange_dict(self) -> dict:
        return {
            "id": self.exchange_id,
            "name": self.name,
            "image": self.image,
            "url": self.url,
            "description": self.description or "",
            "country": self.country or "",
            "year_established": self.year_established,
            "trust_score": self.trust_score,
            "trust_score_rank": self.trust_score_rank,
            "trade_volume_24h_btc": self.trade_volume_24h_btc or 0,
        }


class TrendingCoin(db.Model):
    __tablename__ = "trending_coins"

    cg_id = db.Column(db.String(200), primary_key=True)
    score = db.Column(db.Integer)
    name = db.Column(db.String(200), nullable=False, default="")
    symbol = db.Column(db.String(50), nullable=False, default="")
    image = db.Column(db.String(500))
    market_cap_rank = db.Column(db.Integer)
    payload = db.Column(db.JSON)
    synced_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    source = db.Column(db.String(50), nullable=False, default="coingecko")


class TrendingSnapshot(db.Model):
    """Full CoinGecko trending document for nested template shape."""

    __tablename__ = "trending_snapshots"

    id = db.Column(db.String(50), primary_key=True, default="latest")
    payload = db.Column(db.JSON, nullable=False)
    synced_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    source = db.Column(db.String(50), nullable=False, default="coingecko")


class Category(db.Model):
    __tablename__ = "categories"

    category_id = db.Column(db.String(200), primary_key=True)
    name = db.Column(db.String(200), nullable=False, default="")
    content = db.Column(db.Text)
    market_cap = db.Column(db.Float)
    market_cap_change_24h = db.Column(db.Float)
    volume_24h = db.Column(db.Float)
    top_3_coins = db.Column(db.JSON)
    synced_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    source = db.Column(db.String(50), nullable=False, default="coingecko")

    def to_category_dict(self) -> dict:
        return {
            "id": self.category_id,
            "name": self.name,
            "content": self.content or "",
            "market_cap": self.market_cap,
            "market_cap_change_24h": self.market_cap_change_24h,
            "volume_24h": self.volume_24h,
            "top_3_coins": self.top_3_coins or [],
        }


class SyncLock(db.Model):
    __tablename__ = "sync_locks"

    name = db.Column(db.String(100), primary_key=True)
    locked_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False, default="idle")
    message = db.Column(db.String(500))
