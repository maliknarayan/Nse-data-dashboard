"""NSE investor dashboard.

Run:  python -m streamlit run dashboard/app.py

Reads the local CSV warehouse the collector writes. Everything degrades
gracefully: datasets not yet collected show a hint instead of an error.
"""

from __future__ import annotations

import datetime as dt
import os
import sys

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dashboard import loader as L  # noqa: E402
from dashboard import theme as T  # noqa: E402
from dashboard import signals as S  # noqa: E402
from dashboard import watchlist as W  # noqa: E402
from dashboard import portfolio as PF  # noqa: E402
from dashboard import derive as D  # noqa: E402
from dashboard import insights as I  # noqa: E402
from dashboard import charts as C  # noqa: E402
from dashboard import glossary as G  # noqa: E402
from dashboard import snapshots as SNAP  # noqa: E402
from dashboard import valuation as V  # noqa: E402
from dashboard import technicals as TA  # noqa: E402
from dashboard.ui import (  # noqa: E402
    load_growing, load_snapshot_latest, load_per_date, per_date_dates,
    load_per_date_all, load_manifest, all_symbols, company_map, symbol_history,
    bse_symbols, bse_symbol_history, index_history, index_names, niftyindices_history,
    concall_quarters,
    concall_index, concall_summary, concall_text, match_symbol, SYMBOLS, NAMES, symbol_select,
    _hint, _num, card, _collector, _bse_collector, _niftyindices_collector, _conv_data,
    result_pdfs, result_quarters, result_summary, result_index, concall_peers,
    ratio_hits, industry_ratios, ratio_family,
    result_pdf_quarters, result_pending, market_map, searched, apply_search, search,
    concall_pdf_quarters, concall_pending, _run_concall_analyzer,
    fundamentals_symbols, fundamentals_doc, fundamentals_facts,
    fundamentals_issues, fundamentals_manifest, _parse_results, _run_analyzer,
    peg_table,
)

st.set_page_config(page_title="NSE Investor Dashboard", page_icon="📈", layout="wide",
                   initial_sidebar_state="expanded")
# NOTE: this file is Streamlit's entrypoint (__main__). Shared helpers/cached
# loaders live in dashboard/ui.py, never here — a submodule importing this
# file by module path would re-run it whole (double st.set_page_config crash).
st.markdown(T.CSS, unsafe_allow_html=True)
st.markdown(T.POLISH, unsafe_allow_html=True)
st.markdown(T.RESPONSIVE, unsafe_allow_html=True)
_theme = st.session_state.get("ui_theme", "Midnight")
if _theme == "Midnight":
    st.markdown(T.FILLOW, unsafe_allow_html=True)
elif _theme == "Daylight":
    st.markdown(T.STOCKSCANS, unsafe_allow_html=True)
elif _theme == "Aurora":
    st.markdown(T.AURORA, unsafe_allow_html=True)
elif _theme == "Zine":
    st.markdown(T.ZINE, unsafe_allow_html=True)

# post-theme overrides (win over every theme block): full-width header + visible toggle
st.markdown(T.OVERRIDES, unsafe_allow_html=True)
st.markdown(G.CSS, unsafe_allow_html=True)

# subtle cursor-follow glow — JS runs in an invisible 0-height component, CSS renders in the main page
st.markdown(T.MOUSE_GLOW_CSS, unsafe_allow_html=True)
components.html(T.MOUSE_GLOW_JS, height=0)

# dark charts for dark themes, light chart ink for light themes
_DARK = _theme in ("Midnight", "Aurora")

# ---------------------------------------------------------------- sidebar
st.sidebar.markdown(T.brand("NSE Alpha", "Investor Intelligence"), unsafe_allow_html=True)
st.sidebar.markdown("")

asof = L.snapshot_asof("all_indices") or L.snapshot_asof("top_gainers")

NAV = {
    "📊 Overview": ["⭐ Top Ideas", "📊 Market Pulse", "📡 What's New", "🩺 Data Health", "⚙️ Settings"],
    "🎯 Ideas & Signals": ["🎯 Signals", "🔎 Screener", "💎 Value & PEG", "⚖️ Peer Compare",
                           "🏆 Conviction", "💼 Portfolio", "🧮 Capital Allocator"],
    "📈 Markets": ["🗺️ Market Map", "🚀 Movers", "🗓️ Day Explorer", "🧭 Sectors", "📈 History",
                   "📐 Darvas & Fib"],
    "💰 Flows & Derivatives": ["💰 Smart Money", "📉 Derivatives & FII",
                               "🧩 F&O / Options", "📦 Delivery & Value"],
    "📰 Filings & Calls": ["📞 Concalls", "🧬 Concall Peers", "📜 Guidance Tracker",
                           "📄 Result PDFs", "🧾 Result Scorecard", "🥇 Best of Quarter",
                           "🗂️ Filings", "🔔 Need Attention"],
}
_goto = st.session_state.pop("_goto", None)
if _goto:
    st.session_state["nav_group"] = _goto["group"]
    st.session_state["nav_page"] = _goto["page"]
    if _goto["sym_key"] != "hist_sym" or _goto["sym"] in SYMBOLS:
        st.session_state[_goto["sym_key"]] = _goto["sym"]
    if _goto["sym_key"] == "hist_sym":
        st.session_state["hist_exch"] = "NSE stock"

_grp = st.sidebar.radio("Menu", list(NAV.keys()), label_visibility="collapsed", key="nav_group")
st.sidebar.caption(_grp.split(" ", 1)[1] if " " in _grp else _grp)
PAGE = st.sidebar.radio("nav", NAV[_grp], label_visibility="collapsed", key="nav_page")
G.sidebar()

# ---------------------------------------------------------------- hero
# ---------------------------------------------------------------- top header
st.markdown(T.TOPBAR_CSS, unsafe_allow_html=True)
_chips = [("Date", dt.date.today().strftime("%a, %d %b %Y").upper(), "")]
_idx = load_snapshot_latest("all_indices")
if not _idx.empty and "index" in _idx.columns:
    _n = _idx[_idx["index"].astype(str).str.upper() == "NIFTY 50"]
    if not _n.empty:
        _pc = L.to_num(_n["percentChange"]).iloc[0]
        _lv = L.to_num(_n["last"]).iloc[0]
        _t = "up" if (_pc or 0) >= 0 else "down"
        _chips.append(("Nifty 50", f'{_lv:,.0f} ({_pc:+.2f}%)', _t))
_ad = load_snapshot_latest("advances_declines")
if not _ad.empty and {"metric", "value"} <= set(_ad.columns):
    _m = dict(zip(_ad["metric"], L.to_num(_ad["value"])))
    _r = (_m.get("Advances", 0) / _m.get("Declines", 1)) if _m.get("Declines") else 0
    _chips.append(("A/D ratio", f"{_r:.2f}", "up" if _r > 1 else "down"))
with st.container(key="topbar_row"):
    _hc1, _hc2 = st.columns([5, 1], gap="small", vertical_alignment="center")
    with _hc1:
        st.markdown(T.topbar(_chips), unsafe_allow_html=True)
    with _hc2:
        st.selectbox("Theme", ["Midnight", "Daylight", "Aurora", "Modern", "Zine"],
                    key="ui_theme", label_visibility="collapsed")

st.markdown(T.hero(f"{PAGE}",
                   f"NSE / BSE investor dashboard &nbsp;|&nbsp; as of {asof or '—'}"),
            unsafe_allow_html=True)

# jargon each page leans on — rendered as a collapsed "what do these mean?" panel
PAGE_TERMS = {
    "📊 Market Pulse": ("advance_decline", "ad_ratio", "market_breadth", "pe", "vix"),
    "🎯 Signals": ("accumulation", "distribution", "delivery_pct", "breakout", "week52",
                   "momentum", "conviction_score"),
    "🔎 Screener": ("delivery_pct", "turnover", "pe", "week52", "volume"),
    "⚖️ Peer Compare": ("pe", "pb", "market_cap", "delivery_pct"),
    "🏆 Conviction": ("conviction_score", "accumulation", "delivery_pct", "smart_money"),
    "💼 Portfolio": ("market_cap", "pe", "dividend_yield"),
    "🧮 Capital Allocator": ("conviction_score", "accumulation", "delivery_pct", "concall",
                             "market_breadth"),
    "🚀 Movers": ("gap_up", "week52", "circuit", "volume", "turnover"),
    "🧭 Sectors": ("market_breadth", "pe", "momentum"),
    "💰 Smart Money": ("bulk_deal", "block_deal", "fii", "dii", "smart_money",
                       "short_selling", "delivery_pct"),
    "📉 Derivatives & FII": ("oi", "change_oi", "participant_oi", "fii", "dii",
                             "long_buildup", "short_buildup", "short_covering",
                             "long_unwinding"),
    "🧩 F&O / Options": ("fno", "oi", "change_oi", "pcr", "strike", "expiry",
                         "itm_otm", "premium", "iv", "ban_list", "rollover"),
    "📦 Delivery & Value": ("delivery_pct", "turnover", "volume", "accumulation",
                            "daily_volatility", "var_margin", "pe"),
    "📞 Concalls": ("concall", "guidance", "standalone", "consolidated", "ebitda", "pat"),
    "🧬 Concall Peers": ("concall", "guidance", "ebitda_margin", "revenue", "pat"),
    "🥇 Best of Quarter": ("concall", "guidance", "pat", "ebitda_margin", "conviction_score"),
    "🗂️ Filings": ("corporate_action", "ex_date", "record_date", "bonus", "split",
                   "buyback", "rights_issue", "promoter_pledge"),
    "🩺 Data Health": ("snapshot", "bhavcopy"),
}
if PAGE in PAGE_TERMS:
    G.legend(*PAGE_TERMS[PAGE])


def _nav_row(symbols: list[str], key_prefix: str, group: str = "📈 Markets",
             page: str = "📈 History", sym_key: str = "hist_sym", limit: int = 5) -> None:
    """Small button row under a box strip — click a symbol to jump to its History page."""
    syms = list(dict.fromkeys(str(s) for s in symbols if s))[:limit]
    if not syms:
        return
    cols = st.columns(len(syms))
    for col, sym in zip(cols, syms):
        with col:
            if st.button(f"↗ {sym}", key=f"nav_{key_prefix}_{sym}", width="stretch"):
                st.session_state["_goto"] = {"group": group, "page": page,
                                             "sym_key": sym_key, "sym": sym.upper()}
                st.rerun()


def _dropout_note(page_key: str, today_symbols: list[str]) -> None:
    d = SNAP.dropped_out(page_key, today_symbols)
    if d and d[1]:
        prev_date, gone = d
        st.caption(f"📉 Dropped out of top-5 since {prev_date}: " + ", ".join(gone))


def _conf_num(v) -> float | None:
    """Confidence can be a 0-10 float/int, a digit string, or a HIGH/MEDIUM/LOW label."""
    try:
        return float(v)
    except (TypeError, ValueError):
        pass
    return {"HIGH": 9.0, "MEDIUM": 6.0, "MED": 6.0, "LOW": 3.0}.get(str(v or "").strip().upper())


_BQ_STOPWORDS = {"LIMITED", "LTD", "PVT", "PRIVATE", "THE", "CO"}


def _company_key(name: str) -> str:
    import re as _re0
    toks = [t for t in _re0.sub(r"[^A-Z0-9 ]", " ", str(name or "").upper()).split()
            if t not in _BQ_STOPWORDS]
    return "".join(toks)


# ================================================================ Top Ideas
if PAGE == "⭐ Top Ideas":
    st.caption("One screen, every page's top-5 — click a symbol to jump to its History page. "
               "Each strip remembers yesterday's top-5 to flag who dropped out.")

    def _ti_section(title: str, rows: list[tuple], fmt: str, suffix: str, page_key: str,
                     nav_syms: list[str] | None = None) -> None:
        with card():
            st.markdown(f"#### {title}")
            if not rows:
                _hint()
                return
            SNAP.record(page_key, rows)
            st.markdown(T.rank_boxes(rows, fmt, suffix), unsafe_allow_html=True)
            _nav_row(nav_syms if nav_syms is not None else [s for s, *_ in rows], page_key)
            _dropout_note(page_key, [s for s, *_ in rows])

    _ti_data = _conv_data()
    lb = S.rank_ideas(**_ti_data)
    _ti_section("🏆 Conviction — top ideas", list(zip(lb["Symbol"].head(5), lb["Score"].head(5))),
                "{:+d}", "", "conviction")

    g = _num(load_snapshot_latest("top_gainers").copy(), ["perChange"])
    if not g.empty and "symbol" in g.columns:
        if "legend" in g.columns and "allSec" in g["legend"].values:
            g = g[g["legend"] == "allSec"]
        g = g.drop_duplicates(subset=["symbol"]).dropna(
            subset=["perChange"]).sort_values("perChange", ascending=False)
    _ti_section("🚀 Movers — top gainers",
                list(zip(g["symbol"].head(5), g["perChange"].head(5))) if not g.empty else [],
                "{:+.2f}", "%", "movers_gainers")

    bhav = load_per_date("bhavcopy_delivery")
    if not bhav.empty:
        b = bhav.copy()
        if "SERIES" in b.columns:
            b = b[b["SERIES"] == "EQ"]
        b = _num(b, ["CLOSE_PRICE", "PREV_CLOSE", "DELIV_PER", "TURNOVER_LACS"])
        b["%Chg"] = (b["CLOSE_PRICE"] - b["PREV_CLOSE"]) / b["PREV_CLOSE"] * 100
        scr = b[b["TURNOVER_LACS"].fillna(0) >= 200].sort_values("%Chg", ascending=False)
        _ti_section("🔎 Screener — top scan hits", list(zip(scr["SYMBOL"].head(5), scr["%Chg"].head(5))),
                    "{:+.2f}", "%", "screener")

        dv = b[b["TURNOVER_LACS"].fillna(0) >= 500].sort_values("DELIV_PER", ascending=False)
        _ti_section("📦 Delivery & Value — highest delivery %",
                    list(zip(dv["SYMBOL"].head(5), dv["DELIV_PER"].head(5))), "{:.0f}", "%", "delivery_value")
    else:
        _ti_section("🔎 Screener — top scan hits", [], "{:+.2f}", "%", "screener")
        _ti_section("📦 Delivery & Value — highest delivery %", [], "{:.0f}", "%", "delivery_value")

    for label, name in [("💰 Smart Money — bulk deals, by value", "bulk_deals"),
                        ("💰 Smart Money — block deals, by value", "block_deals")]:
        df = load_growing(name)
        rows = []
        if not df.empty and {"QuantityTraded", "TradePrice/Wght.Avg.Price", "Symbol"} <= set(df.columns):
            v = _num(df.copy(), ["QuantityTraded", "TradePrice/Wght.Avg.Price"])
            v["Value(Cr)"] = (v["QuantityTraded"] * v["TradePrice/Wght.Avg.Price"]) / 1e7
            v = v.sort_values("Value(Cr)", ascending=False).head(5)
            rows = list(zip(v["Symbol"], v["Value(Cr)"]))
        _ti_section(label, rows, "₹{:,.1f}", " Cr", f"smart_money_{name}")

    mau = _num(load_snapshot_latest("most_active_underlying").copy(), ["totTurnover"])
    rows = (list(zip(mau.sort_values("totTurnover", ascending=False)["symbol"].head(5),
                     mau.sort_values("totTurnover", ascending=False)["totTurnover"].head(5)))
            if not mau.empty and "symbol" in mau.columns else [])
    _ti_section("📉 Derivatives & FII — most active underlying", rows, "₹{:,.0f}", " Cr", "derivatives_active")

    fno = load_per_date("fno_bhavcopy")
    rows = []
    if not fno.empty and {"TckrSymb", "OpnIntrst"} <= set(fno.columns):
        f = _num(fno.copy(), ["OpnIntrst"])
        f["SYM"] = f["TckrSymb"].astype(str).str.upper()
        rows = list(f.groupby("SYM")["OpnIntrst"].sum().nlargest(5).items())
    _ti_section("🧩 F&O / Options — most active by OI", rows, "{:,.0f}", "", "fno_oi")

    cqs = sorted(concall_quarters())
    rows = []
    if cqs:
        peers = concall_peers(cqs[-1])
        if not peers.empty and "Rev YoY %" in peers.columns:
            p = peers.dropna(subset=["Rev YoY %"]).sort_values("Rev YoY %", ascending=False).head(5)
            rows = list(zip(p["Symbol"], p["Rev YoY %"]))
    _ti_section(f"🧬 Concall Peers — best reported growth ({cqs[-1] if cqs else '—'})",
                rows, "{:+.1f}", "%", "concall_peers")

    rqs = sorted(result_quarters())
    rows, rq_nav = [], []
    if rqs:
        ridx = result_index(rqs[-1])
        if not ridx.empty and "PAT YoY %" in ridx.columns:
            r = ridx.dropna(subset=["PAT YoY %"]).sort_values("PAT YoY %", ascending=False).head(5)
            rows = list(zip(r["Company"], r["PAT YoY %"]))
            rq_nav = [s for s in (match_symbol(c) for c in r["Company"]) if s]
    _ti_section(f"🧾 Result Scorecard — best PAT growth ({rqs[-1] if rqs else '—'})",
                rows, "{:+.1f}", "%", "result_scorecard", nav_syms=rq_nav)

    bqs = sorted(set(concall_quarters()) | set(result_quarters()))
    rows, bq_nav = [], []
    if bqs:
        cidx, ridx = concall_index(bqs[-1]).copy(), result_index(bqs[-1]).copy()
        if not cidx.empty or not ridx.empty:
            cidx["_key"] = cidx["Company"].map(_company_key) if not cidx.empty else []
            ridx["_key"] = ridx["Company"].map(_company_key) if not ridx.empty else []
            merged = cidx.merge(ridx, on="_key", how="outer", suffixes=("_cc", "_res")) \
                if not cidx.empty and not ridx.empty else pd.DataFrame()
            if not merged.empty:
                merged["Company"] = merged["Company_cc"].fillna(merged["Company_res"])
                good = ((merged["Call"].isin(["BUY"])) | (merged["Verdict_cc"] == "GOOD")) & \
                       (merged["Verdict_res"] == "GOOD")
                best = merged[good].copy()
                best["PAT YoY %"] = pd.to_numeric(best["PAT YoY %"], errors="coerce")
                best = best.dropna(subset=["PAT YoY %"]).sort_values("PAT YoY %", ascending=False).head(5)
                rows = list(zip(best["Company"], best["PAT YoY %"]))
                bq_nav = [s for s in (match_symbol(c) for c in best["Company"]) if s]
    _ti_section(f"🥇 Best of Quarter — concall + result both GOOD ({bqs[-1] if bqs else '—'})",
                rows, "{:+.1f}", "%", "best_of_quarter", nav_syms=bq_nav)

# ================================================================ Market Pulse
if PAGE == "📊 Market Pulse":
    ad = load_snapshot_latest("advances_declines")
    if not ad.empty and {"metric", "value"} <= set(ad.columns):
        m = dict(zip(ad["metric"], L.to_num(ad["value"])))
        adv, dec = int(m.get("Advances", 0)), int(m.get("Declines", 0))
        unc = int(m.get("Unchange", m.get("Unchanged", 0)))
        ratio = (adv / dec) if dec else float("inf")
        cards = [
            T.stat_card("Advances", f"{adv:,}", "stocks up", "up", arrow=True),
            T.stat_card("Declines", f"{dec:,}", "stocks down", "down", arrow=True),
            T.stat_card("A/D Ratio", f"{ratio:.2f}",
                        "bullish breadth" if ratio > 1 else "bearish breadth",
                        "up" if ratio > 1 else "down"),
            T.stat_card("Unchanged", f"{unc:,}", "flat", "neutral"),
        ]
        st.markdown(T.stat_row(cards), unsafe_allow_html=True)
        _tot = adv + dec + unc
        if _tot:
            _as = adv / _tot * 100
            st.markdown(T.progress(_as, "success" if _as >= 50 else "danger",
                        f"Advances share · {_as:.0f}%"), unsafe_allow_html=True)
        dcol, _sp = st.columns([1, 2])
        with dcol:
            with card():
                st.markdown(G.head("Breadth split", "advance_decline", "market_breadth"), unsafe_allow_html=True)
                C.show(C.donut(["Advances", "Declines", "Unchanged"], [adv, dec, unc],
                               [T.GREEN, T.CORAL, "#B8BCCB"], _DARK,
                               center=f"{adv + dec + unc:,}"))
        with _sp:
            with card():
                st.markdown("#### 🧭 Sector heatmap")
                _si = load_snapshot_latest("all_indices")
                if not _si.empty and "index" in _si.columns:
                    _si = _num(_si.copy(), ["percentChange"])
                    if "key" in _si.columns and _si["key"].astype(str).str.contains("Sector", case=False).any():
                        _sec = _si[_si["key"].astype(str).str.contains("Sector", case=False)]
                    else:
                        _kw = "IT|BANK|PHARMA|AUTO|FMCG|METAL|ENERGY|REALTY|MEDIA|FINANC|HEALTH|PSU|CONSUM|INFRA|OIL|CHEM"
                        _sec = _si[_si["index"].astype(str).str.upper().str.contains(_kw)]
                    _sec = _sec.dropna(subset=["percentChange"]).sort_values("percentChange", ascending=False)
                    if not _sec.empty:
                        _rows = list(zip(_sec["index"].astype(str).str.replace("NIFTY ", "", regex=False),
                                         _sec["percentChange"]))
                        st.markdown(T.heatmap(_rows), unsafe_allow_html=True)
                    else:
                        _hint("No sector indices in the collected snapshot.")
                else:
                    _hint()
    else:
        _hint()

    idx = load_snapshot_latest("all_indices")
    if not idx.empty:
        idx = _num(idx, ["last", "percentChange", "pe", "pb", "dy",
                         "perChange30d", "perChange365d", "advances", "declines"])
        headline = ["NIFTY 50", "NIFTY BANK", "NIFTY NEXT 50", "NIFTY MIDCAP 100",
                    "NIFTY IT", "INDIA VIX"]
        hc = idx[idx["index"].isin(headline)]
        cards = []
        for _, r in hc.iterrows():
            pc = r["percentChange"]
            tone = "up" if pc >= 0 else "down"
            cards.append(T.stat_card(r["index"], f'{r["last"]:,.0f}',
                                     f'{pc:+.2f}%', tone, arrow=True, mini=True))
        if cards:
            st.markdown(T.stat_row(cards), unsafe_allow_html=True)

        with card():
            st.markdown(G.head("All indices — valuation & momentum", "pe", "momentum"), unsafe_allow_html=True)
            view = idx[["index", "last", "percentChange", "perChange30d",
                        "perChange365d", "pe", "pb", "dy", "advances", "declines"]].copy()
            view.columns = ["Index", "Last", "%Chg", "%Chg 30d", "%Chg 365d",
                            "P/E", "P/B", "Div Yld", "Adv", "Dec"]
            st.dataframe(
                view.style.background_gradient(subset=["%Chg"], cmap="RdYlGn")
                          .background_gradient(subset=["P/E"], cmap="RdYlGn_r")
                          .format({"Last": "{:,.1f}", "%Chg": "{:+.2f}", "%Chg 30d": "{:+.2f}",
                                   "%Chg 365d": "{:+.2f}", "P/E": "{:.1f}", "P/B": "{:.2f}",
                                   "Div Yld": "{:.2f}", "Adv": "{:.0f}", "Dec": "{:.0f}"}, na_rep="-"),
                width="stretch", height=430,
            )

        rank = idx.dropna(subset=["percentChange"]).set_index("index")["percentChange"]
        b1, b2 = st.columns(2)
        with b1:
            with card():
                st.markdown("#### Top 10 gaining indices")
                C.show(C.hbar(rank.nlargest(10), _DARK, color=T.GREEN))
        with b2:
            with card():
                st.markdown("#### Top 10 losing indices")
                C.show(C.hbar(rank.nsmallest(10), _DARK, color=T.CORAL))
    else:
        _hint()

