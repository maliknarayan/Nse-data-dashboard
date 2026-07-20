"""Core collection engine: retries, polite delay, per-kind logic, run modes."""

from __future__ import annotations

import contextlib
import datetime as dt
import io
import logging
import os
import time
from dataclasses import dataclass, field
from logging.handlers import RotatingFileHandler

from . import calendar_util as cal
from .config import COLLECTED_ON, Settings, registry
from .resolver import resolve
from .storage import NseWarehouse, normalize

log = logging.getLogger("nse_collector")


def setup_logging(settings: Settings, verbose: bool = False) -> logging.Logger:
    os.makedirs(settings.log_dir, exist_ok=True)
    log.handlers.clear()
    log.setLevel(logging.DEBUG if verbose else logging.INFO)

    fh = RotatingFileHandler(
        os.path.join(settings.log_dir, "nse_collector.log"),
        maxBytes=2_000_000, backupCount=10, encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if verbose else logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)s %(message)s"))

    log.addHandler(fh)
    log.addHandler(ch)
    return log


@dataclass
class RunSummary:
    written: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    def line(self) -> str:
        return (f"written={len(self.written)} skipped={len(self.skipped)} "
                f"failed={len(self.failed)}")


class Collector:
    def __init__(self, settings: Settings | None = None):
        self.s = settings or Settings()
        self.wh = NseWarehouse(self.s)
        self.reg = registry()
        self.summary = RunSummary()

    # --- low level fetch with retry/backoff/polite delay ---
    def _fetch(self, ds: dict, **extra):
        fn = resolve(ds["fn"])
        kwargs = {**ds.get("params", {}), **extra}
        last = None
        for attempt in range(1, self.s.retries + 1):
            try:
                # nselib prints column dumps to stdout; swallow to keep logs clean
                with contextlib.redirect_stdout(io.StringIO()):
                    result = fn(**kwargs)
                time.sleep(self.s.polite_delay)
                return result
            except Exception as exc:  # noqa: BLE001
                last = exc
                wait = self.s.backoff_base ** attempt
                log.warning("%s attempt %d/%d failed: %s; retry in %.1fs",
                            ds["name"], attempt, self.s.retries, exc, wait)
                time.sleep(wait)
        raise last  # exhausted retries

    # --- per-kind collection ---
    def collect_snapshot(self, ds: dict, run_date: dt.date, symbol: str | None = None):
        name = ds["name"]
        if ds.get("symbol") and not symbol:
            log.info("skip %s (needs --symbol)", name)
            self.summary.skipped.append(name)
            return
        try:
            extra = {"symbol": symbol} if ds.get("symbol") else {}
            df = normalize(self._fetch(ds, **extra))
            if df.empty:
                log.info("skip %s (empty)", name)
                self.summary.skipped.append(name)
                return
            df[COLLECTED_ON] = cal.to_iso(run_date)
            if ds.get("symbol") and symbol:
                df["symbol"] = symbol
            rows_in, total = self.wh.write_growing(name, df, ds.get("key"), snapshot=True)
            self.wh.append_manifest(run_ts=_now(), dataset=name, kind="snapshot",
                                    target=cal.to_iso(run_date), rows_in=rows_in,
                                    rows_written=rows_in, total_rows=total,
                                    path=self.wh._growing_path(name), status="ok")
            log.info("ok %s: +%d rows (total %d)", name, rows_in, total)
            self.summary.written.append(name)
        except Exception as exc:  # noqa: BLE001
            self._handle_fail(ds, exc, "snapshot", cal.to_iso(run_date))

    def collect_date_range(self, ds: dict, frm: dt.date, to: dt.date):
        name = ds["name"]
        target = f"{cal.to_iso(frm)}..{cal.to_iso(to)}"
        try:
            df = normalize(self._fetch(ds, from_date=cal.to_nse(frm), to_date=cal.to_nse(to)))
            rows_in, total = self.wh.write_growing(name, df, ds.get("key"), snapshot=False)
            self.wh.append_manifest(run_ts=_now(), dataset=name, kind="date_range",
                                    target=target, rows_in=rows_in, rows_written=rows_in,
                                    total_rows=total, path=self.wh._growing_path(name),
                                    status="ok" if rows_in else "empty")
            if rows_in:
                log.info("ok %s: +%d rows (total %d)", name, rows_in, total)
                self.summary.written.append(name)
            else:
                log.info("skip %s (empty for %s)", name, target)
                self.summary.skipped.append(name)
        except Exception as exc:  # noqa: BLE001
            self._handle_fail(ds, exc, "date_range", target)

    def collect_per_date(self, ds: dict, d: dt.date):
        name = ds["name"]
        if self.wh.per_date_exists(name, d):
            log.debug("skip %s %s (file exists)", name, cal.to_iso(d))
            self.summary.skipped.append(f"{name}:{cal.to_iso(d)}")
            return
        try:
            df = normalize(self._fetch(ds, trade_date=cal.to_nse(d)))
            if df.empty:  # holiday / no report published
                log.info("skip %s %s (no data - holiday?)", name, cal.to_iso(d))
                self.summary.skipped.append(f"{name}:{cal.to_iso(d)}")
                return
            rows, path = self.wh.write_per_date(name, df, d)
            self.wh.append_manifest(run_ts=_now(), dataset=name, kind="per_date",
                                    target=cal.to_iso(d), rows_in=rows, rows_written=rows,
                                    total_rows=rows, path=path, status="ok")
            log.info("ok %s %s: %d rows", name, cal.to_iso(d), rows)
            self.summary.written.append(f"{name}:{cal.to_iso(d)}")
        except Exception as exc:  # noqa: BLE001
            # per_date treats errors as holidays/skips by default
            log.info("skip %s %s (error treated as holiday: %s)",
                     name, cal.to_iso(d), exc)
            self.summary.skipped.append(f"{name}:{cal.to_iso(d)}")

    def _handle_fail(self, ds: dict, exc: Exception, kind: str, target: str):
        name = ds["name"]
        self.wh.append_manifest(run_ts=_now(), dataset=name, kind=kind, target=target,
                                rows_in=0, rows_written=0, total_rows="",
                                path="", status=f"error: {exc}")
        if ds.get("optional"):
            log.warning("skip optional %s (%s)", name, exc)
            self.summary.skipped.append(name)
        else:
            log.error("FAIL %s (%s)", name, exc)
            self.summary.failed.append(name)

    # --- selection ---
    def select(self, kinds: set[str] | None = None, names: list[str] | None = None,
               groups: list[str] | None = None) -> list[dict]:
        out = []
        for ds in self.reg.values():
            if kinds and ds["kind"] not in kinds:
                continue
            if names and ds["name"] not in names:
                continue
            if groups and ds.get("group") not in groups:
                continue
            out.append(ds)
        return out

    # --- run modes ---
    def run_daily(self, run_date: dt.date | None = None, names=None, groups=None,
                  symbol: str | None = None) -> RunSummary:
        run_date = run_date or dt.date.today()
        day = cal.last_trading_day(run_date, self.s.holiday_product)
        if not cal.is_trading_day(run_date, self.s.holiday_product):
            log.info("%s is not a trading day; using last trading day %s for per_date",
                     cal.to_iso(run_date), cal.to_iso(day))

        for ds in self.select(names=names, groups=groups):
            if ds["kind"] == "snapshot":
                self.collect_snapshot(ds, run_date, symbol=symbol)
            elif ds["kind"] == "date_range":
                frm = day - dt.timedelta(days=self.s.daily_range_lookback)
                self.collect_date_range(ds, frm, day)
            elif ds["kind"] == "per_date":
                self.collect_per_date(ds, day)
        log.info("DAILY DONE %s | %s", cal.to_iso(run_date), self.summary.line())
        return self.summary

    def run_backfill(self, frm: dt.date, to: dt.date, names=None, groups=None) -> RunSummary:
        """Fill per_date files and merge date_range for a past window."""
        days = list(cal.trading_days(frm, to, self.s.holiday_product))
        log.info("backfill %s..%s (%d trading days)", cal.to_iso(frm), cal.to_iso(to), len(days))
        # date_range: one call spanning the whole window
        for ds in self.select(kinds={"date_range"}, names=names, groups=groups):
            self.collect_date_range(ds, frm, to)
        # per_date: one file per trading day
        for ds in self.select(kinds={"per_date"}, names=names, groups=groups):
            for d in days:
                self.collect_per_date(ds, d)
        log.info("BACKFILL DONE %s..%s | %s", cal.to_iso(frm), cal.to_iso(to),
                 self.summary.line())
        return self.summary


def _now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
