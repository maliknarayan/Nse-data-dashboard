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
from dashboard import valuation as V

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
niftyindices_history = _cache(L.niftyindices_history)
concall_quarters = _cache(L.concall_quarters)
# uncached — the analyzer moves files mid-session, these must always be live
concall_pdf_quarters = L.concall_pdf_quarters
concall_pending = L.concall_pending
concall_index = _cache(L.concall_index)
concall_summary = _cache(L.concall_summary)
concall_text = _cache(L.concall_text)
match_symbol = _cache(L.match_symbol)
industry_map = _cache(L.industry_map)
market_map = _cache(L.market_map)
peg_table = _cache(V.peg_table)
result_pdfs = _cache(L.result_pdfs)
result_quarters = _cache(L.result_quarters)
# uncached — the analyzer moves files mid-session, these must always be live
result_pdf_quarters = L.result_pdf_quarters
result_pending = L.result_pending
result_summary = _cache(L.result_summary)
result_index = _cache(L.result_index)
concall_peers = _cache(L.concall_peers)
ratio_hits = _cache(L.ratio_hits)
industry_ratios = L.industry_ratios
ratio_family = L.ratio_family
fundamentals_symbols = _cache(L.fundamentals_symbols)
fundamentals_doc = _cache(L.fundamentals_doc)
fundamentals_facts = _cache(L.fundamentals_facts)
fundamentals_issues = _cache(L.fundamentals_issues)
fundamentals_manifest = _cache(L.fundamentals_manifest)

SYMBOLS = all_symbols()
NAMES = company_map()

# where result-reference-doc-analaysis.txt lives; override with NSE_RESULT_REF_DIR
REF_DOC_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "Documents")


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


def search(key: str, label: str = "Search", placeholder: str = "symbol, company, keyword…",
           help: str | None = None) -> str:
    """Standard search input. Returns the upper-cased needle ('' when empty)."""
    return st.text_input(label, key=key, placeholder=placeholder, help=help).strip().upper()


def apply_search(df: pd.DataFrame, needle: str, cols: list[str] | None = None) -> pd.DataFrame:
    """Keep rows matching every whitespace-separated term across `cols`."""
    if not needle or df is None or df.empty:
        return df
    use = [c for c in (cols or df.columns) if c in df.columns]
    if not use:
        return df
    hay = df[use].astype(str).agg(" ".join, axis=1).str.upper()
    mask = pd.Series(True, index=df.index)
    for term in needle.split():
        mask &= hay.str.contains(term, regex=False, na=False)
    return df[mask]


def searched(df: pd.DataFrame, key: str, cols: list[str] | None = None,
             label: str = "Search", placeholder: str = "symbol, company, keyword…",
             caption: bool = True) -> pd.DataFrame:
    """Search input + filtered frame in one call — the common table case."""
    q = search(key, label, placeholder)
    out = apply_search(df, q, cols)
    if q and caption:
        st.caption(f"{len(out):,} of {len(df):,} rows match “{q}”.")
    return out


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


def _niftyindices_collector(polite: float = 1.0):
    from niftyindices.collect import NiftyIndicesCollector
    from nse_collector.collector import setup_logging
    from nse_collector.config import Settings
    s = Settings()
    s.data_dir = L.DATA_DIR
    s.log_dir = os.path.join(os.path.dirname(L.DATA_DIR), "logs")
    s.polite_delay = polite
    setup_logging(s)
    return NiftyIndicesCollector(s)


def _parse_results(single: str | None = None, rebuild: bool = False) -> tuple[int, str]:
    """Run the result-PDF parser in-process and hand back (exit code, log)."""
    import contextlib
    import io

    from fundamentals import cli as F

    os.environ["NSE_DATA_DIR"] = L.DATA_DIR  # cli resolves its output off this
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            code = F.run(L.RESULT_PDF_DIR, single, rebuild)
        except Exception as exc:
            print(f"FATAL: {exc}")
            code = 1
    return code, buf.getvalue()


