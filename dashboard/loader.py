"""Read the CSV warehouse for the dashboard.

Thin, cached, and forgiving: a missing dataset returns an empty frame rather
than raising, so the dashboard degrades gracefully until the collector has run.
Only this module knows the on-disk layout — mirrors storage.py so a future
DuckDB/parquet backend is a single-file swap here too.
"""

from __future__ import annotations

import glob
import json
import os

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE)
DATA_DIR = os.environ.get("NSE_DATA_DIR") or os.path.join(_PROJECT_ROOT, "data")


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def to_num(series: pd.Series) -> pd.Series:
    """Coerce NSE numeric text ('-', '1,234.5', ' 12 ') to float."""
    if series.dtype.kind in "if":
        return series
    s = series.astype(str).str.replace(",", "", regex=False).str.strip()
    s = s.replace({"-": None, "": None, "nan": None})
    return pd.to_numeric(s, errors="coerce")


def _growing_path(name: str) -> str:
    return os.path.join(DATA_DIR, name, f"{name}.csv")


def load_growing(name: str) -> pd.DataFrame:
    p = _growing_path(name)
    if not os.path.exists(p):
        return pd.DataFrame()
    try:
        return _clean(pd.read_csv(p))
    except Exception:
        return pd.DataFrame()


def load_snapshot_latest(name: str) -> pd.DataFrame:
    """Latest day's rows from a growing snapshot (max _collected_on)."""
    df = load_growing(name)
    if df.empty or "_collected_on" not in df.columns:
        return df
    latest = df["_collected_on"].max()
    return df[df["_collected_on"] == latest].reset_index(drop=True)


def per_date_dates(name: str) -> list[str]:
    files = glob.glob(os.path.join(DATA_DIR, name, f"{name}_*.csv"))
    dates = []
    for f in files:
        stem = os.path.basename(f)[len(name) + 1: -4]
        dates.append(stem)
    return sorted(dates)


def load_per_date(name: str, date: str | None = None) -> pd.DataFrame:
    dates = per_date_dates(name)
    if not dates:
        return pd.DataFrame()
    d = date or dates[-1]
    p = os.path.join(DATA_DIR, name, f"{name}_{d}.csv")
    if not os.path.exists(p):
        return pd.DataFrame()
    try:
        return _clean(pd.read_csv(p))
    except Exception:
        return pd.DataFrame()


def load_per_date_all(name: str) -> pd.DataFrame:
    """All per_date files stacked, with a `_date` column. For trend charts."""
    frames = []
    for d in per_date_dates(name):
        df = load_per_date(name, d)
        if not df.empty:
            df = df.copy()
            df["_date"] = d
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def all_symbols() -> list[str]:
    """Symbol universe for autocomplete. Prefers the listed master, falls back
    to whatever the latest bhav copy traded."""
    em = load_snapshot_latest("equity_master")
    if not em.empty and "SYMBOL" in em.columns:
        return sorted(em["SYMBOL"].astype(str).str.strip().str.upper().unique())
    bhav = load_per_date("bhavcopy_delivery")
    if not bhav.empty and "SYMBOL" in bhav.columns:
        return sorted(bhav["SYMBOL"].astype(str).str.strip().str.upper().unique())
    return []


def company_map() -> dict:
    """SYMBOL -> company name, from the master (empty if not collected)."""
    em = load_snapshot_latest("equity_master")
    if em.empty or "SYMBOL" not in em.columns:
        return {}
    name_col = next((c for c in em.columns if "NAME" in c.upper()), None)
    if not name_col:
        return {}
    return dict(zip(em["SYMBOL"].astype(str).str.strip().str.upper(),
                    em[name_col].astype(str)))


def symbol_history(symbol: str) -> pd.DataFrame:
    """Per-day OHLC + volume + delivery for one symbol, from all bhav copies."""
    allb = load_per_date_all("bhavcopy_delivery")
    if allb.empty or "SYMBOL" not in allb.columns:
        return pd.DataFrame()
    df = allb[allb["SYMBOL"].astype(str).str.strip().str.upper() == symbol.upper()].copy()
    if df.empty:
        return df
    for c in ["OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE", "PREV_CLOSE",
              "TTL_TRD_QNTY", "DELIV_QTY", "DELIV_PER", "TURNOVER_LACS"]:
        if c in df.columns:
            df[c] = to_num(df[c])
    df["date"] = df["_date"]
    df["%Chg"] = (df["CLOSE_PRICE"] - df["PREV_CLOSE"]) / df["PREV_CLOSE"] * 100
    return df.sort_values("date").reset_index(drop=True)