# ================================================================ Conviction
if PAGE == "🏆 Conviction":
    st.caption("Conviction leaderboard — stocks with aligned signals. Score combines "
               "delivery, volume, price trend, bulk/block deals, breadth and flows.")
    lb = S.rank_ideas(**_conv_data())
    if lb.empty:
        _hint("Needs bhav copy for the latest trading day — fetch/backfill first.")
    else:
        top = lb.iloc[0]
        st.markdown(T.stat_row([
            T.stat_card("Aligned stocks", f"{len(lb)}", "signals agree", "up"),
            T.stat_card("Top pick", str(top["Symbol"]), f"score {int(top['Score']):+d}", top.get("tone", "up") if False else "up"),
            T.stat_card("Avg score", f"{lb['Score'].mean():+.1f}", "conviction", "neutral"),
        ]), unsafe_allow_html=True)
        with card():
            st.markdown(G.head("Full conviction leaderboard", "conviction_score"), unsafe_allow_html=True)
            top5_rows = list(zip(lb["Symbol"].head(5), lb["Score"].head(5)))
            SNAP.record("conviction", top5_rows)
            st.markdown(T.rank_boxes(top5_rows, "{:+d}"), unsafe_allow_html=True)
            _nav_row([s for s, _ in top5_rows], "conviction")
            _dropout_note("conviction", [s for s, _ in top5_rows])
            C.show(C.hbar(lb.set_index("Symbol")["Score"].head(15), _DARK, diverge=True,
                          height=380))
            lb = searched(lb, "conv_q", ["Symbol"], "Search", "symbol")
            st.dataframe(
                lb.style.background_gradient(subset=["Score"], cmap="RdYlGn")
                        .format({"Score": "{:+d}", "Deliv%": "{:.0f}", "%Chg": "{:+.2f}"}, na_rep="-"),
                width="stretch", height=560, hide_index=True)

        prev = SNAP.previous_entry("conviction")
        if prev:
            prev_date, prev_rows = prev
            with card():
                st.markdown(f"#### 🔁 Backtest — {prev_date}'s top-5 picks")
                bt_rows = []
                for sym, score in prev_rows:
                    h = symbol_history(sym)
                    if h.empty:
                        continue
                    h = h[h["date"] >= prev_date]
                    if h.empty or not h.iloc[0]["CLOSE_PRICE"]:
                        continue
                    entry, last = h.iloc[0]["CLOSE_PRICE"], h.iloc[-1]["CLOSE_PRICE"]
                    bt_rows.append((sym, (last - entry) / entry * 100))
                if bt_rows:
                    avg = sum(v for _, v in bt_rows) / len(bt_rows)
                    st.markdown(T.rank_boxes(bt_rows, "{:+.2f}", "%"), unsafe_allow_html=True)
                    st.caption(f"Return since {prev_date} close → latest close. "
                               f"Avg: {avg:+.2f}%. Educational backtest, not advice.")
                else:
                    _hint("No price history yet for those picks since then.")


if PAGE == "📊 Market Pulse":
    with card():
        st.markdown(G.head("🏆 Top conviction — stocks with aligned signals", "conviction_score"), unsafe_allow_html=True)
        lb5 = S.rank_ideas(**_conv_data())
        if lb5.empty:
            _hint("Fetch/backfill bhav copy to compute conviction.")
        else:
            st.dataframe(
                lb5.head(5).style.background_gradient(subset=["Score"], cmap="RdYlGn")
                   .format({"Score": "{:+d}", "Deliv%": "{:.0f}", "%Chg": "{:+.2f}"}, na_rep="-"),
                width="stretch", hide_index=True)
            st.caption("See the **🏆 Conviction** tab for the full leaderboard.")


