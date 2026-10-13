"""Offline test for the PEG proxy: implied EPS, annualised growth, PEG guards."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard import valuation as V

BASE, LATEST = "2026-01-01", "2026-10-06"  # 278 days apart
DATES = [BASE, LATEST]

# GROW doubles EPS, FLAT stands still, LOSS turns negative, SPIKE grows off a dust base
PE = {BASE: {"GROW": 20.0, "FLAT": 15.0, "LOSS": 10.0, "SPIKE": 500.0},
      LATEST: {"GROW": 20.0, "FLAT": 15.0, "LOSS": -5.0, "SPIKE": 20.0}}
CLOSE = {BASE: {"GROW": 200.0, "FLAT": 150.0, "LOSS": 100.0, "SPIKE": 100.0},
         LATEST: {"GROW": 400.0, "FLAT": 150.0, "LOSS": 50.0, "SPIKE": 100.0}}
SYMS = list(PE[BASE])


@pytest.fixture
def warehouse(monkeypatch):
    def per_date_dates(name):
        return DATES

    def load_per_date(name, date=None):
        d = date or LATEST
        if name == "bhavcopy_delivery":
            return pd.DataFrame({"SYMBOL": SYMS, "SERIES": ["EQ"] * len(SYMS),
                                 "CLOSE_PRICE": [CLOSE[d][s] for s in SYMS]})
        if name == "pe_ratio":
            return pd.DataFrame({"SYMBOL": SYMS,
                                 "SYMBOLP/E": [PE[d][s] for s in SYMS]})
        return pd.DataFrame()

    def market_map(date=None):
        return pd.DataFrame({"Symbol": SYMS, "Name": SYMS,
                             "Industry": ["Test"] * len(SYMS),
                             "Close": [CLOSE[LATEST][s] for s in SYMS],
                             "P/E": [PE[LATEST][s] for s in SYMS],
                             "Turnover Cr": [10.0] * len(SYMS)})

    monkeypatch.setattr(V.L, "per_date_dates", per_date_dates)
    monkeypatch.setattr(V.L, "load_per_date", load_per_date)
    monkeypatch.setattr(V.L, "market_map", market_map)


def test_peg_proxy(warehouse):
    df, meta = V.peg_table()
    row = df.set_index("Symbol")
    assert meta["base_date"] == BASE and meta["window_days"] == 278

    # EPS = close / P/E, doubled over 278 days -> 2**(365/278) annualised, PEG = P/E / growth
    assert row.loc["GROW", "EPS now"] == pytest.approx(20.0)
    assert row.loc["GROW", "Growth %"] == pytest.approx((2 ** (365 / 278) - 1) * 100, abs=0.1)
    assert row.loc["GROW", "PEG"] == pytest.approx(20 / row.loc["GROW", "Growth %"])

    # no growth, negative earnings, and a dust-base spike all refuse to produce a PEG
    assert pd.isna(row.loc["FLAT", "PEG"])
    assert pd.isna(row.loc["LOSS", "PEG"])
    assert pd.isna(row.loc["SPIKE", "PEG"])
    assert row.loc["SPIKE", "Growth %"] > V.MAX_GROWTH
