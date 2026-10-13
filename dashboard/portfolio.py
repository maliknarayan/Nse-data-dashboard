"""Persistent portfolio holdings — a tiny JSON file in the warehouse root.

Mirrors watchlist.py's storage pattern: one symbol, one qty, one avg cost per row.
"""

from __future__ import annotations

import json
import os

from .loader import DATA_DIR

_PATH = os.path.join(DATA_DIR, "_portfolio.json")


def load() -> list[dict]:
    if not os.path.exists(_PATH):
        return []
    try:
        with open(_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        return [{"Symbol": str(r.get("Symbol", "")).upper(),
                 "Qty": r.get("Qty"), "AvgCost": r.get("AvgCost")}
                for r in data if str(r.get("Symbol", "")).strip()]
    except Exception:
        return []


def save(rows: list[dict]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(_PATH, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2)


def add(symbol: str, qty: float, avg_cost: float) -> list[dict]:
    """Add a holding, or replace it if the symbol is already in the portfolio."""
    sym = symbol.strip().upper()
    if not sym:
        return load()
    rows = [r for r in load() if r["Symbol"] != sym]
    rows.append({"Symbol": sym, "Qty": qty, "AvgCost": avg_cost})
    save(rows)
    return rows


def remove(symbol: str) -> list[dict]:
    sym = symbol.strip().upper()
    rows = [r for r in load() if r["Symbol"] != sym]
    save(rows)
    return rows
