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
- Optional: Redis (only if you still use legacy Celery)

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

Tables are created automatically on app start (`db.create_all()`). Existing DBs also get
generic identity columns via `ensure_market_coin_identity_columns()` (`platforms`,
`primary_chain`, `contract_address`, `external_ids`, `structure_synced_at`,
`metrics_synced_at`) — names stay provider-agnostic so quote oracles can change later.

## Populate MySQL view tables

Prefer filling from the CLI before browsing (avoids first-hit latency and CG stampedes):

```bash
./venv/bin/python scripts/populate_views.py --tables all --force
```

Selective:

```bash
./venv/bin/python scripts/populate_views.py --tables markets,exchanges,trending,categories
./venv/bin/python scripts/populate_views.py --sync-platforms
```

Patch live Markets metrics (keeps CoinGecko rank / row identity):

```bash
./venv/bin/python scripts/populate_views.py --patch-cmc
./venv/bin/python scripts/populate_views.py --patch-defillama
```

`--sync-platforms` fills generic chain/contract fields from CoinGecko `coins/list`.
DefiLlama patches derive quote keys from those fields (fallback `coingecko:{id}`).

Celery schedules are **legacy**. Production refresh uses **crontab** (see below).

| Job | Cadence | Target |
|-----|---------|--------|
| CG Markets structure | 30 min | MySQL `market_coins` |
| CG platforms / contracts | daily | MySQL `market_coins` identity cols |
| DefiLlama price pulse | 60 s | MySQL `market_coins` price |
| CMC metrics patch | 12 min | MySQL `market_coins` mcap / volume / % |
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

## Production refresh (crontab)

**Preferred.** Cron calls existing CLIs — no Celery Beat/worker required.

```bash
# Install example crontab (edit CRYPTODASH_ROOT if needed)
crontab deploy/crontab.example

# Or merge jobs into: crontab -e
```

Wrapper: [`scripts/run_cron.sh`](scripts/run_cron.sh) (logging + `flock` so jobs do not overlap).

| Job | Cadence |
|----------|---------|
| `run_cron.sh markets` | every 30 min |
| `run_cron.sh sync-platforms` | daily |
| `run_cron.sh patch-defillama` | every **60 s** (price pulse) |
| `run_cron.sh patch-cmc` | every 12 min |
| `run_cron.sh trending` | hourly |
| `run_cron.sh exchanges-categories` | daily |
| `run_cron.sh warm-apicache` | daily |

Logs: `~/logs/cryptodash/cron.log` (override with `CRYPTODASH_LOG_DIR`).

```bash
# Manual smoke test
CRYPTODASH_ROOT=/var/www/html/cryptodash /var/www/html/cryptodash/scripts/run_cron.sh markets
CRYPTODASH_ROOT=/var/www/html/cryptodash /var/www/html/cryptodash/scripts/run_cron.sh patch-cmc
tail -n 50 ~/logs/cryptodash/cron.log
```

Verify cron ran: `grep CRON /var/log/syslog | tail`

## Celery (legacy / optional)

Task modules remain for ad-hoc use, but **do not run Beat/worker in production** if crontab is installed.

```bash
# Only if you intentionally use Celery instead of cron:
./venv/bin/celery -A celery_app.celery worker --loglevel=INFO --concurrency=2
./venv/bin/celery -A celery_app.celery beat --loglevel=INFO
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
scripts/run_cron.sh            # cron entrypoint (flock + logging)
deploy/crontab.example         # production schedule
clients/                    # cg, cmc, av, defillama, messari, lunarcrush
models.py                   # ApiCache + typed view tables
templates/
```

Agent-oriented notes live in [`AGENTS.md`](AGENTS.md).
