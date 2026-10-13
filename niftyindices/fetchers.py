"""niftyindices.com fetchers. Verified endpoint: the daily index-close snapshot.

Confirmed live (2026-10-02): the archive serves this same URL pattern back to
at least 2020, plain GET, no session/cookie dance needed. Keep this the ONLY
place that knows niftyindices.com URLs/headers.
"""

from __future__ import annotations

import datetime as dt
import io

import pandas as pd
import requests

_SNAPSHOT = "https://www.niftyindices.com/Daily_Snapshot/ind_close_all_{ddmmyyyy}.csv"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
}


class NiftyIndicesNoData(Exception):
    """No niftyindices snapshot for the requested date (holiday / not published)."""


def daily_snapshot(trade_date: dt.date) -> pd.DataFrame:
    """Every NSE index's OHLC + turnover + P/E, P/B, Div Yield for one date."""
    url = _SNAPSHOT.format(ddmmyyyy=trade_date.strftime("%d%m%Y"))
    r = requests.get(url, headers=_HEADERS, timeout=30)
    body = r.text
    if r.status_code != 200 or body.lstrip()[:1] == "<":  # HTML = error/SPA page
        raise NiftyIndicesNoData(f"niftyindices snapshot not available for {trade_date}")
    df = pd.read_csv(io.StringIO(body))
    if df.empty:
        raise NiftyIndicesNoData(f"niftyindices snapshot empty for {trade_date}")
    return df.reset_index(drop=True)