def bse_symbols() -> list[str]:
    allb = load_per_date_all("bse_bhavcopy")
    if allb.empty or "TckrSymb" not in allb.columns:
        return []
    return sorted(allb["TckrSymb"].astype(str).str.strip().str.upper().unique())


def bse_symbol_history(symbol: str) -> pd.DataFrame:
    """BSE per-day OHLC + volume for one symbol, normalised to NSE column names."""
    allb = load_per_date_all("bse_bhavcopy")
    if allb.empty or "TckrSymb" not in allb.columns:
        return pd.DataFrame()
    df = allb[allb["TckrSymb"].astype(str).str.strip().str.upper() == symbol.upper()].copy()
    if df.empty:
        return df
    ren = {"OpnPric": "OPEN_PRICE", "HghPric": "HIGH_PRICE", "LwPric": "LOW_PRICE",
           "ClsPric": "CLOSE_PRICE", "PrvsClsgPric": "PREV_CLOSE",
           "TtlTradgVol": "TTL_TRD_QNTY"}
    df = df.rename(columns=ren)
    for c in ren.values():
        if c in df.columns:
            df[c] = to_num(df[c])
    df["date"] = df["_date"]
    df["%Chg"] = (df["CLOSE_PRICE"] - df["PREV_CLOSE"]) / df["PREV_CLOSE"] * 100
    return df.sort_values("date").reset_index(drop=True)


def index_history(index: str) -> pd.DataFrame:
    """Stored EOD history for one index, normalised to OHLC column names."""
    from nse_collector.index_history import safe_name
    p = os.path.join(DATA_DIR, "index_history", f"index_history_{safe_name(index)}.csv")
    if not os.path.exists(p):
        return pd.DataFrame()
    try:
        df = _clean(pd.read_csv(p))
    except Exception:
        return pd.DataFrame()
    ren = {"OPEN_INDEX_VAL": "OPEN_PRICE", "HIGH_INDEX_VAL": "HIGH_PRICE",
           "LOW_INDEX_VAL": "LOW_PRICE", "CLOSE_INDEX_VAL": "CLOSE_PRICE",
           "TRADED_QTY": "TTL_TRD_QNTY"}
    df = df.rename(columns=ren)
    for c in ["OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE", "TTL_TRD_QNTY"]:
        if c in df.columns:
            df[c] = to_num(df[c])
    if "TIMESTAMP" in df.columns:
        df["date"] = pd.to_datetime(df["TIMESTAMP"], errors="coerce",
                                    format="%d-%b-%Y").dt.strftime("%Y-%m-%d")
    df["%Chg"] = df["CLOSE_PRICE"].pct_change() * 100
    return df.sort_values("date").reset_index(drop=True)


def niftyindices_history(index: str) -> pd.DataFrame:
    """Daily OHLC + P/E, P/B, Div Yield trend for one index, from niftyindices.com's
    daily snapshot (broader index coverage + valuation ratios nselib's live
    snapshot doesn't archive)."""
    allb = load_per_date_all("niftyindices_snapshot")
    if allb.empty or "Index Name" not in allb.columns:
        return pd.DataFrame()
    df = allb[allb["Index Name"].astype(str).str.strip().str.upper() == index.strip().upper()].copy()
    if df.empty:
        return df
    ren = {"Open Index Value": "OPEN_PRICE", "High Index Value": "HIGH_PRICE",
           "Low Index Value": "LOW_PRICE", "Closing Index Value": "CLOSE_PRICE",
           "Change(%)": "%Chg", "P/E": "PE", "P/B": "PB", "Div Yield": "DIV_YIELD"}
    df = df.rename(columns=ren)
    for c in ["OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE", "%Chg", "PE", "PB", "DIV_YIELD"]:
        if c in df.columns:
            df[c] = to_num(df[c])
    df["date"] = df["_date"]
    return df.sort_values("date").reset_index(drop=True)


