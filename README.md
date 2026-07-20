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
