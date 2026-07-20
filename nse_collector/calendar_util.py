"""Trading-calendar helpers: weekend + NSE holiday skipping and date formats.

Holidays come from nselib's own calendar so we don't hand-maintain a list.
Fetched once per process and cached; if the fetch fails we fall back to
weekend-only skipping (a per_date fetch on a holiday simply returns empty and
is treated as a skip anyway).
"""

from __future__ import annotations

import datetime as dt
from functools import lru_cache

# nselib wants %d-%m-%Y; warehouse filenames use %Y-%m-%d
NSE_FMT = "%d-%m-%Y"
ISO_FMT = "%Y-%m-%d"
_HOLIDAY_FMT = "%d-%b-%Y"  # e.g. 26-Jan-2026


def to_nse(d: dt.date) -> str:
    return d.strftime(NSE_FMT)


def to_iso(d: dt.date) -> str:
    return d.strftime(ISO_FMT)


def parse_iso(s: str) -> dt.date:
    return dt.datetime.strptime(s, ISO_FMT).date()


@lru_cache(maxsize=1)
def holidays(product: str = "Equities") -> frozenset[dt.date]:
    try:
        import nselib
        df = nselib.trading_holiday_calendar()
        rows = df[df["Product"] == product] if "Product" in df.columns else df
        out: set[dt.date] = set()
        for raw in rows["tradingDate"].tolist():
            try:
                out.add(dt.datetime.strptime(str(raw), _HOLIDAY_FMT).date())
            except ValueError:
                continue
        return frozenset(out)
    except Exception:
        return frozenset()


def is_trading_day(d: dt.date, product: str = "Equities") -> bool:
    if d.weekday() >= 5:  # 5=Sat, 6=Sun
        return False
    return d not in holidays(product)


def trading_days(start: dt.date, end: dt.date, product: str = "Equities"):
    """Yield trading days in [start, end] inclusive, ascending."""
    step = dt.timedelta(days=1)
    cur = start
    while cur <= end:
        if is_trading_day(cur, product):
            yield cur
        cur += step


def last_trading_day(on: dt.date | None = None, product: str = "Equities") -> dt.date:
    """Most recent trading day on/before ``on`` (defaults to today)."""
    d = on or dt.date.today()
    while not is_trading_day(d, product):
        d -= dt.timedelta(days=1)
    return d