def index_names() -> list[str]:
    idx = load_snapshot_latest("all_indices")
    if idx.empty or "index" not in idx.columns:
        return ["NIFTY 50", "NIFTY BANK", "NIFTY NEXT 50", "NIFTY IT", "INDIA VIX"]
    return sorted(idx["index"].astype(str).unique())


import re as _re

CONCALL_DIR = os.path.join(_PROJECT_ROOT, "concall-data")


def _concall_md_dir(quarter: str) -> str:
    """Reports live in quarter/md-files/ (newer layout) or the quarter root (older)."""
    sub = os.path.join(CONCALL_DIR, quarter, "md-files")
    if glob.glob(os.path.join(sub, "*.md")):
        return sub
    return os.path.join(CONCALL_DIR, quarter)


def concall_quarters() -> list[str]:
    if not os.path.isdir(CONCALL_DIR):
        return []
    out = []
    for d in sorted(os.listdir(CONCALL_DIR)):
        p = os.path.join(CONCALL_DIR, d)
        if os.path.isdir(p) and glob.glob(os.path.join(_concall_md_dir(d), "*.md")):
            out.append(d)
    return out


def concall_pdf_quarters() -> list[str]:
    """Every quarter folder under concall-data, analyzed or not."""
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(CONCALL_DIR, "*"))
                  if os.path.isdir(p) and os.path.basename(p) != "done")


def concall_analyzed(quarter: str) -> set[str]:
    """Source PDFs a report already exists for, by basename.

    Snapshots record source_pdf inconsistently — full path in some, basename in
    others — so both forms are normalized to a basename here.
    """
    qdir = os.path.join(CONCALL_DIR, quarter)
    seen = {os.path.basename(p) for p in glob.glob(os.path.join(qdir, "done", "*.pdf"))}
    for rec in concall_summary(quarter).get("concalls") or []:
        src = str(rec.get("source_pdf") or "").replace("\\", "/").strip()
        if src:
            seen.add(os.path.basename(src))
    return seen


def concall_pending(quarter: str) -> list[str]:
    """Transcripts in a quarter folder that have no report yet.

    A PDF can sit in the folder and in done/ at once (a copy that was never
    cleaned up), so presence in the root is not proof it needs analyzing.
    """
    analyzed = concall_analyzed(quarter)
    return sorted(name for name in
                  (os.path.basename(p)
                   for p in glob.glob(os.path.join(CONCALL_DIR, quarter, "*.pdf")))
                  if name not in analyzed)


