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

| Table | Page |
|-------|------|
| `market_coins` + `global_stats` | `/` |
| `exchanges` | `/exchanges` |
| `trending_snapshots` | `/trending` |
| `categories` | `/categories` |

If a table is empty, the corresponding page will call CoinGecko once (with a sync lock), then serve from MySQL.

## Coin detail / search (ApiCache)

These still use the legacy cache store:

```bash
./venv/bin/python scripts/sync_coingecko.py --tasks top-coins,ohlc,search
```

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
| `/coin/<id>` | ApiCache (CoinGecko sync) |
| `/search?q=` | ApiCache |
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
