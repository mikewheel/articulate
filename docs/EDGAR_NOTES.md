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

## Expansion pull — 2026-08-27

Ten more filers pulled with the same conventions (companyfacts API, User-Agent
`Articulate/0.1 (contact: mbw@mbw.dev)`, 0.2s sleep, raw JSON cached in `/tmp/edgar_cache/`;
12 API requests: 10 companyfacts + 1 extra for the legacy XOM CIK + submissions metadata for
SIC codes). Three most recent complete fiscal years each, 10-K annual values only (durations
330-380 days, instants at fiscal year-end), **earliest-filed** value per (tag, period),
`basis: "as_filed"`. Output: `content/companies_real_expanded.json`,
`content/facts_real_expanded.json` (1,275 rows, 30 company-years).

| Company | CIK | Fiscal years pulled | Period ends |
|---|---|---|---|
| XOM | 0000034088 | FY2023-FY2025 | 2023-12-31, 2024-12-31, 2025-12-31 |
| PFE | 0000078003 | FY2023-FY2025 | 2023-12-31, 2024-12-31, 2025-12-31 |
| COST | 0000909832 | FY2023-FY2025 | 2023-09-03, 2024-09-01, 2025-08-31 |
| NFLX | 0001065280 | FY2023-FY2025 | 2023-12-31, 2024-12-31, 2025-12-31 |
| NVDA | 0001045810 | FY2024-FY2026 | 2024-01-28, 2025-01-26, 2026-01-25 |
| BA | 0000012927 | FY2023-FY2025 | 2023-12-31, 2024-12-31, 2025-12-31 |
| UNP | 0000100885 | FY2023-FY2025 | 2023-12-31, 2024-12-31, 2025-12-31 |
| SBUX | 0000829224 | FY2023-FY2025 | 2023-10-01, 2024-09-29, 2025-09-28 |
| NEE | 0000753308 | FY2023-FY2025 | 2023-12-31, 2024-12-31, 2025-12-31 |
| DE | 0000315189 | FY2023-FY2025 | 2023-10-29, 2024-10-27, 2025-11-02 |

No company-years were excluded: all 30 pass the balance-sheet, cash-flow, and gross-profit
identity checks (`scripts/check_facts.py`: 141 checks over 54 company-years across all files,
all green).

### CIK and fiscal-calendar quirks

- **XOM's ticker now maps to a successor entity.** `company_tickers.json` resolves XOM to
  "ExxonMobil Holdings Corp", CIK 0002115436, which has filed only 10-Qs (a 2025-26
  holding-company reorganization). All 10-K history lives under the legacy Exxon Mobil
  Corporation CIK **0000034088**, which is what was pulled and recorded. A production ticker→CIK
  layer must handle successor-entity remapping.
- **NVDA labels fiscal years by end-date year** (fiscal 2026 ended 2026-01-25), unlike KR/HD
  where the label year precedes the Jan/Feb end. Filer convention followed, as with MSFT.
  `fye_month` = 1.
- 52/53-week years: **COST** FY2023 (ended 2023-09-03) and **DE** FY2025 (ended 2025-11-02)
  were 53-week years. COST ends the Sunday nearest August 31 (`fye_month` 8), SBUX the Sunday
  nearest September 30 (`fye_month` 9), DE the last Sunday of October (`fye_month` 10, drifting
  into November in 53-week years).
- **Stock splits break as-filed per-share continuity.** NVDA split 10-for-1 during fiscal 2025
  and NFLX 10-for-1 during fiscal 2025; because rows keep the earliest-filed value, pre-split
  years carry pre-split EPS and diluted shares (NVDA FY2024: $11.93 / 2,494M shares vs FY2025:
  $2.94 / 24,804M; NFLX FY2023-24: $12.03/$19.83 / ~440-450M vs FY2025: $2.53 / 4,344M).
  **Items must not compare per-share figures across the split years for these two filers.**
  A production layer would restate (`as_restated`) from the later filings.

### Tag mapping choices and fallbacks

