"""Loop the result-PDF directory and write the fundamentals warehouse.

    python -m fundamentals                     # parse result-pdf/ -> data/fundamentals/
    python -m fundamentals --pdf path/to.pdf   # one file
    python -m fundamentals --rebuild           # ignore the OCR cache

Layout mirrors the CSV warehouse the collector writes::

    data/fundamentals/<SYMBOL>.json   # per-company facts, nested by statement
    data/fundamentals/_facts.csv      # every fact, long form, all companies
    data/fundamentals/_issues.csv     # cross-foot breaks needing a human look
    data/fundamentals/_manifest.csv   # append-only parse log
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import shutil

import pandas as pd

from . import build, validate

FACT_COLS = ["symbol", "statement", "basis", "tag", "period_type", "period_end",
             "fiscal_label", "audited", "value", "unit", "per_share",
             "source_pdf", "page_no", "ocr", "raw"]
MANIFEST_COLS = ["run_ts", "source_pdf", "sha1", "symbol", "resolved_by",
                 "pages", "facts", "issues", "status"]


def data_dir() -> str:
    return os.environ.get("NSE_DATA_DIR") or "data"


def out_dir() -> str:
    return os.path.join(data_dir(), "fundamentals")


def load_master() -> pd.DataFrame | None:
    p = os.path.join(data_dir(), "equity_master", "equity_master.csv")
    if not os.path.exists(p):
        return None
    try:
        df = pd.read_csv(p)
    except Exception:
        return None
    df.columns = [str(c).strip() for c in df.columns]
    if "SYMBOL" not in df.columns:
        return None
    # snapshot accumulates one row per symbol per collection day
    return df.drop_duplicates(subset=["SYMBOL"], keep="last")


def load_bse_map() -> dict:
    """BSE scrip code -> ISIN, off the latest BSE bhav copy. Lets a covering
    letter that only quotes a scrip code still reach an NSE symbol."""
    files = sorted(glob.glob(os.path.join(data_dir(), "bse_bhavcopy", "*.csv")))
    if not files:
        return {}
    try:
        df = pd.read_csv(files[-1], low_memory=True, usecols=["FinInstrmId", "ISIN"])
    except Exception:
        return {}
    df = df.dropna(subset=["FinInstrmId", "ISIN"])
    return {str(c).strip(): str(i).strip().upper()
            for c, i in zip(df["FinInstrmId"], df["ISIN"])}


def _fact_key(f: dict) -> tuple:
    return (f["basis"], f["statement"], f["tag"], f["period_end"], f["period_type"])


def dedupe(facts: list[dict]) -> list[dict]:
    """One fact per (basis, statement, tag, period). Audited wins, then the
    later filing — a restated figure supersedes the original."""
    best: dict[tuple, dict] = {}
    for f in facts:
        k = _fact_key(f)
        cur = best.get(k)
        if cur is None:
            best[k] = f
            continue
        if bool(f.get("audited")) > bool(cur.get("audited")):
            best[k] = f
        elif bool(f.get("audited")) == bool(cur.get("audited")) \
                and f["source_pdf"] > cur["source_pdf"]:
            best[k] = f
    return list(best.values())


def to_json_doc(symbol: str, ident: dict, facts: list[dict],
                issues: list[dict], sources: list[dict]) -> dict:
    """Nested view for the dashboard: statement -> basis -> period -> tag."""
    tree: dict = {}
    for f in facts:
        tree.setdefault(f["statement"], {}) \
            .setdefault(f["basis"], {}) \
            .setdefault(f["fiscal_label"], {})[f["tag"]] = {
                "value": f["value"],
                "source_pdf": f["source_pdf"],
                "page_no": f["page_no"],
            }
    periods: dict[str, list[dict]] = {}
    seen: set[tuple] = set()
    for f in sorted(facts, key=lambda f: (f["statement"], f["period_end"])):
        k = (f["statement"], f["fiscal_label"])
        if k in seen:
            continue
        seen.add(k)
        periods.setdefault(f["statement"], []).append({
            "fiscal_label": f["fiscal_label"], "period_end": f["period_end"],
            "period_type": f["period_type"], "audited": f["audited"],
        })
    return {
        "symbol": symbol,
        "identity": ident,
        "unit": "INR",
        "note": "values in base rupees; per-share figures unscaled; "
                "absent tag means not reported",
        "sources": sources,
        "periods": periods,
        "statements": tree,
        "issues": issues,
    }


def run(result_dir: str, single: str | None, rebuild: bool) -> int:
    od = out_dir()
    cache = os.path.join(od, "_ocr_cache")
    if rebuild and os.path.isdir(cache):
        shutil.rmtree(cache)
    os.makedirs(od, exist_ok=True)

    pdfs = [single] if single else sorted(glob.glob(os.path.join(result_dir, "*.pdf")))
    if not pdfs:
        print(f"no PDFs in {result_dir}")
        return 1

    master = load_master()
    if master is None:
        print("warning: equity_master.csv not found — symbols taken from the PDF only")
    bse_map = load_bse_map()
    if not bse_map:
        print("warning: no BSE bhav copy — scrip-code resolution unavailable")

    per_symbol: dict[str, dict] = {}
    manifest: list[dict] = []
    run_ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for path in pdfs:
        try:
            res = build.parse_pdf(path, cache_dir=cache, master=master, bse_map=bse_map)
        except Exception as exc:
            print(f"FAIL  {os.path.basename(path)}: {exc}")
            manifest.append({"run_ts": run_ts, "source_pdf": path, "sha1": "",
                             "symbol": "", "resolved_by": "", "pages": 0,
                             "facts": 0, "issues": 0, "status": f"error: {exc}"})
            continue

        sym = res["identity"].get("symbol") or "UNRESOLVED"
        slot = per_symbol.setdefault(sym, {"identity": res["identity"],
                                           "facts": [], "sources": []})
        slot["facts"].extend(res["facts"])
        slot["sources"].append({"pdf": res["source_pdf"], "sha1": res["sha1"],
                                "pages": res["pages"]})
        stmts = sorted({p["statement"] for p in res["pages"] if p.get("statement")})
        print(f"OK    {os.path.basename(path):40s} {sym:12s} "
              f"facts={len(res['facts']):4d} statements={','.join(stmts) or '-'}")
        manifest.append({"run_ts": run_ts, "source_pdf": res["source_pdf"],
                         "sha1": res["sha1"], "symbol": sym,
                         "resolved_by": res["identity"].get("resolved_by", ""),
                         "pages": len(res["pages"]), "facts": len(res["facts"]),
                         "issues": 0, "status": "ok"})

    all_facts: list[dict] = []
    all_issues: list[dict] = []
    for sym, slot in sorted(per_symbol.items()):
        facts = dedupe(slot["facts"])
        facts.extend(validate.derive_missing(facts))
        facts = dedupe(facts)
        issues = validate.check(facts)
        for i in issues:
            i["symbol"] = sym
        facts.sort(key=lambda f: (f["statement"], f["basis"], f["period_end"], f["tag"]))

        doc = to_json_doc(sym, slot["identity"], facts, issues, slot["sources"])
        p = os.path.join(od, f"{sym}.json")
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, p)

        all_facts.extend(facts)
        all_issues.extend(issues)
        print(f"  -> {sym}.json  facts={len(facts)} issues={len(issues)}")

    _write_csv(os.path.join(od, "_facts.csv"), all_facts, FACT_COLS)
    _write_csv(os.path.join(od, "_issues.csv"), all_issues, None)
    _append_manifest(os.path.join(od, "_manifest.csv"), manifest)
    print(f"\n{len(all_facts)} facts, {len(all_issues)} issues -> {od}")
    return 0


def _write_csv(path: str, rows: list[dict], cols: list[str] | None) -> None:
    df = pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols or [])
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


def _append_manifest(path: str, rows: list[dict]) -> None:
    if not rows:
        return
    df = pd.DataFrame([{c: r.get(c, "") for c in MANIFEST_COLS} for r in rows],
                      columns=MANIFEST_COLS)
    df.to_csv(path, mode="a", header=not os.path.exists(path), index=False)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m fundamentals",
                                 description="Parse result PDFs into facts.")
    ap.add_argument("--result-dir", default="result-pdf")
    ap.add_argument("--pdf", help="parse a single PDF instead of the directory")
    ap.add_argument("--rebuild", action="store_true", help="discard the OCR cache")
    a = ap.parse_args(argv)
    return run(a.result_dir, a.pdf, a.rebuild)
