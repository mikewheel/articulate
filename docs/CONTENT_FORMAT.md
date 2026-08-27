# Content interchange format (v0)

All game content lives in `content/` as JSON and is loaded into SQLite by
`scripts/build_db.py`. This document is the **contract** between content
authors (including sub-agents) and the seed loader. Do not deviate from the
field names or enum values below; the loader validates against them.

Money values are in **millions of USD** unless a fact row says otherwise.
All IDs are lowercase `snake_case` strings and must be unique within their file.

## Files

| File | Contents |
|---|---|
| `content/concepts.json` | Concept graph (list of concept objects) — already authored, fixed |
| `content/levels.json` | Level definitions with narrative |
| `content/companies_*.json` | Companies (the loader globs; use `companies_real.json`, `companies_synthetic.json`) |
| `content/facts_*.json` | Canonical financial facts per company-year (globbed the same way) |
| `content/items/*.json` | Item banks; each file is a JSON list of items. One file per level (`l1.json` … `l5.json`) plus `daily.json`. |
| `content/call_scenarios.json` | Earnings-call scenarios (fact sheet + hidden issues) |

## Concepts (`concepts.json`)

```json
{
  "id": "re_rollforward",
  "name": "Retained earnings roll-forward",
  "band": "B",                      // A..H per spec §3
  "cfa": "L1.balance_sheets",
  "prereqs": ["net_income_definition", "dividends_declared"],
  "description": "one or two sentences, player-facing"
}
```

The graph must be acyclic; a test enforces this. **The concept ID list is
fixed** (see `content/concepts.json`, already authored). Items may only
reference existing concept IDs.

## Levels (`levels.json`)

```json
{
  "id": "L1",                        // fixed IDs: L1..L5
  "ordinal": 1,
  "band": "A",
  "title": "...",
  "tagline": "one line",
  "narrative_intro": "2-4 short paragraphs, second person, shown before the level",
  "narrative_outro": "1-2 paragraphs shown on completion",
  "unlock": {"prereq_level": null, "min_mastery": 0.6}
}
```

Fixed level skeleton (titles/narrative are the author's to write, bands and
scope are not):

| id | Band | Scope | Modes |
|---|---|---|---|
| L1 | A | Classify line items, journal entries, accounting equation, lexicon | drills + 3 mini-sudoku |
| L2 | B | Articulation: RE roll-forward, indirect CFO, PP&E roll-forward, cash reconciliation | sudoku set + translate |
| L3 | C | Policies: revenue recognition, LIFO reserve, capitalization, depreciation estimates, deferred taxes, leases | translate + numeric adjustments + journal |
| L4 | D | Ratios on real companies, common-size, DuPont, industry gestalt | forge + lineup (real EDGAR data) |
| L5 | E | Forensics: one synthetic manipulation case + earnings-call interrogation | forensic case + earnings_call |
| L6 | F | CFA L2 dialects: intercorporate investments (equity method/consolidation/NCI), pensions, FX translation vs remeasurement, IFRS vs US GAAP, bank statements | translate + numeric adjustments + choice/journal |
| L7 | E | The reckoning: Sable Peak restates. Restatement autopsy, forensic screens (Beneish, accruals), non-GAAP reconciliation, capstone thesis | numeric + choice + llm_rubric + earnings_call |
| L8 | E | The Vault: boss cases from the public record (Enron FY2000, WorldCom) + Note Hunt on real filings | note_hunt + forensic_case, evidence quoted from actual filings/SEC actions |

`hindsight` items (mode "hindsight", item_type "hindsight_forecast", grader
"probability") live outside the level sequence like daily items (level_id null).

`daily.json` holds Daily Filing items (real, anonymized), outside the level sequence.

## Companies (`companies.json`)

```json
{
  "id": "meridian_tools",           // real companies: lowercase ticker, e.g. "kr"
  "name": "Meridian Tools, Inc.",
  "ticker": null,                    // real: "KR"
  "cik": null,                       // real: zero-padded 10-digit string
  "kind": "synthetic",               // "synthetic" | "real"
  "industry": "industrial tools",
  "sic": null,
  "fye_month": 12,
  "description": "one paragraph, player-facing"
}
```

## Facts (`facts.json`)

One row per (company, fiscal_year, canonical item). Canonical item names are
**exactly** the Appendix A list in `spec.md` (e.g. `revenue`,
`cost_of_revenue`, `gross_profit`, `sga`, `rnd`, `da`, `operating_income`,
`interest_expense`, `pretax_income`, `income_tax`, `net_income`, `cash`,
`receivables`, `inventory`, `total_current_assets`, `ppe_net`, `goodwill`,
`total_assets`, `payables`, `accrued`, `deferred_revenue`, `debt_current`,
`total_current_liabilities`, `debt_noncurrent`, `total_liabilities`,
`common_and_apic`, `retained_earnings`, `total_equity`, `cfo`, `da_addback`,
`sbc`, `working_capital_change`, `capex`, `cfi`, `debt_issued`, `debt_repaid`,
`buybacks`, `dividends`, `cff`, `fx_effect`, `net_change_cash`, …).

```json
{
  "company_id": "kr",
  "fiscal_year": 2024,
  "period_end": "2025-02-01",
  "item": "revenue",
  "value": 147123.0,                 // millions USD; sign conventions: expenses positive,
                                     // cash outflows negative on the CFS (capex < 0, buybacks < 0)
  "unit": "USD_millions",
  "basis": "as_filed",               // "as_filed" | "as_restated" | "synthetic"
  "source_tag": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
  "source_form": "10-K",
  "source_accession": "0001558370-25-XXXXXX"   // null for synthetic
}
```

