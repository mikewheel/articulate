# Articulate

A game for becoming fluent in financial statements. Local-only prototype:
SQLite + FastAPI + a static web client, with content drawn from a synthetic
ledger and real SEC EDGAR filings. Design spec: `spec.md`.

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/build_db.py          # validate content/, build articulate.db
.venv/bin/uvicorn articulate.app:app --app-dir src --port 8642
# open http://127.0.0.1:8642
```

Tests: `.venv/bin/python -m pytest`

Excel version of the Statement Sudoku puzzles (built for the Claude for Excel
connector): `.venv/bin/python scripts/export_excel.py` → `excel/articulate_sudoku.xlsx`.

LLM features (rubric-graded free-text answers, the Level 5 CFO call) run
against a deterministic offline mock until `ANTHROPIC_API_KEY` is set, at
which point they switch to Claude automatically (`src/articulate/llm.py`).

## Layout

| Path | What |
|---|---|
| `db/schema.sql`, `docs/DATA_MODEL.md` | SQLite schema and its rationale |
| `content/` | All game content as JSON (contract: `docs/CONTENT_FORMAT.md`) |
| `content/items/l1..l5.json` | Item banks for the five levels |
| `src/articulate/` | Loader/validator, graders, mastery model, LLM layer, FastAPI app |
| `web/` | Static frontend |
| `scripts/` | `build_db.py`, `export_excel.py`, `gen_synthetic.py`, `check_facts.py` |
| `docs/STORY.md`, `docs/PEDAGOGY.md` | Narrative frame and learning-science grounding |
| `docs/EDGAR_NOTES.md` | What was pulled from EDGAR and how it was mapped |
| `docs/NEXT_PASS.md` | Open questions, data sources to add, deliberate simplifications |
| `tests/` | Schema, grader, mastery, LLM-mock, API, and content-contract tests |