def _parse_concall(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            head = fh.read(2500)
    except Exception:
        return {}
    first = next((ln for ln in head.splitlines() if ln.startswith("# ")), "")
    company = _re.split(r"\s[—-]\s|:", first.lstrip("# ").strip())[0].strip()

    def grab(pat):
        m = _re.search(pat, head, _re.I)
        return m.group(1).strip() if m else ""
    return {
        "Company": company or os.path.basename(path).replace(".md", ""),
        "Verdict": grab(r"\*\*Verdict:\*\*\s*([A-Za-z]+)").upper(),
        "Call": grab(r"\*\*Classification:\*\*\s*([A-Za-z/]+)").upper(),
        "Confidence": grab(r"Management Confidence:\*\*\s*(\d+)"),
        "Date": grab(r"\*\*Date of Analysis:\*\*\s*([\d-]+)"),
        "_file": os.path.basename(path),
    }


def concall_summary(quarter: str) -> dict:
    """Raw concalls-summary.json for one quarter (concall-reader's aggregated snapshot)."""
    p = os.path.join(CONCALL_DIR, quarter, "concalls-summary.json")
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


_CONCALL_VERDICT_TONE = {
    "BUY": "GOOD", "ACCUMULATE ON DIPS": "GOOD",
    "HOLD": "HOLD", "WATCHLIST": "HOLD",
    "AVOID": "BAD",
}


def concall_index(quarter: str) -> pd.DataFrame:
    """One screener row per company for a quarter.

    Prefers the aggregated concalls-summary.json the concall-reader skill
    maintains; falls back to parsing .md headers for quarters analyzed before
    that file existed (the older concall-analyzer output format).
    """
    recs = concall_summary(quarter).get("concalls") or []
    if recs:
        by_pdf = {}
        for r in recs:
            key = r.get("source_pdf") or r.get("company")
            prev = by_pdf.get(key)
            if prev is None or str(r.get("analyzed_on") or "") >= str(prev.get("analyzed_on") or ""):
                by_pdf[key] = r
        rows = []
        for r in by_pdf.values():
            verdict = str(r.get("verdict") or "").upper()
            rows.append({
                "Company": r.get("company") or "—",
                "Verdict": _CONCALL_VERDICT_TONE.get(verdict, "—"),
                "Call": verdict or "—",
                "Confidence": str(r.get("confidence") or "").upper(),
                "Date": r.get("call_date") or r.get("analyzed_on") or "",
                "_file": r.get("source_md") or "",
            })
        return pd.DataFrame(rows)

    files = sorted(glob.glob(os.path.join(_concall_md_dir(quarter), "*.md")))
    rows = [_parse_concall(f) for f in files]
    rows = [r for r in rows if r]
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(columns=["Company", "Verdict", "Call", "Confidence", "Date", "_file"])


def concall_text(quarter: str, filename: str) -> str:
    for p in (os.path.join(CONCALL_DIR, quarter, filename),
              os.path.join(_concall_md_dir(quarter), filename)):
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as fh:
                    return fh.read()
            except Exception:
                return ""
    return ""


def concall_from_md_fallback(quarter: str, company: str) -> dict | None:
    """Fallback: read MD file directly if JSON snapshot unavailable."""
    try:
        from dashboard import concall_md_reader
        return concall_md_reader.fallback_read_concall(quarter, company)
    except ImportError:
        return None


def match_symbol(company: str) -> str | None:
    """Best-effort company-name -> NSE symbol via the equity master."""
    names = company_map()  # SYMBOL -> NAME
    if not names or not company:
        return None
    stop = {"LIMITED", "LTD", "LTD.", "INDIA", "THE", "COMPANY", "CORPORATION",
            "INDUSTRIES", "&", "OF"}
    toks = [t for t in _re.sub(r"[^A-Za-z ]", " ", company).upper().split() if t not in stop]
    if not toks:
        return None
    key = " ".join(toks)
    best = None
    for sym, name in names.items():
        nm = name.upper()
        if key in nm or (toks[0] in nm and (len(toks) < 2 or toks[1] in nm)):
            return sym
        if toks[0] == sym.upper():
            best = sym
    return best


def _industry_pairs(dataset: str, sym_col: str, ind_col: str) -> dict:
    df = load_growing(dataset)
    if df.empty or not {sym_col, ind_col} <= set(df.columns):
        return {}
    m = df[[sym_col, ind_col]].dropna()
    m[sym_col] = m[sym_col].astype(str).str.strip().str.upper()
    m[ind_col] = m[ind_col].astype(str).str.strip()
    m = m[m[ind_col].ne("") & m[ind_col].ne("-") & m[sym_col].ne("")]
    return dict(m.drop_duplicates(sym_col).values)


def industry_map() -> dict:
    """symbol -> industry, from both feeds that carry one.

    Index constituents cover ~1,000 names but only in 22 broad NIFTY sectors;
    corporate announcements are finer ('Pharmaceuticals', not 'Healthcare') but
    only tag companies that actually filed. Broad first, fine wins on overlap.
    """
    out = sector_map()
    out.update(_industry_pairs("corporate_announcements", "symbol", "Industry"))
    return out


def sector_map() -> dict:
    """symbol -> broad NIFTY sector, index constituents only. One taxonomy for
    everyone, so a peer group doesn't split across two granularities."""
    return _industry_pairs("index_constituents", "Symbol", "Industry")


_SIZE_BANDS = [(500, "Mega (₹500cr+)"), (100, "Large (₹100-500cr)"),
               (25, "Mid (₹25-100cr)"), (5, "Small (₹5-25cr)"), (0, "Micro (<₹5cr)")]
_MOVE_BANDS = [(5, "Up > 5%"), (2, "Up 2-5%"), (0, "Up 0-2%"),
               (-2, "Down 0-2%"), (-5, "Down 2-5%"), (-1e9, "Down > 5%")]
_DELIV_BANDS = [(75, "Delivery > 75%"), (50, "Delivery 50-75%"),
                (25, "Delivery 25-50%"), (0, "Delivery < 25%")]


def _band(v, bands, na="Unknown"):
    if pd.isna(v):
        return na
    for cut, name in bands:
        if v >= cut:
            return name
    return bands[-1][1]


def market_map(date: str | None = None) -> pd.DataFrame:
    """One row per EQ stock for the market map — move, liquidity, valuation, industry."""
    bhav = load_per_date("bhavcopy_delivery", date)
    if bhav.empty or "SYMBOL" not in bhav.columns:
        return pd.DataFrame()
    b = bhav.copy()
    if "SERIES" in b.columns:
        b = b[b["SERIES"].astype(str).str.strip() == "EQ"]
    for c in ("CLOSE_PRICE", "PREV_CLOSE", "DELIV_PER", "TTL_TRD_QNTY",
              "TURNOVER_LACS", "NO_OF_TRADES"):
        if c in b.columns:
            b[c] = to_num(b[c])
    b["Symbol"] = b["SYMBOL"].astype(str).str.strip().str.upper()
    b = b.drop_duplicates("Symbol")
    b["%Chg"] = (b["CLOSE_PRICE"] - b["PREV_CLOSE"]) / b["PREV_CLOSE"] * 100
    b["Turnover Cr"] = b["TURNOVER_LACS"] / 100
    b["Name"] = b["Symbol"].map(company_map()).fillna(b["Symbol"])
    b["Industry"] = b["Symbol"].map(industry_map()).fillna("Unclassified")

    pe = load_per_date("pe_ratio", date)
    if not pe.empty:
        pecol = next((c for c in pe.columns if "P/E" in c.upper()), None)
        scol = "SYMBOL" if "SYMBOL" in pe.columns else pe.columns[0]
        if pecol:
            p = pe[[scol, pecol]].copy()
            p.columns = ["Symbol", "P/E"]
            p["Symbol"] = p["Symbol"].astype(str).str.strip().str.upper()
            p["P/E"] = to_num(p["P/E"])
            b = b.merge(p.drop_duplicates("Symbol"), on="Symbol", how="left")
    if "P/E" not in b.columns:
        b["P/E"] = float("nan")

    w52 = load_per_date("week52_high_low", date)
    if not w52.empty and "Adjusted_52_Week_High" in w52.columns:
        w = w52[["SYMBOL", "Adjusted_52_Week_High"]].copy()
        w.columns = ["Symbol", "52wHigh"]
        w["Symbol"] = w["Symbol"].astype(str).str.strip().str.upper()
        w["52wHigh"] = to_num(w["52wHigh"])
        b = b.merge(w.drop_duplicates("Symbol"), on="Symbol", how="left")
        b["% From High"] = (b["CLOSE_PRICE"] - b["52wHigh"]) / b["52wHigh"] * 100
    else:
        b["52wHigh"] = float("nan")
        b["% From High"] = float("nan")

    b["Size tier"] = b["Turnover Cr"].map(lambda v: _band(v, _SIZE_BANDS))
    b["Move band"] = b["%Chg"].map(lambda v: _band(v, _MOVE_BANDS))
    b["Delivery band"] = b["DELIV_PER"].map(lambda v: _band(v, _DELIV_BANDS))
    keep = ["Symbol", "Name", "Industry", "Size tier", "Move band", "Delivery band",
            "CLOSE_PRICE", "%Chg", "DELIV_PER", "Turnover Cr", "TTL_TRD_QNTY",
            "NO_OF_TRADES", "P/E", "% From High"]
    out = b[[c for c in keep if c in b.columns]].rename(
        columns={"CLOSE_PRICE": "Close", "DELIV_PER": "Delivery %",
                 "TTL_TRD_QNTY": "Volume", "NO_OF_TRADES": "Trades"})
    return out.sort_values("Turnover Cr", ascending=False).reset_index(drop=True)


RESULT_PDF_DIR = os.path.join(_PROJECT_ROOT, "result-pdf")
FUND_DIR = os.path.join(DATA_DIR, "fundamentals")


def result_pdfs() -> pd.DataFrame:
    """Every PDF sitting in result-pdf/, with size and mtime."""
    files = sorted(glob.glob(os.path.join(RESULT_PDF_DIR, "*.pdf")))
    rows = []
    for f in files:
        stat = os.stat(f)
        rows.append({"File": os.path.basename(f),
                     "MB": round(stat.st_size / 1_048_576, 2),
                     "Added": pd.to_datetime(stat.st_mtime, unit="s").strftime("%Y-%m-%d %H:%M")})
    return pd.DataFrame(rows)


def result_quarters() -> list[str]:
    """Quarter folders under result-pdf/ that carry an analyzer summary."""
    return sorted(os.path.basename(os.path.dirname(p))
                  for p in glob.glob(os.path.join(RESULT_PDF_DIR, "*", "results-summary.json")))


def result_pdf_quarters() -> list[str]:
    """Every quarter folder under result-pdf/, analyzed or not."""
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(RESULT_PDF_DIR, "*"))
                  if os.path.isdir(p) and os.path.basename(p) != "done")


