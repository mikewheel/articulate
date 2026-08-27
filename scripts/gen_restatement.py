#!/usr/bin/env python
"""Generate Sable Peak Beverages' RESTATED FY2025 financial statements.

Companion to gen_synthetic.py, which injected the FY2025 manipulation:
channel stuffing (the Q4 "Winter Launch" program pushed product to
distributors on 90-day terms with return rights, pulling forward revenue and
driving net receivables 111 -> 200) plus a doubtful-accounts reserve release
(allowance 5.5 -> 4.4), masked in CFO by an inventory drain (75 -> 47) and a
payables stretch (56 -> 93). This script constructs the restatement that the
L7 narrative announces via 8-K, and emits the restated FY2025 rows with basis
"as_restated" alongside the original basis "synthetic" (as-filed) rows.

RESTATEMENT MECHANICS -- the reversal chosen, and why
-----------------------------------------------------
The Winter Launch shipments carried non-standard 90-day payment terms and
return rights, and collectibility was not probable, so under ASC 606 they were
not completed sales at year end. Because NO CASH was ever collected on those
shipments, there is nothing to defer: recording deferred revenue would require
consideration received. The cleanest reversal -- and the one consistent with
how gen_synthetic.py built the injection (the entire inflated balance sits in
receivables; cash and every CFS line are genuine) -- is therefore:

  1. Derecognize the pulled-forward sale:  Dr Revenue 80.0 / Cr Receivables
     (gross) 80.0.  Revenue 1,152.0 -> 1,072.0 (FY2025 growth +28% -> +19%).
  2. Put the goods back on the books at cost (they sit unsold in the channel):
     Dr Inventory 60.8 / Cr Cost of revenue 60.8.  Inventory 47.0 -> 107.8 --
     the "full channel" becomes visible on the restated balance sheet.
  3. Restore the allowance for doubtful accounts to a defensible level:
     4.4 -> 6.4, i.e. ~5.1% of the restated gross receivables book (FY2024
     coverage was ~4.7%; slightly higher is warranted because the remaining
     book still skews to distributors on extended terms). The 2.0 rebuild runs
     through bad-debt expense in SG&A and nets down receivables.
  4. Tax effect at Sable's 25% rate: restated income tax = 25% of restated
     pretax income. The cash taxes actually paid on the as-filed numbers
     (10.8) exceed the restated liability (5.5); the 5.3 overpayment becomes
     an income-tax receivable (other_current_assets). Cash itself is
     untouched.

CASH IS UNCHANGED -- the teaching point. The cash flow statement was never
misstated: cfo / cfi / cff / net_change_cash and the balance-sheet cash are
byte-identical to the as-filed figures. Only the *labels* on accrual lines
move: restated net income falls 32.4 -> 16.5 and the working-capital change
recomputes to -2.1 so that NI + D&A + SBC + WC still equals the same CFO of
38.4. Profit was an opinion; the cash was a fact.

Run:  .venv/bin/python scripts/gen_restatement.py
Reads:  content/facts_synthetic.json  (as-filed sable_peak rows)
Writes: content/facts_synthetic_restated.json  (sable_peak FY2025 only,
        basis "as_restated"; company_id sable_peak so no new company entry)
All values USD millions; sign conventions per docs/CONTENT_FORMAT.md.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_FACTS = ROOT / "content" / "facts_synthetic.json"
OUT_FACTS = ROOT / "content" / "facts_synthetic_restated.json"

TOL = 0.1  # hard tolerance for every identity assert
FY = 2025

# --- restatement adjustments (see module docstring) ------------------------
REVENUE_REVERSED = 80.0     # Winter Launch revenue derecognized
COGS_REVERSED = 60.8        # carrying cost of those goods, back to inventory
ALLOWANCE_FILED = 4.4       # allowance after the improper release (narrative)
ALLOWANCE_RESTATED = 6.4    # restored coverage ~5.1% of restated gross AR
TAX_RATE = 0.25             # Sable's rate (as filed: 10.8 / 43.2 = 25%)


def r(x: float) -> float:
    """Round to 0.1 and normalize -0.0 to 0.0."""
    v = round(x + 0.0, 1)
    return 0.0 if v == 0.0 else v


def load_sable(fy: int) -> dict:
    rows = json.load(open(IN_FACTS))
    out = {}
    for row in rows:
        if row["company_id"] == "sable_peak" and row["fiscal_year"] == fy:
            out[row["item"]] = row["value"]
    assert out, f"no sable_peak FY{fy} rows in {IN_FACTS.name}"
    return out


def build_restated(orig: dict, prior: dict) -> dict:
    """Derive the full restated FY2025 from the as-filed year + adjustments."""
    y = {}

    # --- income statement ---
    y["revenue"] = r(orig["revenue"] - REVENUE_REVERSED)
    y["cost_of_revenue"] = r(orig["cost_of_revenue"] - COGS_REVERSED)
    y["gross_profit"] = r(y["revenue"] - y["cost_of_revenue"])
    bad_debt = r(ALLOWANCE_RESTATED - ALLOWANCE_FILED)
    y["sga"] = r(orig["sga"] + bad_debt)
    y["da"] = orig["da"]
    y["operating_income"] = r(y["gross_profit"] - y["sga"] - y["da"])
    y["interest_expense"] = orig["interest_expense"]
    y["pretax_income"] = r(y["operating_income"] - y["interest_expense"])
    y["income_tax"] = r(TAX_RATE * y["pretax_income"])
    y["net_income"] = r(y["pretax_income"] - y["income_tax"])

    # --- balance sheet ---
    # Cash was never misstated: identical to as-filed.
    y["cash"] = orig["cash"]
    # Receivables in the facts are NET of allowance. Reverse the stuffed
    # gross receivables, then net against the restored allowance.
    gross_filed = orig["receivables"] + ALLOWANCE_FILED
    y["receivables"] = r(gross_filed - REVENUE_REVERSED - ALLOWANCE_RESTATED)
    y["inventory"] = r(orig["inventory"] + COGS_REVERSED)
    # Cash taxes paid on as-filed numbers exceed the restated liability;
    # the overpayment is an income-tax receivable.
    y["other_current_assets"] = r(orig["income_tax"] - y["income_tax"])
    y["total_current_assets"] = r(y["cash"] + y["receivables"]
                                  + y["inventory"]
                                  + y["other_current_assets"])
    y["ppe_net"] = orig["ppe_net"]
    y["total_assets"] = r(y["total_current_assets"] + y["ppe_net"])
    for item in ("payables", "accrued", "debt_current",
                 "total_current_liabilities", "debt_noncurrent",
                 "total_liabilities", "common_and_apic"):
        y[item] = orig[item]
    y["retained_earnings"] = r(prior["retained_earnings"] + y["net_income"]
                               - abs(orig["dividends"]))
    y["total_equity"] = r(y["common_and_apic"] + y["retained_earnings"])

    # --- cash flow statement: cash rows UNCHANGED; only the accrual
    # decomposition of CFO (net income vs working-capital change) moves. ---
    d_ar = r(y["receivables"] - prior["receivables"])
    d_inv = r(y["inventory"] - prior["inventory"])
    d_oca = y["other_current_assets"]  # prior balance was 0
    d_ap = r(y["payables"] - prior["payables"])
    d_acc = r(y["accrued"] - prior["accrued"])
    y["working_capital_change"] = r(-(d_ar + d_inv + d_oca) + (d_ap + d_acc))
    y["da_addback"] = orig["da_addback"]
    y["sbc"] = orig["sbc"]
    for item in ("cfo", "capex", "cfi", "debt_issued", "debt_repaid",
                 "buybacks", "dividends", "cff", "fx_effect",
                 "net_change_cash"):
        y[item] = orig[item]
    return y


def assert_invariants(y: dict, orig: dict, prior: dict) -> None:
    label = f"sable_peak FY{FY} as_restated"
    # Balance sheet balances.
    assert abs(y["total_assets"]
               - (y["total_liabilities"] + y["total_equity"])) < TOL, \
        f"{label}: A != L + E"
    # Cash flow statement internally ties.
    assert abs((y["cfo"] + y["cfi"] + y["cff"] + y["fx_effect"])
               - y["net_change_cash"]) < TOL, \
        f"{label}: CFO+CFI+CFF+FX != net change in cash"
    # Income statement identities.
    assert abs(y["gross_profit"]
               - (y["revenue"] - y["cost_of_revenue"])) < TOL, \
        f"{label}: GP != revenue - COGS"
    assert abs(y["operating_income"]
               - (y["gross_profit"] - y["sga"] - y["da"])) < TOL, \
        f"{label}: operating income does not tie"
    assert abs(y["pretax_income"]
               - (y["operating_income"] - y["interest_expense"])) < TOL, \
        f"{label}: pretax does not tie"
    assert abs(y["net_income"]
               - (y["pretax_income"] - y["income_tax"])) < TOL, \
        f"{label}: NI != pretax - tax"
    # Indirect CFO composition still reaches the UNCHANGED reported CFO.
    assert abs(y["cfo"] - (y["net_income"] + y["da_addback"] + y["sbc"]
                           + y["working_capital_change"])) < TOL, \
        f"{label}: CFO != NI + D&A + SBC + WC change"
    # Subtotal sums.
    assert abs(y["total_current_assets"]
               - (y["cash"] + y["receivables"] + y["inventory"]
                  + y["other_current_assets"])) < TOL, \
        f"{label}: total current assets do not sum"
    assert abs(y["total_assets"]
               - (y["total_current_assets"] + y["ppe_net"])) < TOL, \
        f"{label}: total assets do not sum"
    assert abs(y["total_current_liabilities"]
               - (y["payables"] + y["accrued"] + y["debt_current"])) < TOL, \
        f"{label}: total current liabilities do not sum"
    assert abs(y["total_liabilities"]
               - (y["total_current_liabilities"]
                  + y["debt_noncurrent"])) < TOL, \
        f"{label}: total liabilities do not sum"
    assert abs(y["total_equity"]
               - (y["common_and_apic"] + y["retained_earnings"])) < TOL, \
        f"{label}: total equity does not sum"
    # Roll-forwards from the FY2024 as-filed (clean-year) closing balances.
    assert abs(y["cash"] - (prior["cash"] + y["net_change_cash"])) < TOL, \
        f"{label}: cash does not roll forward"
    assert abs(y["ppe_net"]
               - (prior["ppe_net"] + abs(y["capex"]) - y["da"])) < TOL, \
        f"{label}: PP&E does not roll forward"
    assert abs(y["retained_earnings"]
               - (prior["retained_earnings"] + y["net_income"]
                  - abs(y["dividends"]))) < TOL, \
        f"{label}: RE does not roll forward"
    # The cash flow statement and cash balance are IDENTICAL to as-filed:
    # cash was never misstated.
    for item in ("cash", "cfo", "capex", "cfi", "debt_issued", "debt_repaid",
                 "buybacks", "dividends", "cff", "fx_effect",
                 "net_change_cash", "da_addback", "sbc"):
        assert abs(y[item] - orig[item]) < TOL, \
            f"{label}: {item} must equal the as-filed value"
    # Restatement signature: the manipulation is gone.
    dso = y["receivables"] / y["revenue"] * 365
    assert 35.0 < dso < 45.0, f"{label}: restated DSO {dso:.1f} not normalized"
    assert y["net_income"] < orig["net_income"] - 10.0, \
        f"{label}: restated NI did not fall materially"
    rev_g = y["revenue"] / 900.0 - 1
    assert 0.15 < rev_g < 0.22, f"{label}: restated revenue growth {rev_g:.1%}"


FACT_ORDER = [
    # income statement
    "revenue", "cost_of_revenue", "gross_profit", "sga", "da",
    "operating_income", "interest_expense", "pretax_income", "income_tax",
    "net_income",
    # balance sheet
    "cash", "receivables", "inventory", "other_current_assets",
    "total_current_assets", "ppe_net", "total_assets", "payables", "accrued",
    "debt_current", "total_current_liabilities", "debt_noncurrent",
    "total_liabilities", "common_and_apic", "retained_earnings",
    "total_equity",
    # cash flow statement
    "cfo", "da_addback", "sbc", "working_capital_change", "capex", "cfi",
    "debt_issued", "debt_repaid", "buybacks", "dividends", "cff",
    "fx_effect", "net_change_cash",
]


def main():
    orig = load_sable(FY)
    prior = load_sable(FY - 1)
    y = build_restated(orig, prior)
    assert_invariants(y, orig, prior)

    rows = [{
        "company_id": "sable_peak",
        "fiscal_year": FY,
        "period_end": f"{FY}-12-31",
        "item": item,
        "value": y[item],
        "unit": "USD_millions",
        "basis": "as_restated",
        "source_tag": None,
        "source_form": None,
        "source_accession": None,
    } for item in FACT_ORDER]

    OUT_FACTS.write_text(json.dumps(rows, indent=2) + "\n")
    print(f"sable_peak FY{FY} as_restated: all invariants hold")
    print(f"  revenue   {orig['revenue']:7.1f} -> {y['revenue']:7.1f}  "
          f"(reversed {REVENUE_REVERSED})")
    print(f"  net income {orig['net_income']:6.1f} -> {y['net_income']:7.1f}")
    print(f"  receivables (net) {orig['receivables']:.1f} -> "
          f"{y['receivables']:.1f}  (allowance {ALLOWANCE_FILED} -> "
          f"{ALLOWANCE_RESTATED})")
    print(f"  inventory {orig['inventory']:.1f} -> {y['inventory']:.1f}  "
          f"(goods back at cost {COGS_REVERSED})")
    print(f"  DSO {orig['receivables'] / orig['revenue'] * 365:.1f} -> "
          f"{y['receivables'] / y['revenue'] * 365:.1f} days")
    print(f"  cash/CFO unchanged: cash {y['cash']}, cfo {y['cfo']}, "
          f"net_change_cash {y['net_change_cash']}")
    print(f"wrote {OUT_FACTS.relative_to(ROOT)} ({len(rows)} fact rows)")


if __name__ == "__main__":
    main()
