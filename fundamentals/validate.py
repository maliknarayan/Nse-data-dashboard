"""Cross-foot every statement.

OCR corrupts figures silently — `1,1 10.45` for 1,110.45, dropped subtotals,
thousands separators read as decimal points. Additive identities are the only
cheap way to catch it, so each is checked and any break is reported against the
period it occurred in. Facts are kept either way; the caller decides.
"""

from __future__ import annotations

# additive identities: (result tag, [component tags], sign per component)
_SUMS: list[tuple[str, list[str], list[int]]] = [
    ("total_income", ["revenue_from_operations", "other_income"], [1, 1]),
    ("total_expenses", ["direct_cost", "change_in_inventory",
                        "employee_benefits_expense", "finance_costs",
                        "depreciation_amortization", "other_expenses"],
     [1, 1, 1, 1, 1, 1]),
    ("profit_before_tax", ["total_income", "total_expenses"], [1, -1]),
    ("total_tax_expense", ["current_tax", "deferred_tax", "prior_year_tax"],
     [1, 1, 1]),
    ("profit_for_period", ["profit_before_tax", "total_tax_expense"], [1, -1]),
    ("total_comprehensive_income",
     ["profit_for_period", "other_comprehensive_income"], [1, 1]),
    ("total_equity", ["equity_share_capital", "other_equity"], [1, 1]),
    ("total_assets", ["total_non_current_assets", "total_current_assets"], [1, 1]),
    ("total_equity_and_liabilities", ["total_equity", "total_liabilities"], [1, 1]),
]

# absolute slack in rupees — filings round to 2 decimals in their own unit
ABS_TOL = 20_000.0
REL_TOL = 0.005


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= max(ABS_TOL, REL_TOL * max(abs(a), abs(b)))


def check(facts: list[dict]) -> list[dict]:
    """Report identity breaks and impossible values. Empty list means clean."""
    issues: list[dict] = []
    keyed: dict[tuple, dict[str, float]] = {}
    for f in facts:
        if f["value"] is None:
            continue
        k = (f["basis"], f["statement"], f["period_end"], f["period_type"])
        keyed.setdefault(k, {})[f["tag"]] = f["value"]

    for k, vals in sorted(keyed.items()):
        basis, stmt, pend, ptype = k
        for result, parts, signs in _SUMS:
            if result not in vals:
                continue
            # every component must be present — summing a subset produces a
            # false mismatch whenever the filing simply didn't report a line
            if not all(p in vals for p in parts):
                continue
            present = list(zip(parts, signs))
            total = sum(s * vals[p] for p, s in present)
            if not _close(total, vals[result]):
                issues.append({
                    "kind": "sum_mismatch", "basis": basis, "statement": stmt,
                    "period_end": pend, "period_type": ptype, "tag": result,
                    "reported": vals[result], "computed": total,
                    "components": [p for p, _ in present],
                })
        # diluted EPS can never exceed basic
        b, d = vals.get("eps_basic"), vals.get("eps_diluted")
        if b is not None and d is not None and d > b + 1e-9:
            issues.append({
                "kind": "diluted_gt_basic", "basis": basis, "statement": stmt,
                "period_end": pend, "period_type": ptype, "tag": "eps_diluted",
                "reported": d, "computed": b, "components": ["eps_basic"],
            })
    return issues


def derive_missing(facts: list[dict]) -> list[dict]:
    """Fill subtotals OCR dropped, from components already parsed.

    Only additive identities, only when every component is present and the
    subtotal is absent — never overwrites a printed figure.
    """
    keyed: dict[tuple, dict[str, dict]] = {}
    for f in facts:
        k = (f["basis"], f["statement"], f["period_end"], f["period_type"])
        keyed.setdefault(k, {})[f["tag"]] = f

    added: list[dict] = []
    for k, byTag in keyed.items():
        for result, parts, signs in _SUMS:
            if result in byTag:
                continue
            if not all(p in byTag and byTag[p]["value"] is not None for p in parts):
                continue
            total = sum(s * byTag[p]["value"] for p, s in zip(parts, signs))
            src = byTag[parts[0]]
            added.append({**src, "tag": result, "value": total,
                          "derived_from": parts})
    return added
