"""Darvas boxes and Fibonacci retracement over a symbol's daily OHLC.

Pure functions on a `loader.symbol_history()` frame — no Streamlit, no I/O.

`symbol_history()` returns every trading series for a symbol (EQ, BE, T0, SM) and can
carry two rows for one calendar day, so run `one_bar_per_day()` before anything else.
A symbol migrating EQ<->BE mid-window is still one continuous price series — filtering
to a single series is what breaks it, not the mix.

Then `back_adjust()`, for the genuine splits and bonuses: 9 symbols in the collected
window carry one, and an unadjusted series gives a phantom swing low and a false break.
"""

from __future__ import annotations

import pandas as pd

OHLC = ["OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE"]
FIB_RATIOS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]


def one_bar_per_day(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse to one row per date, preferring the EQ series on a day that has two.

    146 symbol-date pairs in the window carry two series rows; left in, they become two
    candles for one day and break every lookback that counts bars.
    """
    if df.empty or "date" not in df.columns:
        return df
    d = df
    if "SERIES" in d.columns:
        d = d.assign(_eq=(d["SERIES"].astype(str).str.strip() != "EQ").astype(int))
        d = d.sort_values(["date", "_eq"]).drop_duplicates("date", keep="first").drop(columns="_eq")
    else:
        d = d.sort_values("date").drop_duplicates("date", keep="last")
    return d.sort_values("date").reset_index(drop=True)


def back_adjust(df: pd.DataFrame, threshold: float = 0.2) -> tuple[pd.DataFrame, list[dict]]:
    """Scale pre-event bars so split/bonus jumps vanish. Returns (frame, events).

    The exchange restates PREV_CLOSE on an ex-date, so a gap between the prior bar's
    close and this bar's PREV_CLOSE is the adjustment factor.
    """
    d = df.copy()
    if d.empty or "PREV_CLOSE" not in d.columns:
        return d, []
    prev_bar = d["CLOSE_PRICE"].shift(1)
    ratio = (prev_bar / d["PREV_CLOSE"]).replace([float("inf"), -float("inf")], pd.NA)
    # 0.2 is calibrated: it isolates the 9 genuine split/bonus ratios in this dataset and
    # admits none of the market-wide PREV_CLOSE noise on 2026-02-02 and 2026-09-01
    hit = ratio.notna() & ((ratio > 1 + threshold) | (ratio < 1 / (1 + threshold)))
    events = [{"date": d["date"].iat[i], "ratio": float(ratio.iat[i])}
              for i in range(len(d)) if hit.iat[i]]
    if not events:
        return d, []
    inv = pd.Series(1.0, index=range(len(d)))
    inv[hit.to_numpy()] = 1.0 / ratio[hit].to_numpy()
    # bar k scales by the product of every event strictly after it
    tail = inv[::-1].cumprod()[::-1]
    adj = tail.shift(-1).fillna(1.0).to_numpy()
    for c in OHLC + ["PREV_CLOSE"]:
        if c in d.columns:
            d[c] = d[c].to_numpy() * adj
    return d, events


def darvas_boxes(df: pd.DataFrame, confirm: int = 3, lookback: int = 52) -> list[dict]:
    """Darvas boxes over the frame. One dict per box.

    A box opens when a bar sets a new `lookback`-bar high. That high becomes the ceiling
    once `confirm` bars fail to exceed it; a higher bar inside the window resets the count.
    The floor is the lowest low after the ceiling, confirmed the same way. The box ends on
    the first close outside either edge.
    """
    if df.empty or not {"HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE"} <= set(df.columns):
        return []
    d = df.dropna(subset=["HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE"]).reset_index(drop=True)
    hi, lo, cl = (d[c].to_numpy() for c in ["HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE"])
    dates, n = d["date"].tolist(), len(d)
    boxes: list[dict] = []
    i = lookback
    while i < n:
        if hi[i] < hi[max(0, i - lookback):i].max():
            i += 1
            continue
        top, t = hi[i], i
        j = i + 1
        while j < n and j <= t + confirm:          # a higher bar restarts the count
            if hi[j] > top:
                top, t = hi[j], j
            j += 1
        if j >= n:
            break
        bottom, b = lo[t + 1], t + 1
        k = b + 1
        broke_up = False
        while k < n and k <= b + confirm:
            if hi[k] > top:                        # ceiling gone before a floor was set
                broke_up = True
                break
            if lo[k] < bottom:
                bottom, b = lo[k], k
            k += 1
        if broke_up:
            i = k
            continue
        if k >= n:
            break
        exit_i, kind = None, "open"
        for e in range(k, n):
            if cl[e] > top:
                exit_i, kind = e, "breakout"
                break
            if cl[e] < bottom:
                exit_i, kind = e, "breakdown"
                break
        boxes.append({"start": dates[t], "end": dates[exit_i if exit_i is not None else n - 1],
                      "top": float(top), "bottom": float(bottom), "exit": kind})
        i = (exit_i + 1) if exit_i is not None else n
    return boxes


def fib_levels(df: pd.DataFrame, lookback: int | None = None) -> dict:
    """Retracement levels off the swing in the window. {} when there is no range."""
    if df.empty or not {"HIGH_PRICE", "LOW_PRICE"} <= set(df.columns):
        return {}
    d = df.dropna(subset=["HIGH_PRICE", "LOW_PRICE"])
    if lookback:
        d = d.tail(lookback)
    if d.empty:
        return {}
    hi_i, lo_i = d["HIGH_PRICE"].idxmax(), d["LOW_PRICE"].idxmin()
    hi, lo = float(d["HIGH_PRICE"].loc[hi_i]), float(d["LOW_PRICE"].loc[lo_i])
    rng = hi - lo
    if rng <= 0:
        return {}
    up = d.index.get_loc(lo_i) < d.index.get_loc(hi_i)   # low first = leg up, retrace down

    def _at(r: float) -> float:
        # pin the ends to the real extremes; hi - rng*1.0 drifts off lo by ~1e-14
        if r == 0.0:
            return hi if up else lo
        if r == 1.0:
            return lo if up else hi
        return hi - rng * r if up else lo + rng * r

    levels = {r: _at(r) for r in FIB_RATIOS}
    return {"up": bool(up), "high": hi, "low": lo,
            "high_date": d["date"].loc[hi_i], "low_date": d["date"].loc[lo_i],
            "levels": levels}
