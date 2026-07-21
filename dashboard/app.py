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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dashboard import loader as L  # noqa: E402
from dashboard import theme as T  # noqa: E402
from dashboard import signals as S  # noqa: E402
from dashboard import watchlist as W  # noqa: E402
from dashboard import derive as D  # noqa: E402
from dashboard import insights as I  # noqa: E402

st.set_page_config(page_title="NSE Investor Dashboard", page_icon="📈", layout="wide")
st.markdown(T.CSS, unsafe_allow_html=True)

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


# ---------------------------------------------------------------- sidebar
st.sidebar.markdown("## 📈 NSE Dashboard")
st.sidebar.caption("Investor view over the local CSV warehouse")
if st.sidebar.button("🔄 Reload data"):
    st.cache_data.clear()
    st.rerun()

asof = L.snapshot_asof("all_indices") or L.snapshot_asof("top_gainers")

PAGES = ["📊 Market Pulse", "🏆 Conviction", "🎯 Signals", "📞 Concalls", "🚀 Movers", "🗓️ Day Explorer",
         "💰 Smart Money", "📉 Derivatives & FII", "📦 Delivery & Value",
         "🧭 Sectors", "🗂️ Filings", "🔔 Need Attention", "📈 History", "🩺 Data Health"]
PAGE = st.sidebar.radio("nav", PAGES, label_visibility="collapsed")

st.sidebar.markdown("---")
if asof:
    st.sidebar.metric("Snapshot as of", asof)
st.sidebar.caption(f"warehouse: {L.DATA_DIR}")


def _collector(polite: float = 1.0):
    from nse_collector.collector import Collector, setup_logging
    from nse_collector.config import Settings
    s = Settings()
    s.data_dir = L.DATA_DIR
    s.log_dir = os.path.join(os.path.dirname(L.DATA_DIR), "logs")
    s.polite_delay = polite
    setup_logging(s)
    return Collector(s)


st.sidebar.markdown("### ⚙️ Fetch data")
with st.sidebar.expander("Run collector from here", expanded=False):
    if st.button("⬇️ Fetch latest (daily job)", key="fetch_daily", width="stretch"):
        with st.spinner("Fetching from NSE… (snapshots + today's reports)"):
            summ = _collector().run_daily()
        st.success(f"Done — {summ.line()}")
        st.cache_data.clear()

    st.caption("Backfill past dates (historical / per-date reports)")
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
    st.caption("Snapshots (gainers, breadth, option chain) are live-only and "
               "cannot be backfilled — only per-date reports & deal windows.")

with st.sidebar.expander("Fetch BSE data", expanded=False):
    st.caption("BSE EOD bhav copy (BSE-listed universe, ~4800 scrips) — the "
               "non-overlapping BSE data. Scraped from bseindia.com.")

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
st.sidebar.markdown("---")
st.sidebar.caption("Signals are educational, from public data — not investment advice.")

# ---------------------------------------------------------------- hero
st.markdown(T.hero(f"{PAGE}",
                   f"NSE / BSE investor dashboard &nbsp;|&nbsp; as of {asof or '—'}"),
            unsafe_allow_html=True)

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
        dcol, _sp = st.columns([1, 2])
        with dcol:
            with card():
                st.markdown("#### Breadth split")
                donut = pd.DataFrame({"cat": ["Advances", "Declines", "Unchanged"],
                                      "count": [adv, dec, unc]})
                st.vega_lite_chart(donut, {
                    "width": "container", "height": 200,
                    "mark": {"type": "arc", "innerRadius": 55},
                    "encoding": {
                        "theta": {"field": "count", "type": "quantitative"},
                        "color": {"field": "cat", "type": "nominal",
                                  "scale": {"domain": ["Advances", "Declines", "Unchanged"],
                                            "range": [T.GREEN, T.CORAL, "#B8BCCB"]},
                                  "legend": {"title": None}},
                        "tooltip": [{"field": "cat"}, {"field": "count"}],
                    },
                })
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
            st.markdown("#### All indices — valuation & momentum")
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
                st.bar_chart(rank.nlargest(10), color=T.GREEN, horizontal=True)
        with b2:
            with card():
                st.markdown("#### Top 10 losing indices")
                st.bar_chart(rank.nsmallest(10), color=T.CORAL, horizontal=True)
    else:
        _hint()

