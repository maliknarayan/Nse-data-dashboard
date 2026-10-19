"""Chart primitives + the page charts that read real collected data.

Data-dependent cases skip when the dataset isn't collected — they never pass vacuously.

Run:  python -m pytest tests/test_charts.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard import charts as C  # noqa: E402
from dashboard import loader as L  # noqa: E402

DARK = True


def _pts(fig) -> int:
    """Longest data vector across traces — 0 means nothing was plotted."""
    n = 0
    for tr in fig.data:
        for attr in ("x", "values", "labels", "ids"):
            v = getattr(tr, attr, None)
            if v is not None:
                n = max(n, len(v))
    return n


def test_scatter_plots_points():
    d = pd.DataFrame({"a": [1, 2, 3], "b": [1, -2, 3], "n": list("xyz")})
    assert _pts(C.scatter(d, "a", "b", "n", DARK, vline=0, hline=0)) == 3


def test_scatter_empty_frame_is_blank_not_a_crash():
    d = pd.DataFrame({"a": [None], "b": [None], "n": ["x"]})
    assert _pts(C.scatter(d, "a", "b", "n", DARK)) == 0


def test_scatter_drops_rows_missing_the_colour_column():
    d = pd.DataFrame({"a": [1, 2], "b": [1, 2], "c": [1.0, None], "n": ["x", "y"]})
    assert _pts(C.scatter(d, "a", "b", "n", DARK, color="c")) == 1


def test_stacked_keeps_one_trace_per_column():
    m = pd.DataFrame({"ok": [3, 1], "err": [0, 2]}, index=["d1", "d2"])
    fig = C.stacked(m, DARK)
    assert len(fig.data) == 2 and fig.layout.barmode == "stack"


def test_stacked_horizontal_reverses_the_category_axis():
    m = pd.DataFrame({"ok": [3, 1]}, index=["d1", "d2"])
    assert C.stacked(m, DARK, horizontal=True).layout.yaxis.autorange == "reversed"


def test_cycle_is_distinct_then_wraps():
    assert len(set(C.cycle(10))) == 10
    assert C.cycle(11)[10] == C.cycle(1)[0]


def _require(df, what):
    if df is None or (hasattr(df, "empty") and df.empty):
        pytest.skip(f"{what} not collected")
    return df


def test_delivery_scatter_renders_from_bhavcopy():
    b = _require(L.load_per_date("bhavcopy_delivery"), "bhavcopy_delivery").copy()
    b = b[b["SERIES"] == "EQ"] if "SERIES" in b else b
    for c in ["CLOSE_PRICE", "PREV_CLOSE", "DELIV_PER", "TURNOVER_LACS"]:
        b[c] = L.to_num(b[c])
    b["%Chg"] = (b["CLOSE_PRICE"] - b["PREV_CLOSE"]) / b["PREV_CLOSE"] * 100
    fig = C.scatter(b, "DELIV_PER", "%Chg", "SYMBOL", DARK, color="%Chg",
                    size="TURNOVER_LACS", vline=50, hline=0)
    assert _pts(fig) > 100


def test_result_verdict_donut_and_growth_scatter():
    qs = L.result_quarters()
    if not qs:
        pytest.skip("no analyzed result quarters")
    r = L.result_index(qs[-1])
    vc = r["Verdict"].value_counts()
    assert _pts(C.donut(vc.index.tolist(), vc.values.tolist(), C.cycle(len(vc)), DARK)) == len(vc)
    g = r.dropna(subset=["Rev YoY %", "PAT YoY %"])
    if g.empty:
        pytest.skip("no company reports both revenue and PAT growth")
    assert _pts(C.scatter(g, "Rev YoY %", "PAT YoY %", "Company", DARK,
                          color="PAT YoY %", vline=0, hline=0)) == len(g)


def test_concall_call_donut():
    qs = L.concall_quarters()
    if not qs:
        pytest.skip("no analyzed concall quarters")
    mix = L.concall_index(qs[-1])["Call"].replace("", pd.NA).dropna().value_counts()
    if mix.empty:
        pytest.skip("no calls recorded")
    assert _pts(C.donut(mix.index.tolist(), mix.values.tolist(), C.cycle(len(mix)), DARK)) == len(mix)


def test_data_health_stacked_covers_every_dataset():
    man = _require(L.load_manifest(), "manifest").copy()
    s = man["status"].astype(str)
    man["_class"] = "error"
    man.loc[s.str.startswith("ok"), "_class"] = "ok"
    man.loc[s.str.startswith("empty"), "_class"] = "empty"
    mat = pd.crosstab(man["dataset"], man["_class"])
    assert _pts(C.stacked(mat, DARK, horizontal=True)) == man["dataset"].nunique()
