"""Shared UI helpers + cached data-loader wrappers for every dashboard page.

Deliberately NOT the Streamlit entrypoint (app.py is). Page modules under
dashboard/pages_content/ import from here, never from dashboard.app — Streamlit
runs app.py as __main__, and importing it by module path from a submodule
would re-execute the whole script (including st.set_page_config, which
Streamlit refuses to call twice) and crash the app.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from dashboard import loader as L

# cache the warehouse reads; sidebar button clears it after a fresh collection
_cache = st.cache_data(ttl=300)
load_growing = _cache(L.load_growing)
load_snapshot_latest = _cache(L.load_snapshot_latest)
load_per_date = _cache(L.load_per_date)
per_date_dates = _cache(L.per_date_dates)
load_per_date_all = _cache(L.load_per_date_all)
load_manifest = _cache(L.load_manifest)
all_symbols = _cache(L.all_symbols)
company_map = _cache(L.company_map)
symbol_history = _cache(L.symbol_history)
bse_symbols = _cache(L.bse_symbols)
bse_symbol_history = _cache(L.bse_symbol_history)
index_history = _cache(L.index_history)
index_names = _cache(L.index_names)
concall_quarters = _cache(L.concall_quarters)
concall_index = _cache(L.concall_index)
concall_text = _cache(L.concall_text)
match_symbol = _cache(L.match_symbol)

SYMBOLS = all_symbols()
NAMES = company_map()


def symbol_select(label: str, key: str, help: str | None = None) -> str:
    """Searchable symbol picker (type-ahead). Falls back to free text if the
    master isn't collected yet."""
    if SYMBOLS:
        choice = st.selectbox(label, [""] + SYMBOLS, key=key, help=help,
                              format_func=lambda s: f"{s} — {NAMES[s]}" if s in NAMES else s)
        return choice.strip().upper()
    return st.text_input(label, key=key, help=help).strip().upper()


def _hint(msg: str = "No data yet — run the collector to populate this."):
    st.info(msg)


def _num(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    df = df.copy()
    for c in cols:
        if c in df.columns:
            df[c] = L.to_num(df[c])
    return df


def card():
    """A styled card container."""
    return st.container(border=True)


def _collector(polite: float = 1.0):
    from nse_collector.collector import Collector, setup_logging
    from nse_collector.config import Settings
    s = Settings()
    s.data_dir = L.DATA_DIR
    s.log_dir = os.path.join(os.path.dirname(L.DATA_DIR), "logs")
    s.polite_delay = polite
    setup_logging(s)
    return Collector(s)


def _bse_collector(polite: float = 1.0):
    from bse.collect import BseCollector
    from nse_collector.collector import setup_logging
    from nse_collector.config import Settings
    s = Settings()
    s.data_dir = L.DATA_DIR
    s.log_dir = os.path.join(os.path.dirname(L.DATA_DIR), "logs")
    s.polite_delay = polite
    setup_logging(s)
    return BseCollector(s)


def _conv_data():
    return dict(bhav=load_per_date("bhavcopy_delivery"), bulk=load_growing("bulk_deals"),
                block=load_growing("block_deals"), ban=load_per_date("securities_in_ban"),
                vol=load_per_date("daily_volatility"), pe=load_per_date("pe_ratio"),
                most_active=load_snapshot_latest("most_active_value"))
