# CryptoDash

Server-rendered Flask dashboard for cryptocurrency markets. Main list pages read **MySQL**; CoinGecko fills those tables on first use (or via CLI). Coin detail, search, and news use a separate path.

## Architecture (short)

```
CoinGecko API  →  populate_coingecko / populate_views.py  →  MySQL tables
views blueprint (SELECT only)  →  Market / Exchanges / Trending / Categories

cg blueprint  →  ApiCache (coin detail, search, OHLC) + CryptoPanic widgets (news)
```

Other API clients (CMC, Alpha Vantage, DefiLlama, Messari, LunarCrush) are present for future writers; they are not required for the main views today.

## Requirements

- Python 3.12+
- MySQL 8+ (database + user already created)
- CoinGecko API key in `.env`
- Optional: Redis (Celery only)

## Setup

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
# for tests:
./venv/bin/pip install -r requirements-dev.txt
```

Copy or edit `.env`. Important keys:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URI` | MySQL URL, e.g. `mysql+pymysql://USER:PASSWORD@127.0.0.1:3306/cryptodash` |
| `CG_API_KEY` | CoinGecko key |
| `SECRET_KEY` / `DEV_SECRET_KEY` | Flask sessions |
| `VIEWS_RATE_LIMIT` | MySQL list pages (default `120 per minute`) |
| `PAGE_RATE_LIMIT` | Coin detail / search / OHLC (default `60 per minute`) |

URL-encode special characters in the DB password (`/` → `%2F`, `+` → `%2B`).

Tables are created automatically on app start (`db.create_all()`).

## Populate MySQL view tables

Prefer filling from the CLI before browsing (avoids first-hit latency and CG stampedes):

```bash
./venv/bin/python scripts/populate_views.py --tables all --force
```

Selective:

```bash
./venv/bin/python scripts/populate_views.py --tables markets,exchanges,trending,categories
```

Patch live Markets metrics from CMC (keeps CoinGecko rank / row identity):

```bash
./venv/bin/python scripts/populate_views.py --patch-cmc
```

Celery (with Redis) schedules:

| Job | Cadence | Target |
|-----|---------|--------|
| CG Markets structure | 30 min | MySQL `market_coins` |
| CMC metrics patch | 12 min | MySQL `market_coins` prices |
| CG Trending | 1 hour | MySQL `trending_*` |
| CG Exchanges | daily | MySQL `exchanges` |
| CG Categories | daily | MySQL `categories` |
| CG exchange details | daily (top 20) | ApiCache warmer |
| CG top coins / OHLC / search | daily (small) | ApiCache warmer |

The Markets page polls `/api/markets/prices` every 15s and flashes updated prices.

| Table | Page |
|-------|------|
| `market_coins` + `global_stats` | `/` |
| `exchanges` | `/exchanges` |
| `trending_snapshots` | `/trending` |
| `categories` | `/categories` |

If a table is empty, the corresponding page will call CoinGecko once (with a sync lock), then serve from MySQL.

## Coin / search / exchange detail (ApiCache + live-fill)

Secondary routes use ApiCache first. On a miss they **live-fetch CoinGecko once**, store the result, then render. Prewarm popular keys to save Demo credits:

```bash
./venv/bin/python scripts/sync_coingecko.py --tasks top-coins,ohlc,search,exchange-details --limit 15
```

List pages (Market / Exchanges / Trending / Categories) remain MySQL-only after first fill.

### Secrets

- Copy `.env.example` → `.env` (never commit `.env`).
- Rotate any keys that were previously committed to git history.
- Production: `FLASK_ENV=production`, `FLASK_DEBUG=false`, set `SECRET_KEY`.
- Multi-worker: use Redis for `CACHE_TYPE` / `RATELIMIT_STORAGE_URI` (see `.env.example`).

## Run the app

```bash
./venv/bin/python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

`FLASK_DEBUG=true` enables the reloader. The reloader does **not** watch `.env` — restart after config changes.

### Pages

| Path | Source |
|------|--------|
| `/` | MySQL `market_coins` |
| `/exchanges` | MySQL `exchanges` |
| `/trending` | MySQL `trending_snapshots` |
| `/categories` | MySQL `categories` |
| `/coin/<id>` | ApiCache + live-fill on miss |
| `/search?q=` | ApiCache + live-fill on miss |
| `/exchange/<id>` | ApiCache + live-fill on miss |
| `/news` | CryptoPanic embed widgets |

## Celery (optional)

For scheduled background syncs (legacy tasks still registered):

```bash
# Terminal 1 — worker
celery -A celery_app.celery worker --loglevel=info

# Terminal 2 — one Beat process only
celery -A celery_app.celery beat --loglevel=info
```

Requires Redis (`CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` in `.env`).

## Tests

```bash
./venv/bin/python -m pytest -q
```

Tests use an isolated temporary SQLite DB (they must not wipe your MySQL `cryptodash` data).

## Project layout (useful paths)

```
app.py                      # Flask app, MySQL bind, blueprints
blueprints/views/           # DB-read Market / Exchanges / Trending / Categories
blueprints/coingecko/       # Coin detail, search, news, OHLC
services/populate_coingecko.py
scripts/populate_views.py
clients/                    # cg, cmc, av, defillama, messari, lunarcrush
models.py                   # ApiCache + typed view tables
templates/
```

Agent-oriented notes live in [`AGENTS.md`](AGENTS.md).
