"""NiftyIndices.com collector.

Daily index snapshot covering every NSE index family in one file (broad,
sectoral, thematic, strategy, fixed income, G-Sec, SDL, corporate bond) with
OHLC, turnover and P/E, P/B, Div Yield per index - broader and more valuation-
complete than nselib's live index snapshot. Reuses the NSE collector's
storage, calendar and settings so the warehouse stays uniform.
"""

__version__ = "0.1.0"