# ================================================================ Conviction
def _conv_data():
    return dict(bhav=load_per_date("bhavcopy_delivery"), bulk=load_growing("bulk_deals"),
                block=load_growing("block_deals"), ban=load_per_date("securities_in_ban"),
                vol=load_per_date("daily_volatility"), pe=load_per_date("pe_ratio"),
                most_active=load_snapshot_latest("most_active_value"))


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
            st.markdown("#### Full conviction leaderboard")
            st.dataframe(
                lb.style.background_gradient(subset=["Score"], cmap="RdYlGn")
                        .format({"Score": "{:+d}", "Deliv%": "{:.0f}", "%Chg": "{:+.2f}"}, na_rep="-"),
                width="stretch", height=560, hide_index=True)


if PAGE == "📊 Market Pulse":
    with card():
        st.markdown("#### 🏆 Top conviction — stocks with aligned signals")
        lb5 = S.rank_ideas(**_conv_data())
        if lb5.empty:
            _hint("Fetch/backfill bhav copy to compute conviction.")
        else:
            st.dataframe(
                lb5.head(5).style.background_gradient(subset=["Score"], cmap="RdYlGn")
                   .format({"Score": "{:+d}", "Deliv%": "{:.0f}", "%Chg": "{:+.2f}"}, na_rep="-"),
                width="stretch", hide_index=True)
            st.caption("See the **🏆 Conviction** tab for the full leaderboard.")


