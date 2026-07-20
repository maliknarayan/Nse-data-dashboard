"""Command-line entry point.

Examples::

    python -m nse_collector --list
    python -m nse_collector                 # full daily job (after market close)
    python -m nse_collector --snapshot
    python -m nse_collector --all-per-date
    python -m nse_collector --dataset bhavcopy_delivery --dataset fno_bhavcopy
    python -m nse_collector --group derivatives
    python -m nse_collector --symbol NIFTY --dataset option_chain
    python -m nse_collector --backfill --from 2026-07-01 --to 2026-07-10
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys

from . import calendar_util as cal
from .collector import Collector, setup_logging
from .config import Settings
from .resolver import validate_registry


def _parse_date(s: str) -> dt.date:
    return dt.datetime.strptime(s, "%Y-%m-%d").date()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nse_collector",
                                description="Library-first NSE market data collector")
    p.add_argument("--list", action="store_true", help="list datasets + resolve status")
    p.add_argument("--snapshot", action="store_true", help="run snapshot datasets only")
    p.add_argument("--all-per-date", action="store_true",
                   help="run per_date datasets for the last trading day")
    p.add_argument("--all-date-range", action="store_true",
                   help="run date_range datasets for --from..--to (default last 7d)")
    p.add_argument("--dataset", action="append", default=[], metavar="NAME",
                   help="restrict to this dataset (repeatable)")
    p.add_argument("--group", action="append", default=[], metavar="GROUP",
                   help="restrict to this group (repeatable)")
    p.add_argument("--from", dest="frm", type=_parse_date, metavar="YYYY-MM-DD")
    p.add_argument("--to", dest="to", type=_parse_date, metavar="YYYY-MM-DD")
    p.add_argument("--symbol", help="symbol for datasets that need one (option_chain)")
    p.add_argument("--backfill", action="store_true",
                   help="fill per_date + date_range for --from..--to")
    p.add_argument("--polite", type=float, metavar="SECONDS",
                   help="override delay between calls")
    p.add_argument("--verbose", action="store_true")
    return p


def _print_list(collector: Collector) -> None:
    errors = validate_registry(collector.reg)
    print(f"{'name':<22}{'kind':<12}{'group':<14}{'status':<10}fn")
    print("-" * 88)
    for ds in collector.reg.values():
        status = "ERR" if ds["name"] in errors else "ok"
        print(f"{ds['name']:<22}{ds['kind']:<12}{str(ds.get('group','')):<14}"
              f"{status:<10}{ds['fn']}")
    if errors:
        print("\nresolve errors:")
        for name, err in errors.items():
            print(f"  {name}: {err}")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    settings = Settings()
    if args.polite is not None:
        settings.polite_delay = args.polite
    setup_logging(settings, verbose=args.verbose)

    collector = Collector(settings)

    if args.list:
        _print_list(collector)
        return 0

    names = args.dataset or None
    groups = args.group or None

    if args.backfill:
        if not args.frm or not args.to:
            print("--backfill requires --from and --to", file=sys.stderr)
            return 2
        summary = collector.run_backfill(args.frm, args.to, names=names, groups=groups)
    elif args.snapshot or args.all_per_date or args.all_date_range:
        # kind-scoped partial run
        if args.snapshot:
            for ds in collector.select(kinds={"snapshot"}, names=names, groups=groups):
                collector.collect_snapshot(ds, dt.date.today(), symbol=args.symbol)
        if args.all_per_date:
            day = cal.last_trading_day(product=settings.holiday_product)
            for ds in collector.select(kinds={"per_date"}, names=names, groups=groups):
                collector.collect_per_date(ds, day)
        if args.all_date_range:
            to = args.to or cal.last_trading_day(product=settings.holiday_product)
            frm = args.frm or (to - dt.timedelta(days=7))
            for ds in collector.select(kinds={"date_range"}, names=names, groups=groups):
                collector.collect_date_range(ds, frm, to)
        summary = collector.summary
    else:
        # default: full daily job
        summary = collector.run_daily(names=names, groups=groups, symbol=args.symbol)

    print(f"\nSUMMARY: {summary.line()}")
    if summary.failed:
        print("FAILED: " + ", ".join(summary.failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
