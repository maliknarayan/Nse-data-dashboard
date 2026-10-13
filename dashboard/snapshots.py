"""Daily top-5 snapshot history — one JSON file in the warehouse root.

Records what each page's top-5 looked like on a given calendar date, so
pages can show "dropped out since last time" and backtest past picks.
Mirrors watchlist.py's storage pattern.
"""

from __future__ import annotations

import datetime as dt
import json
import os

from .loader import DATA_DIR

_PATH = os.path.join(DATA_DIR, "_top5_history.json")


def _load() -> dict:
    if not os.path.exists(_PATH):
        return {}
    try:
        with open(_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _save(data: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def record(page_key: str, rows: list[tuple]) -> None:
    """Overwrite today's top-N for page_key. rows = (symbol, value, ...) tuples, caller controls N."""
    clean = []
    for row in rows:
        sym, val = row[0], row[1]
        try:
            val = float(val)
        except (TypeError, ValueError):
            continue
        clean.append([str(sym), val])
    if not clean:
        return
    today = dt.date.today().isoformat()
    data = _load()
    data.setdefault(page_key, {})[today] = clean
    _save(data)


def previous_entry(page_key: str) -> tuple[str, list[tuple]] | None:
    """Most recently recorded date BEFORE today for page_key, or None."""
    data = _load().get(page_key, {})
    today = dt.date.today().isoformat()
    dates = sorted(d for d in data if d < today)
    if not dates:
        return None
    d = dates[-1]
    return d, [(r[0], r[1]) for r in data[d]]


def dropped_out(page_key: str, today_symbols: list[str]) -> tuple[str, list[str]] | None:
    """Symbols in the previous recorded top-5 that aren't in today's — (prev_date, symbols)."""
    prev = previous_entry(page_key)
    if not prev:
        return None
    prev_date, prev_rows = prev
    prev_syms = [s for s, _ in prev_rows]
    today_set = {s.upper() for s in today_symbols}
    gone = [s for s in prev_syms if s.upper() not in today_set]
    return prev_date, gone
