"""Tier-1 investor insights: delivery-spike scanner, FII/Client divergence,
portfolio X-ray, and the daily 'what changed' digest. Pure functions over the
warehouse DataFrames so they stay testable and backend-agnostic.
"""

from __future__ import annotations

import re

import pandas as pd

from .loader import to_num


# ----------------------------------------------------------- delivery spike
def delivery_spike(bhav_all: pd.DataFrame, lookback: int = 20,
                   min_turnover_lacs: float = 500, min_ratio: float = 1.5) -> pd.DataFrame:
    """Latest-day delivery% vs each symbol's trailing average — quiet accumulation."""
    if bhav_all.empty or "SYMBOL" not in bhav_all.columns:
        return pd.DataFrame()
    b = bhav_all.copy()
    if "SERIES" in b.columns:
        b = b[b["SERIES"] == "EQ"]
    for c in ["DELIV_PER", "CLOSE_PRICE", "PREV_CLOSE", "TURNOVER_LACS"]:
        if c in b.columns:
            b[c] = to_num(b[c])
    b = b.sort_values("_date")
    last_date = b["_date"].max()
    rows = []
    for sym, g in b.groupby("SYMBOL"):
        if len(g) < 3:
            continue
        cur = g.iloc[-1]
        if cur["_date"] != last_date or pd.isna(cur.get("DELIV_PER")):
            continue
        if (cur.get("TURNOVER_LACS") or 0) < min_turnover_lacs:
            continue
        prior = g.iloc[max(0, len(g) - 1 - lookback):-1]["DELIV_PER"].dropna()
        if prior.empty or prior.mean() == 0:
            continue
        ratio = cur["DELIV_PER"] / prior.mean()
        if ratio >= min_ratio:
            chg = ((cur["CLOSE_PRICE"] - cur["PREV_CLOSE"]) / cur["PREV_CLOSE"] * 100
                   if pd.notna(cur.get("PREV_CLOSE")) and cur["PREV_CLOSE"] else None)
            rows.append({"Symbol": sym, "Deliv%": round(cur["DELIV_PER"], 1),
                         "Avg Deliv%": round(prior.mean(), 1), "Spike x": round(ratio, 2),
                         "%Chg": round(chg, 2) if chg is not None else None,
                         "Close": cur["CLOSE_PRICE"]})
    return pd.DataFrame(rows).sort_values("Spike x", ascending=False).head(50) if rows else pd.DataFrame()


# --------------------------------------------------- FII vs Client divergence
def fii_client_divergence(poi_all: pd.DataFrame) -> pd.DataFrame:
    """Net index-future contracts (long-short) per date for FII vs Client."""
    if poi_all.empty or "Client Type" not in poi_all.columns:
        return pd.DataFrame()
    p = poi_all.copy()
    for c in ["Future Index Long", "Future Index Short"]:
        if c in p.columns:
            p[c] = to_num(p[c])
    p["net"] = p["Future Index Long"] - p["Future Index Short"]
    p["ct"] = p["Client Type"].astype(str).str.upper().str.strip()
    out = []
    for d, g in p.groupby("_date"):
        row = {"date": d}
        for label, key in [("FII", "FII"), ("Client", "CLIENT"), ("DII", "DII"), ("Pro", "PRO")]:
            m = g[g["ct"] == key]
            row[label] = int(m["net"].iloc[0]) if not m.empty else None
        out.append(row)
    return pd.DataFrame(out).sort_values("date").reset_index(drop=True)


# --------------------------------------------------------------- portfolio
def parse_holdings(text: str) -> pd.DataFrame:
    """Parse pasted 'SYMBOL QTY AVGCOST' lines (space/comma/tab separated)."""
    rows = []
    for ln in text.strip().splitlines():
        parts = [x for x in re.split(r"[,\t ]+", ln.strip()) if x]
        if not parts:
            continue
        sym = parts[0].upper()
        if sym in ("SYMBOL", "STOCK") or not re.match(r"^[A-Z&-]+$", sym):
            continue
        qty = to_num(pd.Series([parts[1]])).iloc[0] if len(parts) > 1 else None
        avg = to_num(pd.Series([parts[2]])).iloc[0] if len(parts) > 2 else None
        rows.append({"Symbol": sym, "Qty": qty, "AvgCost": avg})
    return pd.DataFrame(rows)


def portfolio_xray(holdings: pd.DataFrame, bhav: pd.DataFrame, scorer) -> pd.DataFrame:
    """Enrich holdings with LTP, P&L, conviction score+verdict. `scorer(sym)->dict`."""
    if holdings.empty:
        return holdings
    b = bhav.copy()
    if "SERIES" in b.columns:
        b = b[b["SERIES"] == "EQ"]
    px = {}
    if "SYMBOL" in b.columns:
        b["CLOSE_PRICE"] = to_num(b["CLOSE_PRICE"])
        px = dict(zip(b["SYMBOL"].astype(str).str.upper(), b["CLOSE_PRICE"]))
    rows = []
    for _, h in holdings.iterrows():
        sym = h["Symbol"]
        ltp = px.get(sym)
        qty, avg = h.get("Qty"), h.get("AvgCost")
        inv = (qty * avg) if pd.notna(qty) and pd.notna(avg) else None
        cur = (qty * ltp) if pd.notna(qty) and ltp is not None else None
        pnl = (cur - inv) if inv is not None and cur is not None else None
        pnlpc = (pnl / inv * 100) if inv else None
        sc = scorer(sym)
        rows.append({"Symbol": sym, "Qty": qty, "AvgCost": avg, "LTP": ltp,
                     "Invested": round(inv, 0) if inv else None,
                     "Current": round(cur, 0) if cur else None,
                     "P&L": round(pnl, 0) if pnl is not None else None,
                     "P&L%": round(pnlpc, 1) if pnlpc is not None else None,
                     "Conviction": sc.get("score"), "Verdict": sc.get("verdict")})
    return pd.DataFrame(rows)


# ------------------------------------------------------------ what changed
def whats_changed(*, breakouts, spikes, fii_div, ban, earnings, bulk) -> dict:
    """Assemble the daily digest from already-computed pieces + raw frames."""
    out = {}
    out["breakouts"] = breakouts.head(10) if isinstance(breakouts, pd.DataFrame) else pd.DataFrame()
    out["spikes"] = spikes.head(10) if isinstance(spikes, pd.DataFrame) else pd.DataFrame()

    fii_note = None
    if isinstance(fii_div, pd.DataFrame) and len(fii_div) >= 2 and "FII" in fii_div.columns:
        a, b = fii_div["FII"].iloc[-2], fii_div["FII"].iloc[-1]
        if pd.notna(a) and pd.notna(b) and (a >= 0) != (b >= 0):
            fii_note = f"FII index-futures flipped {'long→short' if a >= 0 else 'short→long'} ({a:+,} → {b:+,})"
    out["fii_note"] = fii_note

    if isinstance(ban, pd.DataFrame) and not ban.empty:
        col = "value" if "value" in ban.columns else ban.columns[0]
        out["ban"] = ban[col].astype(str).tolist()
    else:
        out["ban"] = []

    if isinstance(earnings, pd.DataFrame) and not earnings.empty:
        out["earnings"] = earnings.head(15)
    else:
        out["earnings"] = pd.DataFrame()
    return out
