"""XBRL → canonical normalization for the SEC companyfacts bulk data (spec §8.2).

The candidate-tag table codifies the playbook developed during the two manual
pulls (docs/EDGAR_NOTES.md): an ordered list of us-gaap tags per canonical
item, derivation rules when no tag matches, sign conventions, and per-year
quality scoring with a quarantine flag. Values in USD millions.

Period selection: for each tag we keep 10-K "FY" values, group by period end,
and take the EARLIEST-filed value (as-filed; restatement history is content,
spec §8.2). Fiscal years are labeled calendar-anchored: a year ending in
Jan-Jun belongs to the prior calendar year (so Kroger's year ending 2025-02-01
is FY2024). Filers' own labels can differ (NVIDIA calls that FY2026-style);
joins against hand-pulled data should use period_end, not the label.
"""

from datetime import date, timedelta

# ordered candidates per canonical item; "+" prefix = instant (balance sheet)
CANDIDATE_TAGS = {
    # income statement (durations)
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
                "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax",
                "SalesRevenueGoodsNet"],
    "cost_of_revenue": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold",
                        "CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization"],
    "gross_profit": ["GrossProfit"],
    "sga": ["SellingGeneralAndAdministrativeExpense"],
    "rnd": ["ResearchAndDevelopmentExpense"],
    "operating_income": ["OperatingIncomeLoss"],
    "interest_expense": ["InterestExpense", "InterestExpenseNonoperating",
                         "InterestExpenseDebt"],
    "pretax_income": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"],
    "income_tax": ["IncomeTaxExpenseBenefit"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "da": ["DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet"],
    # balance sheet (instants)
    "cash": ["+CashAndCashEquivalentsAtCarryingValue",
             "+CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "short_term_investments": ["+ShortTermInvestments", "+MarketableSecuritiesCurrent"],
    "receivables": ["+AccountsReceivableNetCurrent", "+ReceivablesNetCurrent",
                    "+AccountsNotesAndLoansReceivableNetCurrent"],
    "inventory": ["+InventoryNet"],
    "total_current_assets": ["+AssetsCurrent"],
    "ppe_net": ["+PropertyPlantAndEquipmentNet",
                "+PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization"],
    "operating_lease_rou": ["+OperatingLeaseRightOfUseAsset"],
    "goodwill": ["+Goodwill"],
    "intangibles": ["+FiniteLivedIntangibleAssetsNet", "+IntangibleAssetsNetExcludingGoodwill"],
    "total_assets": ["+Assets"],
    "payables": ["+AccountsPayableCurrent", "+AccountsPayableAndAccruedLiabilitiesCurrent"],
    "deferred_revenue": ["+ContractWithCustomerLiabilityCurrent", "+DeferredRevenueCurrent"],
    "debt_current": ["+LongTermDebtCurrent", "+DebtCurrent",
                     "+LongTermDebtAndCapitalLeaseObligationsCurrent"],
    "total_current_liabilities": ["+LiabilitiesCurrent"],
    "debt_noncurrent": ["+LongTermDebtNoncurrent", "+LongTermDebt",
                        "+LongTermDebtAndCapitalLeaseObligations"],
    "total_liabilities": ["+Liabilities"],
    "retained_earnings": ["+RetainedEarningsAccumulatedDeficit"],
    "nci": ["+MinorityInterest"],
    "total_equity": ["+StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
                     "+StockholdersEquity"],
    # cash flow (durations); flip = stored negative (outflow convention)
    "cfo": ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "cfi": ["NetCashProvidedByUsedInInvestingActivities",
            "NetCashProvidedByUsedInInvestingActivitiesContinuingOperations"],
    "cff": ["NetCashProvidedByUsedInFinancingActivities",
            "NetCashProvidedByUsedInFinancingActivitiesContinuingOperations"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "buybacks": ["PaymentsForRepurchaseOfCommonStock"],
    "dividends": ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"],
    "sbc": ["ShareBasedCompensation"],
    "da_addback": ["DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet"],
    "fx_effect": ["EffectOfExchangeRateOnCashAndCashEquivalents",
                  "EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
                  "EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations"],
    "net_change_cash": [
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect",
        "CashAndCashEquivalentsPeriodIncreaseDecrease"],
    "_net_change_cash_ex_fx": [
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseExcludingExchangeRateEffect"],
}

FLIP_SIGN = {"capex", "buybacks", "dividends"}
ANNUAL_DAYS = (330, 400)


def _fiscal_year(end: date) -> int:
    return end.year - 1 if end.month <= 6 else end.year


def _annual_values(entries, instant: bool) -> dict:
    """period_end -> earliest-filed FY value from 10-K filings."""
    by_end = {}
    for e in entries:
        if e.get("form") not in ("10-K", "10-K/A") or e.get("fp") != "FY":
            continue
        if e.get("val") is None or not e.get("end"):
            continue
        if not instant:
            start = e.get("start")
            if not start:
                continue
            days = (date.fromisoformat(e["end"]) - date.fromisoformat(start)).days
            if not ANNUAL_DAYS[0] <= days <= ANNUAL_DAYS[1]:
                continue
        end = e["end"]
        filed = e.get("filed", "9999-99-99")
        if end not in by_end or filed < by_end[end][0]:
            by_end[end] = (filed, e["val"])
    return {end: val for end, (filed, val) in by_end.items()}


def normalize_company(facts_json: dict) -> dict:
    """companyfacts JSON -> {period_end: {item: value_in_millions}} + quality.

    Returns {"cik", "name", "years": {end_iso: {"fiscal_year", "facts", "quality"}}}
    """
    gaap = facts_json.get("facts", {}).get("us-gaap", {})
    per_item = {}
    for item, candidates in CANDIDATE_TAGS.items():
        for tag in candidates:
            instant = tag.startswith("+")
            concept = gaap.get(tag.lstrip("+"))
            if not concept:
                continue
            usd = concept.get("units", {}).get("USD")
            if not usd:
                continue
            values = _annual_values(usd, instant)
            if values:
                per_item[item] = values
                break

    # collect the fiscal-year ends where a balance sheet exists
    ends = sorted(per_item.get("total_assets", {}))
    years = {}
    for end in ends:
        facts = {}
        for item, values in per_item.items():
            if end in values:
                value = values[end] / 1e6
                if item in FLIP_SIGN:
                    value = -value
                facts[item] = round(value, 3)
        _derive(facts)
        quality = _quality(facts)
        years[end] = {"fiscal_year": _fiscal_year(date.fromisoformat(end)),
                      "facts": facts, "quality": quality}
    return {"cik": facts_json.get("cik"), "name": facts_json.get("entityName"),
            "years": years}


def _derive(f: dict) -> None:
    if "gross_profit" not in f and "revenue" in f and "cost_of_revenue" in f:
        f["gross_profit"] = round(f["revenue"] - f["cost_of_revenue"], 3)
    if "total_liabilities" not in f and "total_assets" in f and "total_equity" in f:
        f["total_liabilities"] = round(f["total_assets"] - f["total_equity"], 3)
    if "net_change_cash" not in f and "_net_change_cash_ex_fx" in f:
        f["net_change_cash"] = round(f["_net_change_cash_ex_fx"] + f.get("fx_effect", 0.0), 3)
    f.pop("_net_change_cash_ex_fx", None)


def _quality(f: dict) -> dict:
    q = {"bs_ok": False, "cf_ok": False, "admitted": False}
    a, l, e = f.get("total_assets"), f.get("total_liabilities"), f.get("total_equity")
    if a and l is not None and e is not None:
        q["bs_ok"] = abs(a - (l + e)) <= max(0.005 * abs(a), 0.5)
    parts = [f.get(k) for k in ("cfo", "cfi", "cff")]
    delta = f.get("net_change_cash")
    if all(p is not None for p in parts) and delta is not None:
        total = sum(parts) + f.get("fx_effect", 0.0)
        q["cf_ok"] = abs(total - delta) <= max(0.01 * abs(delta), 1.0)
    q["admitted"] = (q["bs_ok"] and q["cf_ok"]
                     and f.get("revenue", 0) > 0 and f.get("total_assets", 0) > 0)
    return q