def result_pending(quarter: str) -> list[str]:
    """PDFs in a quarter folder the analyzer hasn't moved into done/ yet."""
    return sorted(os.path.basename(p)
                  for p in glob.glob(os.path.join(RESULT_PDF_DIR, quarter, "*.pdf")))


def result_summary(quarter: str) -> dict:
    """Raw results-summary.json for one quarter."""
    p = os.path.join(RESULT_PDF_DIR, quarter, "results-summary.json")
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _fin(rec: dict, key: str, field: str = "current"):
    return ((rec.get("financials") or {}).get(key) or {}).get(field)


def result_index(quarter: str) -> pd.DataFrame:
    """Flatten a quarter's analyzed results into one screener row per company."""
    recs = result_summary(quarter).get("results") or []
    rows = []
    for i, r in enumerate(recs):
        rows.append({
            "Company": r.get("company") or "—",
            "Verdict": r.get("verdict") or "—",
            "Grade": r.get("sub_verdict") or "—",
            "Rev Cr": _fin(r, "revenue"),
            "Rev YoY %": _fin(r, "revenue", "yoy_pct"),
            "Rev QoQ %": _fin(r, "revenue", "qoq_pct"),
            "EBITDA Cr": _fin(r, "ebitda"),
            "EBITDA YoY %": _fin(r, "ebitda", "yoy_pct"),
            "Margin %": _fin(r, "ebitda_margin"),
            "Margin bps": _fin(r, "ebitda_margin", "yoy_bps"),
            "PAT Cr": _fin(r, "pat"),
            "PAT YoY %": _fin(r, "pat", "yoy_pct"),
            "PAT QoQ %": _fin(r, "pat", "qoq_pct"),
            "Basis": r.get("basis") or "—",
            "SME": bool(r.get("is_sme")),
            "Tags": ", ".join(r.get("tags") or []),
            "Flags": len(r.get("red_flags") or []),
            "Date": r.get("analyzed_on") or "",
            "_i": i,
        })
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(columns=["Company", "Verdict", "Grade", "Rev Cr", "Rev YoY %",
                                  "Rev QoQ %", "EBITDA Cr", "EBITDA YoY %", "Margin %",
                                  "Margin bps", "PAT Cr", "PAT YoY %", "PAT QoQ %", "Basis",
                                  "SME", "Tags", "Flags", "Date", "_i"])


