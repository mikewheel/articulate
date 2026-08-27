# Next pass: open items

Updated 2026-08-27 after the depth expansion (L6/L7, 16-filer roster, live
Claude judge/CFO/classifier).

## Done since the first pass

- Live LLM: `.env` key wired; rubric judge, CFO character, and the
  question→issue classifier all run on Claude (`claude-opus-4-8`) with the
  offline mock as fallback. Mock-graded attempts remain tagged `llm_mock`.
- Real-data roster: 16 filers / 54 company-years, 141 identity checks green.
  Daily Filing rotates one filer per calendar day.
- Depth: L6 (Band F — intercorporate, pensions, FX methods, IFRS vs GAAP,
  banks) and L7 (Sable Peak restatement autopsy, Beneish/accruals screens,
  non-GAAP reading, post-restatement call, capstone thesis).
- Grader evaluation formally de-scoped by Michael (low-risk use case).

## Data sources still worth adding

1. **SEC bulk data** (`companyfacts.zip`, DERA quarterly sets) — unlimited
   Daily rotation, Lineup percentiles via frames, Tag Archaeology. Needs the
   candidate-tag mapping table + quarantine machinery (spec §8.2); biggest
   remaining engineering item.
2. **Filing HTML** (Items 7/8/9A parsed into sections) — Note Hunt, MD&A
   reading, and real forensics bosses (Enron FY2000, WorldCom, etc., which
   must cite the actual public record).
3. **8-K item feeds + AAERs** — Hindsight mode (calibration/Brier scoring)
   resolution labels.

## Remaining simplifications

- Mastery is still EMA + SM-2-ish scheduling (interfaces shaped for
  Glicko-2/FSRS swap; see docs/DATA_MODEL.md).
- No flow-board animation on sudoku solve; cells flash only.
- Single-player, no auth; handle in localStorage.
- Facts are latest-filed only for real companies (as-restated exists only
  for Sable Peak's synthetic restatement).
- Modes not yet built (spec roadmap): Model Studio, Filing Season runs,
  Hindsight, Ratio Forge recipe-crafting UI, mock-exam vignette mode.
