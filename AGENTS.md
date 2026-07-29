# CryptoDash

A server-rendered Flask cryptocurrency dashboard. Main list pages read **typed MySQL tables**.
On first request (empty table), CoinGecko populates those tables; later requests are DB-only.

## Architecture

```
cg_client  --first fill / CLI-->  populate_coingecko  -->  MySQL view tables
                                                          market_coins, exchanges,
                                                          trending_*, categories, global_stats
views blueprint  --SELECT only-->  templates (Market / Exchanges / Trending / Categories)

cg blueprint (remaining) --> ApiCache / CG for coin detail, search, news, exchange detail
```

- **MySQL** via `DATABASE_URI` (`cryptodash` @ `127.0.0.1:3306`). Driver: `PyMySQL`.
- **Views blueprint** [`blueprints/views/`](blueprints/views/) — no HTTP client imports; calls
  `ensure_*()` then reads ORM models in [`models.py`](models.py).
- **Populate** [`services/populate_coingecko.py`](services/populate_coingecko.py) +
  CLI [`scripts/populate_views.py`](scripts/populate_views.py). Uses `sync_locks` to prevent
  concurrent first-fill stampedes.
- **`api_cache`** still used for coin detail / search / OHLC (legacy CG cache path).
- **Other clients** (CMC, AV, DefiLlama, Messari, LunarCrush) remain for Phase 5 writers.
- Error pages: `templates/errors/` via `handlers/errors.py`.

### Main view tables

| Table | Populated by | Served by |
|-------|--------------|-----------|
| `market_coins` + `global_stats` | `ensure_markets` | `/` |
| `exchanges` | `ensure_exchanges` | `/exchanges` |
| `trending_snapshots` (+ `trending_coins`) | `ensure_trending` | `/trending` |
| `categories` | `ensure_categories` | `/categories` |

## Cursor Cloud specific instructions

### Environment
- Python 3.12+. `./venv/bin/pip install -r requirements.txt` (+ `requirements-dev.txt` for tests).
- `.env` drives config (`load_dotenv`). Restart Flask after `.env` edits (reloader does not watch it).
- Redis only needed for Celery.

### Running the app
```bash
./venv/bin/python app.py
```

Populate / refresh MySQL view tables:
```bash
./venv/bin/python scripts/populate_views.py --tables all --force
./venv/bin/python scripts/populate_views.py --tables markets,exchanges
```

Legacy ApiCache sync (coin detail / search still need this):
```bash
./venv/bin/python scripts/sync_coingecko.py --tasks top-coins,ohlc,search
```

### Non-obvious gotchas
- Password special chars in `DATABASE_URI` must be URL-encoded (`/` → `%2F`, `+` → `%2B`).
- Pytest uses temp SQLite via `rebind_db()` — never `drop_all()` without rebinding.
- First page hit on empty tables calls CoinGecko (needs network + API key). Prefer CLI populate in demos.
- `REQUEST_GUARD_COOLDOWN=0` disables session click-spam cooldown.
- Rate limits are split:
  - `PAGE_RATE_LIMIT` — CG secondary routes (coin/search/OHLC) that still use ApiCache.
  - `VIEWS_RATE_LIMIT` — MySQL list pages (default `120 per minute`); protects the app/DB only.

### Lint / test / build
```bash
./venv/bin/python -m pytest -q
```