_PEER_STOP = {"LIMITED", "LTD", "PVT", "PRIVATE", "THE", "CO"}
_PEER_NUM = ["Rev Cr", "Rev YoY %", "EBITDA YoY %", "Margin %", "Margin bps", "PAT YoY %"]
PEER_COLS = (["Company", "Symbol", "Industry", "Sub-industry", "Verdict", "Call",
              "Confidence", "Result verdict", "Grade"] + _PEER_NUM + ["Date", "_file"])


def _peer_key(name: str) -> str:
    toks = [t for t in _re.sub(r"[^A-Z0-9 ]", " ", str(name or "").upper()).split()
            if t not in _PEER_STOP]
    return "".join(toks)


def _peer_symbol(company: str) -> str:
    """match_symbol is loose — it lands 'All E Technologies' on ABDL. Keep a hit
    only when the NSE name actually starts the same way, or a wrong symbol drags
    the company into a wrong peer group."""
    sym = match_symbol(company) or ""
    if not sym:
        return ""
    head = _peer_key(company)[:4]
    return sym if head and head in _peer_key(company_map().get(sym, "")) else ""


def concall_peers(quarter: str) -> pd.DataFrame:
    """A quarter's concall companies tagged with NSE industry and result numbers.

    Left join off the concall index — the peer set is whoever actually held a call.
    Industry comes from corporate announcements, so names it doesn't cover land in
    'Unclassified' instead of dropping out of the table.
    """
    cidx = concall_index(quarter)
    if cidx.empty:
        return pd.DataFrame(columns=PEER_COLS)

    out = cidx.copy()
    out["_key"] = out["Company"].map(_peer_key)
    ridx = result_index(quarter)
    if not ridx.empty:
        r = ridx.copy()
        r["_key"] = r["Company"].map(_peer_key)
        r = (r[["_key", "Verdict", "Grade"] + _PEER_NUM]
             .rename(columns={"Verdict": "Result verdict"})
             .drop_duplicates("_key"))
        out = out.merge(r, on="_key", how="left")
    for col in ["Result verdict", "Grade"]:
        out[col] = out.get(col, pd.Series(dtype=object)).fillna("—")
    for col in _PEER_NUM:
        out[col] = pd.to_numeric(out.get(col), errors="coerce")

    # group on the broad sector so peers land together; keep the finer filing tag
    sectors, inds = sector_map(), industry_map()
    out["Symbol"] = out["Company"].map(_peer_symbol)
    out["Industry"] = out["Symbol"].map(
        lambda s: sectors.get(s) or inds.get(s) or "Unclassified")
    out["Sub-industry"] = out["Symbol"].map(lambda s: inds.get(s) or "—")
    # one company, two transcripts (a re-run under a new filename) — keep the newest
    out["_dedupe"] = out["Symbol"].where(out["Symbol"].ne(""), out["_key"])
    out["_when"] = pd.to_datetime(out["Date"], errors="coerce", format="mixed")
    out = out.sort_values("_when", na_position="first").drop_duplicates("_dedupe", keep="last")
    return out[PEER_COLS].sort_values("Company").reset_index(drop=True)


