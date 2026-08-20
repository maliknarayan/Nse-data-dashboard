"""Word boxes for any page, text-layer or scanned.

One output shape for both paths — (x0, y0, x1, y1, text) in PDF points — so
layout code never knows whether a page was OCR'd. Scanned pages need two
tesseract passes: psm 4 reads the period header row, psm 6 reads the body.
Neither mode does both (psm 6 mangles headers, psm 4 mangles body rows).

OCR output is cached per (pdf sha1, page, pass) so re-parses cost nothing.
"""

from __future__ import annotations

import csv
import hashlib
import os
import shutil
import subprocess
import tempfile

import fitz

Word = tuple[float, float, float, float, str]

# scanned pages get rendered this big before OCR
HEADER_DPI = 500
BODY_DPI = 400
# fraction of page height treated as the period-header band
HEADER_BAND = 0.22
# a page with fewer real characters than this is treated as scanned
TEXT_MIN_CHARS = 200

_TESS_DIRS = [
    r"C:\Program Files\Tesseract-OCR",
    r"C:\Program Files (x86)\Tesseract-OCR",
    "/usr/bin",
    "/usr/local/bin",
]


def tesseract_exe() -> str | None:
    """Locate tesseract — PATH first, then the usual Windows install dirs."""
    found = shutil.which("tesseract")
    if found:
        return found
    for d in _TESS_DIRS:
        for exe in ("tesseract.exe", "tesseract"):
            p = os.path.join(d, exe)
            if os.path.exists(p):
                return p
    return None


def pdf_sha1(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def has_text_layer(page: fitz.Page) -> bool:
    return len(page.get_text().strip()) >= TEXT_MIN_CHARS


def _text_words(page: fitz.Page) -> list[Word]:
    return [(w[0], w[1], w[2], w[3], w[4]) for w in page.get_text("words")
            if w[4].strip()]


def _run_tesseract(png: str, psm: int, exe: str) -> list[tuple[int, int, int, int, str]]:
    """OCR one image, return word boxes in image pixels."""
    with tempfile.TemporaryDirectory() as td:
        stem = os.path.join(td, "out")
        cmd = [exe, png, stem, "--psm", str(psm), "-l", "eng", "tsv"]
        subprocess.run(cmd, check=True, capture_output=True)
        with open(stem + ".tsv", encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE))
    out = []
    for r in rows:
        txt = (r.get("text") or "").strip()
        if not txt or r.get("level") != "5":
            continue
        try:
            left, top = int(r["left"]), int(r["top"])
            w, h = int(r["width"]), int(r["height"])
        except (KeyError, ValueError):
            continue
        out.append((left, top, left + w, top + h, txt))
    return out


def _ocr_words(page: fitz.Page, cache_dir: str, key: str, exe: str) -> list[Word]:
    """Two-pass OCR: psm 4 over the header band, psm 6 over the body."""
    os.makedirs(cache_dir, exist_ok=True)
    rect = page.rect
    words: list[Word] = []

    with tempfile.TemporaryDirectory() as td:
        # header band at high dpi — psm 4 keeps the period columns intact
        clip = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + rect.height * HEADER_BAND)
        hp = os.path.join(td, "hdr.png")
        page.get_pixmap(dpi=HEADER_DPI, clip=clip).save(hp)
        scale = 72.0 / HEADER_DPI
        for x0, y0, x1, y1, t in _cached(cache_dir, f"{key}.h", hp, 4, exe):
            words.append((x0 * scale, y0 * scale, x1 * scale, y1 * scale, t))

        # full page — psm 6 for the line items
        bp = os.path.join(td, "body.png")
        page.get_pixmap(dpi=BODY_DPI).save(bp)
        scale = 72.0 / BODY_DPI
        cutoff = rect.y0 + rect.height * HEADER_BAND
        for x0, y0, x1, y1, t in _cached(cache_dir, f"{key}.b", bp, 6, exe):
            y0s, y1s = y0 * scale, y1 * scale
            # header band already covered by the psm 4 pass
            if y1s <= cutoff:
                continue
            words.append((x0 * scale, y0s, x1 * scale, y1s, t))
    return words


def _cached(cache_dir: str, key: str, png: str, psm: int,
            exe: str) -> list[tuple[int, int, int, int, str]]:
    path = os.path.join(cache_dir, f"{key}.tsv")
    if os.path.exists(path):
        with open(path, encoding="utf-8", newline="") as fh:
            return [(int(a), int(b), int(c), int(d), t)
                    for a, b, c, d, t in csv.reader(fh, delimiter="\t")]
    rows = _run_tesseract(png, psm, exe)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        csv.writer(fh, delimiter="\t").writerows(rows)
    os.replace(tmp, path)
    return rows


def page_words(page: fitz.Page, *, cache_dir: str, sha: str,
               ocr_exe: str | None) -> tuple[list[Word], bool]:
    """Word boxes plus whether OCR was used."""
    if has_text_layer(page):
        return _text_words(page), False
    if not ocr_exe:
        return [], True
    key = f"{sha[:12]}_p{page.number + 1:03d}"
    return _ocr_words(page, cache_dir, key, ocr_exe), True
