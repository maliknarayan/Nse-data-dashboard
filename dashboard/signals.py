"""Decision-support signals derived from the warehouse.

Transparent by design: every score is a sum of named factors, each with a
plain-language reason. Nothing here predicts price — it summarises positioning,
conviction, and risk from public NSE data. Not investment advice.

Pure functions over DataFrames so they unit-test offline without Streamlit.
"""

from __future__ import annotations

import pandas as pd

from .loader import to_num


# --------------------------------------------------------------- market regime
def market_regime(indices: pd.DataFrame, advances_declines: pd.DataFrame) -> dict:
    """Risk-On / Neutral / Risk-Off for the whole market, with reasons."""
    reasons: list[str] = []
    score = 0

    # breadth: advance/decline ratio
    if not advances_declines.empty and {"metric", "value"} <= set(advances_declines.columns):
        m = dict(zip(advances_declines["metric"], to_num(advances_declines["value"])))
        adv, dec = m.get("Advances", 0), m.get("Declines", 0)
        ratio = (adv / dec) if dec else 0
        if ratio >= 1.5:
            score += 2; reasons.append(f"Strong breadth — A/D ratio {ratio:.2f} (many more stocks up)")
        elif ratio >= 1.0:
            score += 1; reasons.append(f"Positive breadth — A/D ratio {ratio:.2f}")
        elif ratio <= 0.7:
            score -= 2; reasons.append(f"Weak breadth — A/D ratio {ratio:.2f} (broad selling)")
        else:
            score -= 1; reasons.append(f"Soft breadth — A/D ratio {ratio:.2f}")

    if not indices.empty and "percentChange" in indices.columns:
        pc = to_num(indices["percentChange"]).dropna()
        if len(pc):
            up_share = (pc > 0).mean()
            if up_share >= 0.6:
                score += 1; reasons.append(f"{up_share:.0%} of indices green")
            elif up_share <= 0.4:
                score -= 1; reasons.append(f"only {up_share:.0%} of indices green")

        # India VIX — fear gauge
        vix_row = indices[indices["index"].astype(str).str.upper() == "INDIA VIX"]
        if not vix_row.empty:
            vix = to_num(vix_row["last"]).iloc[0]
            if pd.notna(vix):
                if vix < 13:
                    score += 1; reasons.append(f"India VIX low ({vix:.1f}) — calm")
                elif vix > 20:
                    score -= 2; reasons.append(f"India VIX high ({vix:.1f}) — fear")
                elif vix > 16:
                    score -= 1; reasons.append(f"India VIX elevated ({vix:.1f})")

    if score >= 2:
        label, tone = "Risk-On", "up"
    elif score <= -2:
        label, tone = "Risk-Off", "down"
    else:
        label, tone = "Neutral", "neutral"
    return {"label": label, "tone": tone, "score": score, "reasons": reasons}


# ------------------------------------------------------------- stock scorecard
def _u(s: pd.Series) -> pd.Series:
    return s.astype(str).str.upper().str.strip()


