"""Datewise index EOD history via nselib index_data (real NSE archive).

Stored one growing CSV per index: data/index_history/index_history_<INDEX>.csv,
deduped by TIMESTAMP and sorted. Separate from the live all_indices snapshot.
"""

from __future__ import annotations

import datetime as dt
import os

import pandas as pd

from . import calendar_util as cal
from .config import Settings
from .resolver import resolve


def safe_name(index: str) -> str:
    return index.strip().upper().replace(" ", "_").replace("/", "-").replace("&", "and")


def path(index: str, settings: Settings) -> str:
    return os.path.join(settings.data_dir, "index_history",
                        f"index_history_{safe_name(index)}.csv")


def fetch_and_store(index: str, frm: dt.date, to: dt.date,
                    settings: Settings | None = None) -> int:
    """Fetch index_data for a window, merge into the per-index CSV. Returns total rows."""
    s = settings or Settings()
    fn = resolve("capital_market.index_data")
    df = fn(index=index, from_date=cal.to_nse(frm), to_date=cal.to_nse(to))
    if not isinstance(df, pd.DataFrame) or df.empty:
        return 0
    p = path(index, s)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if os.path.exists(p):
        try:
            df = pd.concat([pd.read_csv(p), df], ignore_index=True)
        except Exception:
            pass
    key = "TIMESTAMP" if "TIMESTAMP" in df.columns else df.columns[-1]
    df = df.drop_duplicates(subset=[key], keep="last")
    order = pd.to_datetime(df[key], errors="coerce", dayfirst=True)
    df = df.assign(_o=order).sort_values("_o").drop(columns="_o")
    tmp = p + ".tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, p)
    return len(df)
