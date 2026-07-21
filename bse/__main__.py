"""BSE CLI.

    python -m bse                                  # today's BSE bhav copy
    python -m bse --backfill --from 2026-07-01 --to 2026-07-17
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys

from nse_collector.collector import setup_logging
from nse_collector.config import Settings

from .collect import BseCollector


def _date(s: str) -> dt.date:
    return dt.datetime.strptime(s, "%Y-%m-%d").date()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="bse", description="BSE bhav copy collector")
    p.add_argument("--backfill", action="store_true")
    p.add_argument("--from", dest="frm", type=_date)
    p.add_argument("--to", dest="to", type=_date)
    p.add_argument("--polite", type=float)
    p.add_argument("--verbose", action="store_true")
    a = p.parse_args(argv)

    s = Settings()
    if a.polite is not None:
        s.polite_delay = a.polite
    setup_logging(s, verbose=a.verbose)
    c = BseCollector(s)

    if a.backfill:
        if not a.frm or not a.to:
            print("--backfill needs --from and --to", file=sys.stderr)
            return 2
        summ = c.run_backfill(a.frm, a.to)
    else:
        summ = c.run_daily()
    print(f"\nSUMMARY: {summ.line()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
