"""CSV warehouse. All disk layout lives here.

Swap this module for a DuckDB/parquet backend later without touching collector
logic — the collector only calls: normalize, write_growing, write_per_date,
per_date_exists, append_manifest.

Layout::

    data/<dataset>/<dataset>.csv            # snapshot + date_range (growing)
    data/<dataset>/<dataset>_<YYYY-MM-DD>.csv  # per_date (one file per date)
    data/_manifest.csv                      # append-only write log
"""

from __future__ import annotations

import datetime as dt
import os
from typing import Any

import pandas as pd

from .config import COLLECTED_ON, Settings

_MANIFEST_COLS = [
    "run_ts", "dataset", "kind", "target", "rows_in", "rows_written",
    "total_rows", "path", "status",
]


def normalize(obj: Any) -> pd.DataFrame:
    """Coerce any nselib return (DataFrame, tuple, list, dict, None) to a df."""
    if obj is None:
        return pd.DataFrame()
    if isinstance(obj, pd.DataFrame):
        return obj.copy()
    if isinstance(obj, (list, tuple)):
        # some fns return (summary_dict, df); keep the largest embedded df
        frames = [x for x in obj if isinstance(x, pd.DataFrame)]
        if frames:
            return max(frames, key=len).copy()
        if not obj:
            return pd.DataFrame()
        if all(isinstance(x, dict) for x in obj):
            return pd.DataFrame(list(obj))
        return pd.DataFrame({"value": list(obj)})
    if isinstance(obj, dict):
        return pd.DataFrame([obj])
    return pd.DataFrame({"value": [obj]})


def _effective_key(df: pd.DataFrame, key: list[str] | None) -> list[str]:
    """Preferred key columns that actually exist; else all columns."""
    if key:
        present = [c for c in key if c in df.columns]
        if present:
            return present
    return list(df.columns)


class NseWarehouse:
    def __init__(self, settings: Settings | None = None):
        self.s = settings or Settings()

    # --- paths ---
    def _growing_path(self, name: str) -> str:
        return os.path.join(self.s.dataset_dir(name), f"{name}.csv")

    def per_date_path(self, name: str, d: dt.date) -> str:
        from .calendar_util import to_iso
        return os.path.join(self.s.dataset_dir(name), f"{name}_{to_iso(d)}.csv")

    def per_date_exists(self, name: str, d: dt.date) -> bool:
        return os.path.exists(self.per_date_path(name, d))

    # --- writers ---
    def write_growing(self, name: str, df: pd.DataFrame, key: list[str] | None,
                      snapshot: bool) -> tuple[int, int]:
        """Merge df into the one growing CSV, deduped. Returns (rows_in, total)."""
        rows_in = len(df)
        if rows_in == 0:
            existing = self._read(self._growing_path(name))
            return 0, len(existing)

        path = self._growing_path(name)
        existing = self._read(path)
        merged = pd.concat([existing, df], ignore_index=True) if len(existing) else df

        subset = _effective_key(merged, key)
        if snapshot and COLLECTED_ON in merged.columns and COLLECTED_ON not in subset:
            subset = subset + [COLLECTED_ON]
        merged = merged.drop_duplicates(subset=subset, keep="last").reset_index(drop=True)

        self._atomic_write(path, merged)
        return rows_in, len(merged)

    def write_per_date(self, name: str, df: pd.DataFrame, d: dt.date) -> tuple[int, str]:
        """Write one file for a date. Caller guarantees it doesn't exist yet."""
        path = self.per_date_path(name, d)
        self._atomic_write(path, df)
        return len(df), path

    # --- manifest ---
    def append_manifest(self, **row) -> None:
        os.makedirs(self.s.data_dir, exist_ok=True)
        path = self.s.manifest_path
        rec = {c: row.get(c, "") for c in _MANIFEST_COLS}
        line = pd.DataFrame([rec], columns=_MANIFEST_COLS)
        header = not os.path.exists(path)
        line.to_csv(path, mode="a", header=header, index=False)

    # --- helpers ---
    @staticmethod
    def _read(path: str) -> pd.DataFrame:
        if os.path.exists(path):
            try:
                return pd.read_csv(path)
            except pd.errors.EmptyDataError:
                return pd.DataFrame()
        return pd.DataFrame()

    @staticmethod
    def _atomic_write(path: str, df: pd.DataFrame) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.tmp"
        df.to_csv(tmp, index=False)
        os.replace(tmp, path)
