"""Offline tests for the decision-support signals. No network, no Streamlit."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard import signals as S


def _bhav(sym, deliv, close, prev, series="EQ", to=1000):
    return pd.DataFrame([{"SYMBOL": sym, "SERIES": series, "DELIV_PER": deliv,
                          "CLOSE_PRICE": close, "PREV_CLOSE": prev, "TURNOVER_LACS": to,
                          "TTL_TRD_QNTY": 1}])


# --- market regime ---
def test_regime_risk_on():
    idx = pd.DataFrame({"index": ["NIFTY 50", "INDIA VIX"],
                        "percentChange": [1.2, 0.0], "last": [24000, 11]})
    ad = pd.DataFrame({"metric": ["Advances", "Declines"], "value": [2000, 800]})
    r = S.market_regime(idx, ad)
    assert r["label"] == "Risk-On"
    assert r["score"] >= 2


def test_regime_risk_off():
    idx = pd.DataFrame({"index": ["NIFTY 50", "INDIA VIX"],
                        "percentChange": [-1.5, 0.0], "last": [24000, 24]})
    ad = pd.DataFrame({"metric": ["Advances", "Declines"], "value": [500, 2200]})
    r = S.market_regime(idx, ad)
    assert r["label"] == "Risk-Off"
    assert r["reasons"]


# --- stock scorecard ---
def _empty():
    return pd.DataFrame()


def test_scorecard_accumulation():
    sc = S.stock_scorecard("ABC", bhav=_bhav("ABC", 70, 110, 100),
                           bulk=_empty(), block=_empty(), ban=_empty(),
                           vol=_empty(), pe=_empty(), most_active=_empty())
    assert sc["score"] >= 3
    assert "Accumulation" in sc["verdict"]


def test_scorecard_distribution():
    sc = S.stock_scorecard("XYZ", bhav=_bhav("XYZ", 65, 90, 100),
                           bulk=_empty(), block=_empty(), ban=_empty(),
                           vol=_empty(), pe=_empty(), most_active=_empty())
    assert sc["score"] < 0
    names = [f["factor"] for f in sc["factors"]]
    assert "Distribution risk" in names


def test_scorecard_ban_penalizes():
    ban = pd.DataFrame({"value": ["BANNED"]})
    sc = S.stock_scorecard("BANNED", bhav=_bhav("BANNED", 55, 105, 100),
                           bulk=_empty(), block=_empty(), ban=ban,
                           vol=_empty(), pe=_empty(), most_active=_empty())
    names = [f["factor"] for f in sc["factors"]]
    assert "F&O ban" in names
    assert any(f["points"] == -2 for f in sc["factors"])


def test_scorecard_bulk_buy_positive():
    bulk = pd.DataFrame({"Symbol": ["ABC", "ABC"], "Buy/Sell": ["BUY", "BUY"],
                         "QuantityTraded": [1, 1], "TradePrice/Wght.Avg.Price": [1, 1]})
    sc = S.stock_scorecard("ABC", bhav=_bhav("ABC", 30, 100, 100),
                           bulk=bulk, block=_empty(), ban=_empty(),
                           vol=_empty(), pe=_empty(), most_active=_empty())
    assert any("Bulk deals" in f["factor"] and f["points"] > 0 for f in sc["factors"])


# --- screeners ---
def test_screen_accumulation_vs_distribution():
    bhav = pd.concat([_bhav("UP", 60, 110, 100), _bhav("DOWN", 60, 90, 100)],
                     ignore_index=True)
    acc = S.screen_accumulation(bhav, min_turnover_lacs=0, min_deliv=50)
    dis = S.screen_distribution(bhav, min_turnover_lacs=0, min_deliv=50)
    assert "UP" in acc["SYMBOL"].values and "DOWN" not in acc["SYMBOL"].values
    assert "DOWN" in dis["SYMBOL"].values and "UP" not in dis["SYMBOL"].values


def test_institutional_buys_only_buys_sorted():
    bulk = pd.DataFrame({"Symbol": ["A", "B"], "Buy/Sell": ["BUY", "SELL"],
                         "QuantityTraded": [100, 100], "TradePrice/Wght.Avg.Price": [10, 10]})
    ib = S.screen_institutional_buys(bulk)
    assert list(ib["Symbol"]) == ["A"]
