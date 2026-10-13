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
    # symbol -> industry + ISIN for every broad-market index constituent. The only
    # feed with full industry coverage; corporate_announcements only tags filers.
    {"name": "index_constituents", "kind": "snapshot", "group": "reference",
     "fn": "custom.index_constituents", "params": {}, "key": ["Symbol", "Index"],
     "optional": True},
    {"name": "board_meetings", "kind": "date_range", "group": "filings",
     "fn": "custom.board_meetings", "params": {}, "key": None, "optional": True},
    {"name": "shareholding_patterns", "kind": "date_range", "group": "filings",
     "fn": "custom.shareholding_patterns", "params": {}, "key": None, "optional": True},
    {"name": "sast_disclosures", "kind": "date_range", "group": "filings",
     "fn": "custom.sast_disclosures", "params": {}, "key": None, "optional": True},
    {"name": "insider_trading", "kind": "date_range", "group": "filings",
     "fn": "custom.insider_trading", "params": {}, "key": None, "optional": True},
    # nselib's bhav_copy_sme hits a retired per-series archive path (404s on every
    # date) - NSE replaced it with the unified UDiFF bhavcopy zip; this overrides
    # the broken registry entry in config.py (same name -> registry() picks this one)
    {"name": "sme_bhavcopy", "kind": "per_date", "group": "bhav",
     "fn": "custom.sme_bhavcopy", "params": {}, "key": None, "optional": True},
    # daily provisional FII/DII cash-market buy/sell/net - the most-watched
    # single number for Indian equity investors, not covered by nselib at all
    {"name": "fii_dii_activity", "kind": "snapshot", "group": "breadth",
     "fn": "custom.fii_dii_activity", "params": {}, "key": ["category", "date"],
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


_PIT_URL = ("https://www.nseindia.com/api/corporates-pit"
            "?index=equities&from_date={frm}&to_date={to}")
_SAST_URL = ("https://www.nseindia.com/api/corporate-sast-reg29"
             "?index=equities&from_date={frm}&to_date={to}")
_SHP_URL = ("https://www.nseindia.com/api/corporate-share-holdings-master"
            "?index=equities&from_date={frm}&to_date={to}")
_BM_URL = ("https://www.nseindia.com/api/corporate-board-meetings"
           "?index=equities&from_date={frm}&to_date={to}")
# the broad-market family covers ~1,000 names between them; sectoral indices
# would only repeat the same symbols under a coarser label
_INDEX_LISTS = ("Nifty Total Market", "Nifty 500", "Nifty Microcap 250",
                "Nifty Smallcap 250")


def _nse_api(url: str, from_date=None, to_date=None) -> pd.DataFrame:
    """One NSE corporate-filing endpoint -> DataFrame. Shape varies: some return
    a bare list, others wrap it in data/rows."""
    from nselib.libutil import nse_urlfetch
    payload = nse_urlfetch(url.format(frm=from_date, to=to_date)).json()
    rows = payload if isinstance(payload, list) else (
        payload.get("data") or payload.get("rows") or [])
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def index_constituents(**_) -> pd.DataFrame:
    # nselib does the fetch; this only loops the indices and stamps which one
    from nselib import indices
    frames = []
    for name in _INDEX_LISTS:
        try:
            df = indices.constituent_stock_list("BroadMarketIndices", name)
        except Exception:
            continue
        if df is not None and not df.empty:
            frames.append(df.assign(Index=name))
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out.columns = [str(c).strip() for c in out.columns]
    return out


def board_meetings(from_date=None, to_date=None, **_) -> pd.DataFrame:
    return _nse_api(_BM_URL, from_date, to_date)


def shareholding_patterns(from_date=None, to_date=None, **_) -> pd.DataFrame:
    return _nse_api(_SHP_URL, from_date, to_date)


def sast_disclosures(from_date=None, to_date=None, **_) -> pd.DataFrame:
    return _nse_api(_SAST_URL, from_date, to_date)


def insider_trading(from_date=None, to_date=None, **_) -> pd.DataFrame:
    return _nse_api(_PIT_URL, from_date, to_date)


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


_UDIFF_BHAV_URL = ("https://nsearchives.nseindia.com/content/cm/"
                   "BhavCopy_NSE_CM_0_0_0_{yyyymmdd}_F_0000.csv.zip")
_SME_SERIES = {"SM", "ST"}  # SME main board + SME-ITP


def sme_bhavcopy(trade_date=None, **_) -> pd.DataFrame:
    # SME series rows filtered out of NSE's unified UDiFF bhavcopy zip
    import io
    import zipfile
    import datetime as _dt
    from nselib.libutil import nse_urlfetch
    d = _dt.datetime.strptime(trade_date, "%d-%m-%Y")
    url = _UDIFF_BHAV_URL.format(yyyymmdd=d.strftime("%Y%m%d"))
    r = nse_urlfetch(url)
    if r.status_code != 200:
        raise FileNotFoundError(f" Data not found, change the trade_date...")
    z = zipfile.ZipFile(io.BytesIO(r.content))
    df = pd.read_csv(z.open(z.namelist()[0]))
    return df[df["SctySrs"].isin(_SME_SERIES)].reset_index(drop=True)


_FIIDII_URL = "https://www.nseindia.com/api/fiidiiTradeReact"


def fii_dii_activity(**_) -> pd.DataFrame:
    # daily provisional FII/FPI + DII cash-market buy/sell/net
    from nselib.libutil import nse_urlfetch
    data = nse_urlfetch(_FIIDII_URL).json()
    return pd.DataFrame(data) if data else pd.DataFrame()
