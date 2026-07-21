"""Persistent watchlist — a tiny JSON file in the warehouse root.

Kept dead simple and isolated so it survives restarts and can later move to a
DB alongside the storage swap.
"""

from __future__ import annotations

import json
import os

from .loader import DATA_DIR

_PATH = os.path.join(DATA_DIR, "_watchlist.json")
_STATE = os.path.join(DATA_DIR, "_watchlist_state.json")


def load() -> list[str]:
    if not os.path.exists(_PATH):
        return []
    try:
        with open(_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        return [str(s).upper() for s in data if str(s).strip()]
    except Exception:
        return []


def _save(symbols: list[str]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(_PATH, "w", encoding="utf-8") as fh:
        json.dump(sorted(set(symbols)), fh, indent=2)


def add(symbol: str) -> list[str]:
    sym = symbol.strip().upper()
    if not sym:
        return load()
    syms = load()
    if sym not in syms:
        syms.append(sym)
        _save(syms)
    return load()


def remove(symbol: str) -> list[str]:
    sym = symbol.strip().upper()
    syms = [s for s in load() if s != sym]
    _save(syms)
    return syms


def load_state() -> dict:
    if not os.path.exists(_STATE):
        return {}
    try:
        with open(_STATE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_state(scores: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(_STATE, "w", encoding="utf-8") as fh:
        json.dump({str(k).upper(): int(v) for k, v in scores.items()}, fh, indent=2)