# the ratios each family is actually judged on, with the words a transcript uses for them
_RATIO_SETS = {
    "lender": (
        ("NIM", ("nim", "net interest margin", "net interest income", "nii")),
        ("Asset quality", ("gnpa", "nnpa", "stage 3", "slippage", "npa", "gross npa")),
        ("Credit cost", ("credit cost", "credit loss", "provision", "provisioning")),
        ("Book growth", ("advances", "aum", "disbursement", "loan book", "credit growth")),
        ("Funding", ("casa", "deposit", "cost of funds", "cost of borrowing")),
        ("Return ratios", ("roa", "roe", "return on asset", "return on equity")),
        ("Capital", ("capital adequacy", "cet-1", "cet1", "tier 1", "tier-1", "crar")),
        ("Cost ratio", ("cost-to-income", "cost to income", "cost-to-assets", "opex")),
    ),
    "pharma": (
        ("Gross margin", ("gross margin", "gross profit")),
        ("EBITDA margin", ("ebitda margin", "operating margin")),
        ("R&D spend", ("r&d", "research and development")),
        ("US / export mix", ("us market", "us business", "export", "formulation", "anda")),
        ("Price erosion", ("price erosion", "pricing pressure", "realisation", "realization")),
        ("Regulatory", ("usfda", "fda", "inspection", "observation", "form 483", "warning letter")),
        ("Capacity", ("utilisation", "utilization", "capex", "debottleneck", "capacity")),
    ),
    "it": (
        ("Revenue growth cc", ("constant currency", "cc growth", "revenue growth")),
        ("EBIT margin", ("ebit margin", "operating margin", "ebitda margin")),
        ("Deal wins / TCV", ("deal win", "tcv", "order book", "bookings", "pipeline")),
        ("Attrition", ("attrition", "headcount", "utilisation", "utilization")),
        ("Client mix", ("client", "top 10", "vertical", "geography")),
        ("Billing rate", ("billing rate", "realisation", "pricing", "per capita")),
    ),
    "telecom": (
        ("ARPU", ("arpu", "average revenue per user")),
        ("Subscribers", ("subscriber", "net adds", "user base")),
        ("Churn", ("churn",)),
        ("EBITDA margin", ("ebitda margin", "operating margin")),
        ("Capex / network", ("capex", "network rollout", "spectrum", "tower")),
        ("Leverage", ("net debt", "leverage", "debt/ebitda", "deleverag")),
    ),
    "industrial": (
        ("EBITDA margin", ("ebitda margin", "operating margin")),
        ("Gross margin", ("gross margin", "raw material", "rm cost")),
        ("Order book", ("order book", "order inflow", "l1", "tender", "backlog")),
        ("Volume growth", ("volume", "tonnage", "realisation", "realization")),
        ("Capacity", ("utilisation", "utilization", "capex", "capacity", "expansion")),
        ("Working capital", ("working capital", "receivable", "inventory", "debtor")),
        ("Leverage", ("net debt", "leverage", "debt/ebitda", "borrowing")),
    ),
}


