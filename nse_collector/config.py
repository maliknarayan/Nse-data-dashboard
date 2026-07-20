"""Settings and the dataset registry.

Adding a dataset = adding ONE dict to ``DATASETS``. Nothing else changes.

Each dataset dict declares:
    name    : warehouse folder + file stem, also the CLI --dataset id
    kind    : "snapshot" | "date_range" | "per_date"
    fn      : "module.function" resolved against nselib (capital_market,
              derivatives, indices, cash_market, debt)
    params  : static kwargs always passed to the function
    key     : natural key columns for row de-dup. Meaning depends on kind:
              - snapshot   : entity columns; effective key = key + _collected_on
              - date_range : usually None -> a row is unique as a whole
              - per_date   : ignored (one file per date, no in-file dedup)
    group   : optional tag for CLI --group
    symbol  : True if fn needs a --symbol (option chain); such datasets are
              skipped by the plain daily job unless a symbol is supplied
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


@dataclass
class Settings:
    # warehouse root; per-dataset folders live under here
    data_dir: str = os.environ.get("NSE_DATA_DIR", "data")
    log_dir: str = os.environ.get("NSE_LOG_DIR", "logs")
    # seconds slept between every nselib call to stay polite
    polite_delay: float = _env_float("NSE_POLITE_DELAY", 2.0)
    # network retry policy
    retries: int = _env_int("NSE_RETRIES", 3)
    backoff_base: float = _env_float("NSE_BACKOFF_BASE", 2.0)
    # holiday calendar is fetched once and cached; product segment to honour
    holiday_product: str = "Equities"
    manifest_name: str = "_manifest.csv"
    # daily date_range window: NSE rejects from==to, so look back N days and
    # dedupe (also catches deals/corp actions NSE posts a day or two late)
    daily_range_lookback: int = _env_int("NSE_DAILY_RANGE_LOOKBACK", 5)

    def dataset_dir(self, name: str) -> str:
        return os.path.join(self.data_dir, name)

    @property
    def manifest_path(self) -> str:
        return os.path.join(self.data_dir, self.manifest_name)


# stamped on every snapshot row so history accumulates across days
COLLECTED_ON = "_collected_on"


# --- the registry -----------------------------------------------------------
# fn targets verified against nselib 2.5.1 by inspecting real signatures.
DATASETS: list[dict] = [
    # ---- date_range: one call covers a from/to window ----
    {"name": "bulk_deals", "kind": "date_range", "group": "deals",
     "fn": "capital_market.bulk_deal_data", "params": {}, "key": None},
    {"name": "block_deals", "kind": "date_range", "group": "deals",
     "fn": "capital_market.block_deals_data", "params": {}, "key": None},
    {"name": "short_selling", "kind": "date_range", "group": "deals",
     "fn": "capital_market.short_selling_data", "params": {}, "key": None},
    {"name": "corporate_actions", "kind": "date_range", "group": "corporate",
     "fn": "capital_market.corporate_actions_for_equity", "params": {}, "key": None},

    # ---- snapshot: live state only, cannot be backfilled ----
    # gainers/losers repeat a symbol across index buckets -> key includes legend
    {"name": "top_gainers", "kind": "snapshot", "group": "breadth",
     "fn": "capital_market.top_gainers_or_losers",
     "params": {"to_get": "gainers"}, "key": ["symbol", "legend"]},
    # nselib has a typo: valid value is 'loosers' (double-o), not 'losers'
    {"name": "top_losers", "kind": "snapshot", "group": "breadth",
     "fn": "capital_market.top_gainers_or_losers",
     "params": {"to_get": "loosers"}, "key": ["symbol", "legend"]},
    {"name": "most_active_value", "kind": "snapshot", "group": "breadth",
     "fn": "capital_market.most_active_equities",
     "params": {"fetch_by": "value"}, "key": ["symbol"]},
    {"name": "most_active_volume", "kind": "snapshot", "group": "breadth",
     "fn": "capital_market.most_active_equities",
     "params": {"fetch_by": "volume"}, "key": ["symbol"]},
    {"name": "total_traded_stocks", "kind": "snapshot", "group": "breadth",
     "fn": "capital_market.total_traded_stocks", "params": {}, "key": ["symbol"]},
    {"name": "all_indices", "kind": "snapshot", "group": "indices",
     "fn": "capital_market.market_watch_all_indices", "params": {},
     "key": ["index", "indexSymbol", "index_symbol"]},
    {"name": "index_performances", "kind": "snapshot", "group": "indices",
     "fn": "indices.live_index_performances", "params": {},
     "key": ["index", "indexName", "index_name"]},
    {"name": "most_active_underlying", "kind": "snapshot", "group": "derivatives",
     "fn": "derivatives.live_most_active_underlying", "params": {},
     "key": ["symbol", "underlying"]},
    {"name": "option_chain", "kind": "snapshot", "group": "derivatives",
     "fn": "derivatives.nse_live_option_chain", "params": {}, "symbol": True,
     "key": ["symbol", "expiryDate", "strikePrice", "optionType",
             "expiry_date", "strike_price", "option_type"]},

    # ---- per_date: one report per trading date, one file per date ----
    {"name": "bhavcopy_delivery", "kind": "per_date", "group": "bhav",
     "fn": "capital_market.bhav_copy_with_delivery", "params": {}, "key": None},
    {"name": "fno_bhavcopy", "kind": "per_date", "group": "bhav",
     "fn": "derivatives.fno_bhav_copy", "params": {}, "key": None},
    {"name": "week52_high_low", "kind": "per_date", "group": "reports",
     "fn": "capital_market.week_52_high_low_report", "params": {}, "key": None},
    {"name": "cash_turnover", "kind": "per_date", "group": "turnover",
     "fn": "capital_market.category_turnover_cash", "params": {}, "key": None},
    {"name": "fno_turnover", "kind": "per_date", "group": "turnover",
     "fn": "derivatives.category_turnover_fo", "params": {}, "key": None},
    {"name": "pe_ratio", "kind": "per_date", "group": "reports",
     "fn": "capital_market.pe_ratio", "params": {}, "key": None},
    {"name": "fii_deriv_stats", "kind": "per_date", "group": "derivatives",
     "fn": "derivatives.fii_derivatives_statistics", "params": {}, "key": None},
    {"name": "participant_oi", "kind": "per_date", "group": "derivatives",
     "fn": "derivatives.participant_wise_open_interest", "params": {}, "key": None},
    {"name": "participant_volume", "kind": "per_date", "group": "derivatives",
     "fn": "derivatives.participant_wise_trading_volume", "params": {}, "key": None},
    {"name": "securities_in_ban", "kind": "per_date", "group": "derivatives",
     "fn": "derivatives.fno_security_in_ban_period", "params": {}, "key": None},
    {"name": "daily_volatility", "kind": "per_date", "group": "reports",
     "fn": "capital_market.daily_volatility", "params": {}, "key": None},
]


def registry() -> dict[str, dict]:
    """Datasets keyed by name; includes optional custom fetchers if importable."""
    reg = {d["name"]: d for d in DATASETS}
    try:
        from . import custom_fetchers
        reg.update({d["name"]: d for d in custom_fetchers.CUSTOM_DATASETS})
    except Exception:
        # custom module is optional; collector must run fine without it
        pass
    return reg
