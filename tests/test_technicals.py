"""Darvas box + Fibonacci + split back-adjustment.

Synthetic cases pin the algorithm; the real-data cases skip when bhav copies aren't
collected rather than passing vacuously.

Run:  python -m pytest tests/test_technicals.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard import loader as L  # noqa: E402
from dashboard import technicals as TA  # noqa: E402


def _frame(rows):
    """rows = [(high, low, close)] -> an OHLC frame with sane PREV_CLOSE."""
    d = pd.DataFrame(rows, columns=["HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE"])
    d["OPEN_PRICE"] = d["CLOSE_PRICE"]
    d["PREV_CLOSE"] = d["CLOSE_PRICE"].shift(1).fillna(d["CLOSE_PRICE"].iat[0])
    d["date"] = pd.date_range("2026-01-01", periods=len(d), freq="D").date
    return d


def _flat(n, high=100.0, low=90.0, close=95.0):
    return [(high, low, close)] * n


# ---------------------------------------------------------------- back_adjust

def test_back_adjust_removes_a_two_for_one_split():
    d = _frame(_flat(6, 200, 180, 190))
    # split on bar 3: price halves from there on
    for c in ["HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE"]:
        d.loc[3:, c] = d.loc[3:, c] / 2
    # the exchange restates PREV_CLOSE onto the new scale, so only bar 3 shows a gap
    d["PREV_CLOSE"] = d["CLOSE_PRICE"].shift(1).fillna(d["CLOSE_PRICE"].iat[0])
    d.loc[3, "PREV_CLOSE"] = 95.0
    out, events = TA.back_adjust(d)
    assert len(events) == 1 and round(events[0]["ratio"], 3) == 2.0
    assert out["CLOSE_PRICE"].round(4).nunique() == 1, "series should be continuous after adjust"


def test_back_adjust_is_a_no_op_on_a_clean_series():
    d = _frame(_flat(5))
    out, events = TA.back_adjust(d)
    assert events == [] and out["CLOSE_PRICE"].equals(d["CLOSE_PRICE"])


def test_back_adjust_leaves_a_normal_gap_alone():
    d = _frame(_flat(5, 100, 90, 95))
    d.loc[3, "CLOSE_PRICE"] = 104.0   # +9.5%, a real move, under the threshold
    assert TA.back_adjust(d)[1] == []


# ---------------------------------------------------------------- one_bar_per_day

def test_one_bar_per_day_prefers_eq_over_the_other_series():
    d = _frame(_flat(2))
    d["SERIES"] = ["T0", "EQ"]
    d["date"] = [d["date"].iat[0]] * 2          # same calendar day, two series
    d.loc[1, "CLOSE_PRICE"] = 123.0
    out = TA.one_bar_per_day(d)
    assert len(out) == 1 and out["CLOSE_PRICE"].iat[0] == 123.0


def test_one_bar_per_day_keeps_a_series_migration_intact():
    d = _frame(_flat(6))
    d["SERIES"] = ["BE"] * 3 + ["EQ"] * 3       # distinct dates, EQ<->BE migration
    assert len(TA.one_bar_per_day(d)) == 6, "migration is one continuous series, not a dupe"


def test_one_bar_per_day_is_sorted_by_date():
    d = _frame(_flat(4))
    d = d.iloc[::-1]
    assert TA.one_bar_per_day(d)["date"].is_monotonic_increasing


def test_real_history_has_no_duplicate_dates_after_dedup():
    h = L.symbol_history("RELIANCE")
    if h.empty:
        pytest.skip("bhavcopy_delivery not collected")
    assert TA.one_bar_per_day(h)["date"].duplicated().sum() == 0


def test_series_migration_is_not_mistaken_for_a_split():
    """ABANSENT moved BE->EQ on 2026-08-11; the full series is continuous."""
    h = L.symbol_history("ABANSENT")
    if h.empty or len(h) < 60:
        pytest.skip("ABANSENT not collected")
    _, events = TA.back_adjust(TA.one_bar_per_day(h))
    assert events == [], f"migration flagged as a corporate action: {events}"


# ---------------------------------------------------------------- darvas_boxes

def _box_series():
    """10 flat bars, a breakout bar that sets the ceiling, then a range, then a close above."""
    rows = _flat(10, 100, 90, 95)
    rows += [(120, 100, 118)]            # bar 10 — new high, becomes the ceiling
    rows += [(115, 105, 110)] * 3        # fails to exceed -> ceiling confirmed
    rows += [(114, 102, 108)] * 4        # floor settles at 102
    rows += [(130, 120, 125)]            # close clears the ceiling -> breakout
    return _frame(rows)


def test_darvas_finds_the_box_and_its_edges():
    boxes = TA.darvas_boxes(_box_series(), confirm=3, lookback=10)
    assert len(boxes) == 1
    assert boxes[0]["top"] == 120.0 and boxes[0]["bottom"] == 102.0


def test_darvas_marks_a_close_above_the_ceiling_as_breakout():
    assert TA.darvas_boxes(_box_series(), confirm=3, lookback=10)[0]["exit"] == "breakout"


def test_darvas_marks_a_close_below_the_floor_as_breakdown():
    rows = _flat(10, 100, 90, 95) + [(120, 100, 118)] + [(115, 105, 110)] * 3
    rows += [(114, 102, 108)] * 4 + [(104, 95, 96)]     # close under the floor
    assert TA.darvas_boxes(_frame(rows), confirm=3, lookback=10)[0]["exit"] == "breakdown"


def test_darvas_box_still_open_when_price_never_escapes():
    rows = _flat(10, 100, 90, 95) + [(120, 100, 118)] + [(115, 105, 110)] * 3
    rows += [(114, 102, 108)] * 6
    assert TA.darvas_boxes(_frame(rows), confirm=3, lookback=10)[0]["exit"] == "open"


def test_a_higher_bar_inside_the_window_raises_the_ceiling():
    rows = _flat(10, 100, 90, 95)
    rows += [(120, 100, 118), (125, 110, 123)]    # bar 11 tops bar 10 -> ceiling moves up
    rows += [(118, 108, 112)] * 4 + [(117, 106, 110)] * 4
    boxes = TA.darvas_boxes(_frame(rows), confirm=3, lookback=10)
    assert boxes and boxes[0]["top"] == 125.0


def test_darvas_needs_more_bars_than_the_lookback():
    assert TA.darvas_boxes(_frame(_flat(20)), confirm=3, lookback=52) == []


def test_darvas_empty_frame_is_empty_list():
    assert TA.darvas_boxes(pd.DataFrame(), confirm=3) == []


# ---------------------------------------------------------------- fib_levels

def test_fib_on_a_leg_up_retraces_down_from_the_high():
    rows = [(100, 100, 100), (150, 100, 150), (200, 150, 200)]   # low first, then high
    f = TA.fib_levels(_frame(rows))
    assert f["up"] is True and f["low"] == 100.0 and f["high"] == 200.0
    assert f["levels"][0.0] == 200.0 and f["levels"][1.0] == 100.0
    assert f["levels"][0.5] == 150.0


def test_fib_on_a_leg_down_retraces_up_from_the_low():
    rows = [(200, 200, 200), (150, 120, 130), (120, 100, 100)]   # high first
    f = TA.fib_levels(_frame(rows))
    assert f["up"] is False and f["levels"][0.0] == 100.0 and f["levels"][1.0] == 200.0


def test_fib_levels_sit_inside_the_swing():
    f = TA.fib_levels(_frame([(100, 100, 100), (200, 150, 200)]))
    assert all(f["low"] <= p <= f["high"] for p in f["levels"].values())


def test_fib_endpoints_are_exactly_the_swing_extremes():
    """hi - rng*1.0 drifts ~1e-14 below the low on real prices; the ends must be exact."""
    f = TA.fib_levels(_frame([(25.35, 25.35, 25.35), (211.0, 100.0, 211.0)]))
    assert f["levels"][0.0] == f["high"] == 211.0
    assert f["levels"][1.0] == f["low"] == 25.35


def test_fib_levels_never_escape_the_swing_on_real_prices():
    h = L.symbol_history("HFCL")
    if h.empty or len(h) < 60:
        pytest.skip("HFCL not collected")
    f = TA.fib_levels(TA.one_bar_per_day(h), lookback=120)
    assert all(f["low"] <= p <= f["high"] for p in f["levels"].values())


def test_fib_returns_nothing_when_the_range_is_flat():
    assert TA.fib_levels(_frame(_flat(5, 100, 100, 100))) == {}


def test_fib_lookback_only_sees_the_tail():
    rows = [(500, 400, 450)] + _flat(5, 100, 90, 95)   # old spike outside the window
    assert TA.fib_levels(_frame(rows), lookback=5)["high"] == 100.0


# ---------------------------------------------------------------- real data

def _history(sym="RELIANCE"):
    h = L.symbol_history(sym)
    if h.empty:
        pytest.skip("bhavcopy_delivery not collected")
    return h


def test_real_symbol_has_enough_bars_and_clean_ohlc():
    h = _history()
    assert len(h) >= 60
    assert h[TA.OHLC].notna().all().all()


def test_darvas_and_fib_run_on_real_data_without_inverted_edges():
    h, _ = TA.back_adjust(_history())
    for b in TA.darvas_boxes(h):
        assert b["top"] > b["bottom"], f"inverted box {b}"
        assert b["exit"] in {"breakout", "breakdown", "open"}
    f = TA.fib_levels(h, lookback=120)
    assert f and f["high"] > f["low"]
