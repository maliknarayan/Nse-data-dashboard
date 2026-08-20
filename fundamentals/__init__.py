"""Parse SEBI Reg 33 quarterly result PDFs into structured facts.

Deterministic — regex + geometry, no LLM. Values are stored in base rupees;
per-share figures are never scaled; missing values are absent, never 0; every
fact carries its source PDF and page number.

Entry point: ``python -m fundamentals`` (loops result-pdf/).
"""

from __future__ import annotations

RESULT_DIR = "result-pdf"
OUT_DIR = "fundamentals"