# ================================================================ Signals
if PAGE == "🎯 Signals":
    st.caption("⚠️ Educational decision-support from public NSE data — positioning, "
               "conviction and risk, **not** price prediction or investment advice. "
               "Every score is transparent (sum of the named factors below). Do your own research.")

    idx = load_snapshot_latest("all_indices")
    ad = load_snapshot_latest("advances_declines")
    reg = S.market_regime(idx, ad)
    with card():
        st.markdown("#### Market regime — is this an environment to buy?")
        st.markdown(T.stat_row([
            T.stat_card("Regime", reg["label"], f"breadth+VIX score {reg['score']:+d}", reg["tone"]),
        ]), unsafe_allow_html=True)
        for r in reg["reasons"]:
            st.markdown(f"- {r}")
        if not reg["reasons"]:
            _hint("Run the collector to populate breadth/index data.")

    with card():
        st.markdown("#### Stock signal scorecard")
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
                    st.line_chart(t.set_index("_date")["Delivery %"], color=T.INDIGO)
        else:
            st.info("Enter a symbol to generate its scorecard.")

    sc1, sc2 = st.columns(2)
    bhav = load_per_date("bhavcopy_delivery")
    with sc1:
        with card():
            st.markdown("#### 🟢 Accumulation candidates")
            st.caption("High delivery % **and** price up = genuine buying, not churn.")
            acc = S.screen_accumulation(bhav)
            st.dataframe(acc, width="stretch", height=340, hide_index=True) if not acc.empty else _hint()
    with sc2:
        with card():
            st.markdown("#### 🔴 Distribution warnings")
            st.caption("High delivery % **and** price down = strong hands offloading.")
            dis = S.screen_distribution(bhav)
            st.dataframe(dis, width="stretch", height=340, hide_index=True) if not dis.empty else _hint()

    bk1, bk2 = st.columns([1, 1])
    with bk1:
        with card():
            st.markdown("#### 🚀 52-week breakouts")
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
            st.markdown("#### 🏦 Institutional buys today")
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
        st.markdown("#### ⭐ Today's top ideas (ranked)")
        st.caption("High-delivery stocks that rose today, re-scored across all factors and ranked. "
                   "Cross-check with the market regime above before acting.")
        ideas = S.rank_ideas(**_sig_data)
        if not ideas.empty:
            st.dataframe(
                ideas.style.background_gradient(subset=["Score"], cmap="RdYlGn")
                           .format({"Score": "{:+d}", "Deliv%": "{:.0f}", "%Chg": "{:+.2f}"}, na_rep="-"),
                width="stretch", height=380, hide_index=True)
        else:
            _hint("No ideas — needs bhav copy collected for the latest trading day.")

    with card():
        st.markdown("#### 📌 Watchlist")
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
        if idx.empty:
            _hint("No concalls parsed for this quarter.")
        else:
            buy = int((idx["Call"] == "BUY").sum())
            hold = int(idx["Call"].isin(["HOLD"]).sum())
            avoid = int(idx["Call"].isin(["AVOID", "SELL"]).sum())
            conf = pd.to_numeric(idx["Confidence"], errors="coerce")
            st.markdown(T.stat_row([
                T.stat_card("Companies", f"{len(idx)}", q, "neutral"),
                T.stat_card("BUY", f"{buy}", "bullish verdicts", "up"),
                T.stat_card("HOLD / AVOID", f"{hold} / {avoid}", "cautious", "down"),
                T.stat_card("Avg confidence", f"{conf.mean():.1f}/10" if conf.notna().any() else "—",
                            "mgmt tone", "neutral"),
            ]), unsafe_allow_html=True)

            with card():
                st.markdown("#### All concalls")
                colf1, colf2 = st.columns([1, 2])
                vf = colf1.selectbox("Filter call", ["All", "BUY", "HOLD", "AVOID/SELL"], key="cc_vf")
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
                tone = {"BUY": "up", "GOOD": "up"}.get(row["Call"] or row["Verdict"], None)
                tone = "up" if row["Call"] == "BUY" or row["Verdict"] == "GOOD" else (
                    "down" if row["Call"] in ("AVOID", "SELL") or row["Verdict"] == "BAD" else "neutral")
                badges = "".join([
                    T.badge(row["Verdict"] or "—", tone) + " ",
                    T.badge(row["Call"] or "—", tone) + " ",
                    T.badge(f"conf {row['Confidence'] or '?'}/10", "neutral"),
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

# ================================================================ Movers
if PAGE == "🚀 Movers":
    g, l = load_snapshot_latest("top_gainers"), load_snapshot_latest("top_losers")
    legends = sorted(set(g.get("legend", pd.Series(dtype=str)).dropna().unique())
                     | set(l.get("legend", pd.Series(dtype=str)).dropna().unique()))
    default = ["allSec"] + [x for x in legends if x != "allSec"] if "allSec" in legends else legends or ["(none)"]
    bucket = st.selectbox("Index bucket", default)

    def _movers(df):
        if df.empty:
            return df
        df = _num(df, ["ltp", "net_price", "perChange", "turnover"])
        if "legend" in df.columns and bucket in df["legend"].values:
            df = df[df["legend"] == bucket]
        keep = [c for c in ["symbol", "ltp", "net_price", "perChange", "trade_quantity", "turnover"] if c in df.columns]
        return df[keep].sort_values("perChange", ascending=False, na_position="last")

    mc1, mc2 = st.columns(2)
    with mc1:
        with card():
            st.markdown("#### 🟢 Top gainers")
            gg = _movers(g)
            st.dataframe(gg, width="stretch", height=360, hide_index=True) if not gg.empty else _hint()
    with mc2:
        with card():
            st.markdown("#### 🔴 Top losers")
            ll = _movers(l)
            st.dataframe(ll.sort_values("perChange"), width="stretch", height=360, hide_index=True) if not ll.empty else _hint()

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
                st.dataframe(df[keep], width="stretch", height=300, hide_index=True)

# ================================================================ Smart Money
if PAGE == "💰 Smart Money":
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
            st.dataframe(v, width="stretch", height=300, hide_index=True)

    s1, s2 = st.columns(2)
    with s1:
        with card():
            st.markdown("#### Short selling")
            ss = load_growing("short_selling")
            st.dataframe(_num(ss, ["Quantity"]), width="stretch", height=280, hide_index=True) if not ss.empty else _hint()
    with s2:
        with card():
            st.markdown("#### Upcoming corporate actions")
            ca = load_growing("corporate_actions")
            if not ca.empty and "exDate" in ca.columns:
                ca = ca.copy()
                ca["_ex"] = pd.to_datetime(ca["exDate"], errors="coerce", dayfirst=True)
                upcoming = ca[ca["_ex"] >= pd.Timestamp.today().normalize()].sort_values("_ex")
                keep = [c for c in ["symbol", "series", "subject", "exDate", "recDate", "faceVal"] if c in ca.columns]
                st.dataframe(upcoming[keep] if not upcoming.empty else ca[keep],
                             width="stretch", height=280, hide_index=True)
                if upcoming.empty:
                    st.caption("No ex-dates ahead in the window; showing all.")
            else:
                _hint()

# ================================================================ Derivatives & FII
if PAGE == "📉 Derivatives & FII":
    with card():
        st.markdown("#### Participant positioning — net index futures (long − short)")
        st.caption("Positive = net long / bullish. Watch FII vs Client divergence.")
        poi = load_per_date("participant_oi")
        if not poi.empty and "Client Type" in poi.columns:
            p = _num(poi, ["Future Index Long", "Future Index Short",
                           "Total Long Contracts", "Total Short Contracts"])
            p = p[p["Client Type"].astype(str).str.upper() != "TOTAL"]
            p["Net Index Fut"] = p["Future Index Long"] - p["Future Index Short"]
            st.bar_chart(p.set_index("Client Type")["Net Index Fut"],
                         color=T.INDIGO, horizontal=True)
            st.dataframe(p[["Client Type", "Future Index Long", "Future Index Short",
                            "Net Index Fut", "Total Long Contracts", "Total Short Contracts"]],
                         width="stretch", hide_index=True)
        else:
            _hint()

    with card():
        st.markdown("#### FII derivatives — net stance (₹ Cr)")
        fii = load_per_date("fii_deriv_stats")
        if not fii.empty and "fii_derivatives" in fii.columns:
            f = _num(fii, ["buy_value_in_Cr", "sell_value_in_Cr", "open_contracts_value_in_Cr"])
            f["Net Buy (Cr)"] = f["buy_value_in_Cr"] - f["sell_value_in_Cr"]
            st.bar_chart(f.set_index("fii_derivatives")["Net Buy (Cr)"], color=T.CORAL)
            st.dataframe(f[["fii_derivatives", "buy_value_in_Cr", "sell_value_in_Cr",
                            "Net Buy (Cr)", "open_contracts_value_in_Cr"]],
                         width="stretch", hide_index=True)
        else:
            _hint("FII stats need xlrd + the report published for the date.")

    d1, d2 = st.columns(2)
    with d1:
        with card():
            st.markdown("#### Most active underlying")
            mau = load_snapshot_latest("most_active_underlying")
            if not mau.empty:
                mau = _num(mau, ["totTurnover", "latestOI", "totVolume"])
                keep = [c for c in ["symbol", "totVolume", "totTurnover", "latestOI"] if c in mau.columns]
                st.dataframe(mau[keep].sort_values("totTurnover", ascending=False),
                             width="stretch", height=300, hide_index=True)
            else:
                _hint()
    with d2:
        with card():
            st.markdown("#### Securities in F&O ban")
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
        st.markdown("#### Delivery analysis — conviction accumulation")
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
            min_to = st.slider("Min turnover (₹ lacs)", 0, 5000, 500, 100)
            b = b[b["TURNOVER_LACS"] >= min_to]
            keep = [c for c in ["SYMBOL", "CLOSE_PRICE", "%Chg", "DELIV_PER", "TTL_TRD_QNTY",
                                "DELIV_QTY", "TURNOVER_LACS"] if c in b.columns]
            top = b.sort_values("DELIV_PER", ascending=False)[keep].head(50)
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
            st.markdown("#### P/E lookup")
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
            st.markdown("#### Highest volatility (F&O underlyings)")
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
                st.bar_chart(sec.set_index("index")["percentChange"], color=T.INDIGO, horizontal=True)
            with card():
                st.markdown("#### Sector trend table (today / 30d / 365d + valuation)")
                v = sec[["index", "percentChange", "perChange30d", "perChange365d", "pe", "pb", "dy"]].copy()
                v.columns = ["Sector", "%Chg", "%Chg 30d", "%Chg 365d", "P/E", "P/B", "Div Yld"]
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
        st.markdown("#### Corporate announcements")
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
            show = [c for c in ["Filed", "symbol", "Company", "Subject", "Industry", "Attachment"] if c in v.columns]
            st.dataframe(v[show].head(300), width="stretch", height=430, hide_index=True,
                         column_config={"Attachment": st.column_config.LinkColumn("Attachment")})
            st.caption(f"{len(v)} filings (showing up to 300).")

    with card():
        st.markdown("#### 📅 Earnings / events calendar")
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
        st.markdown("#### Corporate actions (dividends / splits / bonus)")
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

        with card():
            st.markdown("#### Flagged events")
            evf = st.selectbox("Event type", ["All"] + list(_EVENTS.keys()), key="na_ev")
            v = flagged if evf == "All" else flagged[flagged["Event"] == evf]
            show = [c for c in ["Filed", "Event", "symbol", "Company", "Subject", "Attachment"] if c in v.columns]
            if v.empty:
                st.success("No such events in the collected window.")
            else:
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
                st.markdown("#### Price (OHLC candlestick)")
                if len(h) >= 1 and {"OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE"} <= set(h.columns):
                    recs = h[["date", "OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE"]].rename(
                        columns={"OPEN_PRICE": "open", "HIGH_PRICE": "high",
                                 "LOW_PRICE": "low", "CLOSE_PRICE": "close"})
                    color = {"condition": {"test": "datum.open <= datum.close", "value": T.GREEN},
                             "value": T.CORAL}
                    st.vega_lite_chart(recs, {
                        "width": "container", "height": 360,
                        "encoding": {"x": {"field": "date", "type": "temporal", "title": None}},
                        "layer": [
                            {"mark": "rule",
                             "encoding": {"y": {"field": "low", "type": "quantitative",
                                                "scale": {"zero": False}, "title": "Price"},
                                          "y2": {"field": "high"}, "color": color}},
                            {"mark": {"type": "bar", "size": 6},
                             "encoding": {"y": {"field": "open", "type": "quantitative"},
                                          "y2": {"field": "close"}, "color": color,
                                          "tooltip": [{"field": "date"}, {"field": "open"},
                                                      {"field": "high"}, {"field": "low"},
                                                      {"field": "close"}]}},
                        ],
                    })

            cH1, cH2 = st.columns(2)
            with cH1:
                with card():
                    st.markdown("#### Volume traded")
                    st.bar_chart(h.set_index("date")["TTL_TRD_QNTY"], color=T.INDIGO)
            with cH2:
                with card():
                    if has_deliv:
                        st.markdown("#### Delivery % trend")
                        st.line_chart(h.set_index("date")["DELIV_PER"], color=T.GREEN)
                    else:
                        st.markdown("#### Close price trend")
                        st.line_chart(h.set_index("date")["CLOSE_PRICE"], color=T.GREEN)
    else:
        st.info("Search a symbol to see its history.")

# ================================================================ Day Explorer
if PAGE == "🗓️ Day Explorer":
    st.caption("Datewise view derived from the bhav copy — gainers, losers, most "
               "active and breadth for ANY collected trading day (NSE doesn't "
               "archive these snapshots, so we recompute them from the day's bhav copy).")
    dates = per_date_dates("bhavcopy_delivery")
    if not dates:
        _hint("No bhav copies collected yet — backfill dates in the sidebar.")
    else:
        pick = st.selectbox("Trading date", list(reversed(dates)), key="day_pick")
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

        dcol, _sp = st.columns([1, 2])
        with dcol:
            with card():
                st.markdown("#### Breadth split")
                st.vega_lite_chart(
                    pd.DataFrame({"cat": ["Advances", "Declines", "Unchanged"],
                                  "count": [adv, dec, br["Unchanged"]]}),
                    {"width": "container", "height": 190,
                     "mark": {"type": "arc", "innerRadius": 50},
                     "encoding": {"theta": {"field": "count", "type": "quantitative"},
                                  "color": {"field": "cat", "type": "nominal",
                                            "scale": {"domain": ["Advances", "Declines", "Unchanged"],
                                                      "range": [T.GREEN, T.CORAL, "#B8BCCB"]},
                                            "legend": {"title": None}}}})

        g1, g2 = st.columns(2)
        with g1:
            with card():
                st.markdown("#### 🟢 Top gainers")
                st.dataframe(D.gainers(bhav).style.format(
                    {"CLOSE_PRICE": "{:,.2f}", "%Chg": "{:+.2f}", "DELIV_PER": "{:.0f}",
                     "TURNOVER_LACS": "{:,.0f}"}, na_rep="-"),
                    width="stretch", height=340, hide_index=True)
        with g2:
            with card():
                st.markdown("#### 🔴 Top losers")
                st.dataframe(D.losers(bhav).style.format(
                    {"CLOSE_PRICE": "{:,.2f}", "%Chg": "{:+.2f}", "DELIV_PER": "{:.0f}",
                     "TURNOVER_LACS": "{:,.0f}"}, na_rep="-"),
                    width="stretch", height=340, hide_index=True)

        a1, a2 = st.columns(2)
        with a1:
            with card():
                st.markdown("#### Most active — value")
                st.dataframe(D.most_active(bhav, "value"), width="stretch", height=320, hide_index=True)
        with a2:
            with card():
                st.markdown("#### Most active — volume")
                st.dataframe(D.most_active(bhav, "volume"), width="stretch", height=320, hide_index=True)

# ================================================================ Data Health
if PAGE == "🩺 Data Health":
    with card():
        st.markdown("#### Collection health")
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
            st.dataframe(last[keep].sort_values("dataset"), width="stretch",
                         height=460, hide_index=True)
        else:
            _hint("No manifest yet — run the collector.")