# ================================================================ What's New
if PAGE == "📡 What's New":
    st.caption("Daily digest — what changed today: breakouts, quiet accumulation, "
               "FII stance, ban entries, results due.")
    d = _conv_data()
    breakouts = S.screen_breakouts(d["bhav"], load_per_date("week52_high_low"))
    spikes = I.delivery_spike(load_per_date_all("bhavcopy_delivery"))
    fii_div = I.fii_client_divergence(load_per_date_all("participant_oi"))
    earn = load_growing("earnings_calendar")
    dig = I.whats_changed(breakouts=breakouts, spikes=spikes, fii_div=fii_div,
                          ban=d["ban"], earnings=earn, bulk=d["bulk"])

    if dig["fii_note"]:
        st.markdown("### ⚠️ " + T.badge(dig["fii_note"], "down"), unsafe_allow_html=True)
    st.markdown(T.stat_row([
        T.stat_card("New/near 52wk highs", f'{len(breakouts)}', "momentum", "up"),
        T.stat_card("Delivery spikes", f'{len(spikes)}', "accumulation", "up"),
        T.stat_card("In F&O ban", f'{len(dig["ban"])}', "avoid leverage", "down" if dig["ban"] else "neutral"),
    ]), unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        with card():
            st.markdown(G.head("🚀 Breakouts (at/near 52wk high)", "breakout", "week52"), unsafe_allow_html=True)
            st.dataframe(breakouts, width="stretch", height=320, hide_index=True) if not breakouts.empty else _hint()
    with c2:
        with card():
            st.markdown(G.head("📦 Delivery spikes (vs 20d avg)", "delivery_pct"), unsafe_allow_html=True)
            st.dataframe(spikes, width="stretch", height=320, hide_index=True) if not spikes.empty else _hint("Needs a few days of bhav copy.")

    with card():
        st.markdown(G.head("🏦 FII vs Client — net index futures trend", "fii", "participant_oi"), unsafe_allow_html=True)
        if not fii_div.empty:
            cols = [c for c in ["FII", "Client", "DII", "Pro"] if c in fii_div.columns]
            C.show(C.lines(fii_div.set_index("date")[cols], _DARK))
        else:
            _hint("Needs participant OI for 2+ days.")

    e1, e2 = st.columns(2)
    with e1:
        with card():
            st.markdown(G.head("📅 Results / events due", "concall"), unsafe_allow_html=True)
            st.dataframe(dig["earnings"], width="stretch", height=280, hide_index=True) if not dig["earnings"].empty else _hint()
    with e2:
        with card():
            st.markdown(G.head("🚫 Securities in F&O ban", "ban_list", "fno"), unsafe_allow_html=True)
            st.dataframe(pd.DataFrame({"Symbol": dig["ban"]}), width="stretch", height=280, hide_index=True) if dig["ban"] else st.success("None in ban.")


# ================================================================ Portfolio
if PAGE == "💼 Portfolio":
    st.caption("Your tracked holdings — persist across sessions. Live LTP, daily move, P&L, "
               "plus the latest concall and result verdict per stock.")

    ac1, ac2, ac3, ac4 = st.columns([2, 1, 1, 1])
    with ac1:
        add_sym = symbol_select("Add company", key="pf_add_sym")
    with ac2:
        add_qty = st.number_input("Qty", min_value=0.0, value=0.0, step=1.0, key="pf_add_qty")
    with ac3:
        add_cost = st.number_input("Avg cost", min_value=0.0, value=0.0, step=1.0, key="pf_add_cost")
    with ac4:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        if st.button("➕ Add", key="pf_add_btn", width="stretch") and add_sym and add_qty > 0:
            PF.add(add_sym, add_qty, add_cost)
            st.rerun()

    holdings = PF.load()
    if not holdings:
        st.info("No holdings yet — add a company above to start tracking your portfolio.")
    else:
        hold_df = pd.DataFrame(holdings)
        d = _conv_data()
        scorer = lambda s: S.stock_scorecard(s, **d)
        px = I.portfolio_xray(hold_df, d["bhav"], scorer)

        bhav = _num(d["bhav"].copy(), ["CLOSE_PRICE", "PREV_CLOSE"])
        if "SERIES" in bhav.columns:
            bhav = bhav[bhav["SERIES"] == "EQ"]
        chg_map = {}
        if "SYMBOL" in bhav.columns:
            for _, r in bhav.iterrows():
                s = str(r["SYMBOL"]).upper()
                if (s not in chg_map and pd.notna(r["CLOSE_PRICE"])
                        and pd.notna(r["PREV_CLOSE"]) and r["PREV_CLOSE"]):
                    chg_map[s] = (r["CLOSE_PRICE"] - r["PREV_CLOSE"]) / r["PREV_CLOSE"] * 100

        # latest concall + result, reverse-matched by symbol (same pattern as Capital Allocator)
        cqs, rqs = sorted(concall_quarters()), sorted(result_quarters())
        latest_cq, latest_rq = (cqs[-1] if cqs else None), (rqs[-1] if rqs else None)
        concall_map, result_map = {}, {}
        if latest_cq:
            for _, r in concall_index(latest_cq).iterrows():
                sym = match_symbol(r["Company"])
                if sym and sym not in concall_map:
                    concall_map[sym] = r
        if latest_rq:
            for _, r in result_index(latest_rq).iterrows():
                sym = match_symbol(r["Company"])
                if sym and sym not in result_map:
                    result_map[sym] = r

        px["%Chg"] = px["Symbol"].map(chg_map)
        px["Concall Verdict"] = px["Symbol"].apply(
            lambda s: concall_map[s]["Call"] if s in concall_map else "—")
        px["Concall Score"] = px["Symbol"].apply(
            lambda s: _conf_num(concall_map[s]["Confidence"]) if s in concall_map else None)
        px["Result Verdict"] = px["Symbol"].apply(
            lambda s: result_map[s]["Verdict"] if s in result_map else "—")
        px["Result Score"] = px["Symbol"].apply(
            lambda s: result_map[s]["PAT YoY %"] if s in result_map else None)
        px["Concall Score"] = pd.to_numeric(px["Concall Score"], errors="coerce")
        px["Result Score"] = pd.to_numeric(px["Result Score"], errors="coerce")

        inv = px["Invested"].dropna().sum()
        cur = px["Current"].dropna().sum()
        pnl = cur - inv
        st.markdown(T.stat_row([
            T.stat_card("Invested", f'₹{inv:,.0f}', f'{len(px)} holdings', "neutral"),
            T.stat_card("Current", f'₹{cur:,.0f}', "market value", "neutral"),
            T.stat_card("P&L", f'₹{pnl:,.0f}', f'{(pnl/inv*100 if inv else 0):+.1f}%',
                        "up" if pnl >= 0 else "down", arrow=True),
            T.stat_card("Avg conviction", f'{px["Conviction"].dropna().mean():+.1f}'
                        if px["Conviction"].notna().any() else "—", "signal", "neutral"),
        ]), unsafe_allow_html=True)

        pf1, pf2 = st.columns(2)
        alloc = px.dropna(subset=["Current"])
        alloc = alloc[alloc["Current"] > 0]
        with pf1:
            with card():
                st.markdown("#### Allocation by market value")
                if alloc.empty:
                    _hint("No priced holdings yet.")
                else:
                    C.show(C.donut(alloc["Symbol"].tolist(), alloc["Current"].tolist(),
                                   C.cycle(len(alloc)), _DARK, center=f'₹{cur:,.0f}'))
        with pf2:
            with card():
                st.markdown("#### P&L % per holding")
                pnl_s = px.dropna(subset=["P&L%"]).set_index("Symbol")["P&L%"]
                if pnl_s.empty:
                    _hint("No priced holdings yet.")
                else:
                    C.show(C.hbar(pnl_s.sort_values(ascending=False), _DARK, diverge=True,
                                  height=220))

        with card():
            st.markdown(G.head("Holdings", "market_cap", "pe", "concall"), unsafe_allow_html=True)
            st.caption(f"Concall: {latest_cq or '—'} · Result: {latest_rq or '—'}. "
                       "Edit qty / avg cost inline — saved automatically.")
            editable = px[["Symbol", "Qty", "AvgCost"]].copy()
            edited = st.data_editor(
                editable, key="pf_editor", hide_index=True, width="stretch", num_rows="fixed",
                column_config={
                    "Symbol": st.column_config.TextColumn("Symbol", disabled=True),
                    "Qty": st.column_config.NumberColumn("Qty", min_value=0.0, step=1.0),
                    "AvgCost": st.column_config.NumberColumn("Avg Cost", min_value=0.0,
                                                             step=0.01, format="%.2f"),
                })

            def _norm(df):
                return [(r["Symbol"], float(r["Qty"]) if pd.notna(r["Qty"]) else None,
                        float(r["AvgCost"]) if pd.notna(r["AvgCost"]) else None)
                        for r in df.to_dict("records")]

            if _norm(edited) != _norm(editable):
                PF.save(edited.to_dict("records"))
                st.rerun()

            show = px[["Symbol", "Qty", "AvgCost", "LTP", "%Chg", "Invested", "Current", "P&L",
                      "P&L%", "Conviction", "Concall Verdict", "Concall Score",
                      "Result Verdict", "Result Score"]].copy()
            # Streamlit's grid renders a null numeric cell as the literal text "None",
            # ignoring Styler na_rep — format these two as plain "-"-safe strings instead.
            show["Concall Score"] = show["Concall Score"].apply(
                lambda v: f"{v:.0f}" if pd.notna(v) else "—")
            show["Result Score"] = show["Result Score"].apply(
                lambda v: f"{v:+.1f}" if pd.notna(v) else "—")
            st.dataframe(
                show.style.background_gradient(subset=["P&L%"], cmap="RdYlGn")
                    .background_gradient(subset=["%Chg"], cmap="RdYlGn")
                    .background_gradient(subset=["Conviction"], cmap="RdYlGn")
                    .format({"AvgCost": "{:,.2f}", "LTP": "{:,.2f}", "%Chg": "{:+.2f}",
                             "Invested": "{:,.0f}", "Current": "{:,.0f}", "P&L": "{:,.0f}",
                             "P&L%": "{:+.1f}", "Conviction": "{:+.0f}"}, na_rep="-"),
                width="stretch", height=420, hide_index=True)

            rem = st.selectbox("Remove a holding", ["—"] + px["Symbol"].tolist(), key="pf_rem")
            if st.button("🗑️ Remove", key="pf_rem_btn") and rem != "—":
                PF.remove(rem)
                st.rerun()

        st.caption("Conviction = live technical signal. Concall/Result verdict + score come from "
                   "the latest collected quarter — cross-check before acting. Not investment advice.")


# ================================================================ Capital Allocator
if PAGE == "🧮 Capital Allocator":
    st.caption("⚠️ Educational decision-support from public NSE data — not investment advice. "
               "Composite of today's technical conviction + the latest concall verdict + the "
               "latest result verdict. Only stocks with a positive composite and no fundamental "
               "red flag are included — basket size varies day to day with opportunity quality. "
               "Verify every pick yourself before acting.")

    amount = st.number_input("Amount to invest this month (₹)", min_value=0, value=100_000,
                             step=5_000, key="cap_amount")

    d = _conv_data()
    ideas = S.rank_ideas(**d)
    if ideas.empty:
        _hint("Needs bhav copy for the latest trading day — fetch/backfill first.")
    else:
        bqs = sorted(set(concall_quarters()) | set(result_quarters()))
        cap_q = st.selectbox("Fundamentals quarter (concall + result)",
                             list(reversed(bqs)) or ["(none collected)"], key="cap_q")

        cidx = concall_index(cap_q) if cap_q in concall_quarters() else pd.DataFrame()
        ridx = result_index(cap_q) if cap_q in result_quarters() else pd.DataFrame()
        concall_map, result_map = {}, {}
        for _, r in cidx.iterrows():
            sym = match_symbol(r["Company"])
            if sym and sym not in concall_map:
                concall_map[sym] = r
        for _, r in ridx.iterrows():
            sym = match_symbol(r["Company"])
            if sym and sym not in result_map:
                result_map[sym] = r

        bhav = _num(d["bhav"].copy(), ["CLOSE_PRICE"])
        if "SERIES" in bhav.columns:
            bhav = bhav[bhav["SERIES"] == "EQ"]
        close_map = {}
        if "SYMBOL" in bhav.columns:
            for _, r in bhav.iterrows():
                s = str(r["SYMBOL"]).upper()
                if s not in close_map:
                    close_map[s] = r["CLOSE_PRICE"]

        candidates = []
        for _, row in ideas.iterrows():
            sym = str(row["Symbol"]).upper()
            composite = float(row["Score"])
            tags, excluded = [], False
            cc = concall_map.get(sym)
            if cc is not None:
                call = str(cc["Call"] or "").upper()
                if call in ("BUY", "ACCUMULATE ON DIPS"):
                    composite += 3
                    tags.append("concall BUY")
                elif call in ("AVOID", "SELL"):
                    composite -= 5
                    excluded = True
                    tags.append("concall AVOID/SELL")
                cn = _conf_num(cc["Confidence"])
                if cn is not None:
                    composite += (cn - 5) / 2
            rr = result_map.get(sym)
            if rr is not None:
                verdict = str(rr["Verdict"] or "").upper()
                if verdict == "GOOD":
                    composite += 3
                    tags.append("result GOOD")
                elif verdict == "BAD":
                    composite -= 5
                    excluded = True
                    tags.append("result BAD")
            if cc is not None and rr is not None and "concall BUY" in tags and "result GOOD" in tags:
                composite += 2
                tags.append("both confirmed")
            candidates.append({"Symbol": sym, "Composite": composite, "Tags": ", ".join(tags) or "—",
                               "Excluded": excluded, "LTP": close_map.get(sym),
                               "Concall": cc["Call"] if cc is not None else "—",
                               "Result": rr["Verdict"] if rr is not None else "—"})

        MIN_N, MAX_N = 3, 10
        picks, used_th = [], None
        for th in (5, 4, 3, 2, 1, 0):
            pool = sorted((c for c in candidates if not c["Excluded"] and c["Composite"] >= th),
                         key=lambda c: -c["Composite"])
            if len(pool) >= MIN_N or (th == 0 and pool):
                picks, used_th = pool[:MAX_N], th
                break
        if not picks:
            pool = sorted((c for c in candidates if not c["Excluded"]), key=lambda c: -c["Composite"])
            picks, used_th = pool[:MIN_N], "n/a"

        idx = load_snapshot_latest("all_indices")
        ad = load_snapshot_latest("advances_declines")
        reg = S.market_regime(idx, ad)

        if not picks:
            _hint("No stock clears a basic quality bar today — every accumulation candidate "
                  "carries a concall/result red flag, or no fundamental data exists at all. "
                  "Market regime: " + reg["label"])
        else:
            min_c = min(p["Composite"] for p in picks)
            shift = max(1.0, 1.0 - min_c)
            weights = [p["Composite"] + shift for p in picks]
            total_w = sum(weights)
            for p, w in zip(picks, weights):
                p["Weight %"] = w / total_w * 100
                p["Allocated ₹"] = amount * w / total_w
                p["Shares"] = int(p["Allocated ₹"] // p["LTP"]) if p["LTP"] else 0
                p["Deployed ₹"] = p["Shares"] * (p["LTP"] or 0)
            deployed = sum(p["Deployed ₹"] for p in picks)
            leftover = amount - deployed

            st.markdown(T.stat_row([
                T.stat_card("Market regime", reg["label"], f"score {reg['score']:+d}", reg["tone"]),
                T.stat_card("Picks", f"{len(picks)}", f"quality bar ≥ {used_th}", "up"),
                T.stat_card("Deployed", f"₹{deployed:,.0f}", f"of ₹{amount:,.0f}", "neutral"),
                T.stat_card("Cash left", f"₹{leftover:,.0f}", "rounding to whole shares", "neutral"),
            ]), unsafe_allow_html=True)

            with card():
                st.markdown(G.head("Suggested allocation", "conviction_score", "concall"),
                            unsafe_allow_html=True)
                top5_rows = [(p["Symbol"], p["Allocated ₹"]) for p in picks[:5]]
                SNAP.record("capital_allocator", top5_rows)
                st.markdown(T.rank_boxes(top5_rows, "₹{:,.0f}"), unsafe_allow_html=True)
                _nav_row([p["Symbol"] for p in picks], "cap_alloc", limit=len(picks))
                _dropout_note("capital_allocator", [p["Symbol"] for p in picks[:5]])

                pdf = pd.DataFrame(picks)[["Symbol", "Composite", "Weight %", "Allocated ₹",
                                          "LTP", "Shares", "Deployed ₹", "Concall", "Result", "Tags"]]
                dep = pdf[pdf["Deployed ₹"] > 0]
                if not dep.empty:
                    C.show(C.donut(dep["Symbol"].tolist(), dep["Deployed ₹"].tolist(),
                                   C.cycle(len(dep)), _DARK, center=f'₹{deployed:,.0f}',
                                   height=260))
                st.dataframe(
                    pdf.style.background_gradient(subset=["Composite"], cmap="RdYlGn")
                       .format({"Composite": "{:+.1f}", "Weight %": "{:.1f}", "Allocated ₹": "{:,.0f}",
                                "LTP": "{:,.2f}", "Deployed ₹": "{:,.0f}"}, na_rep="-"),
                    width="stretch", hide_index=True)
                st.caption("Composite = conviction score (delivery/volume/price/flows) + concall "
                           "verdict + result verdict + confidence, where available. Stocks with no "
                           "concall/result on file are scored on conviction alone — flagged '—'.")


# ================================================================ Signals
if PAGE == "🎯 Signals":
    st.caption("⚠️ Educational decision-support from public NSE data — positioning, "
               "conviction and risk, **not** price prediction or investment advice. "
               "Every score is transparent (sum of the named factors below). Do your own research.")

    idx = load_snapshot_latest("all_indices")
    ad = load_snapshot_latest("advances_declines")
    reg = S.market_regime(idx, ad)
    with card():
        st.markdown(G.head("Market regime — is this an environment to buy?", "market_breadth", "ad_ratio"), unsafe_allow_html=True)
        st.markdown(T.stat_row([
            T.stat_card("Regime", reg["label"], f"breadth+VIX score {reg['score']:+d}", reg["tone"]),
        ]), unsafe_allow_html=True)
        for r in reg["reasons"]:
            st.markdown(f"- {r}")
        if not reg["reasons"]:
            _hint("Run the collector to populate breadth/index data.")

    with card():
        st.markdown(G.head("Stock signal scorecard", "conviction_score"), unsafe_allow_html=True)
        st.caption("Search a symbol — see the transparent buy/sell evidence for that stock today.")
        sym = symbol_select("Symbol", key="scorecard_sym")
        if sym:
            sc = S.stock_scorecard(
                sym,
                bhav=load_per_date("bhavcopy_delivery"),
                bulk=load_growing("bulk_deals"),
                block=load_growing("block_deals"),
                ban=load_per_date("securities_in_ban"),
                vol=load_per_date("daily_volatility"),
                pe=load_per_date("pe_ratio"),
                most_active=load_snapshot_latest("most_active_value"),
            )
            st.markdown(T.stat_row([
                T.stat_card(sc["symbol"], sc["verdict"], f"composite score {sc['score']:+d}", sc["tone"]),
            ]), unsafe_allow_html=True)
            fdf = pd.DataFrame(sc["factors"])
            if not fdf.empty:
                st.dataframe(
                    fdf.style.background_gradient(subset=["points"], cmap="RdYlGn", vmin=-2, vmax=2)
                             .format({"points": "{:+d}"}),
                    width="stretch", hide_index=True)
            st.caption("Verdict = sum of factor points. Positive factors are green, risks red.")

            # multi-day delivery trend (needs >1 collected day)
            allb = load_per_date_all("bhavcopy_delivery")
            if not allb.empty and "SYMBOL" in allb.columns:
                t = allb[allb["SYMBOL"].astype(str).str.upper() == sym].copy()
                if len(t) > 1:
                    t["Delivery %"] = L.to_num(t["DELIV_PER"])
                    st.markdown("**Delivery % trend** — rising delivery = growing conviction")
                    C.show(C.lines(t.set_index("_date")["Delivery %"], _DARK, colors=[T.INDIGO], area=True))
        else:
            st.info("Enter a symbol to generate its scorecard.")

    sc1, sc2 = st.columns(2)
    bhav = load_per_date("bhavcopy_delivery")
    with sc1:
        with card():
            st.markdown(G.head("🟢 Accumulation candidates", "accumulation", "delivery_pct"), unsafe_allow_html=True)
            st.caption("High delivery % **and** price up = genuine buying, not churn.")
            acc = S.screen_accumulation(bhav)
            st.dataframe(acc, width="stretch", height=340, hide_index=True) if not acc.empty else _hint()
    with sc2:
        with card():
            st.markdown(G.head("🔴 Distribution warnings", "distribution"), unsafe_allow_html=True)
            st.caption("High delivery % **and** price down = strong hands offloading.")
            dis = S.screen_distribution(bhav)
            st.dataframe(dis, width="stretch", height=340, hide_index=True) if not dis.empty else _hint()

    bk1, bk2 = st.columns([1, 1])
    with bk1:
        with card():
            st.markdown(G.head("🚀 52-week breakouts", "week52", "breakout"), unsafe_allow_html=True)
            st.caption("Trading at/near 52-week high — momentum + fresh highs.")
            bo = S.screen_breakouts(load_per_date("bhavcopy_delivery"),
                                    load_per_date("week52_high_low"))
            if not bo.empty:
                st.dataframe(
                    bo.style.background_gradient(subset=["%FromHigh"], cmap="Greens")
                            .format({"CLOSE_PRICE": "{:,.2f}", "52wHigh": "{:,.2f}",
                                     "%FromHigh": "{:+.1f}", "%Chg": "{:+.2f}",
                                     "DELIV_PER": "{:.0f}"}, na_rep="-"),
                    width="stretch", height=340, hide_index=True)
            else:
                _hint("Needs bhav copy + 52wk report for the latest day.")
    with bk2:
        with card():
            st.markdown(G.head("🏦 Institutional buys today", "bulk_deal", "block_deal", "smart_money"), unsafe_allow_html=True)
            st.caption("Bulk deals, buy side, by ₹ value.")
            ib = S.screen_institutional_buys(load_growing("bulk_deals"))
            st.dataframe(ib, width="stretch", height=340, hide_index=True) if not ib.empty else _hint("No bulk-deal buys in window.")

    # bundle the cross-dataset inputs once for batch scoring
    _sig_data = dict(
        bhav=load_per_date("bhavcopy_delivery"), bulk=load_growing("bulk_deals"),
        block=load_growing("block_deals"), ban=load_per_date("securities_in_ban"),
        vol=load_per_date("daily_volatility"), pe=load_per_date("pe_ratio"),
        most_active=load_snapshot_latest("most_active_value"),
    )

    with card():
        st.markdown(G.head("⭐ Today's top ideas (ranked)", "conviction_score"), unsafe_allow_html=True)
        st.caption("High-delivery stocks that rose today, re-scored across all factors and ranked. "
                   "Cross-check with the market regime above before acting.")
        ideas = S.rank_ideas(**_sig_data)
        if not ideas.empty:
            top5_rows = list(zip(ideas["Symbol"].head(5), ideas["Score"].head(5)))
            SNAP.record("conviction", top5_rows)
            st.markdown(T.rank_boxes(top5_rows, "{:+d}"), unsafe_allow_html=True)
            _nav_row([s for s, _ in top5_rows], "signals")
            _dropout_note("conviction", [s for s, _ in top5_rows])
            st.dataframe(
                ideas.style.background_gradient(subset=["Score"], cmap="RdYlGn")
                           .format({"Score": "{:+d}", "Deliv%": "{:.0f}", "%Chg": "{:+.2f}"}, na_rep="-"),
                width="stretch", height=380, hide_index=True)
        else:
            _hint("No ideas — needs bhav copy collected for the latest trading day.")

    with card():
        st.markdown(G.head("📌 Watchlist", "conviction_score"), unsafe_allow_html=True)
        wc1, wc2 = st.columns([3, 1])
        with wc1:
            new_sym = symbol_select("Add symbol", key="wl_add")
        if wc2.button("Add", key="wl_add_btn") and new_sym:
            W.add(new_sym); st.rerun()
        wl = W.load()
        if wl:
            wtab = S.score_many(wl, **_sig_data)
            # alerts: compare to last saved scores, then persist current
            alerts = S.compute_alerts(wtab, W.load_state())
            if alerts:
                for a in alerts:
                    icon = "🟢" if a["tone"] == "up" else "🔴"
                    st.markdown(f"{icon} **{a['symbol']}** — {a['change']}")
            W.save_state(dict(zip(wtab["Symbol"], wtab["Score"])))
            st.dataframe(
                wtab.style.background_gradient(subset=["Score"], cmap="RdYlGn")
                          .format({"Score": "{:+d}"}),
                width="stretch", hide_index=True)
            rem = st.selectbox("Remove symbol", ["—"] + wl, key="wl_rem")
            if st.button("Remove", key="wl_rem_btn") and rem != "—":
                W.remove(rem); st.rerun()
        else:
            st.info("Watchlist empty — add a symbol above to track its daily signal.")

# ================================================================ Concalls
if PAGE == "📞 Concalls":
    st.caption("Earnings-call analyses (Claude-generated) — fundamentals view. "
               "Pair a company's verdict with its live technical/flow signal.")
    qs = concall_quarters()
    if not qs:
        _hint("No concall data — add MD files under concall-data/<quarter>/.")
    else:
        q = st.selectbox("Quarter", list(reversed(qs)), key="cc_q")
        idx = concall_index(q)
        cdoc = concall_summary(q)
        if idx.empty:
            _hint("No concalls parsed for this quarter.")
        else:
            buy = int(idx["Call"].isin(["BUY", "ACCUMULATE ON DIPS"]).sum())
            hold = int(idx["Call"].isin(["HOLD", "WATCHLIST"]).sum())
            avoid = int(idx["Call"].isin(["AVOID", "SELL"]).sum())
            conf = pd.to_numeric(idx["Confidence"], errors="coerce")
            conf_disp = (f"{conf.mean():.1f}/10" if conf.notna().any() else
                         idx["Confidence"].mode().iat[0].title() if idx["Confidence"].any() else "—")
            st.markdown(T.stat_row([
                T.stat_card("Companies", f"{len(idx)}", q, "neutral"),
                T.stat_card("BUY / ACCUMULATE", f"{buy}", "bullish verdicts", "up"),
                T.stat_card("HOLD / WATCH / AVOID", f"{hold} / {avoid}", "cautious", "down"),
                T.stat_card("Confidence", conf_disp, "mgmt tone", "neutral"),
            ]), unsafe_allow_html=True)
            if len(idx):
                _bs = buy / len(idx) * 100
                st.markdown(T.progress(_bs, "success", f"BUY / ACCUMULATE verdicts · {_bs:.0f}%"),
                            unsafe_allow_html=True)
            if cdoc.get("last_updated"):
                st.caption(f"`concalls-summary.json` last written on "
                           f"{str(cdoc['last_updated']).replace('T', ' ')}.")

            with card():
                st.markdown("#### Call mix")
                cc_mix = idx["Call"].replace("", pd.NA).dropna().value_counts()
                if cc_mix.empty:
                    _hint("No calls recorded for this quarter.")
                else:
                    C.show(C.donut(cc_mix.index.tolist(), cc_mix.values.tolist(),
                                   C.cycle(len(cc_mix)), _DARK, center=str(len(idx)),
                                   height=280))

            with card():
                st.markdown(G.head("🔝 Top 10 concalls this quarter", "concall", "guidance"),
                            unsafe_allow_html=True)
                st.caption("Ranked by management confidence as read from the call.")
                ranked = idx.assign(_conf=idx["Confidence"].map(_conf_num)) \
                            .dropna(subset=["_conf"]).sort_values("_conf", ascending=False).head(10)
                if ranked.empty:
                    _hint("No confidence score recorded for this quarter's concalls.")
                else:
                    top10_rows = list(zip(ranked["Company"], ranked["_conf"], ranked["Call"]))
                    SNAP.record("concalls_top", list(zip(ranked["Company"], ranked["_conf"])))
                    st.markdown(T.rank_boxes(top10_rows, "{:.0f}", "/10"), unsafe_allow_html=True)
                    nav_syms = [s for s in (match_symbol(c) for c in ranked["Company"]) if s]
                    _nav_row(nav_syms, "concalls_top", limit=10)
                    _dropout_note("concalls_top", list(ranked["Company"]))

            with card():
                st.markdown(G.head("All concalls", "concall", "guidance"), unsafe_allow_html=True)
                colf1, colf2 = st.columns([1, 2])
                vf = colf1.selectbox("Filter call", ["All", "BUY", "ACCUMULATE ON DIPS", "HOLD",
                                                     "WATCHLIST", "AVOID/SELL"], key="cc_vf")
                q_txt = colf2.text_input("Search company", key="cc_search").upper()
                view = idx.copy()
                if vf == "AVOID/SELL":
                    view = view[view["Call"].isin(["AVOID", "SELL"])]
                elif vf != "All":
                    view = view[view["Call"] == vf]
                if q_txt:
                    view = view[view["Company"].str.upper().str.contains(q_txt)]
                st.dataframe(view[["Company", "Verdict", "Call", "Confidence", "Date"]],
                             width="stretch", height=380, hide_index=True)

            with card():
                st.markdown("#### Read analysis")
                comp = st.selectbox("Company", idx["Company"].tolist(), key="cc_read")
                row = idx[idx["Company"] == comp].iloc[0]
                tone = "up" if row["Call"] in ("BUY", "ACCUMULATE ON DIPS") or row["Verdict"] == "GOOD" else (
                    "down" if row["Call"] in ("AVOID", "SELL") or row["Verdict"] == "BAD" else "neutral")
                conf_val = row["Confidence"] or "—"
                conf_num = _conf_num(conf_val)
                conf_lbl = f"conf {conf_num:.0f}/10" if conf_num is not None else f"confidence: {conf_val.title()}"
                badges = "".join([
                    T.badge(row["Verdict"] or "—", tone) + " ",
                    T.badge(row["Call"] or "—", tone) + " ",
                    T.badge(conf_lbl, "neutral"),
                ])
                st.markdown(badges, unsafe_allow_html=True)

                sym = match_symbol(comp)
                if sym:
                    sc = S.stock_scorecard(
                        sym, bhav=load_per_date("bhavcopy_delivery"),
                        bulk=load_growing("bulk_deals"), block=load_growing("block_deals"),
                        ban=load_per_date("securities_in_ban"), vol=load_per_date("daily_volatility"),
                        pe=load_per_date("pe_ratio"), most_active=load_snapshot_latest("most_active_value"))
                    st.markdown(f"**Live signal for {sym}:** " +
                                T.badge(f"{sc['verdict']} ({sc['score']:+d})", sc["tone"]),
                                unsafe_allow_html=True)
                    st.caption("Fundamentals (concall) + technicals/flows (signal) — cross-check both.")
                st.markdown("---")
                st.markdown(concall_text(q, row["_file"]))

# ================================================================ Concall Peers
if PAGE == "🧬 Concall Peers":
    st.caption("Groups a quarter's concalls by NSE industry, then reads each peer's call "
               "verdict next to the numbers it actually reported for that quarter.")

    def _pc(v, suffix="%"):
        return "—" if pd.isna(v) else f"{v:+.1f}{suffix}"

    pqs = concall_quarters()
    if not pqs:
        _hint("No concall data — add MD files under concall-data/<quarter>/.")
    else:
        pq = st.selectbox("Quarter", list(reversed(pqs)), key="peer_q")
        peers = concall_peers(pq)
        if peers.empty:
            _hint(f"No concalls parsed for {pq}.")
        else:
            counts = peers["Industry"].value_counts()
            groups = [i for i in counts.index if i != "Unclassified" and counts[i] >= 2]
            tagged = int(peers["Industry"].ne("Unclassified").sum())
            if not groups:
                _hint("No industry has two or more tagged concalls this quarter — industry "
                      "tags come from corporate announcements, so coverage is partial.")
            else:
                med = peers[peers["Industry"].isin(groups)].groupby("Industry")["Rev YoY %"] \
                           .median().dropna().sort_values(ascending=False)
                if not med.empty:
                    with card():
                        st.markdown("#### Median revenue YoY % by industry")
                        st.caption(f"{int(peers['Rev YoY %'].notna().sum())} of {len(peers)} "
                                   f"peers in {pq} have a reported result to median.")
                        C.show(C.hbar(med, _DARK, diverge=True,
                                      height=max(220, len(med) * 28 + 60)))

                ind = st.selectbox("Industry", groups, key="peer_ind",
                                   format_func=lambda i: f"{i} ({counts[i]})")
                g = peers[peers["Industry"] == ind]
                # EBITDA margin on a bank means nothing — swap the column for lenders
                lender = ratio_family(ind) == "lender"
                bull = int(g["Call"].str.upper()
                           .str.contains("GOOD|BUY|ACCUMULATE", na=False).sum())
                priced = int(g["Rev YoY %"].notna().sum())
                st.markdown(T.stat_row([
                    T.stat_card("Peers on the call", f"{len(g)}", f"{ind} · {pq}", "neutral"),
                    T.stat_card("Bullish calls", f"{bull}/{len(g)}", "GOOD, BUY or accumulate",
                                "up" if bull * 2 >= len(g) else "neutral"),
                    T.stat_card("Median rev YoY", _pc(g["Rev YoY %"].median()),
                                f"{priced} of {len(g)} peers have a result", "neutral"),
                    T.stat_card("Median PAT YoY" if lender else "Median EBITDA margin",
                                _pc(g["PAT YoY %"].median() if lender else g["Margin %"].median()),
                                "reported for the quarter", "neutral"),
                ]), unsafe_allow_html=True)

                with card():
                    st.markdown(G.head(f"{ind} — what they said vs what they reported",
                                       "concall", "guidance", "ebitda_margin"),
                                unsafe_allow_html=True)
                    cols = ["Company", "Symbol", "Sub-industry", "Call", "Confidence",
                            "Result verdict", "Grade", "Rev YoY %", "PAT YoY %"]
                    if not lender:
                        cols[-1:-1] = ["Margin %", "Margin bps"]
                    gv = g[cols].sort_values("Rev YoY %", ascending=False, na_position="last")
                    top5 = gv.dropna(subset=["Rev YoY %"]).head(5)
                    if not top5.empty:
                        top5_rows = list(zip(top5["Symbol"], top5["Rev YoY %"]))
                        SNAP.record("concall_peers", top5_rows)
                        st.markdown(T.rank_boxes(top5_rows, "{:+.1f}", "%"), unsafe_allow_html=True)
                        _nav_row([s for s, _ in top5_rows], "peers")
                        _dropout_note("concall_peers", [s for s, _ in top5_rows])
                    st.dataframe(gv, width="stretch", height=360, hide_index=True)
                    st.caption(
                        f"{tagged} of {len(peers)} concalls this quarter carry an industry tag. "
                        "Tags come from corporate announcements, so a company that filed nothing "
                        "stays untagged and sits out of every peer group. Blank numbers mean no "
                        "analyzed result PDF for that company — run it on 📄 Result PDFs."
                        + (" Margin columns are dropped for lenders — EBITDA margin doesn't "
                           "apply to a bank's P&L." if lender else ""))

                with card():
                    st.markdown(G.head(f"Ratios {ind.lower()} is read on", "ebitda_margin", "pat"),
                                unsafe_allow_html=True)
                    st.markdown(
                        " ".join(T.badge(label, "neutral")
                                 for label, _ in industry_ratios(ind)),
                        unsafe_allow_html=True)
                    st.markdown("")
                    st.dataframe(ratio_hits(pq, ind, tuple(g["Company"])),
                                 width="stretch", height=300, hide_index=True)
                    st.caption(
                        "A ✓ means that ratio came up in the company's own concall highlights or "
                        "key monitorables. A blank means the analysis never recorded it — not "
                        "proof management stayed silent. Ratio set is fixed per industry family "
                        f"({ratio_family(ind)}), so peers are read on the same yardsticks.")

# ================================================================ Guidance Tracker
if PAGE == "📜 Guidance Tracker":
    st.caption("What management said last quarter (and same quarter last year, when available) "
               "next to what's on record now. Side-by-side — no auto-verdict, you judge.")

    def _gt_parse_q(label: str):
        import re as _re3
        m = _re3.match(r"Q(\d)FY(\d+)", label or "")
        return (int(m.group(1)), int(m.group(2))) if m else None

    def _gt_prev_q(label: str) -> str | None:
        p = _gt_parse_q(label)
        if not p:
            return None
        q, fy = p
        return f"Q4FY{fy - 1}" if q == 1 else f"Q{q - 1}FY{fy}"

    def _gt_yoy_q(label: str) -> str | None:
        p = _gt_parse_q(label)
        if not p:
            return None
        q, fy = p
        return f"Q{q}FY{fy - 1}"

    def _gt_highlights(quarter_label: str | None, key: str) -> list:
        if not quarter_label:
            return []
        for r in (concall_summary(quarter_label).get("concalls") or []):
            if _company_key(r.get("company") or "") == key:
                return r.get("highlights") or []
        return []

    cqs = concall_quarters()
    if not cqs:
        _hint("No concall data — add MD files under concall-data/<quarter>/.")
    else:
        cq = st.selectbox("Quarter", list(reversed(cqs)), key="gt_q")
        cur_idx = concall_index(cq)
        if cur_idx.empty:
            _hint(f"No concalls parsed for {cq}.")
        else:
            comp = st.selectbox("Company", sorted(cur_idx["Company"].unique()), key="gt_comp")
            cur_key = _company_key(comp)
            prev_label, yoy_label = _gt_prev_q(cq), _gt_yoy_q(cq)
            prev_available = bool(prev_label and prev_label in cqs)
            yoy_available = bool(yoy_label and yoy_label in cqs)

            st.markdown(T.stat_row([
                T.stat_card("This quarter", cq, "selected", "neutral"),
                T.stat_card("Last quarter", prev_label or "—",
                            "data found" if prev_available else "not collected",
                            "up" if prev_available else "neutral"),
                T.stat_card("Same qtr last year", yoy_label or "—",
                            "data found" if yoy_available else "not collected",
                            "up" if yoy_available else "neutral"),
            ]), unsafe_allow_html=True)

            cur_hl = _gt_highlights(cq, cur_key)
            prev_hl = _gt_highlights(prev_label, cur_key) if prev_available else []
            yoy_hl = _gt_highlights(yoy_label, cur_key) if yoy_available else []

            def _render_quarter(quarter_label: str, hl: list) -> None:
                if hl:
                    for h in hl:
                        pt = h.get("point") if isinstance(h, dict) else str(h)
                        sent = h.get("sentiment") if isinstance(h, dict) else None
                        icon = {"good": "🟢", "bad": "🔴"}.get(sent, "⚪")
                        st.markdown(f"{icon} {pt}")
                    return
                # older quarters' concalls-summary.json predates structured highlights —
                # fall back to verdict/call/confidence so the column isn't just blank
                pidx = concall_index(quarter_label)
                row = (pidx[pidx["Company"].map(_company_key) == cur_key]
                       if not pidx.empty else pd.DataFrame())
                if row.empty:
                    _hint("No highlights recorded.")
                    return
                r = row.iloc[0]
                st.markdown(T.badge(r["Verdict"] or "—", "neutral") + " " +
                            T.badge(r["Call"] or "—", "neutral") + " " +
                            T.badge(f"confidence {r['Confidence']}" if r["Confidence"] else "—",
                                    "neutral"), unsafe_allow_html=True)
                st.caption("No point-by-point highlights for this quarter — verdict/call only.")

            c1, c2, c3 = st.columns(3)
            with c1:
                with card():
                    st.markdown(f"#### 🕐 Said in {prev_label or 'last quarter'}")
                    if not prev_available:
                        _hint("Not available — no concall collected for that quarter.")
                    else:
                        _render_quarter(prev_label, prev_hl)
            with c2:
                with card():
                    st.markdown(f"#### 📅 Said in {yoy_label or 'same qtr last year'}")
                    if not yoy_available:
                        _hint("Not available — no concall collected for that quarter.")
                    else:
                        _render_quarter(yoy_label, yoy_hl)
            with c3:
                with card():
                    st.markdown(f"#### ✅ On record now — {cq}")
                    _render_quarter(cq, cur_hl)

            ridx = result_index(cq)
            ractual = pd.Series(dtype=object)
            if not ridx.empty:
                m = ridx[ridx["Company"].map(_company_key) == cur_key]
                if not m.empty:
                    ractual = m.iloc[0]

            with card():
                st.markdown(f"#### 📊 Actuals this quarter — {cq}")
                if ractual.empty:
                    _hint("No parsed result PDF for this company/quarter — "
                          "run it on 📄 Result PDFs to populate actuals.")
                else:
                    actuals = pd.DataFrame([
                        {"Metric": "Revenue (Cr)", "Current": ractual.get("Rev Cr"),
                         "YoY %": ractual.get("Rev YoY %"), "QoQ %": ractual.get("Rev QoQ %")},
                        {"Metric": "EBITDA (Cr)", "Current": ractual.get("EBITDA Cr"),
                         "YoY %": ractual.get("EBITDA YoY %"), "QoQ %": None},
                        {"Metric": "EBITDA Margin %", "Current": ractual.get("Margin %"),
                         "YoY %": None, "QoQ %": None},
                        {"Metric": "PAT (Cr)", "Current": ractual.get("PAT Cr"),
                         "YoY %": ractual.get("PAT YoY %"), "QoQ %": ractual.get("PAT QoQ %")},
                    ])
                    st.dataframe(
                        actuals.style.format({"Current": "{:,.1f}", "YoY %": "{:+.1f}",
                                              "QoQ %": "{:+.1f}"}, na_rep="—"),
                        width="stretch", hide_index=True)
                    st.caption("YoY/QoQ actuals from the parsed result filing — cross-check "
                               "against the guidance stated above.")

            sym = match_symbol(comp)
            if sym:
                _nav_row([sym], "guidance_tracker")

# ================================================================ Movers
if PAGE == "🗺️ Market Map":
    st.caption("Every listed NSE stock on one canvas. Tile size = liquidity, colour = "
               "the metric you pick. Built from the latest bhav copy, industries from "
               "corporate filings, valuation from the P/E report.")
    mm_dates = per_date_dates("bhavcopy_delivery")
    if not mm_dates:
        _hint("No bhav copy collected yet — fetch or backfill in ⚙️ Settings.")
    else:
        mm_date = st.selectbox("Trading date", list(reversed(mm_dates)), key="mm_date")
        mm = market_map(mm_date)
        if mm.empty:
            _hint("Bhav copy for that date has no EQ rows.")
        else:
            GROUPS = ["Industry", "Size tier", "Move band", "Delivery band"]
            SIZES = {"Turnover (₹cr)": "Turnover Cr", "Volume": "Volume",
                     "Trades": "Trades", "Equal weight": "_equal"}
            COLORS = {"% change": "%Chg", "Delivery %": "Delivery %",
                      "% from 52wk high": "% From High"}

            k1, k2, k3, k4 = st.columns(4)
            grp = k1.selectbox("Group by", GROUPS, key="mm_grp")
            size_lbl = k2.selectbox("Tile size", list(SIZES), key="mm_size")
            col_lbl = k3.selectbox("Colour by", list(COLORS), key="mm_col")
            topn = k4.slider("Max stocks", 50, 1500, 400, 50, key="mm_top",
                             help="Biggest by turnover. Fewer tiles read better.")
            sectors = sorted(s for s in mm["Industry"].unique() if s != "Unclassified")
            n_unc = int((mm["Industry"] == "Unclassified").sum())
            s1, s2 = st.columns([3, 1])
            sec_pick = s1.multiselect("Sectors", sectors, key="mm_sec",
                                      placeholder="all sectors — pick to narrow",
                                      help="Industry tags come from corporate filings, so "
                                           "coverage is partial.")
            inc_unc = s2.checkbox(f"Include unclassified ({n_unc:,})", value=True, key="mm_unc")
            f1, f2 = st.columns([1, 2])
            min_to = f1.slider("Min turnover (₹cr)", 0.0, 100.0, 1.0, 0.5, key="mm_minto")
            with f2:
                mq = search("mm_q", "Search", "symbol, company or industry")

            v = mm[mm["Turnover Cr"].fillna(0) >= min_to].copy()
            if sec_pick:
                keep_ind = set(sec_pick) | ({"Unclassified"} if inc_unc else set())
                v = v[v["Industry"].isin(keep_ind)]
            elif not inc_unc:
                v = v[v["Industry"] != "Unclassified"]
            v = apply_search(v, mq, ["Symbol", "Name", "Industry"])
            v = v.head(topn)
            v["_equal"] = 1.0
            size_col, col_col = SIZES[size_lbl], COLORS[col_lbl]
            # green/red pivots on zero for moves, on the neutral level for the others
            crange, cmid = {"%Chg": (5.0, 0.0), "Delivery %": (50.0, 50.0),
                            "% From High": (25.0, -15.0)}[col_col]

            if v.empty:
                _hint("Nothing left after the filters — widen the sectors, loosen turnover "
                      "or clear the search.")
            else:
                adv = int((v["%Chg"] > 0).sum())
                st.markdown(T.stat_row([
                    T.stat_card("Stocks on map", f"{len(v):,}", f"of {len(mm):,} EQ names", "neutral"),
                    T.stat_card("Advancing", f"{adv:,}", f"{adv / len(v) * 100:.0f}% green",
                                "up" if adv * 2 >= len(v) else "down", arrow=True),
                    T.stat_card("Median move", f'{v["%Chg"].median():+.2f}%', "typical stock", "neutral"),
                    T.stat_card("Turnover", f'₹{v["Turnover Cr"].sum():,.0f} cr', "on the map", "neutral"),
                ]), unsafe_allow_html=True)

                t1, t2, t3 = st.tabs(["🗺️ Treemap", "🟦 Blocks", "📋 Table"])
                with t1:
                    with card():
                        st.markdown(G.head(f"{col_lbl} by {grp.lower()}", "turnover", "delivery_pct"),
                                    unsafe_allow_html=True)
                        C.show(C.treemap(v, grp, "Symbol", size_col, col_col, _DARK,
                                         crange=crange, cmid=cmid, ctitle=col_lbl))
                        st.caption("Tile area = " + size_lbl.lower() +
                                   ". Parent tiles show the size-weighted group move.")
                with t2:
                    with card():
                        st.markdown(f"#### Every stock as a block — {col_lbl.lower()}")
                        C.show(C.heatgrid(v.sort_values(col_col, ascending=False),
                                          "Symbol", col_col, _DARK, crange=crange,
                                          cmid=cmid, ctitle=col_lbl,
                                          hover=["Name", "Industry", "Close", "%Chg",
                                                 "Delivery %", "Turnover Cr"]))
                        st.caption("Sorted best → worst, filled left-to-right, top-down.")
                with t3:
                    with card():
                        st.markdown("#### Map data")
                        show = v.drop(columns=["_equal"])
                        st.dataframe(
                            show.style.background_gradient(subset=["%Chg"], cmap="RdYlGn")
                                .format({"Close": "{:,.2f}", "%Chg": "{:+.2f}",
                                         "Delivery %": "{:.1f}", "Turnover Cr": "{:,.1f}",
                                         "Volume": "{:,.0f}", "Trades": "{:,.0f}",
                                         "P/E": "{:.1f}", "% From High": "{:+.1f}"}, na_rep="-"),
                            width="stretch", height=520, hide_index=True)

                with card():
                    st.markdown("#### Group leaderboard")
                    lb = (v.groupby(grp)
                            .agg(Stocks=("Symbol", "size"),
                                 **{"Turnover Cr": ("Turnover Cr", "sum"),
                                    "Avg %Chg": ("%Chg", "mean"),
                                    "Advancing": ("%Chg", lambda s: int((s > 0).sum()))})
                            .reset_index().sort_values("Avg %Chg", ascending=False))
                    lb["Breadth %"] = lb["Advancing"] / lb["Stocks"] * 100
                    st.dataframe(
                        lb.style.background_gradient(subset=["Avg %Chg", "Breadth %"], cmap="RdYlGn")
                          .format({"Turnover Cr": "{:,.0f}", "Avg %Chg": "{:+.2f}",
                                   "Breadth %": "{:.0f}"}, na_rep="-"),
                        width="stretch", height=340, hide_index=True)
                on_map_unc = int((v["Industry"] == "Unclassified").sum())
                st.caption(
                    f"Bhav copy {mm_date} · "
                    f"{len(sec_pick) or len(sectors)} sector(s) selected · "
                    f"{on_map_unc:,} unclassified name(s) on the map. "
                    f"Across the full universe {(mm['Industry'] != 'Unclassified').sum():,} of "
                    f"{len(mm):,} names carry an industry tag (sourced from corporate filings) — "
                    "untagged names sit in the Unclassified bucket, never dropped silently.")

# ================================================================ Movers
if PAGE == "🚀 Movers":
    g, l = load_snapshot_latest("top_gainers"), load_snapshot_latest("top_losers")
    legends = sorted(set(g.get("legend", pd.Series(dtype=str)).dropna().unique())
                     | set(l.get("legend", pd.Series(dtype=str)).dropna().unique()))
    default = ["allSec"] + [x for x in legends if x != "allSec"] if "allSec" in legends else legends or ["(none)"]
    mv1, mv2 = st.columns([1, 2])
    bucket = mv1.selectbox("Index bucket", default)
    with mv2:
        mv_q = search("mv_q", "Search", "symbol — filters every table below")

    def _movers(df):
        if df.empty:
            return df
        df = _num(df, ["ltp", "net_price", "perChange", "turnover"])
        if "legend" in df.columns and bucket in df["legend"].values:
            df = df[df["legend"] == bucket]
        keep = [c for c in ["symbol", "ltp", "net_price", "perChange", "trade_quantity", "turnover"] if c in df.columns]
        return apply_search(df[keep], mv_q, ["symbol"]).sort_values(
            "perChange", ascending=False, na_position="last")

    mc1, mc2 = st.columns(2)
    with mc1:
        with card():
            st.markdown("#### 🟢 Top gainers")
            gg = _movers(g)
            if gg.empty:
                _hint(f"No gainer matches “{mv_q}”." if mv_q else
                      "No data yet — run the collector to populate this.")
            else:
                top5_rows = list(zip(gg["symbol"].head(5), gg["perChange"].head(5)))
                SNAP.record("movers_gainers", top5_rows)
                st.markdown(T.rank_boxes(top5_rows, "{:+.2f}", "%"), unsafe_allow_html=True)
                _nav_row([s for s, _ in top5_rows], "movers")
                _dropout_note("movers_gainers", [s for s, _ in top5_rows])
                C.show(C.hbar(gg.set_index("symbol")["perChange"].head(10), _DARK,
                              color=T.GREEN, height=280))
                st.dataframe(gg, width="stretch", height=360, hide_index=True)
    with mc2:
        with card():
            st.markdown("#### 🔴 Top losers")
            ll = _movers(l)
            if ll.empty:
                _hint(f"No loser matches “{mv_q}”." if mv_q else
                      "No data yet — run the collector to populate this.")
            else:
                ls = ll.sort_values("perChange")
                C.show(C.hbar(ls.set_index("symbol")["perChange"].head(10), _DARK,
                              color=T.CORAL, height=280))
                st.dataframe(ls, width="stretch", height=360, hide_index=True)

    a1, a2 = st.columns(2)
    for col, (label, name) in zip((a1, a2), [("By value", "most_active_value"), ("By volume", "most_active_volume")]):
        with col:
            with card():
                st.markdown(f"#### Most active — {label.lower()}")
                df = load_snapshot_latest(name)
                if df.empty:
                    _hint(); continue
                df = _num(df, ["lastPrice", "pChange", "totalTradedValue", "totalTradedVolume"])
                keep = [c for c in ["symbol", "lastPrice", "pChange", "totalTradedVolume", "totalTradedValue"] if c in df.columns]
                ma = apply_search(df[keep], mv_q, ["symbol"])
                mcol = "totalTradedValue" if name.endswith("value") else "totalTradedVolume"
                if mcol in ma.columns and ma[mcol].notna().any():
                    C.show(C.hbar(ma.set_index("symbol")[mcol].nlargest(10), _DARK,
                                  color=T.INDIGO, height=260))
                st.dataframe(ma, width="stretch", height=300, hide_index=True)

# ================================================================ Smart Money
if PAGE == "💰 Smart Money":
    with card():
        st.markdown(G.head("FII / DII — cash market (₹ Cr)", "fii", "dii"), unsafe_allow_html=True)
        fd = load_snapshot_latest("fii_dii_activity")
        if not fd.empty and {"category", "buyValue", "sellValue", "netValue"} <= set(fd.columns):
            fd = _num(fd, ["buyValue", "sellValue", "netValue"])
            cards = []
            for _, r in fd.iterrows():
                net = r["netValue"]
                cards.append(T.stat_card(r["category"], f"₹{net:+,.0f} Cr", "net",
                                         "up" if net >= 0 else "down", arrow=True))
            st.markdown(T.stat_row(cards), unsafe_allow_html=True)
            st.dataframe(fd[["category", "date", "buyValue", "sellValue", "netValue"]]
                         .rename(columns={"buyValue": "Buy (Cr)", "sellValue": "Sell (Cr)",
                                           "netValue": "Net (Cr)", "category": "Category", "date": "Date"}),
                         width="stretch", hide_index=True)
        else:
            _hint("Needs a daily/snapshot run to populate fii_dii_activity.")

    for label, name in [("Bulk deals", "bulk_deals"), ("Block deals", "block_deals")]:
        with card():
            st.markdown(f"#### {label} — who's trading big")
            df = load_growing(name)
            if df.empty:
                _hint("No deals in the collected window."); continue
            df = _num(df, ["QuantityTraded", "TradePrice/Wght.Avg.Price"])
            colf1, colf2 = st.columns([1, 2])
            side = colf1.selectbox("Side", ["All", "BUY", "SELL"], key=f"side_{name}")
            sym = colf2.text_input("Filter symbol contains", key=f"sym_{name}").upper()
            v = df.copy()
            if side != "All" and "Buy/Sell" in v.columns:
                v = v[v["Buy/Sell"].astype(str).str.upper().str.startswith(side[0])]
            if sym and "Symbol" in v.columns:
                v = v[v["Symbol"].astype(str).str.upper().str.contains(sym)]
            if {"QuantityTraded", "TradePrice/Wght.Avg.Price"} <= set(v.columns):
                v["Value(Cr)"] = (v["QuantityTraded"] * v["TradePrice/Wght.Avg.Price"]) / 1e7
                top5 = v.sort_values("Value(Cr)", ascending=False).head(5)
                if "Symbol" in top5.columns and not top5.empty:
                    top5_rows = list(zip(top5["Symbol"], top5["Value(Cr)"]))
                    SNAP.record(f"smart_money_{name}", top5_rows)
                    st.markdown(T.rank_boxes(top5_rows, "₹{:,.1f}", " Cr"), unsafe_allow_html=True)
                    _nav_row([s for s, _ in top5_rows], f"sm_{name}")
                    _dropout_note(f"smart_money_{name}", [s for s, _ in top5_rows])
            st.dataframe(v, width="stretch", height=300, hide_index=True)

    s1, s2 = st.columns(2)
    with s1:
        with card():
            st.markdown(G.head("Short selling", "short_selling"), unsafe_allow_html=True)
            ss = load_growing("short_selling")
            if ss.empty:
                _hint()
            else:
                ss = searched(_num(ss, ["Quantity"]), "ss_q", label="Search")
                st.dataframe(ss, width="stretch", height=280, hide_index=True)
    with s2:
        with card():
            st.markdown(G.head("Upcoming corporate actions", "corporate_action", "ex_date"), unsafe_allow_html=True)
            ca = load_growing("corporate_actions")
            if not ca.empty and "exDate" in ca.columns:
                ca = ca.copy()
                ca["_ex"] = pd.to_datetime(ca["exDate"], errors="coerce", dayfirst=True)
                upcoming = ca[ca["_ex"] >= pd.Timestamp.today().normalize()].sort_values("_ex")
                keep = [c for c in ["symbol", "series", "subject", "exDate", "recDate", "faceVal"] if c in ca.columns]
                cav = (upcoming[keep] if not upcoming.empty else ca[keep])
                cav = searched(cav, "ca_q", ["symbol", "subject"], "Search",
                               "symbol or subject (dividend, split…)")
                st.dataframe(cav, width="stretch", height=280, hide_index=True)
                if upcoming.empty:
                    st.caption("No ex-dates ahead in the window; showing all.")
            else:
                _hint()

# ================================================================ Derivatives & FII
if PAGE == "📉 Derivatives & FII":
    with card():
        st.markdown(G.head("Participant positioning — net index futures (long − short)", "participant_oi", "oi"), unsafe_allow_html=True)
        st.caption("Positive = net long / bullish. Watch FII vs Client divergence.")
        poi = load_per_date("participant_oi")
        if not poi.empty and "Client Type" in poi.columns:
            p = _num(poi, ["Future Index Long", "Future Index Short",
                           "Total Long Contracts", "Total Short Contracts"])
            p = p[p["Client Type"].astype(str).str.upper() != "TOTAL"]
            p["Net Index Fut"] = p["Future Index Long"] - p["Future Index Short"]
            C.show(C.hbar(p.set_index("Client Type")["Net Index Fut"], _DARK, diverge=True))
            st.dataframe(p[["Client Type", "Future Index Long", "Future Index Short",
                            "Net Index Fut", "Total Long Contracts", "Total Short Contracts"]],
                         width="stretch", hide_index=True)
        else:
            _hint()

    with card():
        st.markdown(G.head("FII derivatives — net stance (₹ Cr)", "fii", "oi"), unsafe_allow_html=True)
        fii = load_per_date("fii_deriv_stats")
        if not fii.empty and "fii_derivatives" in fii.columns:
            f = _num(fii, ["buy_value_in_Cr", "sell_value_in_Cr", "open_contracts_value_in_Cr"])
            f["Net Buy (Cr)"] = f["buy_value_in_Cr"] - f["sell_value_in_Cr"]
            C.show(C.hbar(f.set_index("fii_derivatives")["Net Buy (Cr)"], _DARK, diverge=True))
            st.dataframe(f[["fii_derivatives", "buy_value_in_Cr", "sell_value_in_Cr",
                            "Net Buy (Cr)", "open_contracts_value_in_Cr"]],
                         width="stretch", hide_index=True)
        else:
            _hint("FII stats need xlrd + the report published for the date.")

    d1, d2 = st.columns(2)
    with d1:
        with card():
            st.markdown(G.head("Most active underlying", "oi", "fno"), unsafe_allow_html=True)
            mau = load_snapshot_latest("most_active_underlying")
            if not mau.empty:
                mau = _num(mau, ["totTurnover", "latestOI", "totVolume"])
                keep = [c for c in ["symbol", "totVolume", "totTurnover", "latestOI"] if c in mau.columns]
                mauv = mau[keep].sort_values("totTurnover", ascending=False)
                top5_rows = list(zip(mauv["symbol"].head(5), mauv["totTurnover"].head(5)))
                SNAP.record("derivatives_active", top5_rows)
                st.markdown(T.rank_boxes(top5_rows, "₹{:,.0f}", " Cr"), unsafe_allow_html=True)
                _nav_row([s for s, _ in top5_rows], "deriv")
                _dropout_note("derivatives_active", [s for s, _ in top5_rows])
                st.dataframe(mauv, width="stretch", height=300, hide_index=True)
            else:
                _hint()
    with d2:
        with card():
            st.markdown(G.head("Securities in F&O ban", "ban_list", "fno"), unsafe_allow_html=True)
            ban = load_per_date("securities_in_ban")
            if not ban.empty:
                col = "value" if "value" in ban.columns else ban.columns[0]
                st.metric("In ban", len(ban))
                st.dataframe(ban.rename(columns={col: "Symbol"}), width="stretch",
                             height=230, hide_index=True)
            else:
                st.success("No securities in ban (or not collected).")

# ================================================================ Delivery & Value
if PAGE == "📦 Delivery & Value":
    with card():
        st.markdown(G.head("Delivery analysis — conviction accumulation", "delivery_pct", "accumulation"), unsafe_allow_html=True)
        st.caption("High delivery % = buyers taking delivery, not intraday churn. "
                   "High delivery + price up often signals genuine accumulation.")
        bhav = load_per_date("bhavcopy_delivery")
        if not bhav.empty:
            b = bhav.copy()
            if "SERIES" in b.columns:
                b = b[b["SERIES"] == "EQ"]
            b = _num(b, ["CLOSE_PRICE", "PREV_CLOSE", "DELIV_PER", "TTL_TRD_QNTY",
                         "DELIV_QTY", "TURNOVER_LACS"])
            b["%Chg"] = (b["CLOSE_PRICE"] - b["PREV_CLOSE"]) / b["PREV_CLOSE"] * 100
            dv1, dv2 = st.columns([2, 1])
            min_to = dv1.slider("Min turnover (₹ lacs)", 0, 5000, 500, 100)
            with dv2:
                dv_q = search("dv_q", "Search", "symbol")
            b = b[b["TURNOVER_LACS"] >= min_to]
            keep = [c for c in ["SYMBOL", "CLOSE_PRICE", "%Chg", "DELIV_PER", "TTL_TRD_QNTY",
                                "DELIV_QTY", "TURNOVER_LACS"] if c in b.columns]
            scat = apply_search(b, dv_q, ["SYMBOL"])
            if not scat.dropna(subset=["DELIV_PER", "%Chg"]).empty:
                st.caption("Top-right quadrant = price up on high delivery — accumulation.")
                C.show(C.scatter(scat, "DELIV_PER", "%Chg", "SYMBOL", _DARK,
                                 color="%Chg", size="TURNOVER_LACS", height=400,
                                 xtitle="Delivery %", ytitle="% change",
                                 vline=50, hline=0))
            top = apply_search(b, dv_q, ["SYMBOL"]).sort_values(
                "DELIV_PER", ascending=False)[keep].head(50)
            top5_rows = list(zip(top["SYMBOL"].head(5), top["DELIV_PER"].head(5)))
            SNAP.record("delivery_value", top5_rows)
            st.markdown(T.rank_boxes(top5_rows, "{:.0f}", "%"), unsafe_allow_html=True)
            _nav_row([s for s, _ in top5_rows], "delivery")
            _dropout_note("delivery_value", [s for s, _ in top5_rows])
            st.dataframe(
                top.style.background_gradient(subset=["DELIV_PER"], cmap="Greens")
                         .background_gradient(subset=["%Chg"], cmap="RdYlGn")
                         .format({"CLOSE_PRICE": "{:,.2f}", "%Chg": "{:+.2f}",
                                  "DELIV_PER": "{:.1f}", "TURNOVER_LACS": "{:,.0f}"}, na_rep="-"),
                width="stretch", height=430, hide_index=True)
            st.caption(f"Bhav copy date: {per_date_dates('bhavcopy_delivery')[-1]}")
        else:
            _hint("Bhav copy not collected yet (published after market close).")

    cV1, cV2 = st.columns(2)
    with cV1:
        with card():
            st.markdown(G.head("P/E lookup", "pe"), unsafe_allow_html=True)
            pe = load_per_date("pe_ratio")
            if not pe.empty:
                q = symbol_select("Symbol", key="pe_sym")
                col = "SYMBOL" if "SYMBOL" in pe.columns else pe.columns[0]
                show = pe[pe[col].astype(str).str.upper() == q] if q else pe.head(30)
                st.dataframe(show, width="stretch", height=300, hide_index=True)
            else:
                _hint()
    with cV2:
        with card():
            st.markdown(G.head("Highest volatility (F&O underlyings)", "daily_volatility", "var_margin"), unsafe_allow_html=True)
            vol = load_per_date("daily_volatility")
            if not vol.empty:
                vcol = next((c for c in vol.columns if "Annualised" in c), None)
                scol = "Symbol" if "Symbol" in vol.columns else vol.columns[1]
                if vcol:
                    v = _num(vol, [vcol]).sort_values(vcol, ascending=False)
                    st.dataframe(v[[scol, vcol]].head(30).rename(columns={vcol: "Annualised Vol"}),
                                 width="stretch", height=300, hide_index=True)
                else:
                    st.dataframe(vol.head(30), width="stretch", height=300, hide_index=True)
            else:
                _hint()

# ================================================================ Sectors
if PAGE == "🧭 Sectors":
    st.caption("Sector rotation — where money is moving. Sector indices ranked by "
               "today's move and 30d / 365d trend.")
    idx = load_snapshot_latest("all_indices")
    if idx.empty:
        _hint("Fetch latest (sidebar) to load index data.")
    else:
        idx = _num(idx, ["percentChange", "perChange30d", "perChange365d", "pe", "pb", "dy"])
        if "key" in idx.columns and idx["key"].astype(str).str.contains("Sector", case=False).any():
            sec = idx[idx["key"].astype(str).str.contains("Sector", case=False)].copy()
        else:
            kw = "IT|BANK|PHARMA|AUTO|FMCG|METAL|ENERGY|REALTY|MEDIA|FINANC|HEALTH|PSU|CONSUM|INFRA|OIL|CHEM"
            sec = idx[idx["index"].astype(str).str.upper().str.contains(kw)].copy()
        sec = sec.dropna(subset=["percentChange"]).sort_values("percentChange", ascending=False)
        if sec.empty:
            _hint("No sector indices in the collected snapshot.")
        else:
            up = sec.iloc[0]; dn = sec.iloc[-1]
            st.markdown(T.stat_row([
                T.stat_card("Leading sector", str(up["index"]), f'{up["percentChange"]:+.2f}%', "up", arrow=True),
                T.stat_card("Lagging sector", str(dn["index"]), f'{dn["percentChange"]:+.2f}%', "down", arrow=True),
                T.stat_card("Sectors up", f'{int((sec["percentChange"]>0).sum())}/{len(sec)}', "green today", "neutral"),
            ]), unsafe_allow_html=True)
            with card():
                st.markdown("#### Today's sector move")
                C.show(C.hbar(sec.set_index("index")["percentChange"], _DARK, diverge=True))
            with card():
                st.markdown(G.head("Sector trend table (today / 30d / 365d + valuation)", "pe", "market_breadth"), unsafe_allow_html=True)
                v = sec[["index", "percentChange", "perChange30d", "perChange365d", "pe", "pb", "dy"]].copy()
                v.columns = ["Sector", "%Chg", "%Chg 30d", "%Chg 365d", "P/E", "P/B", "Div Yld"]
                v = searched(v, "sec_q", ["Sector"], "Search", "sector name")
                st.dataframe(
                    v.style.background_gradient(subset=["%Chg", "%Chg 30d", "%Chg 365d"], cmap="RdYlGn")
                     .format({"%Chg": "{:+.2f}", "%Chg 30d": "{:+.2f}", "%Chg 365d": "{:+.2f}",
                              "P/E": "{:.1f}", "P/B": "{:.2f}", "Div Yld": "{:.2f}"}, na_rep="-"),
                    width="stretch", height=460, hide_index=True)

# ================================================================ Filings
if PAGE == "🗂️ Filings":
    st.caption("Corporate filings & disclosures scraped from NSE (board meetings, "
               "results, announcements) + corporate actions (dividends, splits).")
    with card():
        st.markdown(G.head("Corporate announcements", "corporate_action"), unsafe_allow_html=True)
        ann = load_growing("corporate_announcements")
        if ann.empty:
            _hint("Not collected yet — use the sidebar Fetch/Backfill (it's part of the daily job).")
        else:
            c1, c2 = st.columns([2, 1])
            qa = c1.text_input("Search company / symbol / subject", key="fil_q").upper()
            inds = ["All"] + sorted(ann["Industry"].dropna().astype(str).unique()) if "Industry" in ann.columns else ["All"]
            indf = c2.selectbox("Industry", inds, key="fil_ind")
            v = ann.copy()
            if qa:
                hay = v.astype(str).apply(lambda r: " ".join(r).upper(), axis=1)
                v = v[hay.str.contains(qa)]
            if indf != "All" and "Industry" in v.columns:
                v = v[v["Industry"] == indf]
            if "sort_date" in v.columns:
                per_day = pd.to_datetime(v["sort_date"], errors="coerce").dt.date \
                            .value_counts().sort_index().tail(90)
                if len(per_day) > 1:
                    st.caption("Filings per day — last 90 days with activity.")
                    C.show(C.lines(per_day, _DARK, area=True, height=240))
            show = [c for c in ["Filed", "symbol", "Company", "Subject", "Industry", "Attachment"] if c in v.columns]
            st.dataframe(v[show].head(300), width="stretch", height=430, hide_index=True,
                         column_config={"Attachment": st.column_config.LinkColumn("Attachment")})
            st.caption(f"{len(v)} filings (showing up to 300).")

    with card():
        st.markdown(G.head("📅 Earnings / events calendar", "concall", "guidance"), unsafe_allow_html=True)
        ec = load_growing("earnings_calendar")
        if ec.empty:
            _hint("Not collected yet — sidebar Fetch/Backfill (part of the daily job).")
        else:
            qe = st.text_input("Search company / symbol / purpose", key="ec_q").upper()
            v = ec.copy()
            if qe:
                hay = v.astype(str).apply(lambda r: " ".join(r).upper(), axis=1)
                v = v[hay.str.contains(qe)]
            st.dataframe(v.head(300), width="stretch", height=360, hide_index=True)
            st.caption(f"{len(v)} events (showing up to 300).")

    with card():
        st.markdown(G.head("Corporate actions (dividends / splits / bonus)", "corporate_action", "ex_date", "record_date", "bonus", "split"), unsafe_allow_html=True)
        ca = load_growing("corporate_actions")
        if ca.empty:
            _hint()
        else:
            keep = [c for c in ["symbol", "comp", "series", "subject", "exDate", "recDate", "faceVal"] if c in ca.columns]
            st.dataframe(ca[keep] if keep else ca, width="stretch", height=320, hide_index=True)

# ================================================================ Need Attention
if PAGE == "🔔 Need Attention":
    st.caption("High-impact corporate events — demergers, buybacks, spin-offs, "
               "mergers, delistings, open offers, fundraises — flagged from filings.")
    _EVENTS = {
        "Buyback": r"buy[\s-]?back",
        "Demerger": r"de[\s-]?merger",
        "Merger / Amalgamation": r"amalgamat|scheme of arrangement|\bmerger\b",
        "Acquisition / Stake": r"acquisit|acquire|\bstake\b",
        "Delisting": r"delist",
        "Open offer": r"open offer",
        "Rights issue": r"rights issue",
    }
    ann = load_growing("corporate_announcements")
    if ann.empty:
        _hint("Collect corporate_announcements first (sidebar Fetch/Backfill).")
    else:
        text_cols = [c for c in ["Subject", "Details", "Company", "symbol"] if c in ann.columns]
        hay = ann[text_cols].astype(str).apply(lambda r: " ".join(r), axis=1).str.lower()
        import re as _re
        tags = []
        for _, blob in hay.items():
            hit = [name for name, pat in _EVENTS.items() if _re.search(pat, blob)]
            tags.append(hit[0] if hit else None)
        ann = ann.assign(Event=tags)
        flagged = ann[ann["Event"].notna()].copy()

        counts = flagged["Event"].value_counts()
        cards = [T.stat_card("Flagged", f"{len(flagged)}", "events need attention",
                             "down" if len(flagged) else "neutral", arrow=bool(len(flagged)))]
        for ev in ["Buyback", "Demerger", "Merger / Amalgamation", "Delisting"]:
            cards.append(T.stat_card(ev, f"{int(counts.get(ev, 0))}", "filings", "neutral"))
        st.markdown(T.stat_row(cards), unsafe_allow_html=True)

        if not counts.empty:
            with card():
                st.markdown("#### Flagged events by type")
                C.show(C.hbar(counts, _DARK, color=T.INDIGO,
                              height=max(200, len(counts) * 34 + 60)))

        with card():
            st.markdown("#### Flagged events")
            na1, na2 = st.columns([1, 2])
            evf = na1.selectbox("Event type", ["All"] + list(_EVENTS.keys()), key="na_ev")
            with na2:
                na_q = search("na_q", "Search", "symbol, company or subject")
            v = flagged if evf == "All" else flagged[flagged["Event"] == evf]
            v = apply_search(v, na_q, ["symbol", "Company", "Subject"])
            show = [c for c in ["Filed", "Event", "symbol", "Company", "Subject", "Attachment"] if c in v.columns]
            if v.empty:
                st.success("No such events in the collected window.")
            else:
                if "Filed" in v.columns and "symbol" in v.columns:
                    recent = v.sort_values("Filed", ascending=False).head(5)
                    st.markdown(T.rank_boxes(
                        [(r["symbol"], r.get("Event", "—"), r.get("Filed", ""))
                         for _, r in recent.iterrows()]), unsafe_allow_html=True)
                    _nav_row(recent["symbol"].tolist(), "needattn")
                st.dataframe(v[show], width="stretch", height=460, hide_index=True,
                             column_config={"Attachment": st.column_config.LinkColumn("Attachment")})
                st.caption(f"{len(v)} events.")

# ================================================================ History
if PAGE == "📈 History":
    st.caption("Price / volume / delivery history built from the daily bhav copies "
               "you've collected. Backfill more dates (sidebar) to extend it.")
    exch = st.radio("Source", ["NSE stock", "BSE stock", "NSE index"],
                    horizontal=True, key="hist_exch")

    if exch == "NSE index":
        inames = index_names()
        hsym = st.selectbox("Index", inames, key="hist_idx")
        cfa, cfb = st.columns([1, 3])
        with cfa:
            if st.button("↻ Fetch/refresh history", key="idx_fetch", width="stretch"):
                from nse_collector.index_history import fetch_and_store
                from nse_collector.config import Settings
                s = Settings(); s.data_dir = L.DATA_DIR
                earliest = dt.date.today() - dt.timedelta(days=365)
                with st.spinner(f"Fetching {hsym} EOD history…"):
                    n = fetch_and_store(hsym, earliest, dt.date.today(), s)
                st.success(f"{hsym}: {n} days stored")
                st.cache_data.clear()
        h = index_history(hsym) if hsym else pd.DataFrame()
        is_bse = False
        if h.empty:
            _hint("No stored history — click Fetch/refresh above.")
    else:
        is_bse = exch == "BSE stock"
        if is_bse:
            bsyms = bse_symbols()
            hsym = (st.selectbox("Symbol", [""] + bsyms, key="hist_sym_bse")
                    if bsyms else st.text_input("Symbol", key="hist_sym_bse_txt")).strip().upper()
        else:
            hsym = symbol_select("Symbol", key="hist_sym")
        h = (bse_symbol_history(hsym) if is_bse else symbol_history(hsym)) if hsym else pd.DataFrame()

    if hsym:
        if h.empty:
            if exch != "NSE index":
                _hint("No history yet — backfill dates in the sidebar.")
        else:
            last = h.iloc[-1]
            has_deliv = "DELIV_PER" in h.columns and pd.notna(last.get("DELIV_PER"))
            scards = [
                T.stat_card("Close", f'{last["CLOSE_PRICE"]:,.2f}', f'{hsym} ({exch})',
                            "up" if last["%Chg"] >= 0 else "down", arrow=True),
                T.stat_card("Day %", f'{last["%Chg"]:+.2f}%', "vs prev close",
                            "up" if last["%Chg"] >= 0 else "down"),
            ]
            if has_deliv:
                scards.append(T.stat_card("Delivery", f'{last["DELIV_PER"]:.0f}%',
                                          "of traded qty", "neutral"))
            scards.append(T.stat_card("Days", f'{len(h)}', "collected", "neutral"))
            st.markdown(T.stat_row(scards), unsafe_allow_html=True)

            with card():
                st.markdown(G.head("Price (OHLC candlestick)", "ltp", "gap_up"), unsafe_allow_html=True)
                if len(h) >= 1 and {"OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE"} <= set(h.columns):
                    recs = h[["date", "OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE"]].rename(
                        columns={"OPEN_PRICE": "open", "HIGH_PRICE": "high",
                                 "LOW_PRICE": "low", "CLOSE_PRICE": "close"})
                    C.show(C.candlestick(recs, _DARK))

            if exch == "NSE index":
                nh = niftyindices_history(hsym)
                if not nh.empty and {"PE", "PB", "DIV_YIELD"} <= set(nh.columns):
                    with card():
                        st.markdown(G.head("Valuation trend — P/E, P/B, Div Yield", "pe"),
                                    unsafe_allow_html=True)
                        st.caption("Source: niftyindices.com daily snapshot — not archived "
                                   "anywhere else for most index families.")
                        vcol1, vcol2 = st.columns(2)
                        with vcol1:
                            C.show(C.lines(nh.set_index("date")[["PE", "PB"]], _DARK))
                        with vcol2:
                            C.show(C.lines(nh.set_index("date")["DIV_YIELD"], _DARK, colors=[T.GREEN], area=True))

            cH1, cH2 = st.columns(2)
            with cH1:
                with card():
                    st.markdown(G.head("Volume traded", "volume"), unsafe_allow_html=True)
                    C.show(C.bars(h.set_index("date")["TTL_TRD_QNTY"], _DARK))
            with cH2:
                with card():
                    if has_deliv:
                        st.markdown(G.head("Delivery % trend", "delivery_pct"), unsafe_allow_html=True)
                        C.show(C.lines(h.set_index("date")["DELIV_PER"], _DARK, colors=[T.GREEN], area=True))
                    else:
                        st.markdown("#### Close price trend")
                        C.show(C.lines(h.set_index("date")["CLOSE_PRICE"], _DARK, colors=[T.GREEN], area=True))
    else:
        st.info("Search a symbol to see its history.")

# ================================================================ Darvas & Fib
if PAGE == "📐 Darvas & Fib":
    st.caption("Darvas boxes and Fibonacci retracement on daily OHLC. A box is a "
               "consolidation range — ceiling confirmed by bars that fail to clear it, "
               "floor by bars that fail to break it. Levels are drawn off the swing in "
               "the chosen window.")

    dsym = symbol_select("Symbol", key="df_sym")
    dh = symbol_history(dsym) if dsym else pd.DataFrame()
    if not dsym:
        _hint("Pick a symbol.")
    elif dh.empty:
        _hint("No history for this symbol — backfill bhav copies in the sidebar.")
    elif len(dh) < 60:
        _hint(f"Only {len(dh)} bars collected for {dsym} — needs 60 to place a box or a swing. "
              f"Backfill more bhav copies in the sidebar.")
    else:
        raw_n = len(dh)
        dh = TA.one_bar_per_day(dh)
        dh, events = TA.back_adjust(dh)
        if raw_n > len(dh):
            st.caption(f"{raw_n - len(dh)} duplicate day"
                       f"{'s' if raw_n - len(dh) > 1 else ''} dropped — {dsym} traded in "
                       f"two series on the same date.")
        if events:
            st.warning(f"{dsym} has {len(events)} split/bonus adjustment"
                       f"{'s' if len(events) > 1 else ''} in this window "
                       f"({', '.join(str(e['date']) for e in events)}). Prices are "
                       f"back-adjusted so the levels below are continuous.")

        n_bars = len(dh)
        o1, o2, o3, o4 = st.columns(4)
        confirm = o1.slider("Box confirmation bars", 1, 10, 3, 1, key="df_confirm")
        hi_look = o2.slider("New-high window (bars)", 10, max(20, n_bars // 2),
                            min(52, max(20, n_bars // 2)), 2, key="df_look")
        fib_look = o3.slider("Fib swing window (bars)", 20, n_bars,
                             min(120, n_bars), 10, key="df_fib")
        bars_n = o4.slider("Bars to show", 30, n_bars, n_bars, 10, key="df_bars")

        view = dh.tail(bars_n)
        boxes = [b for b in TA.darvas_boxes(dh, confirm=confirm, lookback=hi_look)
                 if b["end"] >= view["date"].iat[0]]
        fib = TA.fib_levels(dh, lookback=fib_look)

        s1, s2 = st.columns(2)
        show_box = s1.checkbox("Show Darvas boxes", True, key="df_showbox")
        show_fib = s2.checkbox("Show Fibonacci levels", True, key="df_showfib")

        last_close = view["CLOSE_PRICE"].iat[-1]
        live = next((b for b in reversed(boxes) if b["exit"] == "open"), None)
        st.markdown(T.stat_row([
            T.stat_card("Last close", f"{last_close:,.2f}", str(view["date"].iat[-1]), "neutral"),
            T.stat_card("Boxes in view", f"{len(boxes)}",
                        f"{sum(1 for b in boxes if b['exit'] == 'breakout')} broke out, "
                        f"{sum(1 for b in boxes if b['exit'] == 'breakdown')} broke down",
                        "neutral"),
            T.stat_card("Live box", f"{live['bottom']:,.2f}–{live['top']:,.2f}" if live else "—",
                        "floor–ceiling, unresolved" if live else "no open box",
                        "up" if live else "neutral"),
            T.stat_card("Swing", f"{fib['low']:,.2f}→{fib['high']:,.2f}" if fib else "—",
                        ("leg up, retracing down" if fib["up"] else "leg down, retracing up")
                        if fib else "no range in window", "neutral"),
        ]), unsafe_allow_html=True)

        with card():
            st.markdown(G.head("Price with boxes and levels", "ltp", "gap_up"),
                        unsafe_allow_html=True)
            recs = view[["date", "OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE"]].rename(
                columns={"OPEN_PRICE": "open", "HIGH_PRICE": "high",
                         "LOW_PRICE": "low", "CLOSE_PRICE": "close"})
            C.show(C.candlestick(recs, _DARK, height=520,
                                 boxes=boxes if show_box else None,
                                 levels=(fib.get("levels") if fib and show_fib else None)))
            if show_box and not boxes:
                st.caption(f"No box formed — no bar set a {hi_look}-bar high that then held "
                           f"for {confirm} bars. Widen the window or loosen confirmation.")

        db1, db2 = st.columns(2)
        with db1:
            with card():
                st.markdown("#### Boxes")
                if not boxes:
                    _hint("No boxes with these settings.")
                else:
                    bt = pd.DataFrame(boxes)
                    bt["height %"] = (bt["top"] - bt["bottom"]) / bt["bottom"] * 100
                    st.dataframe(
                        bt[["start", "end", "bottom", "top", "height %", "exit"]]
                          .sort_values("start", ascending=False)
                          .style.format({"bottom": "{:,.2f}", "top": "{:,.2f}",
                                         "height %": "{:.1f}"}),
                        width="stretch", height=300, hide_index=True)
        with db2:
            with card():
                st.markdown("#### Fibonacci levels")
                if not fib:
                    _hint("No usable swing in this window.")
                else:
                    st.caption(f"Swing low {fib['low']:,.2f} on {fib['low_date']} · "
                               f"swing high {fib['high']:,.2f} on {fib['high_date']}.")
                    ft = pd.DataFrame({"Level": [f"{r * 100:.1f}%" for r in fib["levels"]],
                                       "Price": list(fib["levels"].values())})
                    ft["Distance %"] = (last_close - ft["Price"]) / ft["Price"] * 100
                    st.dataframe(ft.style.format({"Price": "{:,.2f}",
                                                  "Distance %": "{:+.1f}"}),
                                 width="stretch", height=300, hide_index=True)

# ================================================================ Day Explorer
if PAGE == "🗓️ Day Explorer":
    st.caption("Datewise view derived from the bhav copy — gainers, losers, most "
               "active and breadth for ANY collected trading day (NSE doesn't "
               "archive these snapshots, so we recompute them from the day's bhav copy).")
    dates = per_date_dates("bhavcopy_delivery")
    if not dates:
        _hint("No bhav copies collected yet — backfill dates in the sidebar.")
    else:
        de1, de2 = st.columns([1, 2])
        pick = de1.selectbox("Trading date", list(reversed(dates)), key="day_pick")
        with de2:
            de_q = search("de_q", "Search", "symbol — filters every table below")
        bhav = load_per_date("bhavcopy_delivery", pick)
        br = D.breadth(bhav)
        adv, dec = br["Advances"], br["Declines"]
        ratio = (adv / dec) if dec else float("inf")
        st.markdown(T.stat_row([
            T.stat_card("Advances", f'{adv:,}', pick, "up", arrow=True),
            T.stat_card("Declines", f'{dec:,}', pick, "down", arrow=True),
            T.stat_card("A/D ratio", f'{ratio:.2f}',
                        "bullish" if ratio > 1 else "bearish", "up" if ratio > 1 else "down"),
            T.stat_card("Unchanged", f'{br["Unchanged"]:,}', "flat", "neutral"),
        ]), unsafe_allow_html=True)
        _tot = adv + dec + br["Unchanged"]
        if _tot:
            _as = adv / _tot * 100
            st.markdown(T.progress(_as, "success" if _as >= 50 else "danger",
                        f"Advances share · {_as:.0f}%"), unsafe_allow_html=True)

        dcol, _sp = st.columns([1, 2])
        with dcol:
            with card():
                st.markdown(G.head("Breadth split", "advance_decline", "market_breadth"), unsafe_allow_html=True)
                C.show(C.donut(["Advances", "Declines", "Unchanged"],
                               [adv, dec, br["Unchanged"]],
                               [T.GREEN, T.CORAL, "#B8BCCB"], _DARK,
                               center=f'{adv + dec + br["Unchanged"]:,}'))

        g1, g2 = st.columns(2)
        with g1:
            with card():
                st.markdown("#### 🟢 Top gainers")
                st.dataframe(apply_search(D.gainers(bhav), de_q, ["SYMBOL"]).style.format(
                    {"CLOSE_PRICE": "{:,.2f}", "%Chg": "{:+.2f}", "DELIV_PER": "{:.0f}",
                     "TURNOVER_LACS": "{:,.0f}"}, na_rep="-"),
                    width="stretch", height=340, hide_index=True)
        with g2:
            with card():
                st.markdown("#### 🔴 Top losers")
                st.dataframe(apply_search(D.losers(bhav), de_q, ["SYMBOL"]).style.format(
                    {"CLOSE_PRICE": "{:,.2f}", "%Chg": "{:+.2f}", "DELIV_PER": "{:.0f}",
                     "TURNOVER_LACS": "{:,.0f}"}, na_rep="-"),
                    width="stretch", height=340, hide_index=True)

        a1, a2 = st.columns(2)
        with a1:
            with card():
                st.markdown(G.head("Most active — value", "turnover"), unsafe_allow_html=True)
                st.dataframe(apply_search(D.most_active(bhav, "value"), de_q, ["SYMBOL"]),
                             width="stretch", height=320, hide_index=True)
        with a2:
            with card():
                st.markdown(G.head("Most active — volume", "volume"), unsafe_allow_html=True)
                st.dataframe(apply_search(D.most_active(bhav, "volume"), de_q, ["SYMBOL"]),
                             width="stretch", height=320, hide_index=True)

# ================================================================ Data Health
if PAGE == "🩺 Data Health":
    with card():
        st.markdown(G.head("Collection health", "snapshot", "bhavcopy"), unsafe_allow_html=True)
        man = load_manifest()
        if not man.empty:
            man = man.copy()
            last = (man.sort_values("run_ts") if "run_ts" in man.columns else man).groupby("dataset").tail(1)
            keep = [c for c in ["dataset", "kind", "target", "rows_written", "total_rows",
                                "status", "run_ts"] if c in last.columns]
            ok = last["status"].astype(str).str.startswith("ok").sum() if "status" in last else 0
            cc = [T.stat_card("Datasets with data", int(ok), "collected", "up"),
                  T.stat_card("Write events", len(man), "total runs logged", "neutral")]
            st.markdown(T.stat_row(cc), unsafe_allow_html=True)
            if "status" in man.columns:
                _s = man["status"].astype(str)
                man["_class"] = "error"
                man.loc[_s.str.startswith("ok"), "_class"] = "ok"
                man.loc[_s.str.startswith("empty"), "_class"] = "empty"
                mat = pd.crosstab(man["dataset"], man["_class"])
                mat = mat[[c for c in ["ok", "empty", "error"] if c in mat.columns]]
                mat = mat.loc[mat.sum(axis=1).sort_values(ascending=False).index]
                st.caption("Every logged run per dataset, by outcome.")
                C.show(C.stacked(mat, _DARK, colors=[T.GREEN, "#F5C451", T.CORAL],
                                 horizontal=True, height=max(320, len(mat) * 22 + 80)))
            dh = searched(last[keep].sort_values("dataset"), "dh_q",
                          ["dataset", "kind", "status"], "Search", "dataset or status")
            st.dataframe(dh, width="stretch", height=460, hide_index=True)
        else:
            _hint("No manifest yet — run the collector.")

# ================================================================ Screener
if PAGE == "🔎 Screener":
    st.caption("Multi-factor stock scan — stack filters (price move, delivery, "
               "valuation, volatility, distance from 52wk high) to surface names.")
    bhav = load_per_date("bhavcopy_delivery")
    if bhav.empty:
        _hint("Needs the latest bhav copy — fetch/backfill first.")
    else:
        b = bhav.copy()
        if "SERIES" in b.columns:
            b = b[b["SERIES"] == "EQ"]
        b = _num(b, ["CLOSE_PRICE", "PREV_CLOSE", "DELIV_PER", "TTL_TRD_QNTY", "TURNOVER_LACS"])
        b["SYM"] = b["SYMBOL"].astype(str).str.upper()
        b["%Chg"] = (b["CLOSE_PRICE"] - b["PREV_CLOSE"]) / b["PREV_CLOSE"] * 100

        # merge P/E
        pe = load_per_date("pe_ratio")
        if not pe.empty:
            pecol = next((c for c in pe.columns if "P/E" in c.upper()), None)
            if pecol:
                p = pe.rename(columns={pe.columns[0]: "SYM"})[["SYM", pecol]].copy()
                p["SYM"] = p["SYM"].astype(str).str.upper()
                p["P/E"] = L.to_num(p[pecol])
                b = b.merge(p[["SYM", "P/E"]], on="SYM", how="left")
        if "P/E" not in b.columns:
            b["P/E"] = float("nan")

        # merge annualised volatility
        vol = load_per_date("daily_volatility")
        if not vol.empty:
            vcol = next((c for c in vol.columns if "Annualised" in c), None)
            scol = "Symbol" if "Symbol" in vol.columns else vol.columns[1]
            if vcol:
                v = vol[[scol, vcol]].copy()
                v.columns = ["SYM", "Ann.Vol"]
                v["SYM"] = v["SYM"].astype(str).str.upper()
                v["Ann.Vol"] = L.to_num(v["Ann.Vol"])
                b = b.merge(v, on="SYM", how="left")
        if "Ann.Vol" not in b.columns:
            b["Ann.Vol"] = float("nan")

        # merge 52wk high -> % from high
        w52 = load_per_date("week52_high_low")
        if not w52.empty and "Adjusted_52_Week_High" in w52.columns:
            w = w52.rename(columns={"SYMBOL": "SYM"})[["SYM", "Adjusted_52_Week_High"]].copy()
            w["SYM"] = w["SYM"].astype(str).str.upper()
            w["52wHigh"] = L.to_num(w["Adjusted_52_Week_High"])
            b = b.merge(w[["SYM", "52wHigh"]], on="SYM", how="left")
            b["%FromHigh"] = (b["CLOSE_PRICE"] - b["52wHigh"]) / b["52wHigh"] * 100
        else:
            b["52wHigh"] = float("nan"); b["%FromHigh"] = float("nan")

        # filters
        f1, f2, f3 = st.columns(3)
        min_chg = f1.slider("Min % change", -15.0, 20.0, 0.0, 0.5, key="sc_chg")
        min_del = f2.slider("Min delivery %", 0, 100, 0, 5, key="sc_del")
        min_to = f3.slider("Min turnover (₹ lacs)", 0, 5000, 200, 100, key="sc_to")
        f4, f5, f6 = st.columns(3)
        max_pe = f4.number_input("Max P/E (0 = any)", 0.0, 500.0, 0.0, 5.0, key="sc_pe")
        near_high = f5.checkbox("Within X% of 52wk high", key="sc_nh")
        high_gap = f6.slider("X% from high", 0.0, 25.0, 5.0, 0.5, key="sc_gap", disabled=not near_high)
        sc_q = search("sc_q", "Search", "symbol — narrow the scan to specific names")

        m = b[(b["%Chg"] >= min_chg) & (b["DELIV_PER"].fillna(0) >= min_del)
              & (b["TURNOVER_LACS"].fillna(0) >= min_to)]
        m = apply_search(m, sc_q, ["SYMBOL"])
        if max_pe > 0:
            m = m[m["P/E"].notna() & (m["P/E"] <= max_pe)]
        if near_high:
            m = m[m["%FromHigh"] >= -high_gap]

        st.markdown(T.stat_row([
            T.stat_card("Matches", f"{len(m):,}", "stocks pass filters", "up" if len(m) else "neutral"),
            T.stat_card("Avg % change", f'{m["%Chg"].mean():+.2f}%' if len(m) else "—", "of matches", "neutral"),
            T.stat_card("Avg delivery", f'{m["DELIV_PER"].mean():.0f}%' if len(m) else "—", "conviction", "neutral"),
        ]), unsafe_allow_html=True)

        with card():
            st.markdown("#### Scan results")
            if m.empty:
                _hint("No stocks match — loosen the filters.")
            else:
                keep = ["SYMBOL", "CLOSE_PRICE", "%Chg", "DELIV_PER", "TURNOVER_LACS",
                        "P/E", "Ann.Vol", "%FromHigh"]
                out = m[keep].sort_values("%Chg", ascending=False)
                top5_rows = list(zip(out["SYMBOL"].head(5), out["%Chg"].head(5)))
                SNAP.record("screener", top5_rows)
                st.markdown(T.rank_boxes(top5_rows, "{:+.2f}", "%"), unsafe_allow_html=True)
                _nav_row([s for s, _ in top5_rows], "screener")
                _dropout_note("screener", [s for s, _ in top5_rows])
                if out.dropna(subset=["P/E", "%Chg"]).shape[0] > 1:
                    C.show(C.scatter(out, "P/E", "%Chg", "SYMBOL", _DARK, color="%Chg",
                                     size="TURNOVER_LACS", height=380,
                                     xtitle="P/E", ytitle="% change", hline=0))
                st.dataframe(
                    out.style.background_gradient(subset=["%Chg"], cmap="RdYlGn")
                       .background_gradient(subset=["DELIV_PER"], cmap="Greens")
                       .format({"CLOSE_PRICE": "{:,.2f}", "%Chg": "{:+.2f}", "DELIV_PER": "{:.0f}",
                                "TURNOVER_LACS": "{:,.0f}", "P/E": "{:.1f}", "Ann.Vol": "{:.2f}",
                                "%FromHigh": "{:+.1f}"}, na_rep="-"),
                    width="stretch", height=460, hide_index=True)
                st.caption(f"Bhav copy date: {per_date_dates('bhavcopy_delivery')[-1]}")

# ================================================================ Value & PEG
if PAGE == "💎 Value & PEG":
    st.caption("Stocks at a sane P/E, ranked by PEG. Earnings growth is implied "
               "from the warehouse (close ÷ P/E gives TTM EPS, compared across the "
               "stored history and annualised) — a proxy for reported growth, not a "
               "substitute for it.")
    vdf, vmeta = peg_table()
    if vdf.empty:
        _hint("Needs the bhav copy and P/E report — fetch/backfill first.")
    elif vmeta.get("window_days", 0) < V.MIN_WINDOW_DAYS:
        _hint(f"Only {vmeta.get('window_days', 0)} days of overlapping history — "
              f"need {V.MIN_WINDOW_DAYS}+ before growth means anything. Backfill more dates.")
    else:
        f1, f2, f3 = st.columns(3)
        pe_lo, pe_hi = f1.slider("P/E band", 0.0, 100.0, (10.0, 25.0), 1.0, key="vp_pe")
        max_peg = f2.slider("Max PEG", 0.1, 3.0, 1.0, 0.1, key="vp_peg")
        min_to = f3.slider("Min turnover (₹ cr)", 0.0, 50.0, 2.0, 0.5, key="vp_to")
        f4, f5, f6 = st.columns(3)
        below_sector = f4.checkbox("Cheaper than its sector median", key="vp_sec")
        min_growth = f5.slider("Min growth %", 0.0, 100.0, 10.0, 5.0, key="vp_g")
        # sorting by PEG otherwise floats the biggest implied growth to the top,
        # and that is exactly where a small earnings base distorts the number most
        max_growth = f6.slider("Max growth %", 50.0, V.MAX_GROWTH, 100.0, 25.0, key="vp_gmax")
        vq = search("vp_q", "Search", "symbol, company or industry")

        m = vdf[vdf["P/E"].between(pe_lo, pe_hi)
                & vdf["PEG"].notna() & (vdf["PEG"] <= max_peg)
                & vdf["Growth %"].between(min_growth, max_growth)
                & (vdf["Turnover Cr"].fillna(0) >= min_to)]
        if below_sector:
            m = m[m["vs Sector %"] < 0]
        m = apply_search(m, vq, ["Symbol", "Name", "Industry"])
        m = m.sort_values("PEG")

        st.markdown(T.stat_row([
            T.stat_card("Matches", f"{len(m):,}", "stocks pass filters",
                        "up" if len(m) else "neutral"),
            T.stat_card("Median P/E", f'{m["P/E"].median():.1f}' if len(m) else "—",
                        "of matches", "neutral"),
            T.stat_card("Median PEG", f'{m["PEG"].median():.2f}' if len(m) else "—",
                        "1.0 = fairly priced for growth", "neutral"),
            T.stat_card("Growth window", f'{vmeta["window_days"]}d',
                        f'{vmeta["base_date"]} → {vmeta["latest_date"]}', "neutral"),
        ]), unsafe_allow_html=True)

        with card():
            st.markdown("#### Reasonable P/E, cheapest PEG first")
            if m.empty:
                _hint("No stocks match — widen the P/E band or raise max PEG.")
            else:
                top5 = list(zip(m["Symbol"].head(5), m["PEG"].head(5)))
                SNAP.record("value_peg", top5)
                st.markdown(T.rank_boxes(top5, "{:.2f}", " PEG"), unsafe_allow_html=True)
                _nav_row([s for s, _ in top5], "value_peg")
                _dropout_note("value_peg", [s for s, _ in top5])
                if m.dropna(subset=["Growth %", "P/E"]).shape[0] > 1:
                    st.caption("Bottom-right = high growth at a low multiple. Bubble = turnover.")
                    C.show(C.scatter(m, "Growth %", "P/E", "Symbol", _DARK, color="vs Sector %",
                                     size="Turnover Cr", height=400,
                                     xtitle="EPS growth %", ytitle="P/E"))
                st.dataframe(
                    m.style.background_gradient(subset=["PEG"], cmap="RdYlGn_r")
                     .background_gradient(subset=["Growth %"], cmap="Greens")
                     .format({"Close": "{:,.2f}", "P/E": "{:.1f}", "Sector P/E": "{:.1f}",
                              "vs Sector %": "{:+.0f}", "EPS then": "{:,.2f}",
                              "EPS now": "{:,.2f}", "Growth %": "{:+.1f}", "PEG": "{:.2f}",
                              "Turnover Cr": "{:,.1f}", "Delivery %": "{:.0f}",
                              "% From High": "{:+.1f}"}, na_rep="-"),
                    width="stretch", height=520, hide_index=True)
                st.caption(
                    f"{vdf['P/E'].notna().sum():,} stocks priced, "
                    f"{vdf['PEG'].notna().sum():,} with a usable PEG. Blank PEG means "
                    f"loss-making, shrinking earnings, or growth off too small a base "
                    f"(>{V.MAX_GROWTH:.0f}%) to trust — never a filled-in guess.")

# ================================================================ Peer Compare
if PAGE == "⚖️ Peer Compare":
    st.caption("Side-by-side comparison — pick a few stocks to line up price move, "
               "delivery, valuation, volatility and distance from 52wk high.")
    picks = st.multiselect("Stocks to compare (2–6)", SYMBOLS, key="peer_pick",
                           format_func=lambda s: f"{s} — {NAMES[s]}" if s in NAMES else s)
    if len(picks) < 2:
        st.info("Select at least two symbols to compare.")
    else:
        bhav = load_per_date("bhavcopy_delivery")
        pe = load_per_date("pe_ratio")
        vol = load_per_date("daily_volatility")
        w52 = load_per_date("week52_high_low")
        pecol = next((c for c in pe.columns if "P/E" in c.upper()), None) if not pe.empty else None
        vcol = next((c for c in vol.columns if "Annualised" in c), None) if not vol.empty else None
        vscol = ("Symbol" if "Symbol" in vol.columns else (vol.columns[1] if not vol.empty else None))

        rows = []
        for s in picks:
            r = {"Symbol": s}
            bb = bhav[bhav["SYMBOL"].astype(str).str.upper() == s] if not bhav.empty else pd.DataFrame()
            if not bb.empty:
                x = _num(bb, ["CLOSE_PRICE", "PREV_CLOSE", "DELIV_PER", "TURNOVER_LACS"]).iloc[0]
                r["LTP"] = x["CLOSE_PRICE"]
                r["%Chg"] = (x["CLOSE_PRICE"] - x["PREV_CLOSE"]) / x["PREV_CLOSE"] * 100
                r["Delivery%"] = x["DELIV_PER"]
                r["Turnover(L)"] = x["TURNOVER_LACS"]
            if pecol:
                pp = pe[pe.iloc[:, 0].astype(str).str.upper() == s]
                if not pp.empty:
                    r["P/E"] = L.to_num(pp[pecol]).iloc[0]
            if vcol and vscol:
                vv = vol[vol[vscol].astype(str).str.upper() == s]
                if not vv.empty:
                    r["Ann.Vol"] = L.to_num(vv[vcol]).iloc[0]
            if not w52.empty and "Adjusted_52_Week_High" in w52.columns:
                ww = w52[w52["SYMBOL"].astype(str).str.upper() == s]
                if not ww.empty:
                    hi = L.to_num(ww["Adjusted_52_Week_High"]).iloc[0]
                    r["52wHigh"] = hi
                    if r.get("LTP") and hi:
                        r["%FromHigh"] = (r["LTP"] - hi) / hi * 100
            rows.append(r)
        comp = pd.DataFrame(rows).set_index("Symbol")

        st.markdown(T.stat_row([
            T.stat_card("Best today", comp["%Chg"].idxmax() if "%Chg" in comp else "—",
                        f'{comp["%Chg"].max():+.2f}%' if "%Chg" in comp else "", "up", arrow=True),
            T.stat_card("Weakest today", comp["%Chg"].idxmin() if "%Chg" in comp else "—",
                        f'{comp["%Chg"].min():+.2f}%' if "%Chg" in comp else "", "down", arrow=True),
            T.stat_card("Compared", f"{len(comp)}", "stocks", "neutral"),
        ]), unsafe_allow_html=True)

        with card():
            st.markdown(G.head("Comparison table", "pe", "delivery_pct"), unsafe_allow_html=True)
            fmt = {c: "{:,.2f}" for c in ["LTP", "Turnover(L)", "52wHigh"] if c in comp.columns}
            fmt.update({c: "{:+.2f}" for c in ["%Chg", "%FromHigh"] if c in comp.columns})
            fmt.update({"Delivery%": "{:.0f}", "P/E": "{:.1f}", "Ann.Vol": "{:.2f}"})
            grad = [c for c in ["%Chg", "Delivery%"] if c in comp.columns]
            sty = comp.style.format({k: v for k, v in fmt.items() if k in comp.columns}, na_rep="-")
            if grad:
                sty = sty.background_gradient(subset=grad, cmap="RdYlGn")
            st.dataframe(sty, width="stretch")
        if "%Chg" in comp.columns:
            with card():
                st.markdown("#### Today's move (%)")
                C.show(C.hbar(comp["%Chg"], _DARK, diverge=True))

# ================================================================ F&O / Options
if PAGE == "🧩 F&O / Options":
    st.caption("Derivatives from the F&O bhav copy — open interest, OI buildup, "
               "put/call ratio and a strike-wise option chain.")
    fno = load_per_date("fno_bhavcopy")
    if fno.empty:
        _hint("F&O bhav copy not collected for the latest day yet.")
    else:
        f = _num(fno.copy(), ["StrkPric", "OpnIntrst", "ChngInOpnIntrst",
                              "TtlTradgVol", "TtlTrfVal", "ClsPric", "UndrlygPric"])
        f["SYM"] = f["TckrSymb"].astype(str).str.upper()
        opts = f[f["OptnTp"].astype(str).str.upper().isin(["CE", "PE"])]
        ce_oi = opts[opts["OptnTp"].str.upper() == "CE"]["OpnIntrst"].sum()
        pe_oi = opts[opts["OptnTp"].str.upper() == "PE"]["OpnIntrst"].sum()
        pcr = (pe_oi / ce_oi) if ce_oi else 0

        st.markdown(T.stat_row([
            T.stat_card("Underlyings", f'{f["SYM"].nunique():,}', "in F&O", "neutral"),
            T.stat_card("Put/Call OI", f"{pcr:.2f}", "PCR (>1 = bearish hedging)",
                        "down" if pcr > 1 else "up"),
            T.stat_card("Total OI", f'{f["OpnIntrst"].sum():,.0f}', "open contracts", "neutral"),
            T.stat_card("Contracts traded", f'{f["TtlTradgVol"].sum():,.0f}', "today's volume", "neutral"),
        ]), unsafe_allow_html=True)

        o1, o2 = st.columns(2)
        with o1:
            with card():
                st.markdown(G.head("Most active underlyings — by OI", "oi", "fno"), unsafe_allow_html=True)
                by_oi = f.groupby("SYM")["OpnIntrst"].sum().nlargest(15)
                top5_rows = list(by_oi.head(5).items())
                SNAP.record("fno_oi", top5_rows)
                st.markdown(T.rank_boxes(top5_rows, "{:,.0f}"), unsafe_allow_html=True)
                _nav_row([s for s, _ in top5_rows], "fno")
                _dropout_note("fno_oi", [s for s, _ in top5_rows])
                C.show(C.hbar(by_oi, _DARK, color=T.INDIGO))
        with o2:
            with card():
                st.markdown(G.head("OI buildup — biggest change", "change_oi", "long_buildup", "short_buildup"), unsafe_allow_html=True)
                chg = f.groupby("SYM")["ChngInOpnIntrst"].sum()
                top = pd.concat([chg.nlargest(8), chg.nsmallest(8)]).sort_values()
                C.show(C.hbar(top, _DARK, diverge=True))

        with card():
            st.markdown(G.head("Option chain", "strike", "oi", "pcr", "itm_otm"), unsafe_allow_html=True)
            usyms = sorted(opts["SYM"].dropna().unique())
            if not usyms:
                _hint("No option rows in the F&O bhav copy.")
            else:
                cc1, cc2 = st.columns([1, 1])
                usel = cc1.selectbox("Underlying", usyms, key="fno_sym")
                exps = sorted(opts[opts["SYM"] == usel]["XpryDt"].dropna().astype(str).unique())
                esel = cc2.selectbox("Expiry", exps, key="fno_exp")
                sub = opts[(opts["SYM"] == usel) & (opts["XpryDt"].astype(str) == esel)]
                ce = (sub[sub["OptnTp"].str.upper() == "CE"]
                      [["StrkPric", "OpnIntrst", "ChngInOpnIntrst", "ClsPric"]]
                      .rename(columns={"OpnIntrst": "CE OI", "ChngInOpnIntrst": "CE ΔOI", "ClsPric": "CE LTP"}))
                pe_ = (sub[sub["OptnTp"].str.upper() == "PE"]
                       [["StrkPric", "OpnIntrst", "ChngInOpnIntrst", "ClsPric"]]
                       .rename(columns={"OpnIntrst": "PE OI", "ChngInOpnIntrst": "PE ΔOI", "ClsPric": "PE LTP"}))
                chain = ce.merge(pe_, on="StrkPric", how="outer").sort_values("StrkPric")
                chain = chain[["CE OI", "CE ΔOI", "CE LTP", "StrkPric", "PE LTP", "PE ΔOI", "PE OI"]]
                st.dataframe(
                    chain.style.background_gradient(subset=["CE OI"], cmap="Reds")
                         .background_gradient(subset=["PE OI"], cmap="Greens")
                         .format({"StrkPric": "{:,.1f}", "CE OI": "{:,.0f}", "PE OI": "{:,.0f}",
                                  "CE ΔOI": "{:+,.0f}", "PE ΔOI": "{:+,.0f}",
                                  "CE LTP": "{:,.2f}", "PE LTP": "{:,.2f}"}, na_rep="-"),
                    width="stretch", height=460, hide_index=True)
                up = opts[opts["SYM"] == usel]["UndrlygPric"].dropna()
                if not up.empty:
                    st.caption(f"{usel} underlying ≈ {up.iloc[0]:,.2f} · expiry {esel}")

# ================================================================ Result PDFs
if PAGE == "📄 Result PDFs":
    st.caption("Parse quarterly/annual result PDFs dropped into `result-pdf/` into a "
               "structured fundamentals warehouse, then read the statements here.")

    STMT_LABEL = {"pnl": "Profit & Loss", "bs": "Balance Sheet", "cf": "Cash Flow"}
    STMT_TERM = {"pnl": "pnl", "bs": "balance_sheet", "cf": "cash_flow"}

    pdfs = result_pdfs()
    pc1, pc2 = st.columns([1, 1])
    with pc1:
        with card():
            st.markdown(G.head("🧾 Run the parser", "audited", "standalone", "consolidated"),
                        unsafe_allow_html=True)
            st.caption(f"{len(pdfs)} PDF(s) waiting in `result-pdf/`.")
            target = st.selectbox("Scope", ["All PDFs"] + list(pdfs["File"]) if not pdfs.empty
                                  else ["All PDFs"], key="pdf_scope",
                                  help="Parse the whole folder or a single file.")
            rebuild = st.checkbox("Discard OCR cache (slower, re-reads every page)",
                                  key="pdf_rebuild")
            if st.button("📄 Parse result PDFs", key="pdf_parse", width="stretch",
                         type="primary", disabled=pdfs.empty):
                single = None if target == "All PDFs" else os.path.join(L.RESULT_PDF_DIR, target)
                with st.spinner("Parsing PDFs — OCR can take a few minutes…"):
                    code, log = _parse_results(single, rebuild)
                st.cache_data.clear()
                (st.success if code == 0 else st.error)(
                    "Parse finished." if code == 0 else "Parser exited with errors.")
                st.session_state["pdf_log"] = log
            if st.session_state.get("pdf_log"):
                with st.expander("Parser output", expanded=True):
                    st.code(st.session_state["pdf_log"], language="text")
    with pc2:
        with card():
            st.markdown("#### 📥 Files in `result-pdf/`")
            if pdfs.empty:
                _hint("Drop result PDFs into `result-pdf/` and press Parse.")
            else:
                st.markdown(T.table(searched(pdfs, "pdf_q", ["File"], "Search", "file name"),
                                    height=260), unsafe_allow_html=True)

    fsyms = fundamentals_symbols()
    if not fsyms:
        _hint("Nothing parsed yet — run the parser above.")
    else:
        facts = fundamentals_facts()
        st.markdown(T.section("Parsed fundamentals",
                              f"{len(fsyms)} company file(s) · {len(facts):,} facts"),
                    unsafe_allow_html=True)
        fsel = st.selectbox("Company", fsyms, key="fund_sym")
        doc = fundamentals_doc(fsel)
        ident = doc.get("identity", {}) or {}

        mc = [T.stat_card("Symbol", fsel, ident.get("name", "") or "—"),
              T.stat_card("Source PDFs", len(doc.get("sources", []) or []), "filings parsed"),
              T.stat_card("Facts", f"{len(facts[facts['symbol'] == fsel]) if not facts.empty else 0:,}",
                          "line items extracted"),
              T.stat_card("Checks failed", len(doc.get("issues", []) or []),
                          "cross-foot breaks",
                          "down" if doc.get("issues") else "up")]
        st.markdown(T.stat_row(mc), unsafe_allow_html=True)
        if fsel == "UNRESOLVED":
            st.warning("These facts came from PDFs whose company symbol could not be "
                       "matched against the equity master — treat them as unlabelled.")

        sub = facts[facts["symbol"] == fsel] if not facts.empty else pd.DataFrame()
        if sub.empty:
            _hint("No facts extracted for this company — the PDF may be a scan the "
                  "parser could not read.")
        else:
            avail = [s for s in ("pnl", "bs", "cf") if s in set(sub["statement"])]
            tabs = st.tabs([STMT_LABEL[s] for s in avail] + ["Sources", "Data checks"])
            for tab, stmt in zip(tabs, avail):
                with tab:
                    ss = sub[sub["statement"] == stmt]
                    bases = sorted(ss["basis"].dropna().unique())
                    basis = st.radio("Basis", bases, horizontal=True, key=f"fb_{stmt}",
                                     help=f"{G.h('standalone')}\n\n{G.h('consolidated')}")
                    ss = ss[ss["basis"] == basis]
                    # one column per label, oldest period first — a label can repeat
                    # across filings with different period_end, so dedupe after sorting
                    order = list(dict.fromkeys(
                        ss.sort_values("period_end")["fiscal_label"].tolist()))
                    piv = ss.pivot_table(index="tag", columns="fiscal_label",
                                         values="value", aggfunc="last")
                    piv = piv.reindex(columns=[c for c in order if c in piv.columns])
                    piv.index = [t.replace("_", " ").title() for t in piv.index]
                    piv.index.name = "Line item"
                    st.markdown(G.head(STMT_LABEL[stmt], STMT_TERM[stmt], "audited"),
                                unsafe_allow_html=True)
                    st.dataframe(piv.style.format("{:,.0f}", na_rep="—"),
                                 width="stretch", height=520)
                    st.caption("Values in base rupees as filed. Per-share figures "
                               "(EPS) are unscaled. A blank cell means the line was "
                               "not reported that period.")
            with tabs[len(avail)]:
                srcs = pd.DataFrame(doc.get("sources", []) or [])
                if srcs.empty:
                    _hint("No source metadata.")
                else:
                    srcs["pdf"] = srcs["pdf"].apply(os.path.basename)
                    srcs["pages"] = srcs["pages"].apply(
                        lambda p: len(p) if isinstance(p, list) else p)
                    st.markdown(T.table(srcs.rename(columns={
                        "pdf": "File", "sha1": "SHA-1", "pages": "Pages"})),
                        unsafe_allow_html=True)
                st.markdown("##### Parse log")
                man = fundamentals_manifest()
                if not man.empty:
                    st.markdown(T.table(man.head(30), height=300), unsafe_allow_html=True)
            with tabs[len(avail) + 1]:
                st.markdown(G.head("Cross-foot checks", "cross_foot"), unsafe_allow_html=True)
                iss = pd.DataFrame(doc.get("issues", []) or [])
                if iss.empty:
                    st.success("Every total the parser could test adds up.")
                else:
                    st.markdown(T.table(iss), unsafe_allow_html=True)
                    st.caption("A break usually means an OCR misread or a disclosure "
                               "the taxonomy does not model yet — verify against the "
                               "PDF before relying on that line.")

        G.legend("pnl", "balance_sheet", "cash_flow", "standalone", "consolidated",
                 "audited", "revenue", "ebitda", "pat", "eps", "operating_margin",
                 "cross_foot")

# ================================================================ Result Scorecard
if PAGE == "🧾 Result Scorecard":
    st.caption("Quarterly result filings scored by the analyzer — verdict, financials, "
               "positives and red flags per company. Reads "
               "`result-pdf/<quarter>/results-summary.json`.")

    RS_TONE = {"GOOD": "up", "BAD": "down", "MIXED": "neutral"}
    # (json key, label, unit) — margin carries bps deltas, everything else pct
    RS_ROWS = [("revenue", "Revenue", "cr"), ("ebitda", "EBITDA", "cr"),
               ("ebitda_margin", "EBITDA margin", "pct"), ("pbt", "PBT", "cr"),
               ("pbt_ex_exceptional", "PBT ex-exceptional", "cr"), ("pat", "PAT", "cr"),
               ("pat_after_minority", "PAT after minority", "cr"),
               ("pat_before_jv", "PAT before JV", "cr"),
               ("pbt_before_jv", "PBT before JV", "cr"),
               ("pat_continuing_operations", "PAT continuing ops", "cr"),
               ("other_income", "Other income", "cr"),
               ("depreciation", "Depreciation", "cr"),
               ("finance_cost", "Finance cost", "cr"),
               ("exceptional_item", "Exceptional item", "cr")]

    # sector lines the analyzer emits beyond the common set — (label, unit)
    RS_IND = {
        "total_income": ("Total income", "cr"),
        "net_interest_income": ("Net interest income (NII)", "cr"),
        "nii": ("Net interest income (NII)", "cr"),
        "interest_income": ("Interest income", "cr"),
        "fees_and_commission_income": ("Fees & commission income", "cr"),
        "pre_provision_operating_profit": ("Pre-provision operating profit", "cr"),
        "operating_profit_pre_provision": ("Pre-provision operating profit", "cr"),
        "operating_profit_(pre_provision)": ("Pre-provision operating profit", "cr"),
        "operating_profit_before_provisions": ("Pre-provision operating profit", "cr"),
        "ppop_to_total_income_pct": ("PPOP / total income", "pct"),
        "ppop_margin_on_revenue_pct": ("PPOP margin on revenue", "pct"),
        "provisions": ("Provisions & contingencies", "cr"),
        "provisions_and_contingencies": ("Provisions & contingencies", "cr"),
        "impairment_on_financial_instruments": ("Impairment on financial instruments", "cr"),
        "impairment_allowances": ("Impairment allowances", "cr"),
        "net_loss_on_derecognition": ("Net loss on derecognition", "cr"),
        "net_gain_fair_value": ("Net gain on fair value changes", "cr"),
        "gross_npa_pct_standalone": ("Gross NPA", "pct"),
        "capital_adequacy_pct_standalone": ("Capital adequacy (CAR)", "pct"),
        "effective_tax_rate_pct": ("Effective tax rate", "pct"),
        "net_worth": ("Net worth", "cr"),
        "debt_equity": ("Debt / equity (x)", "num"),
        "gross_premium_income": ("Gross premium income", "cr"),
        "first_year_premium": ("First-year premium", "cr"),
        "renewal_premium": ("Renewal premium", "cr"),
        "single_premium": ("Single premium", "cr"),
        "policyholders_surplus": ("Policyholders' surplus", "cr"),
        "transfer_from_policyholders_ac": ("Transfer from policyholders' a/c", "cr"),
        "operating_margin": ("Operating margin", "pct"),
        "net_revenue_ex_excise": ("Net revenue (ex-excise)", "cr"),
        "revenue_net_of_excise": ("Net revenue (ex-excise)", "cr"),
        "ebitda_margin_on_net_revenue": ("EBITDA margin on net revenue", "pct"),
        "ebitda_margin_net_of_excise": ("EBITDA margin on net revenue", "pct"),
        "excise_duty_vat_tcs": ("Excise duty / VAT / TCS", "cr"),
        "volumes_mt": ("Volumes (MT)", "num"),
        "segment_revenue_zinc_lead": ("Segment revenue — zinc & lead", "cr"),
        "segment_revenue_silver": ("Segment revenue — silver", "cr"),
    }
    RS_GENERIC = {k for k, _, _ in RS_ROWS}

    def _rs_ind_label(k):
        if k in RS_IND:
            return RS_IND[k]
        unit = "pct" if k.endswith("_pct") or "margin" in k else "num"
        return k.replace("_", " ").strip().capitalize(), unit

    def _rs_fmt(v, unit):
        if v is None:
            return "—"
        return f"{v:,.2f}%" if unit == "pct" else f"{v:,.2f}"

    def _rs_delta(blk, pct_key, bps_key):
        if blk.get(bps_key) is not None:
            return f"{blk[bps_key]:+,.0f} bps"
        return f"{blk[pct_key]:+.2f}%" if blk.get(pct_key) is not None else "—"

    rqs = result_quarters()
    if not rqs:
        _hint("No analyzed results yet — run the result analyzer so it writes "
              "`result-pdf/<quarter>/results-summary.json`.")
    else:
        rq = st.selectbox("Quarter", list(reversed(rqs)), key="rs_q")
        rdoc = result_summary(rq)
        ridx = result_index(rq)
        recs = rdoc.get("results") or []

        if ridx.empty:
            _hint(f"`results-summary.json` for {rq} has no result records.")
        else:
            good = int((ridx["Verdict"] == "GOOD").sum())
            bad = int((ridx["Verdict"] == "BAD").sum())
            mixed = int((ridx["Verdict"] == "MIXED").sum())
            st.markdown(T.stat_row([
                T.stat_card("Companies", f"{len(ridx)}", rq, "neutral"),
                T.stat_card("GOOD", f"{good}", "beats / clean quarters", "up"),
                T.stat_card("BAD", f"{bad}", "misses / weak quarters", "down"),
                T.stat_card("MIXED", f"{mixed}",
                            f"{int(ridx['Flags'].sum())} red flags total", "neutral"),
            ]), unsafe_allow_html=True)
            _gs = good / len(ridx) * 100
            st.markdown(T.progress(_gs, "success", f"GOOD verdicts · {_gs:.0f}%"),
                        unsafe_allow_html=True)
            if rdoc.get("last_updated"):
                st.caption(f"Analyzer last wrote this file on "
                           f"{str(rdoc['last_updated']).replace('T', ' ')}.")

            rv1, rv2 = st.columns([1, 2])
            with rv1:
                with card():
                    st.markdown("#### Verdict mix")
                    vc = ridx["Verdict"].value_counts()
                    C.show(C.donut(vc.index.tolist(), vc.values.tolist(),
                                   C.cycle(len(vc)), _DARK, center=str(len(ridx)),
                                   height=280))
            with rv2:
                with card():
                    st.markdown("#### Revenue vs PAT growth")
                    rs = ridx.dropna(subset=["Rev YoY %", "PAT YoY %"])
                    if rs.shape[0] < 2:
                        _hint("Not enough companies with both growth figures.")
                    else:
                        st.caption("Top-right = revenue and profit both growing.")
                        C.show(C.scatter(rs, "Rev YoY %", "PAT YoY %", "Company", _DARK,
                                         color="PAT YoY %", height=280,
                                         xtitle="Revenue YoY %", ytitle="PAT YoY %",
                                         vline=0, hline=0))

            with card():
                st.markdown(G.head("All analyzed results", "revenue", "ebitda", "pat",
                                   "operating_margin"), unsafe_allow_html=True)
                rc1, rc2, rc3 = st.columns([1, 1, 2])
                rvf = rc1.selectbox("Filter verdict", ["All", "GOOD", "BAD", "MIXED"],
                                    key="rs_vf")
                _tags = sorted({t for r in recs for t in (r.get("tags") or [])})
                rtf = rc2.selectbox("Filter tag", ["All"] + _tags, key="rs_tf")
                rq_txt = rc3.text_input("Search company", key="rs_search").upper()

                view = ridx.copy()
                if rvf != "All":
                    view = view[view["Verdict"] == rvf]
                if rtf != "All":
                    view = view[view["Tags"].str.contains(rtf, regex=False)]
                if rq_txt:
                    view = view[view["Company"].str.upper().str.contains(rq_txt)]

                if view.empty:
                    _hint("No companies match these filters.")
                else:
                    top5 = view.dropna(subset=["PAT YoY %"]).sort_values(
                        "PAT YoY %", ascending=False).head(5)
                    if not top5.empty:
                        top5_rows = list(zip(top5["Company"], top5["PAT YoY %"]))
                        SNAP.record("result_scorecard", top5_rows)
                        st.markdown(T.rank_boxes(top5_rows, "{:+.1f}", "%"), unsafe_allow_html=True)
                        nav_syms = [s for s in (match_symbol(c) for c in top5["Company"]) if s]
                        _nav_row(nav_syms, "resscore")
                        _dropout_note("result_scorecard", [c for c, _ in top5_rows])
                    st.dataframe(
                        view[["Company", "Verdict", "Grade", "Rev Cr", "Rev YoY %",
                              "Rev QoQ %", "EBITDA Cr", "EBITDA YoY %", "Margin %",
                              "Margin bps", "PAT Cr", "PAT YoY %", "PAT QoQ %",
                              "Basis", "SME", "Flags", "Tags"]],
                        width="stretch", height=380, hide_index=True)
                    st.caption("All money figures in ₹ Cr as filed. Click a column "
                               "header to sort. Margin delta is YoY in basis points.")

            with card():
                st.markdown("#### Read the analysis")
                pick = st.selectbox("Company", ridx["_i"].tolist(), key="rs_read",
                                    format_func=lambda i: ridx.loc[
                                        ridx["_i"] == i, "Company"].iloc[0])
                rec = recs[pick]
                _t = RS_TONE.get(rec.get("verdict"), "neutral")
                _bd = [T.badge(rec.get("verdict") or "—", _t),
                       T.badge(rec.get("sub_verdict") or "—", _t),
                       T.badge(rec.get("basis") or "—", "neutral")]
                if rec.get("is_sme"):
                    _bd.append(T.badge("SME", "neutral"))
                if rec.get("sector_profile") and rec["sector_profile"] != "default":
                    _bd.append(T.badge(rec["sector_profile"].replace("_", " "), "neutral"))
                _bd += [T.badge(t, "neutral") for t in (rec.get("tags") or [])]
                st.markdown(" ".join(_bd), unsafe_allow_html=True)

                rsym = match_symbol(rec.get("company") or "")
                if rsym:
                    rsc = S.stock_scorecard(
                        rsym, bhav=load_per_date("bhavcopy_delivery"),
                        bulk=load_growing("bulk_deals"), block=load_growing("block_deals"),
                        ban=load_per_date("securities_in_ban"),
                        vol=load_per_date("daily_volatility"), pe=load_per_date("pe_ratio"),
                        most_active=load_snapshot_latest("most_active_value"))
                    st.markdown(f"**Live signal for {rsym}:** " +
                                T.badge(f"{rsc['verdict']} ({rsc['score']:+d})", rsc["tone"]),
                                unsafe_allow_html=True)
                    st.caption("Result verdict (fundamentals) + live signal "
                               "(technicals/flows) — cross-check both.")

                st.markdown("---")
                fin = rec.get("financials") or {}
                frows = []
                for k, lab, unit in RS_ROWS:
                    blk = fin.get(k) or {}
                    if all(blk.get(p) is None for p in ("current", "yoy", "qoq")):
                        continue
                    frows.append({
                        "Line item": lab,
                        rq: _rs_fmt(blk.get("current"), unit),
                        "YoY": _rs_fmt(blk.get("yoy"), unit),
                        "YoY Δ": _rs_delta(blk, "yoy_pct", "yoy_bps"),
                        "QoQ": _rs_fmt(blk.get("qoq"), unit),
                        "QoQ Δ": _rs_delta(blk, "qoq_pct", "qoq_bps"),
                    })
                if frows:
                    st.markdown(T.table(pd.DataFrame(frows)), unsafe_allow_html=True)
                    st.caption(f"Values in ₹ {rec.get('currency_unit') or 'Cr'} as filed, "
                               f"{rec.get('basis') or 'unstated'} basis.")

                # sector lines live both in financials and in bank_/nbfc_metrics
                ind_src = {k: v for k, v in fin.items()
                           if k not in RS_GENERIC and isinstance(v, dict)}
                for _mk in ("bank_metrics", "nbfc_metrics"):
                    ind_src.update({k: v for k, v in (rec.get(_mk) or {}).items()
                                    if isinstance(v, dict)})
                irows, _seen = [], set()
                for k, blk in ind_src.items():
                    if all(blk.get(p) is None for p in ("current", "yoy", "qoq")):
                        continue
                    lab, unit = _rs_ind_label(k)
                    if lab in _seen:
                        continue
                    _seen.add(lab)
                    irows.append({
                        "Industry metric": lab,
                        rq: _rs_fmt(blk.get("current"), unit),
                        "YoY": _rs_fmt(blk.get("yoy"), unit),
                        "YoY Δ": _rs_delta(blk, "yoy_pct", "yoy_bps"),
                        "QoQ": _rs_fmt(blk.get("qoq"), unit),
                        "QoQ Δ": _rs_delta(blk, "qoq_pct", "qoq_bps"),
                    })
                if irows:
                    st.markdown("##### Industry metrics")
                    st.markdown(T.table(pd.DataFrame(irows)), unsafe_allow_html=True)
                    st.caption("Sector-specific lines for this company — read alongside "
                               "the table above. Margins and ratios in %, rest in "
                               f"₹ {rec.get('currency_unit') or 'Cr'}.")

                if rec.get("highlight_text"):
                    st.code(rec["highlight_text"], language="text")

                if rec.get("verdict_reason"):
                    st.markdown("##### Why this verdict")
                    st.markdown(rec["verdict_reason"])

                gc1, gc2 = st.columns(2)
                with gc1:
                    st.markdown("##### ✅ Positives")
                    pos = rec.get("positives") or []
                    st.markdown("\n".join(f"- {p}" for p in pos) if pos
                                else "_None recorded._")
                with gc2:
                    st.markdown("##### 🚩 Red flags")
                    rfs = rec.get("red_flags") or []
                    st.markdown("\n".join(f"- {p}" for p in rfs) if rfs
                                else "_None recorded._")

                if rec.get("notes"):
                    st.markdown("##### Analyst notes")
                    st.info(rec["notes"])

                if rec.get("post_text"):
                    with st.expander("Share text (copy-ready)"):
                        st.code(rec["post_text"], language="text")

                st.caption(f"Source PDF: `{rec.get('source_pdf') or '—'}` · "
                           f"analyzed {rec.get('analyzed_on') or '—'}")

        G.legend("revenue", "ebitda", "pat", "operating_margin", "standalone",
                 "consolidated", "pnl")

# ================================================================ Best of Quarter
if PAGE == "🥇 Best of Quarter":
    st.caption("Cross-checks the concall verdict against the result verdict for the same "
               "quarter — surfaces companies where fundamentals agree both ways, and flags "
               "the ones where they don't.")

    bqs = sorted(set(concall_quarters()) | set(result_quarters()))
    if not bqs:
        _hint("No analyzed concalls or results yet — run those agents first.")
    else:
        bq = st.selectbox("Quarter", list(reversed(bqs)), key="bq_q")
        cidx = concall_index(bq)
        ridx = result_index(bq)
        if cidx.empty and ridx.empty:
            _hint(f"No concall or result index for {bq} yet — run those agents first.")
        else:
            cidx = cidx.copy()
            ridx = ridx.copy()
            cidx["_key"] = cidx["Company"].map(_company_key)
            ridx["_key"] = ridx["Company"].map(_company_key)
            merged = cidx.merge(ridx, on="_key", how="outer", suffixes=("_cc", "_res"))

            merged["Company"] = merged["Company_cc"].fillna(merged["Company_res"])
            for col in ["Verdict_cc", "Call", "Confidence"]:
                merged[col] = merged[col].fillna("NA")
            for col in ["Verdict_res", "Grade", "Rev YoY %", "PAT YoY %"]:
                merged[col] = merged[col].fillna("NA")
            merged["Flags"] = merged["Flags"].fillna(0)

            has_cc = merged["Call"].ne("NA")
            has_res = merged["Verdict_res"].ne("NA")
            good_cc = has_cc & (merged["Call"].eq("BUY") | merged["Verdict_cc"].eq("GOOD"))
            bad_cc = has_cc & (merged["Call"].isin(["AVOID", "SELL"]) | merged["Verdict_cc"].eq("BAD"))
            good_res = has_res & merged["Verdict_res"].eq("GOOD")
            bad_res = has_res & merged["Verdict_res"].eq("BAD")

            merged["Combo"] = "Mixed / unclear"
            merged.loc[~has_res, "Combo"] = "❔ No result"
            merged.loc[~has_cc, "Combo"] = "❔ No concall"
            merged.loc[good_cc & good_res, "Combo"] = "✅ Both GOOD"
            merged.loc[bad_cc & bad_res, "Combo"] = "🚩 Both BAD"
            merged.loc[good_cc & bad_res, "Combo"] = "⚠️ Concall up, result down"
            merged.loc[bad_cc & good_res, "Combo"] = "⚠️ Result up, concall down"

            both_good = int((merged["Combo"] == "✅ Both GOOD").sum())
            both_bad = int((merged["Combo"] == "🚩 Both BAD").sum())
            conflict = int(merged["Combo"].str.startswith("⚠️").sum())
            st.markdown(T.stat_row([
                T.stat_card("Companies", f"{len(merged)}", f"concall + result union for {bq}", "neutral"),
                T.stat_card("Both GOOD", f"{both_good}", "concall + result agree bullish", "up"),
                T.stat_card("Both BAD", f"{both_bad}", "concall + result agree bearish", "down"),
                T.stat_card("Conflicting", f"{conflict}", "concall and result disagree", "neutral"),
            ]), unsafe_allow_html=True)

            ov = merged[has_cc & has_res]
            if not ov.empty:
                with card():
                    st.markdown("#### Concall call vs result verdict")
                    st.caption(f"{len(ov)} companies in {bq} have both a concall and a result.")
                    mat = pd.crosstab(ov["Call"], ov["Verdict_res"])
                    C.show(C.stacked(mat, _DARK, height=320))

            with card():
                st.markdown(G.head("Companies with both a concall and a result", "concall", "pat"),
                            unsafe_allow_html=True)
                combos = ["All", "✅ Both GOOD", "🚩 Both BAD",
                          "⚠️ Concall up, result down", "⚠️ Result up, concall down",
                          "Mixed / unclear", "❔ No concall", "❔ No result"]
                bqf = st.selectbox("Filter", combos, key="bq_filter")
                view = merged if bqf == "All" else merged[merged["Combo"] == bqf]
                if view.empty:
                    _hint("No companies match this combination for the quarter.")
                else:
                    best = merged[merged["Combo"] == "✅ Both GOOD"].copy()
                    best["PAT YoY %"] = pd.to_numeric(best["PAT YoY %"], errors="coerce")
                    best = best.dropna(subset=["PAT YoY %"]).sort_values(
                        "PAT YoY %", ascending=False).head(5)
                    if not best.empty:
                        top5_rows = list(zip(best["Company"], best["PAT YoY %"]))
                        SNAP.record("best_of_quarter", top5_rows)
                        st.markdown(T.rank_boxes(top5_rows, "{:+.1f}", "%"), unsafe_allow_html=True)
                        nav_syms = [s for s in (match_symbol(c) for c in best["Company"]) if s]
                        _nav_row(nav_syms, "bestq")
                        _dropout_note("best_of_quarter", [c for c, _ in top5_rows])
                    show = view.rename(columns={
                        "Verdict_cc": "Concall verdict",
                        "Call": "Concall call", "Verdict_res": "Result verdict",
                        "Grade": "Result grade",
                    })[["Company", "Combo", "Concall verdict", "Concall call",
                        "Confidence", "Result verdict", "Result grade",
                        "Rev YoY %", "PAT YoY %", "Flags"]]
                    st.dataframe(show, width="stretch", height=380, hide_index=True)
                    st.caption("Company match is name-based — a miss here usually means the "
                               "concall and result filings spell the company slightly differently.")

# ================================================================ Settings
if PAGE == "⚙️ Settings":
    st.caption("Fetch and maintain the local data warehouse.")
    sc1, sc2 = st.columns(2)
    with sc1:
        with card():
            st.markdown("#### 🔄 NSE data")
            if st.button("🔄 Reload data (clear cache)", key="reload_data", width="stretch"):
                st.cache_data.clear()
                st.rerun()
            st.caption("Fetch latest — snapshots + today's reports")
            if st.button("⬇️ Fetch latest (daily job)", key="fetch_daily", width="stretch"):
                with st.spinner("Fetching from NSE…"):
                    summ = _collector().run_daily()
                st.success(f"Done — {summ.line()}")
                st.cache_data.clear()
            st.caption("Backfill past dates (per-date reports)")
            _today = dt.date.today()
            bf_from = st.date_input("From", value=_today - dt.timedelta(days=7), key="bf_from")
            bf_to = st.date_input("To", value=_today, key="bf_to")
            if st.button("⏪ Backfill range", key="bf_btn", width="stretch"):
                if bf_from > bf_to:
                    st.error("From date must be ≤ To date.")
                else:
                    with st.spinner(f"Backfilling {bf_from} → {bf_to}…"):
                        summ = _collector().run_backfill(bf_from, bf_to)
                    st.success(f"Done — {summ.line()}")
                    st.cache_data.clear()
            st.caption("Snapshots (gainers, breadth, option chain) are live-only "
                       "and cannot be backfilled.")
    with sc2:
        with card():
            st.markdown("#### 🅱️ BSE data")
            st.caption("BSE EOD bhav copy (~4800 scrips) from bseindia.com.")
            if st.button("⬇️ Fetch latest BSE", key="bse_daily", width="stretch"):
                with st.spinner("Fetching BSE bhav copy…"):
                    summ = _bse_collector().run_daily()
                st.success(f"Done — {summ.line()}")
                st.cache_data.clear()
            bse_from = st.date_input("From", value=dt.date.today() - dt.timedelta(days=7), key="bse_from")
            bse_to = st.date_input("To", value=dt.date.today(), key="bse_to")
            if st.button("⏪ Backfill BSE range", key="bse_bf", width="stretch"):
                if bse_from > bse_to:
                    st.error("From date must be ≤ To date.")
                else:
                    with st.spinner(f"Backfilling BSE {bse_from} → {bse_to}…"):
                        summ = _bse_collector().run_backfill(bse_from, bse_to)
                    st.success(f"Done — {summ.line()}")
                    st.cache_data.clear()
    with card():
        st.markdown("#### 📐 niftyindices.com data")
        st.caption("Daily index snapshot — every NSE index family (broad, sectoral, "
                   "thematic, strategy, fixed income, G-Sec, SDL, corporate bond) with "
                   "OHLC, turnover and P/E, P/B, Div Yield. Broader coverage + valuation "
                   "history than NSE's own live index snapshot.")
        ni1, ni2 = st.columns(2)
        with ni1:
            if st.button("⬇️ Fetch latest", key="ni_daily", width="stretch"):
                with st.spinner("Fetching niftyindices.com snapshot…"):
                    summ = _niftyindices_collector().run_daily()
                st.success(f"Done — {summ.line()}")
                st.cache_data.clear()
        with ni2:
            ni_from = st.date_input("From", value=dt.date.today() - dt.timedelta(days=7), key="ni_from")
            ni_to = st.date_input("To", value=dt.date.today(), key="ni_to")
        if st.button("⏪ Backfill range", key="ni_bf", width="stretch"):
            if ni_from > ni_to:
                st.error("From date must be ≤ To date.")
            else:
                with st.spinner(f"Backfilling niftyindices {ni_from} → {ni_to}…"):
                    summ = _niftyindices_collector().run_backfill(ni_from, ni_to)
                st.success(f"Done — {summ.line()}")
                st.cache_data.clear()

    with card():
        st.markdown("#### 📄 Result PDFs")
        st.caption("Parse everything in `result-pdf/` into the fundamentals warehouse. "
                   "Full control and the parsed statements live on the "
                   "**📄 Result PDFs** page.")
        if st.button("📄 Parse result PDFs", key="pdf_parse_settings", width="stretch"):
            with st.spinner("Parsing PDFs — OCR can take a few minutes…"):
                code, log = _parse_results()
            st.cache_data.clear()
            (st.success if code == 0 else st.error)(
                "Parse finished." if code == 0 else "Parser exited with errors.")
            st.code(log, language="text")
    with card():
        st.markdown("#### 🤖 Result analyzer (agent)")
        st.caption("Hand a quarter folder to the `result-analyzer` agent — it grades every "
                   "filing GOOD / BAD / MIXED, appends the record to "
                   "`results-summary.json` and moves the PDF into `done/`. The graded "
                   "screener lives on the **📄 Result PDFs** page.")
        aq = result_pdf_quarters()
        if not aq:
            _hint("No quarter folders under `result-pdf/` — create e.g. `result-pdf/Q1FY27` "
                  "and drop the filings in.")
        else:
            ac1, ac2 = st.columns(2)
            with ac1:
                aquarter = st.selectbox("Quarter", aq, key="agent_quarter")
            apend = result_pending(aquarter)
            with ac2:
                ascope = st.selectbox("Scope", ["All pending"] + apend, key="agent_scope")
            st.caption(f"{len(apend)} PDF(s) pending in `result-pdf/{aquarter}/`.")
            if st.button("🤖 Run result-analyzer", key="agent_run", width="stretch",
                         type="primary", disabled=not apend):
                with st.spinner(f"Agent reading {aquarter} — this can take several minutes…"):
                    acode, alog = _run_analyzer(
                        aquarter, None if ascope == "All pending" else ascope)
                st.cache_data.clear()
                (st.success if acode == 0 else st.error)(
                    "Agent finished." if acode == 0 else "Agent exited with errors.")
                st.session_state["agent_log"] = alog
        if st.session_state.get("agent_log"):
            with st.expander("Agent output", expanded=True):
                st.code(st.session_state["agent_log"], language="text")
    with card():
        st.markdown("#### 📞 Concall reader (skill)")
        st.caption("Hand a quarter folder to the `concall-reader` skill — each transcript "
                   "becomes a transcript-only Markdown report + JSON snapshot that stay in "
                   "that quarter folder, then the PDF moves into `done/`. Read the reports on "
                   "the **📞 Concalls** page.")
        cq = concall_pdf_quarters()
        if not cq:
            _hint("No quarter folders under `concall-data/` — create e.g. "
                  "`concall-data/Q1FY27` and drop the transcripts in.")
        else:
            cc1, cc2 = st.columns(2)
            with cc1:
                cquarter = st.selectbox("Quarter", cq, key="concall_quarter")
            cpend = concall_pending(cquarter)
            with cc2:
                cscope = st.selectbox("Scope", ["All pending"] + cpend, key="concall_scope")
            st.caption(f"{len(cpend)} transcript(s) pending in `concall-data/{cquarter}/`.")
            if st.button("📞 Run concall-reader", key="concall_run", width="stretch",
                         type="primary", disabled=not cpend):
                n = 1 if cscope != "All pending" else len(cpend)
                with st.spinner(f"Reading {n} transcript(s)…"):
                    ccode, clog = _run_concall_analyzer(
                        cquarter, None if cscope == "All pending" else cscope)
                st.cache_data.clear()
                (st.success if ccode == 0 else st.error)(
                    "Concall reader finished." if ccode == 0
                    else "Concall reader exited with errors.")
                st.session_state["concall_log"] = clog
        if st.session_state.get("concall_log"):
            with st.expander("Agent output", expanded=True):
                st.code(st.session_state["concall_log"], language="text")

# ---------------------------------------------------------------- footer
st.markdown(T.footer(asof), unsafe_allow_html=True)
