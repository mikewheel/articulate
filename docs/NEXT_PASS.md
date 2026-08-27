# Next pass: open questions and data sources

## Data sources that would improve gameplay (need your call)

1. **SEC bulk data** (`companyfacts.zip`, quarterly Financial Statement Data
   Sets). Free/public. The current pull is per-company via the companyfacts
   API for six filers. Bulk unlocks Lineup peer percentiles (frames), Tag
   Archaeology (custom tags live only in the DERA sets), and unlimited Daily
   Filing rotation. Needs ~2-10 GB local disk and a normalize layer with a
   golden-test harness (spec §8.2) — the single biggest engineering item.
2. **Filing HTML** (10-K Items 7/8/9A). Needed for Note Hunt, MD&A reading,
   and boss forensics cases (Enron/WorldCom write-ups must cite the actual
   text). Public; needs a section parser.
3. **8-K item feeds + AAERs** for Hindsight resolution labels (Items 4.01,
   4.02, 1.03) and real forensics labels. Public via EDGAR full-text search.
4. **CFA curriculum outlines** (already public PDFs) to refine the concept →
   module mapping beyond my draft tags.
5. **Anthropic API keys** — set `ANTHROPIC_API_KEY` and the judge + CFO switch
   from the offline mock to Claude (`claude-opus-4-8`) automatically; no code
   change. Worth deciding: pin a cheaper model for the judge? Spec §10 says
   pin model versions and keep a human-labeled golden set for the grader —
   the `evals/` harness does not exist yet.
6. **Claude for Excel connector** — the workbook in `excel/` is built for it
   (coach prompt + hidden key sheet). Nothing server-side needed; just open
   the workbook with the connector enabled and paste the coach prompt.

## Deliberate simplifications in this pass (all flagged in code/docs)

- **Mastery**: per-concept EMA instead of Glicko-2; SM-2-ish scheduling
  instead of FSRS. Interfaces shaped for the swap (docs/DATA_MODEL.md §4-5).
- **LLM grading offline**: the mock judge is keyword overlap and is recorded
  as `grader_source='llm_mock'` so those attempts can be re-graded when keys
  arrive.
- **Question→issue classifier** (earnings call) is the same keyword matcher
  for both mock and live modes, per spec §5.6 (deterministic scoring); it
  needs recorded fixtures and a real classifier next.
- **Single player table, no auth** — handle typed in the browser.
- **No flow-board animation** on sudoku solve (spec §5.2 feedback juice) —
  cells flash green/red only.
- **EDGAR facts are latest-filed only**; the schema supports as-filed vs
  as-restated (`facts.basis`) but the pull doesn't populate history yet.

## Known risks carried forward

- XBRL normalization debt (spec §10 warning) — the six-company hand-mapped
  pull works, but scaling to arbitrary tickers needs the candidate-tag table +
  quarantine machinery.
- LLM judge drift — needs the eval set + agreement gate before real grading
  counts toward mastery.