- **XOM**: no `cost_of_revenue`, `gross_profit`, or `operating_income` — Exxon presents revenue
  against a single "total costs and other deductions" block (a teaching tell, like DAL).
  `inventory` ← derived `EnergyRelatedInventory + InventoryPartsAndComponentsNetOfReserves`
  (the two balance-sheet inventory lines: crude/products/merchandise + materials and supplies).
  `payables` ← `AccountsPayableAndAccruedLiabilitiesCurrent` (combined AP+accrued line;
  `accrued` dropped to avoid double counting). `total_equity` ←
  `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` (NCI ~$7B) so
  A = L + E exactly. `common_and_apic` ← `CommonStockValue` (Exxon's single "common stock
  without par value" line; its FY2024 jump 17,781 → 46,238 is the all-stock Pioneer deal).
- **PFE**: `revenue` ← `Revenues` (includes ~$8-9B/yr of alliance/collaboration revenue;
  `RevenueFromContractWithCustomerExcludingAssessedTax` was only tagged FY2023). `rnd` ←
  `ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost`. No `operating_income`
  (Pfizer's income statement goes straight from costs to pretax income). `total_equity` ←
  including-NCI tag (closes exactly).
- **COST**: clean generic mapping. Caveat: `revenue` (= `Revenues` =
  `RevenueFromContractWithCustomerExcludingAssessedTax`) includes membership fee income, while
  `cost_of_revenue` covers merchandise only, so the derived `gross_profit` (12.8%) is
  membership-flattered; merchandise-only margin is ~2pp lower. Items state gross margin with
  this in mind. `goodwill` tagged only through FY2024 (immaterial, $994M);
  `operating_lease_current` missing FY2025. `nci` dropped (zero).
- **NFLX**: `sga` unavailable as a combined tag; Netflix presents marketing and G&A separately
  (left unmapped — `SellingAndMarketingExpense`/`GeneralAndAdministrativeExpense` exist if
  needed). `intangibles` ← `FiniteLivedIntangibleAssetsNet` = the **content library**
  (~$32.8B, 59% of assets), tagged only from FY2024 (FY2023 used an extension tag, so that year
  has no row). `interest_expense` ← `InterestExpenseNonoperating`. `common_and_apic` ←
  `CommonStockValue` (Netflix combines stock + APIC in one line).
- **NVDA**: `capex` ← `PaymentsToAcquireProductiveAssets` (its CFS line covers property,
  equipment, and intangibles together; plain PP&E-purchases tag absent). `interest_expense` ←
  `InterestExpenseNonoperating`. `gross_profit` tagged directly (`GrossProfit`).
- **BA**: `sga` ← `GeneralAndAdministrativeExpense` (Boeing presents G&A only, no combined
  SG&A). `interest_expense` ← `InterestAndDebtExpense` (its "Interest and debt expense" line;
  plain `InterestExpense` absent). `debt_issued`/`debt_repaid` ← `ProceedsFromIssuanceOfDebt` /
  `RepaymentsOfDebt`. `total_equity` ← including-NCI tag: **negative** −17,228 (FY2023) and
  −3,914 (FY2024), positive 5,457 (FY2025) — identity closes exactly with the negative values.
  The FY2024 ~$24B equity rescue (`ProceedsFromIssuanceOfCommonStock` 18,200 +
  `ProceedsFromIssuanceOfConvertiblePreferredStock` 5,657) has no canonical fact row; used as
  item context only. `GrossProfit` is tagged and **negative** in FY2024 (−1,991).
- **UNP**: `ppe_net` ←
  `PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization`
  (HD precedent; plain tag only in FY2023). `inventory` ← `MaterialsSuppliesAndOther`
  (railroads hold no merchandise). `da_addback` ← `Depreciation`. `debt_repaid` ←
  `RepaymentsOfDebtAndCapitalLeaseObligations`. `accrued` dropped: UNP's
  `AccountsPayableAndAccruedLiabilitiesCurrent` is a combined line while `AccountsPayableCurrent`
  (mapped to `payables`) is the note-level trade AP; keeping both would double count. No COGS
  line (tell). `interest_expense` ← `InterestExpenseNonoperating` for FY2024-25.
- **SBUX**: `cost_of_revenue` **omitted deliberately**: Starbucks' "Product and distribution
  costs" (`ProductionAndDistributionCosts`, ~31% of revenue) excludes store operating costs, so
  a derived "gross margin" of ~68% would be economically misleading for a restaurant operator —
  no COGS/gross-profit rows (DAL precedent). `sga` ← `GeneralAndAdministrativeExpense`.
  `total_equity` ← including-NCI tag: **negative all three years** (−7,987.8 / −7,441.6 /
  −8,089.2); balance-sheet identity holds exactly with the negative values, and
  `retained_earnings` is itself a deficit.
- **NEE**: `revenue` ← `RegulatedAndUnregulatedOperatingRevenue` (utility revenue tag).
  `interest_expense` omitted: only `InterestPaidNet` (cash basis) is tagged; the income-statement
  interest line is inside "Other income (deductions)" without a standard tag — NEE is not used
  for coverage items. `capex` omitted: FPL capex and NEER "independent power investments" are
  extension-tagged; `cfi` carries the total, so the cash identity still ties. `da_addback` ←
  `DepreciationAndAmortization`. `payables` ← `AccountsPayableCurrentAndNoncurrent` (the only
  AP tag). `total_equity` ← derived including-NCI equity **plus temporary-equity redeemable NCI**
  (`TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests`,
  1,256 / 401 / 0): without the mezzanine piece FY2023 misses the 0.5% identity tolerance.
  `nci` ← `MinorityInterest` (permanent NCI only, ~$10-12B of tax-equity partners).
- **DE**: unclassified balance sheet (captive finance), so no
  `total_current_assets`/`total_current_liabilities` — correct and used as a tell.
  `pretax_income` ← `...BeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments`.
  `operating_income` dropped (tagged FY2023-24 only; not derivable for FY2025).
  `receivables` ← `AccountsReceivableNet` (trade only; the ~$44B financing receivables book is
  extension-tagged and absent — the biggest single gap in this pull). `ppe_net` and
  `debt_noncurrent` ("Long-term borrowings") are extension-tagged and therefore **absent**;
  `debt_current` ← `DebtCurrent` (short-term borrowings incl. current maturities), so DE's
  mapped debt understates total debt — DE is not used for leverage-level items.
  `payables` ← `AccountsPayableAndAccruedLiabilitiesCurrentAndNoncurrent` (combined line;
  `accrued` dropped). `debt_issued`/`debt_repaid` ←
  `ProceedsFromDebtMaturingInMoreThanThreeMonths` / `RepaymentsOfDebtMaturingInMoreThanThreeMonths`.
- **Equity with NCI, generally**: wherever NCI exists (XOM, PFE, BA, SBUX, DE), `total_equity`
  uses the including-NCI tag per the CAT precedent so A = L + E closes; DE retains a ≤$97M gap
  (redeemable NCI, within tolerance). `common_and_apic` falls back per filer:
  combined tag → derived `CommonStockValue + AdditionalPaidInCapital(CommonStock)` (BA, UNP,
  SBUX, NEE, COST) → `CommonStockValue` alone where the filer combines them (XOM, NFLX, DE).

### Reconciliation results

All 30 new company-years: balance sheet exact to the million except DE (gap = mezzanine NCI,
≤0.1% of assets); cash-flow identity exact (PFE FY2025 off by $1.0M, at tolerance); gross
profit exact where present (NVDA and BA tag `GrossProfit`; PFE, COST, NFLX derived, exact by
construction). `scripts/check_facts.py` and `scripts/build_db.py --check` both green.

### Additional quirks worth knowing

- **BA FY2024** is the roster's real-world stress case: net loss −11,817, CFO −12,080,
  negative gross profit, revenue down 14% (strike), rescued by the ~$24B equity raise. Deferred
  revenue (customer advances on undelivered aircraft) is ~$60B, 91% of FY2024 revenue.
- **COST FY2024** dividends of 9,041 include the $15/share special dividend (regular run-rate
  is ~$1.3-2.2B).
- **NEE's tax line** is a persistent net benefit (FY2025: −802 on 4,530 pretax, ≈ −18%
  effective rate) from renewables credits — used as a Daily clue, not an error.
- **PFE FY2023** carries the COVID-cliff distortions: gross margin 57% (inventory write-offs),
  net income 2,119, plus the $43.4B Seagen acquisition funded by 30,831 of new debt.
- **XOM FY2024** common stock jump (17,781 → 46,238) is the all-stock Pioneer acquisition;
  PP&E jumped $79B the same year.
- **DE FY2025** and **COST FY2023** flow-based ratios are flattered by their 53rd week.
