"""Parse one result PDF into facts plus the identity it belongs to.

Identity is read off the covering letter (NSE symbol, BSE scrip code, ISIN, CIN)
and resolved against data/equity_master.csv — that table stays the sole
authority for symbols. Nothing here invents a company record.
"""

from __future__ import annotations

import os
import re

import fitz

from . import extract, layout
from . import taxonomy as TX

_SYMBOL = re.compile(r"NSE\s*Symbol\s*[-:–]\s*([A-Z0-9&$-]{2,20})", re.I)
_SCRIP = re.compile(r"Scrip\s*Code\s*[-:–]\s*(\d{5,7})", re.I)
_ISIN = re.compile(r"\b(INE[A-Z0-9]{9})\b")
_CIN = re.compile(r"\b([LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})\b")

# a covering letter is addressed TO the exchanges — never mistake them for the filer
_ADDRESSEE = re.compile(
    r"\b(?:BSE|NSE|MSEI)\s+(?:Limited|Ltd\.?)"
    r"|\b(?:Bombay|National|Metropolitan|Calcutta)\s+Stock\s+Exchange", re.I)


def read_identity(doc: fitz.Document) -> dict:
    """Symbol / scrip code / ISIN / CIN / name from the first few pages."""
    head = "\n".join(doc[i].get_text() for i in range(min(3, len(doc))))
    out: dict = {}
    if m := _SYMBOL.search(head):
        out["symbol"] = m.group(1).strip().upper()
    if m := _SCRIP.search(head):
        out["bse_code"] = m.group(1)
    if m := _ISIN.search(head):
        out["isin"] = m.group(1)
    if m := _CIN.search(head):
        out["cin"] = m.group(1)
    for line in head.splitlines():
        s = line.strip()
        if _ADDRESSEE.search(s):
            continue
        if re.search(r"\b(Limited|Ltd\.?)\b", s) and 5 < len(s) < 90:
            out["company_name"] = re.sub(r"\s+", " ", s)
            break
    return out


def resolve_symbol(ident: dict, master, bse_map: dict | None = None) -> tuple[str | None, str]:
    """Map to an equity_master SYMBOL. ISIN first, then BSE code, then name."""
    if master is None or master.empty:
        return ident.get("symbol"), "pdf_only"
    m = master
    isins = m["ISIN NUMBER"].astype(str).str.upper()
    if isin := ident.get("isin"):
        hit = m[isins == isin.upper()]
        if not hit.empty:
            return str(hit.iloc[0]["SYMBOL"]).strip().upper(), "isin"
    # scrip code is the only per-company id on most BSE covering letters
    if bse_map and (code := ident.get("bse_code")):
        if mapped := bse_map.get(str(code).strip()):
            hit = m[isins == mapped.upper()]
            if not hit.empty:
                return str(hit.iloc[0]["SYMBOL"]).strip().upper(), "bse_code"
    if sym := ident.get("symbol"):
        hit = m[m["SYMBOL"].astype(str).str.upper() == sym.upper()]
        if not hit.empty:
            return str(hit.iloc[0]["SYMBOL"]).strip().upper(), "symbol"
    if name := ident.get("company_name"):
        key = re.sub(r"[^A-Z ]", " ", name.upper())
        key = re.sub(r"^FOR\b", " ", key)  # name lifted from a signature block
        key = re.sub(r"\b(LIMITED|LTD|FORMERLY|KNOWN|AS|PRIVATE)\b", " ", key)
        key = re.sub(r"\s+", " ", key).strip()
        if key:
            names = m["NAME OF COMPANY"].astype(str).str.upper()
            hit = m[names.str.contains(re.escape(key), na=False)]
            if not hit.empty:
                return str(hit.iloc[0]["SYMBOL"]).strip().upper(), "name"
    return ident.get("symbol"), "unresolved"


