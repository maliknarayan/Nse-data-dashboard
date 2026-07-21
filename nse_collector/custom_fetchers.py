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
    # full listed-equity master (symbol + company name + ISIN) from NSE's public
    # EQUITY_L.csv; nselib's equity_list() is broken in 2.5.1. Powers autocomplete.
    {"name": "equity_master", "kind": "snapshot", "group": "reference",
     "fn": "custom.equity_master", "params": {}, "key": ["SYMBOL"],
     "optional": True},
    # corporate filings/announcements (board meetings, results, disclosures)
    {"name": "corporate_announcements", "kind": "date_range", "group": "filings",
     "fn": "custom.corporate_announcements", "params": {}, "key": ["seq_id"],
     "optional": True},
]

_EQUITY_L_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
_ANNOUNCE_URL = ("https://www.nseindia.com/api/corporate-announcements"
                 "?index=equities&from_date={frm}&to_date={to}")


def corporate_announcements(from_date=None, to_date=None, **_):
    # corporate filings/disclosures feed — not in nselib, scraped via NSE session
    from nselib.libutil import nse_urlfetch
    r = nse_urlfetch(_ANNOUNCE_URL.format(frm=from_date, to=to_date))
    data = r.json()
    if not isinstance(data, list) or not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    keep = ["symbol", "sm_name", "desc", "attchmntText", "smIndustry",
            "an_dt", "sort_date", "attchmntFile", "seq_id"]
    df = df[[c for c in keep if c in df.columns]]
    ren = {"sm_name": "Company", "desc": "Subject", "attchmntText": "Details",
           "smIndustry": "Industry", "an_dt": "Filed", "attchmntFile": "Attachment"}
    return df.rename(columns=ren)


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


def equity_master() -> pd.DataFrame:
    # reuse nselib's session handling to fetch the public master CSV
    import io
    from nselib.libutil import nse_urlfetch
    r = nse_urlfetch(_EQUITY_L_URL)
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = [c.strip() for c in df.columns]
    return df


def mwpl() -> pd.DataFrame:
    # stub: MWPL is not in nselib; implement against the live source if needed
    raise NotImplementedError(
        "mwpl is a stub - wire it to the live NSE MWPL source and verify output"
    )