def ratio_family(industry: str) -> str:
    s = str(industry or "").lower()
    if "bank" in s or "financ" in s or "nbfc" in s:
        return "lender"
    if "pharma" in s or "healthcare" in s or "hospital" in s or "drug" in s:
        return "pharma"
    if "software" in s or "computers" in s or "it enabled" in s:
        return "it"
    if "telecom" in s:
        return "telecom"
    return "industrial"


def industry_ratios(industry: str) -> tuple:
    """The ratio set this industry is read on — labels plus the words to look for."""
    return _RATIO_SETS[ratio_family(industry)]


def ratio_hits(quarter: str, industry: str, companies: tuple[str, ...]) -> pd.DataFrame:
    """Which of the industry's standard ratios each peer actually discussed on its call.

    Text search over the snapshot's own highlights and monitorables — a blank means
    the analysis never recorded that ratio, not that management stayed silent on it.
    """
    ratios = industry_ratios(industry)
    blobs: dict[str, str] = {}
    for r in concall_summary(quarter).get("concalls") or []:
        parts = [str(r.get("verdict_rationale") or "")]
        parts += [str(h.get("point") or "") for h in (r.get("highlights") or [])
                  if isinstance(h, dict)]
        parts += [str(m) for m in (r.get("key_monitorables") or [])]
        key = _peer_key(r.get("company"))
        blobs[key] = blobs.get(key, "") + " " + " ".join(parts).lower()
    rows = []
    for company in companies:
        txt = blobs.get(_peer_key(company), "")
        rows.append({"Company": company,
                     **{label: ("✓" if any(w in txt for w in words) else "")
                        for label, words in ratios}})
    return pd.DataFrame(rows)


def fundamentals_symbols() -> list[str]:
    if not os.path.isdir(FUND_DIR):
        return []
    return sorted(os.path.basename(p)[:-5]
                  for p in glob.glob(os.path.join(FUND_DIR, "*.json")))


def fundamentals_doc(symbol: str) -> dict:
    p = os.path.join(FUND_DIR, f"{symbol}.json")
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _fund_csv(name: str) -> pd.DataFrame:
    p = os.path.join(FUND_DIR, name)
    if not os.path.exists(p):
        return pd.DataFrame()
    try:
        return _clean(pd.read_csv(p))
    except Exception:
        return pd.DataFrame()


def fundamentals_facts() -> pd.DataFrame:
    return _fund_csv("_facts.csv")


def fundamentals_issues() -> pd.DataFrame:
    return _fund_csv("_issues.csv")


def fundamentals_manifest() -> pd.DataFrame:
    """Parse log, newest run first."""
    df = _fund_csv("_manifest.csv")
    if df.empty or "run_ts" not in df.columns:
        return df
    return df.sort_values("run_ts", ascending=False)


def load_manifest() -> pd.DataFrame:
    p = os.path.join(DATA_DIR, "_manifest.csv")
    if not os.path.exists(p):
        return pd.DataFrame()
    try:
        return _clean(pd.read_csv(p))
    except Exception:
        return pd.DataFrame()


def snapshot_asof(name: str) -> str | None:
    df = load_growing(name)
    if df.empty or "_collected_on" not in df.columns:
        return None
    return str(df["_collected_on"].max())
