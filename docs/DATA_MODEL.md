# Articulate data model (v0, local SQLite)

Database: `articulate.db` in the project root, built from `db/schema.sql` by
`scripts/build_db.py`, which validates and loads everything under `content/`.
The database is a **build artifact**: content JSON is the source of truth for
game content, the DB adds player state. Rebuilding content tables is
idempotent and preserves player state.

```
.venv/bin/python scripts/build_db.py            # validate content + (re)build articulate.db
.venv/bin/python scripts/build_db.py --check    # validate only, touch nothing
```

## Design decisions

1. **Content as JSON, state in SQL.** Items, levels, concepts, and financial
   facts are authored as JSON (contract: `docs/CONTENT_FORMAT.md`) and loaded
   into SQLite. That keeps authoring reviewable in git and makes the DB
   disposable. Player tables (`players`, `attempts`, `concept_mastery`,
   `review_schedule`, `call_transcripts`) are never dropped by the loader.

2. **Polymorphic items with JSON payloads.** One `items` table covers every
   mode. The `grader` column is the discriminator; `payload` and `answer_key`
   are JSON validated (shape per grader) at load time by the loader and at
   write time by `json_valid` CHECKs. Alternative — a table per item type —
   was rejected: eleven modes are coming (spec §5) and the game loop treats
   items uniformly (present payload → collect submission → grade → feedback).

3. **Long/narrow fact store.** `facts` is one row per (company, fiscal year,
   canonical line item, basis), mirroring the XBRL shape. Real and synthetic
   companies share the table; provenance columns (`source_tag`, `source_form`,
   `source_accession`, `basis`) keep the door open for as-filed vs as-restated
   history (spec §8.2 says restatements are content, so we never overwrite —
   we add rows with a different basis). Canonical item names are the spec
   Appendix A list; sign conventions are in `CONTENT_FORMAT.md` and enforced
   by identity checks at load time.

4. **Mastery is a per-concept EMA, not Glicko-2 (yet).** Spec §6 calls for
   Glicko-2 per concept with rating deviation. For a local first playable,
   `concept_mastery` stores a scalar in [0,1] updated by
   `m' = m + k·(score − m)` (k = 0.35), plus an attempt count. Level unlocks
   read the mean mastery over the level's exercised concepts against
   `levels.min_mastery`. The table shape (player × concept × scalar +
   uncertainty proxy via attempt count) is deliberately the same shape a
   Glicko-2 implementation needs, so the swap is contained in
   `src/articulate/mastery.py`.

5. **Spaced repetition is an SM-2-flavored stand-in for FSRS**, in
   `review_schedule` (interval, ease, reps, lapses). Same argument: the
   scheduling interface (`due_at` per player × item) is stable; the algorithm
   behind it is swappable.

6. **Answer keys never leave the server.** The API strips `answer_key` and
   hints from item payloads; hints are fetched one at a time and counted, and
   grading happens server-side only. This is a game-integrity property with a
   test (`tests/test_api.py`).

7. **LLM-graded prose is recorded with its provenance.** `attempts.grader_source`
   distinguishes `deterministic`, `llm_mock` (the offline keyword judge used
   until API keys exist), and `llm` (real Claude). When real grading arrives,
   mock-graded attempts can be identified and re-graded.

## Entity relationships

```
concepts ──< concept_prereqs (DAG, validated acyclic at load)
concepts ──< item_concepts >── items >── levels (nullable: daily items)
items ──< item_hints (ordered; hint text points at a concept, never a value)
companies ──< facts
companies ──< call_scenarios (CFO fact sheet + hidden issues as JSON)
players ──< attempts >── items
players ──< concept_mastery >── concepts
players ──< review_schedule >── items
players ──< call_transcripts >── call_scenarios
```

## Table notes

- **concepts / concept_prereqs** — the concept graph (spec §6), ~50 nodes for
  bands A–E plus two H nodes. Acyclicity is enforced by a topological sort in
  the loader and a test.
- **levels** — five levels, L1–L5, linear unlock chain via `prereq_level_id`
  with `min_mastery` threshold. Narrative text lives here (mentor voice).
- **facts** — values in USD **millions**. Expenses positive on the income
  statement; outflows negative on the cash flow statement. Identity checks at
  load: A = L + E within 0.5% of assets; CFO+CFI+CFF+FX = Δcash within 1%;
  gross profit consistency. Company-years failing checks are rejected
  (synthetic) or must be listed in `docs/EDGAR_NOTES.md` (real, quarantine).
- **items** — see `CONTENT_FORMAT.md` for payload/answer_key shapes per
  grader. `ordinal` orders items in a level; authors leave gaps of 10.
- **attempts** — full submission + structured feedback JSON, append-only.
  `correct` is score/max ≥ 0.99 for deterministic graders, ≥ pass_points/total
  for rubric graders.
- **call_transcripts** — the L5 earnings-call dialogue, one row per turn, with
  the hidden issues a question uncovered (`issues_hit`).

## What is deliberately missing (next passes)

- Glicko-2 ratings + item difficulty ratings from play data (spec §6).
- FSRS parameters; the current scheduler is enough to drive "due drills" UX.
- Raw XBRL fact archive (as-filed vs as-restated rows exist in the schema via
  `basis`, but the EDGAR pull currently loads latest-filed values only).
- Seasons, leaderboards, seeded runs, loadouts (spec §5.9), multi-player.
