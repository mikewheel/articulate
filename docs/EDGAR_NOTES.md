# EDGAR pull notes (real-data authoring, 2026-08)

## What was pulled

Source: `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` for six filers, plus
`company_tickers.json` for ticker→CIK. All requests sent
`User-Agent: Articulate/0.1 (contact: mbw@mbw.dev)` with a 0.2s sleep between calls
(7 requests total). Raw responses cached in `/tmp/edgar_cache/` (outside the repo).

Three most recent complete fiscal years per company, annual values from 10-K filings only
(durations 330-380 days; instants at fiscal year-end). Where the same (tag, period) appears in
multiple 10-Ks (a 10-K restates the prior two years), the **earliest-filed** value was taken
(`basis: "as_filed"`), and that filing's accession number is recorded per row.

| Company | CIK | Fiscal years pulled | Period ends |
|---|---|---|---|
| KR | 0000056873 | FY2023-FY2025 | 2024-02-03, 2025-02-01, 2026-01-31 |
| MSFT | 0000789019 | FY2024-FY2026 | 2024-06-30, 2025-06-30, 2026-06-30 |
| DAL | 0000027904 | FY2023-FY2025 | 2023-12-31, 2024-12-31, 2025-12-31 |
| JPM | 0000019617 | FY2023-FY2025 | 2023-12-31, 2024-12-31, 2025-12-31 |
| CAT | 0000018230 | FY2023-FY2025 | 2023-12-31, 2024-12-31, 2025-12-31 |
| HD | 0000354950 | FY2023-FY2025 | 2024-01-28, 2025-02-02, 2026-02-01 |

MSFT's fiscal-year labels follow Microsoft's own convention (FY ends June 30 of the label year),
so its three years are labeled 2024-2026 while the calendar-year filers are 2023-2025.

## Fiscal-year quirks

- **KR** ends the Saturday nearest January 31; **HD** the Sunday nearest January 31. Both are
  52/53-week retail calendars: KR FY2023 (ended 2024-02-03) and HD FY2024 (ended 2025-02-02)
  were **53-week years**, which slightly flatters their revenue and flow-based ratios vs the
  52-week years around them. Items do not adjust for this; a production layer should flag week
  counts. `fye_month` is recorded as 1 for both even though the actual end date drifts into
  early February in some years.
- Fiscal-year labels for Jan/Feb-enders follow the filer convention (KR "fiscal 2024" ends
  February 1, 2025).

## Tag mapping choices and fallbacks

General fallback order followed spec §8.2 (e.g. revenue:
`RevenueFromContractWithCustomerExcludingAssessedTax` → `Revenues` → `SalesRevenueNet`).
Non-obvious per-company choices:

- **KR**
  - `cost_of_revenue` ← `CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization`.
    Kroger's "Merchandise costs" **exclude D&A**, so the derived `gross_profit`
    (revenue − merchandise costs) is slightly richer than a peer that buries D&A in COGS.
  - `inventory` ← derived `FIFOInventoryAmount − InventoryLIFOReserve` (7,038 = 9,442 − 2,404 for
    FY2024). Kroger tags the FIFO amount and the reserve but not the net LIFO balance-sheet line.
  - `interest_expense` ← `−InterestIncomeExpenseNonoperatingNet` (Kroger's income-statement line
    is "Net interest expense"; the standalone `InterestExpense` tag stopped after FY2023).
  - `sga` unavailable: "Operating, general and administrative" is a company extension tag, which
    the companyfacts API omits.
- **MSFT**
  - `sga` ← derived `SellingAndMarketingExpense + GeneralAndAdministrativeExpense` (Microsoft
    presents them separately and never tags combined SG&A).
  - `interest_expense` ← `InterestExpenseNonoperating` (plain `InterestExpense` stopped after FY2024).
  - `da_addback` omitted: the CFS line "Depreciation, amortization, and other" is not tagged with
    a standard total-D&A concept (only component tags: `Depreciation`,
    `AmortizationOfIntangibleAssets`, `FinanceLeaseRightOfUseAssetAmortization`, which do not sum
    exactly to the "and other" line).
  - `fx_effect` ← `EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations` (the only FX tag present).
- **DAL**
  - No COGS/gross-profit: airlines do not present a cost-of-goods line. Left absent (itself a
    teaching tell used in Lineup).
  - `total_liabilities` ← derived `Assets − StockholdersEquity`: Delta does not tag `Liabilities`
    (only "Total liabilities and stockholders' equity").
  - `interest_expense` ← `−InterestIncomeExpenseNonoperatingNet` ("Interest expense, net").
  - `deferred_revenue` (air traffic liability) is tagged with company extension tags only, so it
    is absent here despite being economically large.
  - `short_term_investments` FY2025 missing (position wound down; FY2024 value is 0).