def _run_analyzer(quarter: str, single: str | None = None,
                  timeout: int = 3600) -> tuple[int, str]:
    """Drive the result-analyzer agent headlessly over one quarter folder."""
    import shutil
    import subprocess

    exe = shutil.which("claude")
    if not exe:
        return 1, ("`claude` CLI not found on PATH. Install Claude Code "
                   "(npm i -g @anthropic-ai/claude-code) to run the agent from here.")

    root = os.path.dirname(L.RESULT_PDF_DIR)
    target = os.path.join(L.RESULT_PDF_DIR, quarter)
    scope = f"only the file {single}" if single else "every unprocessed PDF"
    prompt = (f"Run the result-analyzer routine on {target} — process {scope}. "
              "Append each record to results-summary.json in that folder, then move "
              "the PDF into done/ once the record is written.")
    cmd = [exe, "-p", prompt, "--agent", "result-analyzer",
           "--permission-mode", "acceptEdits"]
    # agent reads its house-style reference doc from outside the repo
    ref = os.environ.get("NSE_RESULT_REF_DIR", REF_DOC_DIR)
    if ref and os.path.isdir(ref):
        cmd += ["--add-dir", ref]
    try:
        r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 1, f"Agent timed out after {timeout}s — rerun to pick up where it stopped."
    return r.returncode, (r.stdout + r.stderr).strip()


def _concall_tidy(target: str, done: str, pdf: str, before: set[str]) -> str:
    """Retire a processed transcript — the agent no longer touches the filesystem.

    Doing this here keeps rm/mv off the agent's permission surface; an unallowed
    Bash call is a hard stop in headless -p mode, not a prompt.
    """
    import glob
    import shutil

    made = sorted(n for n in set(os.listdir(target)) - before
                  if n.endswith((".md", ".json")))
    if not any(n.endswith(".md") for n in made):
        return f"--- {pdf}: no report written, PDF left in place"
    for scratch in glob.glob(os.path.join(target, "*_text.txt")):
        try:
            os.remove(scratch)
        except OSError:
            pass
    try:
        os.makedirs(done, exist_ok=True)
        shutil.move(os.path.join(target, pdf), os.path.join(done, pdf))
    except OSError as exc:
        return f"--- {pdf}: wrote {', '.join(made)} but could not retire PDF — {exc}"
    return f"--- {pdf}: wrote {', '.join(made)}, PDF moved to done/"


def _run_concall_analyzer(quarter: str, single: str | None = None,
                          timeout: int = 3600) -> tuple[int, str]:
    """Drive the concall-reader skill headlessly over one quarter folder."""
    import shutil
    import subprocess

    from dashboard import concall_merge

    exe = shutil.which("claude")
    if not exe:
        return 1, ("`claude` CLI not found on PATH. Install Claude Code "
                   "(npm i -g @anthropic-ai/claude-code) to run the agent from here.")

    root = os.path.dirname(L.CONCALL_DIR)
    target = os.path.join(L.CONCALL_DIR, quarter)
    done = os.path.join(target, "done")
    files = [single] if single else L.concall_pending(quarter)
    if not files:
        return 1, f"No transcripts pending in concall-data/{quarter}."

    logs, worst = [], 0
    # one run per transcript to keep each run's context to a single document
    for name in files:
        prompt = (
            f"Use the concall-reader skill.\n"
            f"Read the earnings concall transcript at {os.path.join(target, name)}.\n"
            f"Write both outputs inside {target} — that quarter folder is the only "
            f"place they may go. Follow the skill's naming rules for the filenames.\n"
            f"Do not move the PDF and do not clean up scratch files — stop after "
            f"the second write."
        )
        cmd = [exe, "-p", prompt, "--permission-mode", "acceptEdits"]
        before = set(os.listdir(target))
        try:
            r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=timeout)
            out, code = (r.stdout + r.stderr).strip(), r.returncode
        except subprocess.TimeoutExpired:
            out, code = f"timed out after {timeout}s", 1
        worst = max(worst, code)
        logs.append(f"=== {name} (exit {code}) ===\n{out}")
        if code == 0:
            logs.append(_concall_tidy(target, done, name, before))

    # the agents no longer touch concalls-summary.json — rebuild it once, here
    try:
        data = concall_merge.build(target)
        concall_merge.write(target, data)
        logs.append(f"=== concalls-summary.json rebuilt ({data['count']} concalls) ===")
    except Exception as exc:
        worst = max(worst, 1)
        logs.append(f"=== concalls-summary.json rebuild FAILED ===\n{exc}")
    return worst, "\n\n".join(logs)


def _conv_data():
    return dict(bhav=load_per_date("bhavcopy_delivery"), bulk=load_growing("bulk_deals"),
                block=load_growing("block_deals"), ban=load_per_date("securities_in_ban"),
                vol=load_per_date("daily_volatility"), pe=load_per_date("pe_ratio"),
                most_active=load_snapshot_latest("most_active_value"))
