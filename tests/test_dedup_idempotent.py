"""Offline tests: dedup + idempotent per-date skip. Fetch is mocked; no network.

Run:  python -m pytest tests/ -q
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import pytest

# make the package importable when run from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nse_collector.config import COLLECTED_ON, Settings
from nse_collector.collector import Collector
from nse_collector.storage import NseWarehouse, normalize


@pytest.fixture
def settings(tmp_path) -> Settings:
    s = Settings()
    s.data_dir = str(tmp_path / "data")
    s.log_dir = str(tmp_path / "logs")
    s.polite_delay = 0.0
    s.retries = 1
    return s


# --- normalize ---
def test_normalize_variants():
    assert normalize(None).empty
    assert list(normalize([{"a": 1}, {"a": 2}]).columns) == ["a"]
    assert normalize(["X", "Y"])["value"].tolist() == ["X", "Y"]
    # tuple of (summary dict, df) -> keeps the df
    df = pd.DataFrame({"symbol": ["A"], "v": [1]})
    assert normalize(({"Advances": 5}, df))["symbol"].tolist() == ["A"]


# --- snapshot dedup ---
def test_snapshot_same_day_dedups(settings, monkeypatch):
    c = Collector(settings)
    ds = {"name": "top_gainers", "kind": "snapshot",
          "fn": "capital_market.top_gainers_or_losers",
          "params": {"to_get": "gainers"}, "key": ["symbol"]}
    frame = pd.DataFrame({"symbol": ["A", "B"], "ltp": [10, 20]})
    monkeypatch.setattr(c, "_fetch", lambda d, **k: frame.copy())

    day = dt.date(2026, 7, 20)
    c.collect_snapshot(ds, day)
    c.collect_snapshot(ds, day)  # rerun same day -> must not duplicate

    out = pd.read_csv(c.wh._growing_path("top_gainers"))
    assert len(out) == 2
    assert set(out["symbol"]) == {"A", "B"}
    assert out[COLLECTED_ON].unique().tolist() == ["2026-07-20"]


def test_snapshot_different_days_accumulate(settings, monkeypatch):
    c = Collector(settings)
    ds = {"name": "top_gainers", "kind": "snapshot",
          "fn": "capital_market.top_gainers_or_losers",
          "params": {}, "key": ["symbol"]}
    monkeypatch.setattr(c, "_fetch",
                        lambda d, **k: pd.DataFrame({"symbol": ["A"], "ltp": [10]}))
    c.collect_snapshot(ds, dt.date(2026, 7, 20))
    c.collect_snapshot(ds, dt.date(2026, 7, 21))

    out = pd.read_csv(c.wh._growing_path("top_gainers"))
    assert len(out) == 2  # same symbol, two different days
    assert sorted(out[COLLECTED_ON].unique()) == ["2026-07-20", "2026-07-21"]


# --- date_range dedup (whole-row) ---
def test_date_range_dedups_full_row(settings, monkeypatch):
    c = Collector(settings)
    ds = {"name": "bulk_deals", "kind": "date_range",
          "fn": "capital_market.bulk_deal_data", "params": {}, "key": None}
    frame = pd.DataFrame({"symbol": ["A", "B"], "qty": [100, 200]})
    monkeypatch.setattr(c, "_fetch", lambda d, **k: frame.copy())

    d = dt.date(2026, 7, 20)
    c.collect_date_range(ds, d, d)
    c.collect_date_range(ds, d, d)  # overlapping window -> identical rows dropped

    out = pd.read_csv(c.wh._growing_path("bulk_deals"))
    assert len(out) == 2


# --- per_date idempotent skip ---
def test_per_date_skips_existing(settings, monkeypatch):
    c = Collector(settings)
    ds = {"name": "bhavcopy_delivery", "kind": "per_date",
          "fn": "capital_market.bhav_copy_with_delivery", "params": {}, "key": None}

    calls = {"n": 0}

    def fake_fetch(d, **k):
        calls["n"] += 1
        return pd.DataFrame({"symbol": ["A"], "close": [1]})

    monkeypatch.setattr(c, "_fetch", fake_fetch)
    day = dt.date(2026, 7, 20)

    c.collect_per_date(ds, day)
    assert calls["n"] == 1
    assert c.wh.per_date_exists("bhavcopy_delivery", day)

    c.collect_per_date(ds, day)  # file exists -> must not fetch again
    assert calls["n"] == 1


def test_per_date_empty_is_holiday_skip(settings, monkeypatch):
    c = Collector(settings)
    ds = {"name": "pe_ratio", "kind": "per_date",
          "fn": "capital_market.pe_ratio", "params": {}, "key": None}
    monkeypatch.setattr(c, "_fetch", lambda d, **k: pd.DataFrame())
    day = dt.date(2026, 7, 20)
    c.collect_per_date(ds, day)
    assert not c.wh.per_date_exists("pe_ratio", day)  # no file written on holiday


def test_per_date_error_treated_as_holiday(settings, monkeypatch):
    c = Collector(settings)
    ds = {"name": "pe_ratio", "kind": "per_date",
          "fn": "capital_market.pe_ratio", "params": {}, "key": None}

    def boom(d, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(c, "_fetch", boom)
    day = dt.date(2026, 7, 20)
    c.collect_per_date(ds, day)  # must not raise
    assert not c.wh.per_date_exists("pe_ratio", day)
    assert f"pe_ratio:{day.isoformat()}" in c.summary.skipped
