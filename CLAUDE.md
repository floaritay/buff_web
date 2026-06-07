# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

BUFF 饰品自动化购买工具集 — automates purchasing low-price CS2 items from [BUFF](https://buff.163.com). Python-only, no build step.

## Commands

```bash
# Install dependencies
pip install requests
pip install flask          # optional, for dashboard only

# Run tools (all from repo root)
python scripts/item_buyer.py --search "AK-47"
python scripts/item_buyer.py 45678 --max-price 5.0 --dry-run
python scripts/buff_buyer.py --max-price 0.05 --dry-run
python scripts/buff_charm_searcher.py --event austin --dry-run
python scripts/dashboard.py

# Root-level shims still work (forward to scripts/)
python buff_buyer.py
python item_buyer.py

# Windows quick start
start_buy.bat
```

There are no tests or linter configured. Use `--dry-run` to validate behavior without placing real orders.

## Architecture

### Class hierarchy

```
BuffClient (buff/client.py)        — base class: session, cookie, CSRF, buy_item(), get_sell_orders()
├── BuffBuyer (buff/buyer.py)      — graffiti filter + buy loop
├── BuffCharmSearcher (buff/charm_searcher.py) — charm enumeration + gun search + buy loop
└── BuffItemBuyer (buff/item_buyer.py)         — single-item buy, polling, batch monitoring
```

`BuffClient.buy_item()` is the unified purchase flow used by all three subclasses. It handles session init → sell order fetch → filtering → per-order buy → seller offer request → SQLite recording.

### Key modules in `buff/`

- **client.py** — `BuffClient` base: `_init_buy_session()` (multi-step page visit for CSRF), `_extract_csrf_token()` (5 patterns), `buy_single_order()`, `buy_item()`, `_record_to_db()`
- **retry.py** — `api_request()`: exponential backoff wrapper for 429/5xx/timeout
- **log.py** — `setup_logging()`: configures the `"buff"` logger (called once in `BuffClient.__init__`)
- **db.py** — SQLite layer (`price_snapshots`, `purchase_history`, `monitored_items` tables). Thread-safe via `threading.Lock`
- **utils.py** — Cookie file I/O, `tried_items` JSON persistence, `make_tried_item()` factory
- **config.py** — `CHARM_EVENTS` dict mapping event names to `CharmEvent` dataclass
- **dashboard.py** — Flask app: data APIs + tool execution (`POST /api/run`, SSE stream, stop). Tool definitions in `TOOLS` dict

### CLI entry points in `scripts/`

Each script adds `scripts/../` to `sys.path`, creates the appropriate `Buff*` instance, handles cookie login via `validate_login_or_prompt()`, and runs the tool. Root-level `buff_buyer.py` and `item_buyer.py` are compatibility shims that forward to `scripts/`.

### Data flow

1. Cookie stored in `cookie.txt` (or `BUFF_COOKIE` env var), loaded by `buff/utils.py`
2. Purchase records persisted as JSON per tool (e.g. `item_purchases.json`, `graffiti_purchases.json`)
3. Price snapshots and purchase history written to `buff_data.db` (SQLite, WAL mode)
4. Dashboard reads from the same SQLite DB

## Conventions

- All HTTP requests go through `BuffClient._api_request()` → `buff.retry.api_request()` (retry + backoff)
- All logging via `from buff.log import logger` + `logger.info/warning/error/debug()` — never `print()` in library code
- CSRF tokens refreshed per-order via `_refresh_csrf_token()`
- New charm events: add to `CHARM_EVENTS` in `buff/config.py` with a `CharmEvent` dataclass entry
