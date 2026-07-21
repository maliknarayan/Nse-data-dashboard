"""BSE fetchers. Verified endpoint: EOD UDiFF bhav copy (plain CSV).

Other BSE APIs (indices/gainers) are heavily gated and were unreliable when
built — add them here as they're confirmed. Keep this the ONLY place that knows
BSE URLs/headers.
"""

from __future__ import annotations

import datetime as dt
import io

import pandas as pd
import requests

_BASE = "https://www.bseindia.com"
# UDiFF EOD bhav copy — whole BSE cash market for a date
_BHAV = ("https://www.bseindia.com/download/BhavCopy/Equity/"
         "BhavCopy_BSE_CM_0_0_0_{ymd}_F_0000.CSV")
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Referer": "https://www.bseindia.com/",
    "Accept": "text/csv,application/octet-stream,*/*",
}


class BseNoData(Exception):
    """No BSE data for the requested date (holiday / not published / blocked)."""


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(_HEADERS)
    try:  # warm a cookie so the download host serves the file
        s.get(_BASE, timeout=10)
    except requests.RequestException:
        pass
    return s


def bhav_copy(trade_date: dt.date) -> pd.DataFrame:
    """BSE EOD bhav copy for a date, equities only. Raises BseNoData if absent."""
    url = _BHAV.format(ymd=trade_date.strftime("%Y%m%d"))
    r = _session().get(url, timeout=30)
    body = r.text
    if r.status_code != 200 or body.lstrip()[:1] == "<":  # HTML = error/SPA page
        raise BseNoData(f"BSE bhav copy not available for {trade_date}")
    df = pd.read_csv(io.StringIO(body))
    if "FinInstrmTp" in df.columns:
        df = df[df["FinInstrmTp"] == "STK"]
    if df.empty:
        raise BseNoData(f"BSE bhav copy empty for {trade_date}")
    return df.reset_index(drop=True)
