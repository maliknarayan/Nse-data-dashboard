"""BSE (Bombay Stock Exchange) collector.

BSE has no clean library like nselib, so this is a small, isolated scraper for
data NOT already covered by NSE — primarily the BSE EOD bhav copy (the BSE-listed
universe, ~4800 scrips, many BSE-only). Reuses the NSE collector's storage,
calendar and settings so the warehouse stays uniform.

BSE gates its endpoints; fetchers degrade gracefully (a blocked/holiday day is
skipped, never a crash), mirroring the per_date behaviour on the NSE side.
"""

__version__ = "0.1.0"
