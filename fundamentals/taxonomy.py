"""Canonical fact tags and the label patterns that map onto them.

Ordered — first match wins, so specific patterns precede general ones
("total income" before "income"). Labels arrive OCR-damaged, so matching runs
on a normalised string with the corruptions seen in real filings folded out.

``per_share`` tags are exempt from unit scaling: EPS and face value are printed
in rupees regardless of whether the statement is in millions or lakhs.
"""

from __future__ import annotations

import re

PNL, BS, CF = "pnl", "bs", "cf"

# OCR substitutions observed in Online2PDF / tesseract output
_FIXES = {
    "eauity": "equity", "eauitv": "equity", "deffered": "deferred",
    "pavables": "payables", "pavable": "payable", "recelvables": "receivables",
    "inventorv": "inventory", "propertv": "property", "eaquity": "equity",
    "amortisation": "amortization", "vear": "year", "penod": "period",
}


def normalize(label: str) -> str:
    s = label.lower()
    s = re.sub(r"[^a-z0-9%/ ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for bad, good in _FIXES.items():
        s = s.replace(bad, good)
    return s


# (tag, statement, per_share, pattern)
RULES: list[tuple[str, str, bool, str]] = [
    # --- P&L ---
    ("revenue_from_operations", PNL, False, r"revenue from operations"),
    ("other_income", PNL, False, r"^\w?\)? ?other income"),
    ("total_income", PNL, False, r"total income"),
    ("direct_cost", PNL, False, r"direct cost|cost of materials|purchases of stock"),
    ("change_in_inventory", PNL, False, r"changes? in inventor"),
    ("employee_benefits_expense", PNL, False, r"employee benefit"),
    ("finance_costs", PNL, False, r"finance cost"),
    ("depreciation_amortization", PNL, False, r"depreciation and amortization"),
    ("other_expenses", PNL, False, r"other expenses"),
    ("total_expenses", PNL, False, r"total expenses"),
    ("profit_before_tax", PNL, False, r"profit before tax"),
    ("current_tax", PNL, False, r"^\(?i\)? ?current tax|current tax$"),
    ("deferred_tax", PNL, False, r"deferred tax(?! liabilit)"),
    ("prior_year_tax", PNL, False, r"provisions of income tax of earlier"),
    ("total_tax_expense", PNL, False, r"total tax expense"),
    ("profit_for_period", PNL, False, r"profit for the period"),
    ("remeasurement_defined_benefit", PNL, False, r"re measurement gains"),
    ("fx_translation_oci", PNL, False, r"foreign exchange difference on translation"),
    ("other_comprehensive_income", PNL, False, r"total other comprehensive income"),
    ("total_comprehensive_income", PNL, False, r"total comprehensive income"),
    ("paid_up_equity_share_capital", PNL, False, r"paid up equity share capital"),
    ("eps_basic", PNL, True, r"^\w?\)? ?basic"),
    ("eps_diluted", PNL, True, r"^\w?\)? ?diluted"),

    # --- balance sheet ---
    ("property_plant_equipment", BS, False, r"property plant and equipment"),
    ("capital_work_in_progress", BS, False, r"capital work in progress"),
    ("right_of_use_assets", BS, False, r"right of use asset"),
    ("investments_non_current", BS, False, r"^\(?i\)? ?investments"),
    ("other_financial_assets", BS, False, r"other financial asset"),
    ("other_non_current_assets", BS, False, r"other non current asset"),
    ("total_non_current_assets", BS, False, r"total non current asset"),
    ("inventory", BS, False, r"^\w? ?\)? ?inventor"),
    ("trade_receivables", BS, False, r"trade receivable"),
    ("cash_and_equivalents", BS, False, r"cash and cash equivalents$"),
    ("other_bank_balances", BS, False, r"bank balances other than cash"),
    ("other_current_assets", BS, False, r"other current asset"),
    ("total_current_assets", BS, False, r"total current asset"),
    ("total_assets", BS, False, r"total assets"),
    ("equity_share_capital", BS, False, r"equity share capital"),
    ("other_equity", BS, False, r"other equity"),
    ("total_equity", BS, False, r"total equity$"),
    ("deferred_tax_liabilities", BS, False, r"deferred tax liabilit"),
    ("trade_payables_msme", BS, False, r"dues of micro and small"),
    ("trade_payables_other", BS, False, r"dues other than micro and small"),
    ("provisions", BS, False, r"^\w?\)? ?provisions"),
    ("current_tax_liability", BS, False, r"current tax liability"),
    ("other_current_liabilities", BS, False, r"other current liabilit"),
    ("total_current_liabilities", BS, False, r"total current liabilit"),
    ("total_liabilities", BS, False, r"total liabilities$"),
    ("total_equity_and_liabilities", BS, False, r"total equity and liabilit"),

    # --- cash flow ---
    ("cf_operating_before_wc", CF, False, r"before working capital changes"),
    ("cf_cash_from_operations", CF, False, r"cash generated from.*operations"),
    ("cf_tax_paid", CF, False, r"income tax paid"),
    ("cf_net_operating", CF, False, r"operating activities \(i\)|from.*used in.*operating activities"),
    ("cf_purchase_ppe", CF, False, r"purchase of property plant"),
    ("cf_investment_subsidiary", CF, False, r"investment in subsidiar"),
    ("cf_net_investing", CF, False, r"investing activities"),
    ("cf_working_capital_loan", CF, False, r"working capital loan"),
    ("cf_repay_lt_borrowings", CF, False, r"repayment of long term borrowing"),
    ("cf_proceeds_lt_borrowings", CF, False, r"proceeds of long term borrowing"),
    ("cf_lease_payments", CF, False, r"payment of lease liabilit"),
    ("cf_finance_charges", CF, False, r"finance charges paid"),
    ("cf_ipo_charges", CF, False, r"payment of ipo charges"),
    ("cf_ipo_proceeds", CF, False, r"proceeds from ipo"),
    ("cf_net_financing", CF, False, r"financing activities"),
    ("cf_net_change_cash", CF, False, r"net increase.*decrease.*cash"),
    ("cf_cash_opening", CF, False, r"cash and cash equivalents at the beginning"),
    ("cf_cash_closing", CF, False, r"cash and cash equivalents at the end"),
]

_COMPILED = [(tag, stmt, ps, re.compile(pat)) for tag, stmt, ps, pat in RULES]

PER_SHARE = {tag for tag, _, ps, _ in RULES if ps}


def match(label: str, statement: str) -> tuple[str, bool] | None:
    """(tag, per_share) for a line label, or None if it isn't a tracked item."""
    norm = normalize(label)
    if not norm:
        return None
    for tag, stmt, ps, rx in _COMPILED:
        if stmt == statement and rx.search(norm):
            return tag, ps
    return None
