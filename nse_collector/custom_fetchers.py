"""OPTIONAL custom fetchers for data NOT covered by nselib.

STUBS — verify against the live NSE site before trusting them. The whole file
is optional: delete it (or its datasets) and the collector runs unchanged.
Datasets here are marked ``optional: True`` so a failure is logged as a skip,
never a hard run failure.

- advances_declines : best-effort, derived from the summary dict that
  ``capital_market.total_traded_stocks`` already returns. Confirm the numbers
  match the NSE site before relying on them.
- mwpl : Market-Wide Position Limit. Not exposed by nselib and not implemented;
  wire it to the live source yourself if you need it.
"""

from __future__ import annotations

import pandas as pd

CUSTOM_DATASETS: list[dict] = [
    {"name": "advances_declines", "kind": "snapshot", "group": "breadth",
     "fn": "custom.advances_declines", "params": {}, "key": ["metric"],
     "optional": True},
    {"name": "mwpl", "kind": "snapshot", "group": "derivatives",
     "fn": "custom.mwpl", "params": {}, "key": None, "optional": True},
]


def advances_declines() -> pd.DataFrame:
    # reuse the breadth summary nselib already returns; verify vs live site
    from nselib import capital_market
    result = capital_market.total_traded_stocks()
    summary = None
    if isinstance(result, (list, tuple)):
        summary = next((x for x in result if isinstance(x, dict)), None)
    if not summary:
        return pd.DataFrame()
    return pd.DataFrame([{"metric": k, "value": v} for k, v in summary.items()])


def mwpl() -> pd.DataFrame:
    # stub: MWPL is not in nselib; implement against the live source if needed
    raise NotImplementedError(
        "mwpl is a stub - wire it to the live NSE MWPL source and verify output"
    )
