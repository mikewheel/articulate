# Next pass: open items

Updated 2026-08-27 (second pass) after completing the prior list: SEC bulk
pipeline, generated dailies, Hindsight calibration mode, and the L8 Vault.

## Done

- **SEC bulk pipeline**: `data/companyfacts.zip` (1.3GB, regenerable) →
  `src/articulate/normalize.py` (codified candidate-tag table, derivations,
  as-filed selection, quality scoring/quarantine per spec §8.2) →
  `scripts/build_bulk.py` → `data/edgar_bulk.db` (13,948 companies, 111k
  company-years, 31k admitted, 2.5M facts). Golden test cross-checks bulk
  output against the hand-curated pulls.
- **Generated Daily Filing**: `scripts/gen_daily.py` builds a 420-company
  pool with SIC classifications and pool percentiles → 365 deterministic
  items; rotation now spans 380 puzzles (>1 year).
- **Hindsight mode** (spec §5.7): probability grader with Brier scoring,
  15 verified historical cases (Lehman → Hertz, plus survivors that teach
  base rates), calibration curve.
- **L8 The Vault**: Enron FY2000 and WorldCom FY2001 boss cases with
  verbatim-verified excerpts from the actual filings; Note Hunt item type.
- Solve juice: cascading settle animation + balance tone on a tied sudoku.

## Still open (roughly in value order)

1. **Filing-HTML section parser** for arbitrary filers — Note Hunt beyond
   the two hand-built boss cases, MD&A reading items, Comparative Reading
   (IFRS 20-F vs 10-K). The Vault items quote hand-extracted text; a parser
   would make this generative.
2. **DERA Financial Statement Data Sets** — company extension tags (the gap
   the bulk companyfacts feed can't close: KR's SG&A, DAL's air traffic
   liability) and Tag Archaeology as an item type.
3. **Hindsight expansion from bulk**: 8-K item feeds (4.01/4.02/1.03) could
   label thousands of company-years in `edgar_bulk.db` for generated
   forecasting items; currently all 15 cases are hand-curated.
4. **Mastery**: still EMA + SM-2-flavored scheduling rather than
   Glicko-2/FSRS (interfaces shaped for the swap; fine for solo play).
5. **Remaining spec modes**: Model Studio (grid three-statement builder),
   Filing Season runs, Ratio Forge recipe-crafting UI, mock-exam vignettes.
6. Multi-profile/auth if this ever leaves localhost.

## Operational notes

- `data/` is git-ignored and regenerable: re-download companyfacts.zip, then
  `build_bulk.py` (~3 min) and `gen_daily.py`. Disk footprint ~3GB.
- Rebuilding content tables preserves player state; only schema CHECK
  changes force a fresh DB.
