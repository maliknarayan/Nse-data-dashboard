"""Library-first NSE (India) market data collector.

Fetch engine is the ``nselib`` PyPI package. This package only adds a
config-driven registry, a CSV warehouse, dedup/idempotency, scheduling glue
and a CLI on top of it. When NSE changes, upgrade ``nselib`` — do not patch
scrapers here.
"""

__version__ = "0.1.0"
