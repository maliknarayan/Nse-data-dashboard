"""Valuation screen — P/E plus a PEG proxy built from the warehouse.

NSE publishes P/E per symbol but no earnings, so EPS is implied: close ÷ P/E,
i.e. trailing-twelve-month EPS as the exchange computed it that day. Comparing
that implied EPS across two dates far enough apart gives an earnings growth
rate, annualised, and PEG = P/E ÷ growth%. It is a proxy, not reported growth —
the window is whatever history exists, and only turns into a true year-on-year
number once the warehouse holds 12 months of both datasets.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from . import loader as L

# above this the 'then' EPS was a near-zero base, not real growth
MAX_GROWTH = 300.0
MIN_WINDOW_DAYS = 150


def _eps(date: str) -> pd.DataFrame:
    """Implied TTM EPS for one date: close ÷ P/E, EQ series only."""
    bhav = L.load_per_date("bhavcopy_delivery", date)
    pe = L.load_per_date("pe_ratio", date)
    if bhav.empty or pe.empty or "SYMBOL" not in bhav.columns:
        return pd.DataFrame()
    b = bhav.copy()
    if "SERIES" in b.columns:
        b = b[b["SERIES"].astype(str).str.strip() == "EQ"]
    b["Symbol"] = b["SYMBOL"].astype(str).str.strip().str.upper()
    b["Close"] = L.to_num(b["CLOSE_PRICE"])
    pecol = next((c for c in pe.columns if "P/E" in c.upper()), None)
    if not pecol:
        return pd.DataFrame()
    scol = "SYMBOL" if "SYMBOL" in pe.columns else pe.columns[0]
    p = pe[[scol, pecol]].copy()
    p.columns = ["Symbol", "P/E"]
    p["Symbol"] = p["Symbol"].astype(str).str.strip().str.upper()
    p["P/E"] = L.to_num(p["P/E"])
    out = b[["Symbol", "Close"]].drop_duplicates("Symbol").merge(
        p.drop_duplicates("Symbol"), on="Symbol", how="inner")
    out["EPS"] = out["Close"] / out["P/E"]
    return out[["Symbol", "Close", "P/E", "EPS"]]


def _base_date(latest: str) -> str | None:
    """Oldest date held by both datasets, as long as it clears the window."""
    shared = sorted(set(L.per_date_dates("pe_ratio")) & set(L.per_date_dates("bhavcopy_delivery")))
    if not shared:
        return None
    end = dt.date.fromisoformat(latest)
    for d in shared:
        if (end - dt.date.fromisoformat(d)).days >= MIN_WINDOW_DAYS:
            return d
    return None


def peg_table() -> tuple[pd.DataFrame, dict]:
    """One row per EQ stock: valuation now, implied earnings growth, PEG proxy.

    Returns (frame, meta) — meta carries the dates the growth window spans.
    PEG is blank — never faked — when EPS is negative at either end, growth is
    not positive, or growth is too large to trust off a tiny base.
    """
    mm = L.market_map()
    if mm.empty:
        return pd.DataFrame(), {}
    dates = L.per_date_dates("bhavcopy_delivery")
    latest = dates[-1]
    base = _base_date(latest)
    now, then = _eps(latest), (_eps(base) if base else pd.DataFrame())
    if now.empty:
        return pd.DataFrame(), {}

    df = mm.merge(now[["Symbol", "EPS"]].rename(columns={"EPS": "EPS now"}),
                  on="Symbol", how="left")
    if then.empty:
        df["EPS then"] = float("nan")
        days = 0
    else:
        df = df.merge(then[["Symbol", "EPS"]].rename(columns={"EPS": "EPS then"}),
                      on="Symbol", how="left")
        days = (dt.date.fromisoformat(latest) - dt.date.fromisoformat(base)).days

    ok = df["EPS now"].gt(0) & df["EPS then"].gt(0) & (days >= MIN_WINDOW_DAYS)
    df["Growth %"] = float("nan")
    df.loc[ok, "Growth %"] = ((df.loc[ok, "EPS now"] / df.loc[ok, "EPS then"])
                              ** (365 / days) - 1) * 100
    usable = df["Growth %"].between(0, MAX_GROWTH, inclusive="neither")
    df["PEG"] = float("nan")
    df.loc[usable, "PEG"] = df.loc[usable, "P/E"] / df.loc[usable, "Growth %"]

    df["Sector P/E"] = df.groupby("Industry")["P/E"].transform("median")
    df["vs Sector %"] = (df["P/E"] - df["Sector P/E"]) / df["Sector P/E"] * 100
    keep = ["Symbol", "Name", "Industry", "Close", "P/E", "Sector P/E", "vs Sector %",
            "EPS then", "EPS now", "Growth %", "PEG", "Turnover Cr", "Delivery %",
            "% From High"]
    meta = {"base_date": base or "", "latest_date": latest, "window_days": days}
    return df[[c for c in keep if c in df.columns]].copy(), meta
