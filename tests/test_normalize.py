import json
import zipfile
from pathlib import Path

import pytest

from articulate import PROJECT_ROOT
from articulate.normalize import _annual_values, normalize_company

BULK_ZIP = PROJECT_ROOT / "data" / "companyfacts.zip"


def entry(end, val, form="10-K", fp="FY", start=None, filed="2024-03-01"):
    e = {"end": end, "val": val, "form": form, "fp": fp, "filed": filed}
    if start:
        e["start"] = start
    return e


class TestAnnualValues:
    def test_picks_earliest_filed_as_filed(self):
        entries = [entry("2023-12-31", 100, filed="2024-02-20"),
                   entry("2023-12-31", 90, filed="2025-02-20")]  # restated later
        assert _annual_values(entries, instant=True) == {"2023-12-31": 100}

    def test_duration_must_be_annual(self):
        entries = [entry("2023-12-31", 25, start="2023-10-01"),   # quarterly
                   entry("2023-12-31", 100, start="2023-01-01")]  # annual
        assert _annual_values(entries, instant=False) == {"2023-12-31": 100}

    def test_ignores_non_10k(self):
        entries = [entry("2023-12-31", 100, form="10-Q", fp="Q3")]
        assert _annual_values(entries, instant=True) == {}


class TestNormalizeCompany:
    def make(self, tag_values):
        gaap = {}
        for tag, val in tag_values.items():
            gaap[tag] = {"units": {"USD": [entry("2024-06-30", val,
                                                 start="2023-07-01")]}}
        # instants need no start; overwrite for BS tags
        for tag in ("Assets", "Liabilities", "StockholdersEquity"):
            if tag in gaap:
                gaap[tag] = {"units": {"USD": [entry("2024-06-30", tag_values[tag])]}}
        return {"cik": 1, "entityName": "Test Co", "facts": {"us-gaap": gaap}}

    def test_normalizes_and_admits_clean_company(self):
        data = self.make({
            "Revenues": 1000e6, "NetIncomeLoss": 100e6,
            "Assets": 2000e6, "Liabilities": 1200e6, "StockholdersEquity": 800e6,
            "NetCashProvidedByUsedInOperatingActivities": 150e6,
            "NetCashProvidedByUsedInInvestingActivities": -60e6,
            "NetCashProvidedByUsedInFinancingActivities": -70e6,
            "CashAndCashEquivalentsPeriodIncreaseDecrease": 20e6,
        })
        out = normalize_company(data)
        year = out["years"]["2024-06-30"]
        assert year["fiscal_year"] == 2023  # June year-end -> prior-year label
        assert year["facts"]["revenue"] == 1000.0
        assert year["quality"]["bs_ok"] and year["quality"]["cf_ok"]
        assert year["quality"]["admitted"]

    def test_quarantines_untied_balance_sheet(self):
        data = self.make({
            "Revenues": 1000e6, "Assets": 2000e6,
            "Liabilities": 900e6, "StockholdersEquity": 800e6,  # off by 300
            "NetCashProvidedByUsedInOperatingActivities": 150e6,
            "NetCashProvidedByUsedInInvestingActivities": -60e6,
            "NetCashProvidedByUsedInFinancingActivities": -70e6,
            "CashAndCashEquivalentsPeriodIncreaseDecrease": 20e6,
        })
        out = normalize_company(data)
        assert not out["years"]["2024-06-30"]["quality"]["admitted"]

    def test_derives_liabilities_and_flips_capex(self):
        data = self.make({
            "Revenues": 1000e6, "Assets": 2000e6, "StockholdersEquity": 800e6,
            "PaymentsToAcquirePropertyPlantAndEquipment": 50e6,
        })
        facts = next(iter(normalize_company(data)["years"].values()))["facts"]
        assert facts["total_liabilities"] == 1200.0
        assert facts["capex"] == -50.0


@pytest.mark.skipif(not BULK_ZIP.exists(), reason="bulk zip not downloaded")
def test_bulk_matches_hand_pulled_golden():
    """Golden cross-check (spec §8.2): bulk normalization must agree with the
    hand-curated pulls for straightforward filers, joined on period_end."""
    hand = {}
    for path in (PROJECT_ROOT / "content").glob("facts_real*.json"):
        for row in json.loads(path.read_text()):
            hand[(row["company_id"], row["period_end"], row["item"])] = row["value"]
    companies = {}
    for path in (PROJECT_ROOT / "content").glob("companies_real*.json"):
        for co in json.loads(path.read_text()):
            companies[co["id"]] = int(co["cik"])

    z = zipfile.ZipFile(BULK_ZIP)
    for company_id in ("msft", "cat", "nvda", "unp"):
        cik = companies[company_id]
        bulk = normalize_company(json.loads(z.read(f"CIK{cik:010d}.json")))
        matched = total = 0
        for end, year in bulk["years"].items():
            for item, value in year["facts"].items():
                key = (company_id, end, item)
                if key not in hand:
                    continue
                total += 1
                if abs(value - hand[key]) <= max(0.01 * abs(hand[key]), 1.0):
                    matched += 1
        assert total >= 15, f"{company_id}: too little overlap ({total})"
        assert matched / total >= 0.8, f"{company_id}: only {matched}/{total} agree"
