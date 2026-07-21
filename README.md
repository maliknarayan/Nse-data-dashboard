# NSE Market Data Collector

Library-first collector that downloads NSE (India) **Market Data** datasets into
a local CSV warehouse on a daily schedule. A dashboard reads the CSVs later.

## Core principle: library-first

The fetch engine is the [`nselib`](https://pypi.org/project/nselib/) package.
It handles NSE's cookie/session handshake and anti-bot headers. **We do not
hand-roll scrapers.** When NSE changes, upgrade `nselib` — don't patch code here.

Every registered dataset is verified against the **installed** `nselib` at
runtime (`--list` shows resolve status), because function names are read from the
package, not from memory.

---

## Setup

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate     Linux/Mac:  source .venv/bin/activate
pip install -r requirements.txt

python -m nse_collector --list          # confirm every dataset resolves "ok"
```

Requires Python 3.10+. Tested on Python 3.14 + nselib 2.5.1.

> Note: `nselib.cash_market` has an internal import bug in some builds. None of
> the registered datasets use it — the resolver imports modules lazily, so a
> broken submodule only affects datasets that reference it, never the whole run.

---

## The one distinction that matters: snapshot vs historical

NSE datasets split into two fundamentally different types. This drives storage,
idempotency, and whether backfill is even possible.

| kind | what it is | can backfill? | storage |
|------|-----------|---------------|---------|
| **snapshot** | live state only (top gainers, most active, live indices, option chain) | **No** — history exists only if we run daily | one growing `<dataset>.csv`, each row stamped `_collected_on`, deduped so same-day re-runs don't duplicate but different days accumulate |
| **date_range** | one call covers a from/to window (bulk/block/short deals, corporate actions) | Yes | one growing `<dataset>.csv`, merged + deduped (a row is unique as a whole) |
| **per_date** | one report per trading date (bhav copy, F&O bhav, 52wk H/L, turnover, PE, FII stats, participant OI/volume, ban list, daily volatility) | Yes | one file per date `<dataset>_<YYYY-MM-DD>.csv`; a date whose file exists is skipped (idempotent backfill) |

**Why snapshots can't be backfilled:** NSE only serves the *current* live value.
If you didn't run the collector on a given day, that day's gainers/most-active
snapshot is gone forever. Run daily to build history.

### Warehouse layout

```
data/
  <dataset>/<dataset>.csv               # snapshot + date_range (growing)
  <dataset>/<dataset>_2026-07-16.csv    # per_date (one file per date)
  _manifest.csv                         # append-only write log of every run
```

Storage is isolated in `nse_collector/storage.py`. Swap it for DuckDB/parquet
later without touching collector logic — the collector only calls `normalize`,
`write_growing`, `write_per_date`, `per_date_exists`, `append_manifest`.

---

## Datasets

`python -m nse_collector --list` prints all of them. Summary:

- **deals / corporate** (date_range): bulk deals, block deals, short selling, corporate actions
- **breadth** (snapshot): top gainers, top losers, most active by value, most active by volume, total traded stocks, advances/declines*
- **indices** (snapshot): all indices (live), live index performances
- **derivatives**: most active underlying (snapshot), live option chain (snapshot, needs `--symbol`), F&O bhav copy, F&O turnover, FII derivatives stats, participant-wise OI, participant-wise volume, securities in ban (per_date), MWPL* (snapshot, stub)
- **bhav** (per_date): bhav copy with delivery, F&O bhav copy
- **reports** (per_date): 52-week high/low, PE ratio, daily volatility
- **turnover** (per_date): cash turnover, F&O turnover

\* `advances_declines` and `mwpl` are **optional custom fetchers** in
`custom_fetchers.py` (data not in nselib), clearly marked as stubs to verify
against the live site. Delete the file or its datasets and the collector runs
unchanged. `advances_declines` is best-effort (derived from the summary
`total_traded_stocks` already returns); `mwpl` is an unimplemented stub.

Per-stock OHLCV+delivery history comes from the **daily bhav copy**
(`bhavcopy_delivery` — whole market in one file), not by looping thousands of
symbols.

---

## Adding a dataset

Add ONE dict to `DATASETS` in `nse_collector/config.py`:

```python
{"name": "my_dataset", "kind": "per_date", "group": "reports",
 "fn": "capital_market.some_function", "params": {}, "key": None},
```

- `fn` is `"module.function"` resolved against nselib (`capital_market`,
  `derivatives`, `indices`, `cash_market`, `debt`) or `"custom.<fn>"`.
- `kind` picks the fetch/storage behaviour (see table above).
- `key` is the natural key for de-dup:
  - snapshot: entity columns (effective key = `key + _collected_on`). Include any
    bucket/category column — e.g. gainers repeat a symbol across index buckets,
    so their key is `["symbol", "legend"]`.
  - date_range: usually `None` (whole-row dedup).
  - per_date: ignored (one file per date).

Then verify: `python -m nse_collector --list` should show it `ok`.

---

## CLI

```
--list                 list datasets + resolve status
--snapshot             run snapshot datasets only
--all-per-date         run per_date datasets for the last trading day
--all-date-range       run date_range datasets for --from..--to (default last 7d)
--dataset NAME         restrict to a dataset (repeatable)
--group GROUP          restrict to a group (repeatable)
--from / --to          YYYY-MM-DD window (backfill / date_range)
--symbol SYM           symbol for datasets that need one (option_chain)
--backfill             fill per_date + date_range for --from..--to
--polite SECONDS       override delay between calls
--verbose              debug logging
```

Examples:

```bash
python -m nse_collector                              # full daily job
python -m nse_collector --snapshot
python -m nse_collector --group derivatives
python -m nse_collector --symbol NIFTY --dataset option_chain
python -m nse_collector --backfill --from 2026-07-01 --to 2026-07-10
```

---

## Daily automation

**Single command** for the daily job (run after market close, ~18:30 IST):

```bash
python -m nse_collector
```

It runs all snapshots + that day's per_date reports + that day's date_range
merge. It is **idempotent** — safe to re-run the same day:

- snapshot: same-day rows dedupe on natural key + `_collected_on`
- date_range: identical rows dropped on merge
- per_date: a date whose file already exists is skipped without fetching

Weekends and NSE holidays are skipped gracefully (holiday list comes from
nselib's own calendar). Empty/error per_date results are treated as holidays and
skipped, never crash. Every call retries with exponential backoff and honours a
configurable polite delay. A rotating log is written to `logs/nse_collector.log`
and every run prints a `written / skipped / failed` summary.

### crontab (Mon–Fri, 18:30 IST)

Set the machine timezone to IST or prefix with `TZ`. `deploy/run_daily.sh` wraps
the venv + `cd` (edit its paths first, `chmod +x` it).

```cron
# m h dom mon dow   command
30 18 * * 1-5  TZ=Asia/Kolkata /opt/nse-market-collector/deploy/run_daily.sh >> /var/log/nse-collector.cron.log 2>&1
```

### systemd timer alternative

Copy `deploy/nse-collector.service` and `deploy/nse-collector.timer` to
`/etc/systemd/system/` (edit paths/user first), then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now nse-collector.timer
systemctl list-timers nse-collector.timer     # verify next run
journalctl -u nse-collector.service -f        # watch a run
```

The timer fires `Mon..Fri 18:30 Asia/Kolkata`, `Persistent=true` so a missed run
(box was off) is caught up on next boot.

### Backfill

Fill a past window for historical/per_date + date_range datasets in one shot:

```bash
python -m nse_collector --backfill --from 2026-07-01 --to 2026-07-10
# scope it:
python -m nse_collector --backfill --from 2026-07-01 --to 2026-07-10 \
    --dataset bhavcopy_delivery --group derivatives
```

Backfill is idempotent — re-running skips dates already on disk. Snapshots are
**not** backfillable (see the distinction above) and are ignored by `--backfill`.

---

## Dashboard (investor view)

A Streamlit app reads the warehouse directly. Install deps (`requirements.txt`
already includes `streamlit` + `xlrd`) then:

```bash
python -m streamlit run dashboard/app.py
```

(Use `python -m streamlit` — the bare `streamlit` command only works if
Python's Scripts dir is on PATH.)

Tabs, all built for an investor reading the day's tape:

| tab | what it answers |
|-----|-----------------|
| 📊 **Market Pulse** | Breadth (advances/declines, A/D ratio), headline index cards, full index table with **P/E, P/B, div yield + 30d/365d momentum** (valuation heatmap), best/worst indices |
| 🚀 **Movers** | Top gainers/losers by index bucket, most active by value & volume |
| 💰 **Smart Money** | Bulk & block deals (side + symbol filter, deal value in ₹Cr), short selling, upcoming corporate actions (ex-date ahead) |
| 📉 **Derivatives & FII** | Participant net index-future positioning (FII/DII/Client/Pro — who's directional), FII net buy/sell by instrument, most active underlyings, F&O ban list |
| 🎯 **Delivery & Value** | **Delivery % leaders** (conviction accumulation = high delivery + price up), P/E lookup, highest-volatility underlyings |
| 🎯 **Signals** | Decision-support (see below) |
| 📈 **History** | Per-symbol OHLC candlestick + volume + delivery-% trend, built from the bhav copies you've collected/backfilled. Extends as you backfill more dates. |
| 🩺 **Data Health** | Last collection per dataset, row counts, freshness (from `_manifest.csv`) |

### 🎯 Signals — decision-support, not advice

Transparent buy/sell *evidence* from the data. Every score is the sum of named
factors, each shown with a plain-English reason — no black box, no price
prediction. Educational only.

- **Market regime** — Risk-On / Neutral / Risk-Off from A/D ratio, % indices
  green, and India VIX. Answers "is this an environment to buy?"
- **Stock scorecard** — type a symbol → factor breakdown (delivery conviction,
  accumulation vs distribution, bulk/block smart-money, F&O-ban & volatility
  risk, P/E) → composite verdict (Accumulation / Neutral / Caution / Avoid).
- **Screeners** — accumulation candidates (high delivery + up), distribution
  warnings (high delivery + down), **52-week breakouts** (at/near 52wk high),
  institutional buys (bulk deals by value).
- **Today's top ideas** — the high-delivery/up universe re-scored across all
  factors and ranked.
- **Watchlist** — persistent (`data/_watchlist.json`); each symbol scored daily.
  **Alerts** flag when a watched symbol's signal turns cautious / weakens /
  strengthens vs the last run (state in `data/_watchlist_state.json`).
- **Delivery-% trend** — per-symbol multi-day delivery chart in the scorecard
  (needs a few collected days; rising delivery = growing conviction).

Market Pulse also shows a **breadth donut** (advances / declines / unchanged).

**Symbol autocomplete** — every symbol picker is a searchable dropdown showing
`SYMBOL — Company Name`, backed by the full listed-equity master (`equity_master`
dataset, ~2400 names from NSE's public `EQUITY_L.csv`; `nselib.equity_list()` is
broken in 2.5.1). Collect it with `python -m nse_collector --dataset equity_master`
(also runs in the daily job). Falls back to the latest bhav copy's symbols if the
master isn't collected yet.

Logic lives in `dashboard/signals.py` (pure functions, unit-tested offline).
Signals sharpen as the warehouse accumulates history; with only a few days
collected, valuation/trend context is limited — the code does not fake it.

The app is cached (5 min TTL); hit **🔄 Reload data** in the sidebar after a
fresh collection. Missing datasets show a hint, never an error — so it works
even before the first full collection.

Storage reads are isolated in `dashboard/loader.py` (mirrors `storage.py`) —
swap both to DuckDB/parquet without touching the UI.

## BSE data (separate from the NSE library-first pipeline)

BSE has no clean library, so `bse/` is a small isolated scraper for data **not**
covered by NSE — the **BSE EOD bhav copy** (BSE-listed universe, ~4800–5300
scrips, many BSE-only), from bseindia.com's UDiFF CSV. It reuses the NSE
collector's storage, calendar and settings, and stores per-date files
`data/bse_bhavcopy/bse_bhavcopy_<date>.csv`.

```bash
python -m bse                                       # today's BSE bhav copy
python -m bse --backfill --from 2026-07-01 --to 2026-07-17
```

Or from the dashboard sidebar → **Fetch BSE data** (fetch latest / backfill).
The **📈 History** tab has an **NSE / BSE** toggle to chart either exchange
(BSE has OHLC + volume; no delivery %).

BSE gates its endpoints and changes them often — fetchers degrade gracefully
(blocked/holiday date → skip, never crash). Only the bhav copy is confirmed
working; add more BSE endpoints in `bse/fetchers.py` as you verify them. NSE
already covers deals, gainers, indices etc., so those are intentionally not
duplicated from BSE.

## Datewise history for "live-only" data

NSE/BSE archive EOD reports per date (bhav copy etc.) but do **not** archive live
snapshots (gainers, most active, breadth). Those are recomputed datewise:

- **🗓️ Day Explorer tab** — pick any collected trading date → breadth (cards +
  donut), gainers, losers, most active, all **derived from that day's bhav copy**
  (`dashboard/derive.py`). Works retroactively for every date you've backfilled.
- **Index EOD history** — real NSE archive via `index_data`
  (`nse_collector/index_history.py`), stored per index at
  `data/index_history/index_history_<INDEX>.csv`. In the **📈 History** tab pick
  **NSE index** → Fetch/refresh → candlestick.
- Option-chain OI stays daily-capture only (no exchange archive exists).

## Concalls (fundamentals view)

Drop Claude-generated concall analysis MDs under `concall-data/<quarter>/`
(e.g. `concall-data/Q4FY26/Company_Q4FY26.md`). The **📞 Concalls** page
auto-detects quarters and parses each file's header
(`**Verdict:** … **Classification:** … **Management Confidence:** n/10`):

- Overview strip (companies, BUY count, HOLD/AVOID, avg confidence)
- Filterable/searchable table with verdict + call badges
- Full-analysis reader (rendered markdown)
- Best-effort **company → symbol** match shows the stock's **live signal
  scorecard** beside the concall — fundamentals + technicals/flows together

Files with a different layout (no verdict header) still list and render; they
just show a blank verdict. Add new quarters by dropping a folder — no code change.

## Config via environment

| var | default | meaning |
|-----|---------|---------|
| `NSE_DATA_DIR` | `data` | warehouse root |
| `NSE_LOG_DIR` | `logs` | log directory |
| `NSE_POLITE_DELAY` | `2.0` | seconds between every call |
| `NSE_RETRIES` | `3` | attempts per call |
| `NSE_BACKOFF_BASE` | `2.0` | backoff = base ** attempt |

---

## Tests

Offline, no network (fetch is mocked):

```bash
python -m pytest tests/ -q
```

Covers the return-type normalizer, snapshot same-day dedup, snapshot
multi-day accumulation, date_range whole-row dedup, and per_date idempotent
skip + holiday/error handling.

---

## Legal / etiquette

This data is publicly published by NSE, but **NSE's terms restrict automated
access**. Use this for **personal / research** purposes only. Keep the polite
delay in place (don't lower it), run once daily after close rather than polling,
and do not redistribute the data commercially. You are responsible for complying
with NSE's terms of use. If you need bulk or commercial data, use NSE's official
paid data feeds.
