"""niftyindices.com collection - mirrors bse.collect.BseCollector.

Only the daily index snapshot for now. Idempotent: a date whose file exists
is skipped. Errors treated as holidays (niftyindices has no public calendar
API to check against, unlike the NSE trading-holiday one).
"""

from __future__ import annotations

import datetime as dt
import logging
import time

from nse_collector import calendar_util as cal
from nse_collector.config import Settings
from nse_collector.storage import NseWarehouse
from nse_collector.collector import RunSummary, _now

from . import fetchers

log = logging.getLogger("nse_collector")  # share the collector's rotating log

DATASET = "niftyindices_snapshot"


class NiftyIndicesCollector:
    def __init__(self, settings: Settings | None = None):
        self.s = settings or Settings()
        self.wh = NseWarehouse(self.s)
        self.summary = RunSummary()

    def _fetch(self, d: dt.date):
        last = None
        for attempt in range(1, self.s.retries + 1):
            try:
                df = fetchers.daily_snapshot(d)
                time.sleep(self.s.polite_delay)
                return df
            except fetchers.NiftyIndicesNoData:
                raise
            except Exception as exc:  # noqa: BLE001
                last = exc
                time.sleep(self.s.backoff_base ** attempt)
        raise last

    def collect_snapshot(self, d: dt.date):
        iso = cal.to_iso(d)
        if self.wh.per_date_exists(DATASET, d):
            self.summary.skipped.append(f"{DATASET}:{iso}")
            return
        try:
            df = self._fetch(d)
            rows, path = self.wh.write_per_date(DATASET, df, d)
            self.wh.append_manifest(run_ts=_now(), dataset=DATASET, kind="per_date",
                                    target=iso, rows_in=rows, rows_written=rows,
                                    total_rows=rows, path=path, status="ok")
            log.info("ok %s %s: %d rows", DATASET, iso, rows)
            self.summary.written.append(f"{DATASET}:{iso}")
        except fetchers.NiftyIndicesNoData:
            log.info("skip %s %s (no data - holiday?)", DATASET, iso)
            self.summary.skipped.append(f"{DATASET}:{iso}")
        except Exception as exc:  # noqa: BLE001
            log.info("skip %s %s (error: %s)", DATASET, iso, exc)
            self.summary.skipped.append(f"{DATASET}:{iso}")

    def run_daily(self, run_date: dt.date | None = None) -> RunSummary:
        day = cal.last_trading_day(run_date or dt.date.today(), self.s.holiday_product)
        self.collect_snapshot(day)
        log.info("NIFTYINDICES DAILY DONE %s | %s", cal.to_iso(day), self.summary.line())
        return self.summary

    def run_backfill(self, frm: dt.date, to: dt.date) -> RunSummary:
        days = list(cal.trading_days(frm, to, self.s.holiday_product))
        log.info("NIFTYINDICES backfill %s..%s (%d days)", cal.to_iso(frm), cal.to_iso(to), len(days))
        for d in days:
            self.collect_snapshot(d)
        log.info("NIFTYINDICES BACKFILL DONE | %s", self.summary.line())
        return self.summary
