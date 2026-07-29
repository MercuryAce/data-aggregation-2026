# CryptoDash

A server-rendered Flask cryptocurrency dashboard. Pages are **cache-first**: Celery/CLI
sync scripts pull from external APIs into a local SQLite `ApiCache`, and Flask routes read
only from that cache (cache miss → HTTP 503). There is no live upstream call on page load.

## Architecture

```
sync scripts / Celery beat  →  HTTP clients  →  services/cache_store.py  →  SQLite ApiCache
Flask routes                →  *_service / market_service               →  templates
```

- **SQLite `ApiCache`** (`models.py`, file at `DATABASE_URI` / `instance/cache.db`) — current
  snapshots (markets, coin details, FX, news, etc.). Shared by Flask, Celery, and sync CLIs.
- **MongoDB Atlas** (`services/timeseries_store.py`) — optional price ticks only; no-op if
  `MONGODB_URI` is unset or unreachable. Auth via X.509 cert (`MONGODB_TLS_CERT_FILE`).
- **flask-caching** / **flask-limiter** — still in-process memory by default (`CACHE_TYPE`,
  `RATELIMIT_STORAGE_URI` in `.env`). Separate from `ApiCache`.
- **UI** — CoinGecko blueprint only (`blueprints/coingecko/`). Market/Coin pages mash up CMC
  live prices with CG structure via `services/market_service.py` + `services/id_map.py`.
  Messari / DefiLlama / Alpha Vantage are backend feeds (no dump UI).

### Data sources (clients + sync)

| Source | Client | Sync script | Role |
|--------|--------|-------------|------|
| CoinMarketCap | `clients/cmc_client.py` | `scripts/sync_cmc.py` | Primary ranked/live prices |
| CoinGecko | `clients/cg_client.py` | `scripts/sync_coingecko.py` | Structure, images, details, OHLC |
| DefiLlama | `clients/defillama_client.py` | `scripts/sync_defillama.py` | DeFi TVL / prices overlay |
| Messari | `clients/messari_client.py` | `scripts/sync_messari.py` | Asset enrichment |
| Alpha Vantage | `clients/av_client.py` | `scripts/sync_alphavantage.py` | News/sentiment, ETF, FX, metals |

Celery tasks live in `tasks/sync_tasks.py`; schedule in `celeryconfig.py` (Redis broker).

Error pages: `templates/errors/` via `handlers/errors.py`.

## Cursor Cloud specific instructions

### Environment
- Python 3.12+. Dependencies in `venv/` (gitignored). Install: `./venv/bin/pip install -r requirements.txt`
  (dev/tests: also `requirements-dev.txt`). System package `python3.12-venv` required to create the venv.
- Config is driven by `.env` (`load_dotenv()` in `config.py` / clients). The Flask reloader does
  **not** watch `.env` — restart after edits.
- Redis is required for Celery (`CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`).
- Outbound internet required for syncs and CDN CSS/JS.

### Running the app
```bash
./venv/bin/python app.py          # http://127.0.0.1:5000 ; FLASK_DEBUG=true for reload
```

Celery (optional for background refresh; CLI sync works without it):
```bash
celery -A celery_app.celery worker --loglevel=info
celery -A celery_app.celery beat --loglevel=info   # only one Beat process
```

Cold-start / refill cache examples:
```bash
./venv/bin/python scripts/sync_cmc.py --tasks listings,map
./venv/bin/python scripts/sync_coingecko.py --tasks markets,trending,categories,exchanges,top-coins,ohlc,search --pages 10
./venv/bin/python scripts/sync_defillama.py --tasks protocols,chains,current_prices
./venv/bin/python scripts/sync_messari.py --tasks assets,asset_details
./venv/bin/python scripts/sync_alphavantage.py --tasks news,metals,fx   # throttles ~13s between calls
./venv/bin/python -c "from app import app; from services.id_map import build_id_map
with app.app_context(): build_id_map()"
```

### Non-obvious gotchas
- **`DATABASE_URI`** must be an absolute `sqlite:////…/instance/cache.db` path (pinned in `.env`)
  so Flask, Celery, and sync scripts share one file. `instance/` is gitignored.
- SQLite uses **WAL** (`PRAGMA journal_mode=WAL`) for concurrent writers. Do not delete
  `instance/cache.db` (or `-wal`/`-shm` sidecars) while the app is running.
- **Pytest must not wipe prod DB**: `tests/conftest.py` calls `rebind_db()` before
  `db.drop_all()`. Never call `drop_all()` after only changing `SQLALCHEMY_DATABASE_URI` —
  Flask-SQLAlchemy keeps the old engine until rebound.
- `SECRET_KEY` is required for sessions (`allow_request` anti–click-spam). Falls back to
  `DEV_SECRET_KEY` in non-production. Both are in `.env`.
- Rate-limit env values must be full flask-limiter strings (`"2000 per day"`, not `"2000"`).
- `REQUEST_GUARD_COOLDOWN=0` and a higher `PAGE_RATE_LIMIT` are set in `.env` for cached-page
  browsing; rapid hits can still 429 if limits are tightened.
- Alpha Vantage free tier is ~5 req/min / ~25 req/day — sync script sleeps between calls;
  use `--no-throttle` only with a premium key or in unit tests (mocked).
- AV soft failures: HTTP 200 bodies with `Note` / `Information` / `Error Message` are raised
  as `AvAPIError` in `clients/av_client.py`.
- Mongo ticks are best-effort; sync continues if Mongo is down.
- Git remotes: prefer SSH (`git@github.com:…`) — HTTPS through Cursor’s credential helper
  socket often fails in an external terminal.

### Lint / test / build
```bash
./venv/bin/python -m pytest -q
```
- Tests live under `tests/` (`pytest.ini`, `requirements-dev.txt`). No live network in unit tests.
- No separate linter/build step. “Build” = Flask dev server + optional Celery + sync CLIs.