def parse_pdf(path: str, *, cache_dir: str, master=None, bse_map=None) -> dict:
    """Facts + identity + per-page notes for one PDF."""
    doc = fitz.open(path)
    sha = extract.pdf_sha1(path)
    ocr_exe = extract.tesseract_exe()
    ident = read_identity(doc)
    symbol, how = resolve_symbol(ident, master, bse_map)

    facts: list[dict] = []
    pages: list[dict] = []
    rel = os.path.relpath(path).replace("\\", "/")

    # read every page once, then resolve units — a scanned page often loses its
    # unit line to OCR, and every statement in one filing shares the same unit
    scanned: list[dict] = []
    for page in doc:
        pno = page.number + 1
        words, used_ocr = extract.page_words(page, cache_dir=cache_dir, sha=sha,
                                             ocr_exe=ocr_exe)
        if not words:
            pages.append({"page": pno, "statement": None, "ocr": used_ocr,
                          "note": "no words (scanned and no OCR engine)"})
            continue
        text = " ".join(w[4] for w in words)
        stmt = layout.detect_statement(text[:600])
        if not stmt:
            continue
        scanned.append({"pno": pno, "words": words, "text": text, "stmt": stmt,
                        "ocr": used_ocr, "scale": layout.detect_unit(text[:1500])})

    doc_scale = next((p["scale"] for p in scanned if p["scale"] is not None), None)

    for pg in scanned:
        pno, words, text, stmt, used_ocr = (pg["pno"], pg["words"], pg["text"],
                                            pg["stmt"], pg["ocr"])
        scale, unit_src = pg["scale"], "page"
        if scale is None:
            scale, unit_src = doc_scale, "document"
        if scale is None:
            pages.append({"page": pno, "statement": stmt, "ocr": used_ocr,
                          "note": "unit not stated anywhere — page skipped"})
            continue
        basis = layout.detect_basis(text[:600])

        rows = layout.group_rows(words)
        bands = layout.column_bands(rows)
        if not bands:
            pages.append({"page": pno, "statement": stmt, "ocr": used_ocr,
                          "note": "no numeric columns found"})
            continue

        lines = layout.parse_lines(rows, bands, stmt)
        if not lines:
            pages.append({"page": pno, "statement": stmt, "ocr": used_ocr,
                          "note": "no tracked line items"})
            continue

        # header ends where the first real figure row starts
        first_y = min(y for y, g in rows
                      if len([w for w in g if layout.is_figure(w[4])]) >= 2)
        periods = layout.parse_periods(rows, bands, first_y, stmt)
        if not any(periods):
            pages.append({"page": pno, "statement": stmt, "ocr": used_ocr,
                          "note": "period header not resolved"})
            continue

        got = 0
        for tag, bi, raw in lines:
            per = periods[bi] if bi < len(periods) else None
            if not per:
                continue
            val = layout.to_value(raw)
            nil = val is None and layout.is_nil(raw)
            # a printed dash is a reported nil; anything else unparsable is absent
            if val is None and not nil:
                continue
            if nil:
                val = 0.0
            per_share = tag in TX.PER_SHARE
            facts.append({
                "symbol": symbol, "tag": tag, "statement": stmt, "basis": basis,
                "period_type": per["period_type"], "period_end": per["period_end"],
                "fiscal_label": per["fiscal_label"], "audited": per["audited"],
                # per-share figures are printed in rupees, never in the page unit
                "value": val if per_share else val * scale,
                "unit": "INR", "per_share": per_share, "reported_nil": nil,
                "source_pdf": rel, "page_no": pno, "ocr": used_ocr,
                "raw": raw.strip(),
            })
            got += 1
        pages.append({"page": pno, "statement": stmt, "basis": basis,
                      "ocr": used_ocr, "scale": scale, "unit_from": unit_src,
                      "columns": len(bands),
                      "periods": [p["fiscal_label"] if p else None for p in periods],
                      "facts": got})

    doc.close()
    return {"identity": {**ident, "symbol": symbol, "resolved_by": how},
            "facts": facts, "pages": pages, "sha1": sha, "source_pdf": rel}