- **JPM** (sparse by design — the canonical schema is nonfinancial-shaped)
  - `revenue` ← `Revenues` (total net revenue, i.e. net interest income + noninterest income).
  - `interest_expense` ← `InterestExpenseOperating` (a bank's interest expense is an operating
    cost, not a financing coverage item; do not use it for coverage ratios).
  - `cash` ← `CashAndDueFromBanks` (narrow vault-cash line; interest-bearing deposits with banks,
    ~$0.3-0.6T, are a separate tag not mapped).
  - `debt_noncurrent` ← `LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities`:
    JPM's balance-sheet "Long-term debt" line includes current maturities and there is no split.
    `debt_current` ← `ShortTermBorrowings`.
  - No inventory, gross profit, operating income, PP&E, or current/non-current splits — correct
    for a bank, and used as the Lineup tell.
- **CAT**
  - `net_income` ← `ProfitLoss` (consolidated incl. tiny NCI); Caterpillar stopped tagging
    `NetIncomeLoss` in 10-Ks after 2010. NCI is −$2 to −$4M, immaterial.
  - `interest_expense` omitted: "Interest expense excluding Financial Products" is an extension
    tag; consolidated interest expense inseparable from Cat Financial's operating interest.
    (`InterestPaidNet`, cash basis, exists but is not the IS line.) CAT is therefore not used for
    coverage items.
  - `total_equity` ← `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` so
    the balance-sheet identity closes exactly.
  - LIFO: `InventoryLIFOReserve` (3,423 / 3,864 / 4,305) is used as item context, not as a
    canonical fact row (no canonical item exists for it).
- **HD**
  - `ppe_net` ← `PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization`
    for all three years (plain `PropertyPlantAndEquipmentNet` disappears in FY2025; the two tags
    are equal in FY2023-24).
  - `net_change_cash` ← derived: `...PeriodIncreaseDecreaseExcludingExchangeRateEffect + fx_effect`
    (HD tags only the excluding-FX change; the derivation makes the CFS identity close exactly).
  - `interest_expense` ← `InterestExpenseNonoperating` for FY2024-25 (`InterestExpense` only in FY2023).
  - `debt_current`/`debt_noncurrent` ← `LongTermDebtAndCapitalLeaseObligations(Current)` — HD's
    debt tags include finance leases.

Derived rows carry `source_tag: "derived:..."` naming the inputs. `treasury_stock` is stored
negative; CFS outflows (capex, acquisitions, buybacks, dividends, debt_repaid) are stored
negative per the contract. EPS rows use unit `USD_per_share`; diluted shares use `shares_millions`.

## Reconciliation results

`scripts/check_facts.py` (run it: `.venv/bin/python scripts/check_facts.py`): 48 checks over 18
company-years, all green.

- Balance-sheet identity (A = L + E, ±0.5%): exact to the million for all 18 company-years
  (DAL's liabilities are derived, so its check is definitional).
- Cash-flow identity (CFO+CFI+CFF+FX = Δcash, ±1%): exact for all 18. Missing `fx_effect`
  (KR, DAL — purely/largely domestic, no FX line) treated as 0.
- Gross-profit consistency: exact where present (MSFT and HD tag `GrossProfit`; KR and CAT are
  derived, hence exact by construction).

## What a production normalize layer should handle (punted here)

- **Extension tags.** The single biggest gap: KR's SG&A and merchandise-cost detail, DAL's air
  traffic liability, CAT's machinery-vs-finance interest split all live in company extension
  tags, which companyfacts omits. Production should ingest the DERA Financial Statement Data
  Sets (which include extensions) per spec §8.1.
- **Segment/coverage splits for financials.** JPM needs its own canonical schema (deposits,
  loans, NII/NIR, provisions); forcing banks into a merchandise schema loses most of the story.
- **Average vs ending balances** for turnover/ROE ratios: items state their convention in the
  prompt instead of normalizing (opening balances for the first pulled year would need a fourth
  year of data).
- **53-week years**, changed tag usage across eras (`InterestExpense` → `InterestExpenseNonoperating`
  around FY2024 across several filers), restatement tracking (`as_restated` basis), quarterly
  data, dimension-qualified facts (companyfacts returns only undimensioned totals), and
  finance-lease vs operating-lease splits inside "debt" tags (HD includes finance leases in its
  debt tags; DAL's exclude operating leases but include finance leases).
- **KR gross margin comparability**: merchandise costs exclude D&A, so KR gross margin is not
  strictly comparable to a retailer that includes D&A in COGS. Items use it only within-company
  or with the caveat stated.