def stock_scorecard(symbol: str, *, bhav: pd.DataFrame, bulk: pd.DataFrame,
                    block: pd.DataFrame, ban: pd.DataFrame, vol: pd.DataFrame,
                    pe: pd.DataFrame, most_active: pd.DataFrame) -> dict:
    """Transparent factor scorecard for one symbol. Returns verdict + factors."""
    sym = symbol.upper().strip()
    factors: list[dict] = []  # {name, points, note}

    def add(name, points, note):
        factors.append({"factor": name, "points": points, "note": note})

    # --- delivery conviction + accumulation/distribution ---
    row = pd.DataFrame()
    if not bhav.empty and "SYMBOL" in bhav.columns:
        b = bhav.copy()
        b = b[_u(b["SYMBOL"]) == sym]
        if "SERIES" in b.columns:
            b = b[b["SERIES"].isin(["EQ", "BE"])] if len(b) else b
        row = b
    if not row.empty:
        r = row.iloc[0]
        deliv = to_num(pd.Series([r.get("DELIV_PER")])).iloc[0]
        close = to_num(pd.Series([r.get("CLOSE_PRICE")])).iloc[0]
        prev = to_num(pd.Series([r.get("PREV_CLOSE")])).iloc[0]
        chg = ((close - prev) / prev * 100) if (pd.notna(close) and pd.notna(prev) and prev) else None

        if pd.notna(deliv):
            if deliv >= 60:
                add("Delivery conviction", 2, f"Very high delivery {deliv:.0f}% — strong hands")
            elif deliv >= 45:
                add("Delivery conviction", 1, f"Above-average delivery {deliv:.0f}%")
            elif deliv < 25:
                add("Delivery conviction", -1, f"Low delivery {deliv:.0f}% — speculative churn")
            # accumulation vs distribution
            if chg is not None:
                if deliv >= 45 and chg > 1:
                    add("Accumulation", 2, f"High delivery + price up {chg:+.1f}% — genuine buying")
                elif deliv >= 45 and chg < -1:
                    add("Distribution risk", -2, f"High delivery + price down {chg:+.1f}% — strong hands selling")
        if chg is not None:
            add("Price action", 1 if chg > 2 else (-1 if chg < -2 else 0),
                f"Close {chg:+.1f}% vs prev")
    else:
        add("Data", 0, "No bhav copy row (non-EQ or not collected yet)")

    # --- smart money: bulk/block deals ---
    def deal_side(df, label):
        if df.empty or "Symbol" not in df.columns:
            return
        d = df[_u(df["Symbol"]) == sym]
        if d.empty or "Buy/Sell" not in d.columns:
            return
        sides = _u(d["Buy/Sell"])
        buys = sides.str.startswith("B").sum()
        sells = sides.str.startswith("S").sum()
        if buys > sells:
            add(f"{label} (smart money)", 1, f"{buys} buy vs {sells} sell trades")
        elif sells > buys:
            add(f"{label} (smart money)", -1, f"{sells} sell vs {buys} buy trades")
    deal_side(bulk, "Bulk deals")
    deal_side(block, "Block deals")

    # --- attention/liquidity ---
    if not most_active.empty and "symbol" in most_active.columns:
        if sym in set(_u(most_active["symbol"])):
            add("Liquidity", 0, "Among most-active — liquid, high attention")

    # --- risk flags ---
    if not ban.empty:
        col = "value" if "value" in ban.columns else ban.columns[0]
        if sym in set(_u(ban[col])):
            add("F&O ban", -2, "In F&O ban — avoid fresh leveraged longs")
    if not vol.empty:
        scol = "Symbol" if "Symbol" in vol.columns else None
        vcol = next((c for c in vol.columns if "Annualised" in c), None)
        if scol and vcol:
            vr = vol[_u(vol[scol]) == sym]
            if not vr.empty:
                av = to_num(pd.Series([vr.iloc[0][vcol]])).iloc[0]
                if pd.notna(av) and av > 0.5:
                    add("Volatility", -1, f"High annualised vol {av:.0%} — size down")

    # --- valuation (crude, P/E only) ---
    if not pe.empty:
        scol = "SYMBOL" if "SYMBOL" in pe.columns else pe.columns[0]
        pcol = next((c for c in pe.columns if "P/E" in c.upper()), None)
        pr = pe[_u(pe[scol]) == sym]
        if not pr.empty and pcol:
            val = to_num(pd.Series([pr.iloc[0][pcol]])).iloc[0]
            if pd.notna(val):
                if val <= 0:
                    add("Valuation", -1, "Negative earnings (P/E n/a)")
                elif val > 60:
                    add("Valuation", -1, f"Rich valuation — P/E {val:.0f}")
                elif val < 15:
                    add("Valuation", 1, f"Low P/E {val:.0f}")

    total = sum(f["points"] for f in factors)
    if total >= 3:
        verdict, tone = "Accumulation signs — constructive", "up"
    elif total >= 1:
        verdict, tone = "Mildly positive", "up"
    elif total <= -3:
        verdict, tone = "Distribution / Avoid", "down"
    elif total <= -1:
        verdict, tone = "Caution", "down"
    else:
        verdict, tone = "Neutral / watch", "neutral"

    return {"symbol": sym, "score": total, "verdict": verdict, "tone": tone,
            "factors": factors}


# ------------------------------------------------------------------- screeners
def _bhav_eq(bhav: pd.DataFrame, min_turnover_lacs: float) -> pd.DataFrame:
    if bhav.empty:
        return pd.DataFrame()
    b = bhav.copy()
    if "SERIES" in b.columns:
        b = b[b["SERIES"] == "EQ"]
    for c in ["CLOSE_PRICE", "PREV_CLOSE", "DELIV_PER", "TURNOVER_LACS", "TTL_TRD_QNTY"]:
        if c in b.columns:
            b[c] = to_num(b[c])
    b["%Chg"] = (b["CLOSE_PRICE"] - b["PREV_CLOSE"]) / b["PREV_CLOSE"] * 100
    if "TURNOVER_LACS" in b.columns:
        b = b[b["TURNOVER_LACS"] >= min_turnover_lacs]
    return b


def screen_accumulation(bhav, min_turnover_lacs=500, min_deliv=50):
    b = _bhav_eq(bhav, min_turnover_lacs)
    if b.empty:
        return b
    hit = b[(b["DELIV_PER"] >= min_deliv) & (b["%Chg"] > 0)]
    return hit.sort_values("DELIV_PER", ascending=False)[
        ["SYMBOL", "CLOSE_PRICE", "%Chg", "DELIV_PER", "TURNOVER_LACS"]].head(40)


