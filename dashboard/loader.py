"""Read the CSV warehouse for the dashboard.

Thin, cached, and forgiving: a missing dataset returns an empty frame rather
than raising, so the dashboard degrades gracefully until the collector has run.
Only this module knows the on-disk layout — mirrors storage.py so a future
DuckDB/parquet backend is a single-file swap here too.
"""

from __future__ import annotations

import glob
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
