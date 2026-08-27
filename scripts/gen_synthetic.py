#!/usr/bin/env python
"""Generate the two synthetic companies for Articulate.

Constructs three fiscal years (2023, 2024, 2025) of identity-consistent
financials for:

  * meridian_tools -- a clean mid-cap industrial tool maker.
  * sable_peak     -- a beverage distributor with an injected FY3 manipulation
                      (channel stuffing + doubtful-accounts reserve release).
                      FY1-FY2 clean. The allowance detail lives in the L5 case
                      narrative, not in the canonical facts; the *inflated net
                      receivables* sit on the balance sheet and everything ties.

Statements are built from drivers + accounting identities (cash is the plug
from the cash flow statement, RE from the roll-forward, PP&E from the
roll-forward), so the balance sheet balances by construction -- and then every
invariant is hard-asserted anyway.

Run:  .venv/bin/python scripts/gen_synthetic.py
Writes: content/companies_synthetic.json, content/facts_synthetic.json
All values are USD millions, basis "synthetic". Sign conventions per
docs/CONTENT_FORMAT.md: IS expenses positive; CFS outflows negative.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_COMPANIES = ROOT / "content" / "companies_synthetic.json"
OUT_FACTS = ROOT / "content" / "facts_synthetic.json"

TOL = 0.1  # hard tolerance for every identity assert


def r(x: float) -> float:
    """Round to 0.1 and normalize -0.0 to 0.0."""
    v = round(x + 0.0, 1)
    return 0.0 if v == 0.0 else v


# ---------------------------------------------------------------------------
# Company configurations: an opening (pre-FY1) balance-sheet state plus
# per-year drivers. Everything else is derived through identities.
# ---------------------------------------------------------------------------

MERIDIAN = {
    "id": "meridian_tools",
    "name": "Meridian Tools, Inc.",
    "industry": "industrial tools",
    "description": (
        "A mid-cap maker of professional power tools and precision fastening "
        "systems sold through industrial distributors. Steady ~6% growth, "
        "~40% gross margins, disciplined capex a bit above depreciation, "
        "modest debt paid down on schedule, and a growing dividend. The kind "
        "of company whose statements articulate cleanly -- which is exactly "
        "why it is your training ground."
    ),
    # State at the end of the year before FY2023 (not emitted).
    "opening": {
        "cash": 95.0, "receivables": 148.0, "inventory": 155.0,
        "ppe_net": 520.0, "payables": 72.0, "accrued": 58.0,
        "debt_current": 15.0, "debt_noncurrent": 260.0,
        "common_and_apic": 133.0, "retained_earnings": 380.0,
    },
    "drivers": {
        2023: {"revenue": 1000.0, "cogs": 600.0, "sga": 210.0, "rnd": 30.0,
               "da": 60.0, "interest": 12.0, "tax": 22.0, "sbc": 12.0,
               "capex": 72.0, "receivables": 152.0, "inventory": 160.0,
               "payables": 75.0, "accrued": 60.0,
               "debt_current": 15.0, "debt_noncurrent": 245.0,
               "debt_issued": 0.0, "debt_repaid": 15.0,
               "dividends": 30.0, "buybacks": 0.0},
        2024: {"revenue": 1060.0, "cogs": 634.0, "sga": 220.0, "rnd": 32.0,
               "da": 63.0, "interest": 11.0, "tax": 25.0, "sbc": 12.0,
               "capex": 75.6, "receivables": 160.0, "inventory": 168.0,
               "payables": 79.0, "accrued": 63.0,
               "debt_current": 15.0, "debt_noncurrent": 230.0,
               "debt_issued": 0.0, "debt_repaid": 15.0,
               "dividends": 33.0, "buybacks": 0.0},
        2025: {"revenue": 1123.0, "cogs": 672.0, "sga": 230.0, "rnd": 34.0,
               "da": 65.0, "interest": 10.0, "tax": 28.0, "sbc": 12.0,
               "capex": 78.0, "receivables": 170.0, "inventory": 176.0,
               "payables": 83.0, "accrued": 66.0,
               "debt_current": 15.0, "debt_noncurrent": 215.0,
               "debt_issued": 0.0, "debt_repaid": 15.0,
               "dividends": 36.0, "buybacks": 0.0},
    },
}

# Sable Peak FY3 injection: channel stuffing (Q4 push with extended payment
# terms -> receivables +80% on revenue +28%, DSO 45.0 -> 63.4) plus a
# doubtful-accounts reserve release (allowance 5.5 -> 4.4, -20%; narrative
# only -- receivables here are net). CFO is held roughly flat vs FY2 (39.0 ->
# 38.4 while net income jumps +35%) because the quarter's cash strain was
# masked by draining inventory into the channel (75 -> 47) and stretching
# payables (56 -> 93). Every inflated balance sits on the balance sheet and
# the statements still tie exactly.
SABLE = {
    "id": "sable_peak",
    "name": "Sable Peak Beverages, Inc.",
    "industry": "beverage distribution",
    "description": (
        "A regional distributor of craft sodas, teas, and sparkling waters, "
        "selling through a network of independent beverage distributors. "
        "Thin gross margins, fast inventory turns, and a working-capital-"
        "heavy model where the gap between shipping product and collecting "
        "cash is the whole game. FY2025 was, management says, a breakout "
        "year. Read it carefully."
    ),
    "opening": {
        "cash": 40.0, "receivables": 97.0, "inventory": 68.0,
        "ppe_net": 150.0, "payables": 52.0, "accrued": 30.0,
        "debt_current": 10.0, "debt_noncurrent": 190.0,
        "common_and_apic": 33.0, "retained_earnings": 40.0,
    },
    "drivers": {
        2023: {"revenue": 850.0, "cogs": 646.0, "sga": 150.0,
               "da": 18.0, "interest": 8.0, "tax": 7.0, "sbc": 4.0,
               "capex": 22.0, "receivables": 102.0, "inventory": 71.0,
               "payables": 53.0, "accrued": 31.0,
               "debt_current": 10.0, "debt_noncurrent": 180.0,
               "debt_issued": 0.0, "debt_repaid": 10.0,
               "dividends": 8.0, "buybacks": 0.0},
        2024: {"revenue": 900.0, "cogs": 684.0, "sga": 157.0,
               "da": 19.0, "interest": 8.0, "tax": 8.0, "sbc": 4.0,
               "capex": 23.0, "receivables": 111.0, "inventory": 75.0,
               "payables": 56.0, "accrued": 33.0,
               "debt_current": 10.0, "debt_noncurrent": 170.0,
               "debt_issued": 0.0, "debt_repaid": 10.0,
               "dividends": 9.0, "buybacks": 0.0},
        # FY3: the injected year.
        2025: {"revenue": 1152.0, "cogs": 875.0, "sga": 205.8,
               "da": 20.0, "interest": 8.0, "tax": 10.8, "sbc": 4.0,
               "capex": 24.0, "receivables": 200.0, "inventory": 47.0,
               "payables": 93.0, "accrued": 39.0,
               "debt_current": 30.0, "debt_noncurrent": 160.0,  # +20 revolver
               "debt_issued": 20.0, "debt_repaid": 10.0,
               "dividends": 10.0, "buybacks": 0.0},
    },
}


def build_years(cfg):
    """Derive full statements per fiscal year from opening state + drivers."""
    prev = dict(cfg["opening"])
    prev["total_debt"] = prev["debt_current"] + prev["debt_noncurrent"]
    years = {}
    for fy in sorted(cfg["drivers"]):
        d = cfg["drivers"][fy]
        y = {}
        # --- income statement (expenses positive) ---
        y["revenue"] = d["revenue"]
        y["cost_of_revenue"] = d["cogs"]
        y["gross_profit"] = r(d["revenue"] - d["cogs"])
        y["sga"] = d["sga"]
        if "rnd" in d:
            y["rnd"] = d["rnd"]
        y["da"] = d["da"]
        y["operating_income"] = r(
            y["gross_profit"] - d["sga"] - d.get("rnd", 0.0) - d["da"])
        y["interest_expense"] = d["interest"]
        y["pretax_income"] = r(y["operating_income"] - d["interest"])
        y["income_tax"] = d["tax"]
        y["net_income"] = r(y["pretax_income"] - d["tax"])

        # --- cash flow statement (outflows negative) ---
        d_ar = r(d["receivables"] - prev["receivables"])
        d_inv = r(d["inventory"] - prev["inventory"])
        d_ap = r(d["payables"] - prev["payables"])
        d_acc = r(d["accrued"] - prev["accrued"])
        y["working_capital_change"] = r(-(d_ar + d_inv) + (d_ap + d_acc))
        y["da_addback"] = d["da"]
        y["sbc"] = d["sbc"]
        y["cfo"] = r(y["net_income"] + d["da"] + d["sbc"]
                     + y["working_capital_change"])
        y["capex"] = r(-d["capex"])
        y["cfi"] = y["capex"]
        y["debt_issued"] = d["debt_issued"]
        y["debt_repaid"] = r(-d["debt_repaid"])
        y["buybacks"] = r(-d["buybacks"])
        y["dividends"] = r(-d["dividends"])
        y["cff"] = r(y["debt_issued"] + y["debt_repaid"] + y["buybacks"]
                     + y["dividends"])
        y["fx_effect"] = 0.0
        y["net_change_cash"] = r(y["cfo"] + y["cfi"] + y["cff"]
                                 + y["fx_effect"])

        # --- balance sheet (cash, PP&E, RE, APIC derived by roll-forward) ---
        y["cash"] = r(prev["cash"] + y["net_change_cash"])
        y["receivables"] = d["receivables"]
        y["inventory"] = d["inventory"]
        y["total_current_assets"] = r(y["cash"] + d["receivables"]
                                      + d["inventory"])
        y["ppe_net"] = r(prev["ppe_net"] + d["capex"] - d["da"])
        y["total_assets"] = r(y["total_current_assets"] + y["ppe_net"])
        y["payables"] = d["payables"]
        y["accrued"] = d["accrued"]
        y["debt_current"] = d["debt_current"]
        y["total_current_liabilities"] = r(d["payables"] + d["accrued"]
                                           + d["debt_current"])
        y["debt_noncurrent"] = d["debt_noncurrent"]
        y["total_liabilities"] = r(y["total_current_liabilities"]
                                   + d["debt_noncurrent"])
        y["common_and_apic"] = r(prev["common_and_apic"] + d["sbc"])
        y["retained_earnings"] = r(prev["retained_earnings"] + y["net_income"]
                                   - d["dividends"])
        y["total_equity"] = r(y["common_and_apic"] + y["retained_earnings"])

        # Debt schedule must reconcile with financing flows.
        new_debt = d["debt_current"] + d["debt_noncurrent"]
        assert abs(new_debt - (prev["total_debt"] + d["debt_issued"]
                               - d["debt_repaid"])) < TOL, \
            f"{cfg['id']} FY{fy}: debt schedule does not tie to financing"

        years[fy] = y
        prev = {"cash": y["cash"], "receivables": y["receivables"],
                "inventory": y["inventory"], "ppe_net": y["ppe_net"],
                "payables": y["payables"], "accrued": y["accrued"],
                "debt_current": y["debt_current"],
                "debt_noncurrent": y["debt_noncurrent"],
                "common_and_apic": y["common_and_apic"],
                "retained_earnings": y["retained_earnings"],
                "total_debt": new_debt}
    return years


def assert_invariants(cfg, years):
    cid = cfg["id"]
    fys = sorted(years)
    for fy in fys:
        y = years[fy]
        # Balance sheet balances.
        assert abs(y["total_assets"]
                   - (y["total_liabilities"] + y["total_equity"])) < TOL, \
            f"{cid} FY{fy}: A != L + E"
        # Cash flow statement internally ties.
        assert abs((y["cfo"] + y["cfi"] + y["cff"] + y["fx_effect"])
                   - y["net_change_cash"]) < TOL, \
            f"{cid} FY{fy}: CFO+CFI+CFF+FX != net change in cash"
        # Gross profit identity.
        assert abs(y["gross_profit"]
                   - (y["revenue"] - y["cost_of_revenue"])) < TOL, \
            f"{cid} FY{fy}: GP != revenue - COGS"
        # Net income ties from pretax and tax.
        assert abs(y["net_income"]
                   - (y["pretax_income"] - y["income_tax"])) < TOL, \
            f"{cid} FY{fy}: NI != pretax - tax"
        # Indirect CFO composition.
        assert abs(y["cfo"] - (y["net_income"] + y["da_addback"] + y["sbc"]
                               + y["working_capital_change"])) < TOL, \
            f"{cid} FY{fy}: CFO != NI + D&A + SBC + WC change"
        # Subtotal sums.
        assert abs(y["total_current_assets"]
                   - (y["cash"] + y["receivables"] + y["inventory"])) < TOL
        assert abs(y["total_assets"]
                   - (y["total_current_assets"] + y["ppe_net"])) < TOL
        assert abs(y["total_equity"]
                   - (y["common_and_apic"] + y["retained_earnings"])) < TOL

    # Roll-forwards from opening state into FY1, then year over year.
    prev_cash = cfg["opening"]["cash"]
    prev_ppe = cfg["opening"]["ppe_net"]
    prev_re = cfg["opening"]["retained_earnings"]
    for fy in fys:
        y = years[fy]
        # Cash on the BS ties to prior cash + net change in cash.
        assert abs(y["cash"] - (prev_cash + y["net_change_cash"])) < TOL, \
            f"{cid} FY{fy}: cash does not roll forward"
        # PP&E roll-forward (capex is negative on the CFS; use |capex|).
        assert abs(y["ppe_net"]
                   - (prev_ppe + abs(y["capex"]) - y["da"])) < TOL, \
            f"{cid} FY{fy}: PP&E does not roll forward"
        # Retained earnings roll-forward (dividends negative on the CFS).
        assert abs(y["retained_earnings"]
                   - (prev_re + y["net_income"] - abs(y["dividends"]))) < TOL, \
            f"{cid} FY{fy}: RE does not roll forward"
        prev_cash, prev_ppe, prev_re = (y["cash"], y["ppe_net"],
                                        y["retained_earnings"])


FACT_ORDER = [
    # income statement
    "revenue", "cost_of_revenue", "gross_profit", "sga", "rnd", "da",
    "operating_income", "interest_expense", "pretax_income", "income_tax",
    "net_income",
    # balance sheet
    "cash", "receivables", "inventory", "total_current_assets", "ppe_net",
    "total_assets", "payables", "accrued", "debt_current",
    "total_current_liabilities", "debt_noncurrent", "total_liabilities",
    "common_and_apic", "retained_earnings", "total_equity",
    # cash flow statement
    "cfo", "da_addback", "sbc", "working_capital_change", "capex", "cfi",
    "debt_issued", "debt_repaid", "buybacks", "dividends", "cff",
    "fx_effect", "net_change_cash",
]


def emit_facts(cfg, years):
    rows = []
    for fy in sorted(years):
        y = years[fy]
        for item in FACT_ORDER:
            if item not in y:
                continue  # e.g. sable_peak has no rnd line
            rows.append({
                "company_id": cfg["id"],
                "fiscal_year": fy,
                "period_end": f"{fy}-12-31",
                "item": item,
                "value": y[item],
                "unit": "USD_millions",
                "basis": "synthetic",
                "source_tag": None,
                "source_form": None,
                "source_accession": None,
            })
    return rows


def emit_company(cfg):
    return {
        "id": cfg["id"],
        "name": cfg["name"],
        "ticker": None,
        "cik": None,
        "kind": "synthetic",
        "industry": cfg["industry"],
        "sic": None,
        "fye_month": 12,
        "description": cfg["description"],
    }


def main():
    companies, facts = [], []
    for cfg in (MERIDIAN, SABLE):
        years = build_years(cfg)
        assert_invariants(cfg, years)
        companies.append(emit_company(cfg))
        facts.extend(emit_facts(cfg, years))
        print(f"{cfg['id']}: all invariants hold for FY"
              f"{', FY'.join(str(f) for f in sorted(years))}")

    # Red-flag signature checks for the injected Sable Peak FY3 (the injector
    # must move its signature metrics in the documented direction).
    sy = build_years(SABLE)
    rev_g = sy[2025]["revenue"] / sy[2024]["revenue"] - 1
    ar_g = sy[2025]["receivables"] / sy[2024]["receivables"] - 1
    dso2 = sy[2024]["receivables"] / sy[2024]["revenue"] * 365
    dso3 = sy[2025]["receivables"] / sy[2025]["revenue"] * 365
    ni_g = sy[2025]["net_income"] / sy[2024]["net_income"] - 1
    assert abs(rev_g - 0.28) < 0.005, "sable FY3 revenue growth != ~28%"
    assert abs(ar_g - 0.80) < 0.01, "sable FY3 receivables growth != ~80%"
    assert abs(dso2 - 45.0) < 0.5 and dso3 > 60.0, "sable DSO jump missing"
    assert abs(ni_g - 0.35) < 0.005, "sable FY3 NI growth != ~35%"
    assert abs(sy[2025]["cfo"] - sy[2024]["cfo"]) < 1.0, "sable CFO not flat"
    print(f"sable_peak FY3 signature: revenue {rev_g:+.1%}, receivables "
          f"{ar_g:+.1%}, DSO {dso2:.1f} -> {dso3:.1f} days, NI {ni_g:+.1%}, "
          f"CFO {sy[2024]['cfo']:.1f} -> {sy[2025]['cfo']:.1f}")

    OUT_COMPANIES.write_text(json.dumps(companies, indent=2) + "\n")
    OUT_FACTS.write_text(json.dumps(facts, indent=2) + "\n")
    print(f"wrote {OUT_COMPANIES.relative_to(ROOT)} "
          f"({len(companies)} companies)")
    print(f"wrote {OUT_FACTS.relative_to(ROOT)} ({len(facts)} fact rows)")


if __name__ == "__main__":
    main()
