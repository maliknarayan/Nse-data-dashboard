"""Derive 'live-only' snapshots datewise from a stored bhav copy.

NSE/BSE don't archive gainers / most-active / breadth per date, but they're all
recomputable from the daily bhav copy — so we get real datewise history for
every date collected, retroactively. Pure functions over a bhav-copy DataFrame.
"""

from __future__ import annotations

import pandas as pd

from .loader import to_num


def _eq(bhav: pd.DataFrame) -> pd.DataFrame:
    b = bhav.copy()
    if "SERIES" in b.columns:
        b = b[b["SERIES"] == "EQ"]
    for c in ["CLOSE_PRICE", "PREV_CLOSE", "TTL_TRD_QNTY", "TURNOVER_LACS", "DELIV_PER"]:
        if c in b.columns:
            b[c] = to_num(b[c])
    b["%Chg"] = (b["CLOSE_PRICE"] - b["PREV_CLOSE"]) / b["PREV_CLOSE"] * 100
    return b


def breadth(bhav: pd.DataFrame) -> dict:
    b = _eq(bhav).dropna(subset=["%Chg"])
    return {"Advances": int((b["%Chg"] > 0).sum()),
            "Declines": int((b["%Chg"] < 0).sum()),
            "Unchanged": int((b["%Chg"] == 0).sum())}


def _cols(b: pd.DataFrame) -> list[str]:
    return [c for c in ["SYMBOL", "CLOSE_PRICE", "%Chg", "TTL_TRD_QNTY",
                        "TURNOVER_LACS", "DELIV_PER"] if c in b.columns]


def gainers(bhav: pd.DataFrame, n: int = 50, min_turnover_lacs: float = 100) -> pd.DataFrame:
    b = _eq(bhav)
    b = b[b.get("TURNOVER_LACS", 0) >= min_turnover_lacs] if "TURNOVER_LACS" in b.columns else b
    return b.sort_values("%Chg", ascending=False)[_cols(b)].head(n)


def losers(bhav: pd.DataFrame, n: int = 50, min_turnover_lacs: float = 100) -> pd.DataFrame:
    b = _eq(bhav)
    b = b[b.get("TURNOVER_LACS", 0) >= min_turnover_lacs] if "TURNOVER_LACS" in b.columns else b
    return b.sort_values("%Chg", ascending=True)[_cols(b)].head(n)


def most_active(bhav: pd.DataFrame, by: str = "value", n: int = 50) -> pd.DataFrame:
    b = _eq(bhav)
    col = "TURNOVER_LACS" if by == "value" else "TTL_TRD_QNTY"
    if col not in b.columns:
        return pd.DataFrame()
    return b.sort_values(col, ascending=False)[_cols(b)].head(n)
