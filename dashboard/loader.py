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


def index_names() -> list[str]:
    idx = load_snapshot_latest("all_indices")
    if idx.empty or "index" not in idx.columns:
        return ["NIFTY 50", "NIFTY BANK", "NIFTY NEXT 50", "NIFTY IT", "INDIA VIX"]
    return sorted(idx["index"].astype(str).unique())


import re as _re

CONCALL_DIR = os.path.join(_PROJECT_ROOT, "concall-data")


def concall_quarters() -> list[str]:
    if not os.path.isdir(CONCALL_DIR):
        return []
    out = []
    for d in sorted(os.listdir(CONCALL_DIR)):
        p = os.path.join(CONCALL_DIR, d)
        if os.path.isdir(p) and glob.glob(os.path.join(p, "*.md")):
            out.append(d)
    return out


def concall_pdf_quarters() -> list[str]:
    """Every quarter folder under concall-data, analyzed or not."""
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(CONCALL_DIR, "*"))
                  if os.path.isdir(p) and os.path.basename(p) != "done")


def concall_pending(quarter: str) -> list[str]:
    """Transcripts in a quarter folder the analyzer hasn't moved into done/ yet."""
    return sorted(os.path.basename(p)
                  for p in glob.glob(os.path.join(CONCALL_DIR, quarter, "*.pdf")))


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


def concall_index(quarter: str) -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(CONCALL_DIR, quarter, "*.md")))
    rows = [_parse_concall(f) for f in files]
    rows = [r for r in rows if r]
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def concall_text(quarter: str, filename: str) -> str:
    p = os.path.join(CONCALL_DIR, quarter, filename)
    if not os.path.exists(p):
        return ""
    try:
        with open(p, encoding="utf-8") as fh:
            return fh.read()
    except Exception:
        return ""


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


def industry_map() -> dict:
    """symbol -> industry. Corporate announcements are the only feed carrying it,
    so coverage is partial (roughly the names that filed something)."""
    ann = load_growing("corporate_announcements")
    if ann.empty or not {"symbol", "Industry"} <= set(ann.columns):
        return {}
    m = ann[["symbol", "Industry"]].dropna()
    m["symbol"] = m["symbol"].astype(str).str.strip().str.upper()
    m["Industry"] = m["Industry"].astype(str).str.strip()
    m = m[m["Industry"].ne("") & m["Industry"].ne("-") & m["symbol"].ne("")]
    return dict(m.drop_duplicates("symbol").values)


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
