-- Articulate: local SQLite schema (v0)
-- See docs/DATA_MODEL.md for the design rationale.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------- content --

CREATE TABLE IF NOT EXISTS concepts (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    band        TEXT NOT NULL CHECK (band IN ('A','B','C','D','E','F','G','H')),
    cfa         TEXT,
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS concept_prereqs (
    concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    prereq_id  TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    PRIMARY KEY (concept_id, prereq_id),
    CHECK (concept_id <> prereq_id)
);

CREATE TABLE IF NOT EXISTS levels (
    id              TEXT PRIMARY KEY,
    ordinal         INTEGER NOT NULL UNIQUE,
    band            TEXT NOT NULL CHECK (band IN ('A','B','C','D','E','F','G','H')),
    title           TEXT NOT NULL,
    tagline         TEXT NOT NULL DEFAULT '',
    narrative_intro TEXT NOT NULL DEFAULT '',
    narrative_outro TEXT NOT NULL DEFAULT '',
    prereq_level_id TEXT REFERENCES levels(id),
    min_mastery     REAL NOT NULL DEFAULT 0.6 CHECK (min_mastery BETWEEN 0 AND 1)
);

CREATE TABLE IF NOT EXISTS companies (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    ticker      TEXT,
    cik         TEXT,                      -- zero-padded 10 digits for real filers
    kind        TEXT NOT NULL CHECK (kind IN ('synthetic','real')),
    industry    TEXT,
    sic         TEXT,
    fye_month   INTEGER CHECK (fye_month BETWEEN 1 AND 12),
    description TEXT NOT NULL DEFAULT ''
);

-- Long/narrow fact store, one row per (company, year, canonical item, basis) --
-- mirrors the XBRL shape so real and synthetic data live in one table.
CREATE TABLE IF NOT EXISTS facts (
    id               INTEGER PRIMARY KEY,
    company_id       TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    fiscal_year      INTEGER NOT NULL,
    period_end       TEXT,                 -- ISO date
    item             TEXT NOT NULL,        -- canonical line item (spec Appendix A)
    value            REAL NOT NULL,        -- USD millions; signs per CONTENT_FORMAT.md
    unit             TEXT NOT NULL DEFAULT 'USD_millions',
    basis            TEXT NOT NULL DEFAULT 'as_filed'
                     CHECK (basis IN ('as_filed','as_restated','synthetic')),
    source_tag       TEXT,
    source_form      TEXT,
    source_accession TEXT,
    UNIQUE (company_id, fiscal_year, item, basis)
);
CREATE INDEX IF NOT EXISTS idx_facts_lookup ON facts (company_id, fiscal_year);

CREATE TABLE IF NOT EXISTS items (
    id          TEXT PRIMARY KEY,
    mode        TEXT NOT NULL CHECK (mode IN
                 ('drill','sudoku','forge','lineup','forensics','earnings_call','daily',
                  'hindsight')),
    item_type   TEXT NOT NULL CHECK (item_type IN
                 ('sort','journal','translate','lexicon','sudoku','ratio_build',
                  'ratio_interpret','lineup_match','forensic_case','cfo_question',
                  'daily_filing','hindsight_forecast','note_hunt')),
    level_id    TEXT REFERENCES levels(id),          -- NULL for daily items
    ordinal     INTEGER NOT NULL DEFAULT 0,
    difficulty  INTEGER NOT NULL DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 5),
    grader      TEXT NOT NULL CHECK (grader IN
                 ('choice','numeric','grid','mapping','llm_rubric','probability')),
    payload     TEXT NOT NULL CHECK (json_valid(payload)),
    answer_key  TEXT NOT NULL CHECK (json_valid(answer_key)),
    explanation TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_items_level ON items (level_id, ordinal);

CREATE TABLE IF NOT EXISTS item_concepts (
    item_id    TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    concept_id TEXT NOT NULL REFERENCES concepts(id),
    PRIMARY KEY (item_id, concept_id)
);

CREATE TABLE IF NOT EXISTS item_hints (
    item_id    TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    ordinal    INTEGER NOT NULL,
    concept_id TEXT REFERENCES concepts(id),
    text       TEXT NOT NULL,
    PRIMARY KEY (item_id, ordinal)
);

CREATE TABLE IF NOT EXISTS call_scenarios (
    id            TEXT PRIMARY KEY,
    company_id    TEXT NOT NULL REFERENCES companies(id),
    cfo_name      TEXT NOT NULL,
    cfo_persona   TEXT NOT NULL,
    fact_sheet    TEXT NOT NULL CHECK (json_valid(fact_sheet)),
    hidden_issues TEXT NOT NULL CHECK (json_valid(hidden_issues)),
    max_questions INTEGER NOT NULL DEFAULT 5
);

-- ------------------------------------------------------------ player state --

CREATE TABLE IF NOT EXISTS players (
    id         INTEGER PRIMARY KEY,
    handle     TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS attempts (
    id            INTEGER PRIMARY KEY,
    player_id     INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    item_id       TEXT NOT NULL REFERENCES items(id),
    submitted     TEXT NOT NULL CHECK (json_valid(submitted)),
    score         REAL NOT NULL,
    max_score     REAL NOT NULL,
    correct       INTEGER NOT NULL CHECK (correct IN (0,1)),   -- score/max >= pass bar
    feedback      TEXT NOT NULL CHECK (json_valid(feedback)),
    grader_source TEXT NOT NULL CHECK (grader_source IN ('deterministic','llm_mock','llm')),
    hints_used    INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_attempts_player ON attempts (player_id, item_id);

-- Simplified mastery model (EMA per concept). Stand-in for Glicko-2 (spec §6);
-- the interface (per-concept scalar + attempt count) is what the real rating
-- system will also expose, so swapping it later is contained.
CREATE TABLE IF NOT EXISTS concept_mastery (
    player_id       INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    concept_id      TEXT NOT NULL REFERENCES concepts(id),
    mastery         REAL NOT NULL DEFAULT 0 CHECK (mastery BETWEEN 0 AND 1),
    attempts        INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT,
    PRIMARY KEY (player_id, concept_id)
);

-- Simplified spaced-repetition schedule (SM-2-flavored stand-in for FSRS).
CREATE TABLE IF NOT EXISTS review_schedule (
    player_id     INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    item_id       TEXT NOT NULL REFERENCES items(id),
    due_at        TEXT NOT NULL,
    interval_days REAL NOT NULL DEFAULT 1,
    ease          REAL NOT NULL DEFAULT 2.5,
    reps          INTEGER NOT NULL DEFAULT 0,
    lapses        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (player_id, item_id)
);

CREATE TABLE IF NOT EXISTS call_transcripts (
    id          INTEGER PRIMARY KEY,
    player_id   INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    scenario_id TEXT NOT NULL REFERENCES call_scenarios(id),
    turn        INTEGER NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('analyst','cfo')),
    content     TEXT NOT NULL,
    issues_hit  TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(issues_hit)),
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