Sign conventions: income-statement expense items are **positive** magnitudes;
cash-flow outflows are **negative** (capex, buybacks, dividends, debt_repaid);
`treasury_stock` is negative on the balance sheet. Identity checks in the test
suite assume these conventions:

- `total_assets == total_liabilities + total_equity` (±0.5% of assets)
- `cfo + cfi + cff + fx_effect == net_change_cash` (±1% of |Δcash|, min 1.0)
- `gross_profit == revenue - cost_of_revenue` when all three present

## Items (`items/*.json`)

```json
{
  "id": "l1_sort_001",               // prefix with level id
  "mode": "drill",                   // drill | sudoku | forge | lineup | forensics | earnings_call | daily
  "item_type": "sort",               // sort | journal | translate | lexicon | sudoku |
                                     // ratio_build | ratio_interpret | lineup_match |
                                     // forensic_case | cfo_question | daily_filing
  "level_id": "L1",                  // or null for daily
  "ordinal": 10,                     // presentation order within level; leave gaps of 10
  "concept_ids": ["statement_roles"],
  "difficulty": 1,                   // 1..5, author's estimate
  "grader": "choice",                // choice | numeric | grid | mapping | llm_rubric
  "payload": { },
  "answer_key": { },
  "hints": [{"concept_id": "statement_roles", "text": "Which statement reports position at a point in time?"}],
  "explanation": "Shown after grading. Always explain the WHY and the investor 'so what'."
}
```

### Payload / answer_key by grader

**choice** — payload `{"prompt": str, "context": str|null, "choices": [str]}`;
answer_key `{"correct_index": int, "why_wrong": [str|null per choice]}`.

**numeric** — payload `{"prompt": str, "context": str|null, "unit": str}`;
answer_key `{"value": number, "tolerance_abs": number|null, "tolerance_rel": number|null}` (at least one tolerance).

**grid** (sudoku) — payload:
```json
{
  "intro": "scenario text",
  "company_id": "meridian_tools",    // or null for standalone scenarios
  "statements": [
    {"name": "Income Statement (FY2, $M)",
     "rows": [
       {"key": "revenue", "label": "Revenue", "value": 1000.0, "blank": false, "indent": 0, "subtotal": false},
       {"key": "net_income", "label": "Net income", "value": null, "blank": true, "indent": 0, "subtotal": true}
     ]}
  ],
  "identities": ["Gross profit = Revenue − COGS", "RE roll-forward"]
}
```
answer_key `{"cells": {"net_income": 75.0}, "tolerance_abs": 0.5}`.
Row `key`s must be unique across the whole item. Every blank cell must be
derivable from the visible cells via identities (unique solution) — authors
must verify with arithmetic before writing the item.

**mapping** (lineup) — payload:
```json
{
  "prompt": "Match each anonymized company to its industry.",
  "left": [{"key": "A", "label": "Company A", "stats": [{"name": "Gross margin", "value": "22%"}, ...]}],
  "right": ["Grocery chain", "Enterprise software", "Airline", "Bank"]
}
```
answer_key `{"map": {"A": 1, "B": 0, ...}, "tells": {"A": "explanation of the tell"}}` (values are indices into `right`).

**probability** (hindsight_forecast) — payload:
```json
{
  "prompt": "Probability that this filer takes a goodwill impairment within the next fiscal year?",
  "context": "the as-of-date dossier: key figures/ratios visible at the time, NOTHING from after as_of",
  "as_of": "2018-02-23",
  "company_label": "a global industrial conglomerate"   // anonymized until feedback
}
```
answer_key:
```json
{
  "outcome": true,
  "base_rate": 0.05,                  // honest rough base rate for the event class
  "resolution": "What actually happened, with dates — revealed as feedback",
  "source": "8-K / 10-K accession or public action establishing the outcome",
  "company": "General Electric"       // revealed in feedback
}
```
Submitted as `{"p": 0.0..1.0}`. Scored by Brier: score = 1 − (p − outcome)²;
"correct" means beating the base-rate forecast. The context MUST be strictly
as-of-date (no leakage), and outcome/resolution MUST rest on the public record.

**llm_rubric** (translate, ratio_interpret, forensic prose, cfo_question) —
payload `{"prompt": str, "context": str|null, "response_guidance": "e.g. 2-3 sentences"}`;
answer_key:
```json
{
  "model_answer": "best-in-class answer",
  "rubric": [
    {"id": "mechanics", "points": 1, "description": "States that depreciation expense falls"},
    {"id": "so_what", "points": 2, "description": "Links to earnings quality / investor implication"}
  ],
  "pass_points": 2
}
```

### Earnings call (L5)

`earnings_call` items use `item_type: "cfo_question"`, grader `llm_rubric`, and
an extra payload key `"scenario_id"` referencing `content/call_scenarios.json`:

```json
{
  "id": "sable_call",
  "company_id": "...",
  "cfo_name": "...", "cfo_persona": "1-2 sentences",
  "fact_sheet": {"revenue_fy2": 1180.0, "...": "every number the CFO may state"},
  "hidden_issues": [
    {"id": "channel_stuffing", "summary": "...", "reveal_threshold": "what kind of question uncovers it"}
  ],
  "max_questions": 5
}
```

## Validation

`scripts/build_db.py --check` validates every file against this contract and
runs the identity checks before writing the DB. Run it before finishing.
