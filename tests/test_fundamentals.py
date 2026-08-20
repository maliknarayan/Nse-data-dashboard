"""Parser guards. The OCR-repair cases are the ones that silently corrupt data."""

from __future__ import annotations

import datetime as dt
import json
import os

import pytest

from fundamentals import layout, validate
from fundamentals import taxonomy as TX

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_JSON = os.path.join(_ROOT, "data", "fundamentals", "EBGNG.json")


@pytest.mark.parametrize("raw,expect", [
    ("2,270.35", 2270.35),
    ("(924.43)", -924.43),
    ("89,39", 89.39),          # decimal point read as a comma
    ("194,27", 194.27),
    ("1,1 10.45", 1110.45),    # space injected mid-number
    ("(70. 10)", -70.10),      # space after the decimal point
    ("2.613.39", 2613.39),     # thousands separator read as a period
    ("_3.68", 3.68),           # stray leading underscore
    ("-", None),               # nil, not zero
    ("", None),
])
def test_to_value(raw, expect):
    assert layout.to_value(raw) == expect


@pytest.mark.parametrize("raw", ["58", "2025", "1,234", "-", "Ill"])
def test_bare_integers_are_not_figures(raw):
    """A value without decimals is an OCR fragment — '58' out of '1.58'."""
    assert not layout.is_figure(raw)


@pytest.mark.parametrize("raw", ["2,270.35", "(924.43)", "89,39", "0.86"])
def test_real_figures_are_figures(raw):
    assert layout.is_figure(raw)


@pytest.mark.parametrize("end,ptype,expect", [
    (dt.date(2025, 12, 31), "quarter", "Q3FY26"),
    (dt.date(2026, 3, 31), "quarter", "Q4FY26"),
    (dt.date(2025, 9, 30), "quarter", "Q2FY26"),
    (dt.date(2025, 6, 30), "quarter", "Q1FY26"),
    (dt.date(2026, 3, 31), "year", "FY26"),
    (dt.date(2025, 9, 30), "half_year", "H1FY26"),
    (dt.date(2025, 12, 31), "nine_month", "9MFY26"),
])
def test_fiscal_label(end, ptype, expect):
    assert layout.fiscal_label(end, ptype) == expect


def test_eps_is_flagged_per_share():
    """Per-share figures must never be unit-scaled."""
    assert "eps_basic" in TX.PER_SHARE
    assert "eps_diluted" in TX.PER_SHARE
    assert "revenue_from_operations" not in TX.PER_SHARE


def test_validator_needs_all_components():
    """A partial component set must not raise a false sum mismatch."""
    facts = [
        {"basis": "standalone", "statement": "pnl", "period_end": "2025-12-31",
         "period_type": "quarter", "tag": "total_tax_expense", "value": 5.48},
        {"basis": "standalone", "statement": "pnl", "period_end": "2025-12-31",
         "period_type": "quarter", "tag": "current_tax", "value": 6.90},
    ]
    assert validate.check(facts) == []


def test_validator_catches_sum_mismatch():
    """Magnitudes are base rupees — the tolerance absorbs 2-decimal rounding of
    a millions-denominated statement, so a real break has to be larger."""
    facts = [
        {"basis": "standalone", "statement": "pnl", "period_end": "2025-12-31",
         "period_type": "quarter", "tag": "revenue_from_operations",
         "value": 2_270_350_000.0},
        {"basis": "standalone", "statement": "pnl", "period_end": "2025-12-31",
         "period_type": "quarter", "tag": "other_income", "value": 4_730_000.0},
        {"basis": "standalone", "statement": "pnl", "period_end": "2025-12-31",
         "period_type": "quarter", "tag": "total_income", "value": 9_999_000_000.0},
    ]
    issues = validate.check(facts)
    assert [i["kind"] for i in issues] == ["sum_mismatch"]


def test_validator_tolerates_rounding():
    """Components that round to a hair off the printed subtotal must pass."""
    facts = [
        {"basis": "standalone", "statement": "pnl", "period_end": "2025-12-31",
         "period_type": "quarter", "tag": "revenue_from_operations",
         "value": 2_270_350_000.0},
        {"basis": "standalone", "statement": "pnl", "period_end": "2025-12-31",
         "period_type": "quarter", "tag": "other_income", "value": 4_730_000.0},
        {"basis": "standalone", "statement": "pnl", "period_end": "2025-12-31",
         "period_type": "quarter", "tag": "total_income", "value": 2_275_090_000.0},
    ]
    assert validate.check(facts) == []


def test_validator_catches_diluted_above_basic():
    facts = [
        {"basis": "standalone", "statement": "pnl", "period_end": "2026-03-31",
         "period_type": "year", "tag": "eps_basic", "value": 3.50},
        {"basis": "standalone", "statement": "pnl", "period_end": "2026-03-31",
         "period_type": "year", "tag": "eps_diluted", "value": 3.68},
    ]
    assert [i["kind"] for i in validate.check(facts)] == ["diluted_gt_basic"]


# --- integration: needs a parsed warehouse, skipped when absent ---

@pytest.fixture(scope="module")
def doc():
    if not os.path.exists(_JSON):
        pytest.skip("run `python -m fundamentals` first")
    with open(_JSON, encoding="utf-8") as fh:
        return json.load(fh)


def _val(doc, stmt, basis, period, tag):
    return doc["statements"][stmt][basis][period][tag]["value"]


def test_values_are_base_rupees(doc):
    """228.02 million on the page must land as 228,020,000 rupees."""
    assert _val(doc, "pnl", "consolidated", "FY26",
                "paid_up_equity_share_capital") == pytest.approx(228_020_000)
    assert _val(doc, "pnl", "consolidated", "FY26",
                "profit_for_period") == pytest.approx(1_320_160_000)


def test_eps_stays_in_rupees(doc):
    assert _val(doc, "pnl", "consolidated", "FY26",
                "eps_basic") == pytest.approx(11.58)
    assert _val(doc, "pnl", "standalone", "FY26",
                "eps_basic") == pytest.approx(3.50)


def test_every_fact_carries_provenance(doc):
    for stmt, bases in doc["statements"].items():
        for basis, periods in bases.items():
            for period, tags in periods.items():
                for tag, f in tags.items():
                    assert f["source_pdf"], (stmt, basis, period, tag)
                    assert isinstance(f["page_no"], int), (stmt, basis, period, tag)


def test_seven_quarters_both_bases(doc):
    want = {"Q2FY25", "Q3FY25", "Q4FY25", "Q1FY26", "Q2FY26", "Q3FY26", "Q4FY26"}
    for basis in ("standalone", "consolidated"):
        assert want <= set(doc["statements"]["pnl"][basis])


def test_no_zero_stands_in_for_missing(doc):
    """Only a printed dash may be zero; absent lines must be absent."""
    facts = doc["statements"]
    for stmt, bases in facts.items():
        for basis, periods in bases.items():
            for period, tags in periods.items():
                for tag, f in tags.items():
                    if f["value"] == 0:
                        assert tag not in ("revenue_from_operations",
                                           "total_income", "total_assets")