def screen_distribution(bhav, min_turnover_lacs=500, min_deliv=50):
    b = _bhav_eq(bhav, min_turnover_lacs)
    if b.empty:
        return b
    hit = b[(b["DELIV_PER"] >= min_deliv) & (b["%Chg"] < 0)]
    return hit.sort_values("DELIV_PER", ascending=False)[
        ["SYMBOL", "CLOSE_PRICE", "%Chg", "DELIV_PER", "TURNOVER_LACS"]].head(40)


def score_many(symbols, *, bhav, bulk, block, ban, vol, pe, most_active) -> pd.DataFrame:
    """Run the scorecard over a list of symbols -> ranked summary table."""
    rows = []
    for sym in symbols:
        sc = stock_scorecard(sym, bhav=bhav, bulk=bulk, block=block, ban=ban,
                             vol=vol, pe=pe, most_active=most_active)
        rows.append({"Symbol": sc["symbol"], "Score": sc["score"],
                     "Verdict": sc["verdict"]})
    if not rows:
        return pd.DataFrame(columns=["Symbol", "Score", "Verdict"])
    return pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)


def rank_ideas(*, bhav, bulk, block, ban, vol, pe, most_active,
               min_turnover_lacs=1000, top_universe=40) -> pd.DataFrame:
    """Today's actionable ideas: score the high-delivery/up universe, rank by score."""
    uni = screen_accumulation(bhav, min_turnover_lacs=min_turnover_lacs, min_deliv=45)
    if uni.empty:
        return pd.DataFrame(columns=["Symbol", "Score", "Verdict"])
    syms = uni["SYMBOL"].astype(str).head(top_universe).tolist()
    ranked = score_many(syms, bhav=bhav, bulk=bulk, block=block, ban=ban,
                        vol=vol, pe=pe, most_active=most_active)
    # attach delivery + %chg for context
    ctx = uni.set_index("SYMBOL")[["DELIV_PER", "%Chg"]]
    ranked = ranked.merge(ctx, left_on="Symbol", right_index=True, how="left")
    return ranked.rename(columns={"DELIV_PER": "Deliv%"})


def screen_breakouts(bhav, week52, min_turnover_lacs=1000, near_pct=5):
    """Stocks trading at/near their 52-week high — momentum breakouts."""
    b = _bhav_eq(bhav, min_turnover_lacs)
    if b.empty or week52.empty or "SYMBOL" not in week52.columns:
        return pd.DataFrame()
    w = week52.copy()
    w["52wHigh"] = to_num(w["Adjusted_52_Week_High"])
    w = w[["SYMBOL", "52wHigh"]].dropna()
    m = b.merge(w, on="SYMBOL", how="inner")
    m["%FromHigh"] = (m["CLOSE_PRICE"] - m["52wHigh"]) / m["52wHigh"] * 100
    hit = m[m["CLOSE_PRICE"] >= m["52wHigh"] * (1 - near_pct / 100)]
    keep = ["SYMBOL", "CLOSE_PRICE", "52wHigh", "%FromHigh", "%Chg",
            "DELIV_PER", "TURNOVER_LACS"]
    return hit.sort_values("%FromHigh", ascending=False)[
        [c for c in keep if c in hit.columns]].head(40)


def compute_alerts(current: pd.DataFrame, prev_state: dict) -> list[dict]:
    """Flag watchlist symbols whose signal changed materially since last run."""
    alerts = []
    if current.empty:
        return alerts
    for _, r in current.iterrows():
        sym, now = r["Symbol"], int(r["Score"])
        was = prev_state.get(sym)
        if was is None:
            continue
        was = int(was)
        if now < 0 <= was:
            alerts.append({"symbol": sym, "change": f"turned cautious ({was:+d} → {now:+d})", "tone": "down"})
        elif was - now >= 3:
            alerts.append({"symbol": sym, "change": f"weakening ({was:+d} → {now:+d})", "tone": "down"})
        elif now - was >= 3:
            alerts.append({"symbol": sym, "change": f"strengthening ({was:+d} → {now:+d})", "tone": "up"})
    return alerts


def screen_institutional_buys(bulk: pd.DataFrame):
    if bulk.empty or "Buy/Sell" not in bulk.columns:
        return pd.DataFrame()
    d = bulk.copy()
    d = d[_u(d["Buy/Sell"]).str.startswith("B")]
    q, p = "QuantityTraded", "TradePrice/Wght.Avg.Price"
    if {q, p} <= set(d.columns):
        d[q], d[p] = to_num(d[q]), to_num(d[p])
        d["Value(Cr)"] = (d[q] * d[p]) / 1e7
        keep = [c for c in ["Date", "Symbol", "ClientName", "QuantityTraded",
                            "TradePrice/Wght.Avg.Price", "Value(Cr)"] if c in d.columns]
        return d.sort_values("Value(Cr)", ascending=False)[keep].head(40)
    return d.head(40)
