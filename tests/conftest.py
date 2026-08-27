import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from articulate.db import connect, init_schema  # noqa: E402


@pytest.fixture
def db(tmp_path):
    conn = connect(tmp_path / "test.db")
    init_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def seeded_db(db):
    """Minimal hand-built content for unit tests (independent of content/)."""
    db.execute("INSERT INTO concepts (id, name, band) VALUES ('c1', 'Concept 1', 'A')")
    db.execute("INSERT INTO concepts (id, name, band) VALUES ('c2', 'Concept 2', 'A')")
    db.execute("""INSERT INTO levels (id, ordinal, band, title) VALUES ('L1', 1, 'A', 'Test level')""")
    db.execute("""INSERT INTO items (id, mode, item_type, level_id, ordinal, difficulty,
                  grader, payload, answer_key)
                  VALUES ('i1', 'drill', 'sort', 'L1', 10, 1, 'choice',
                  '{"prompt": "p", "choices": ["a", "b"]}',
                  '{"correct_index": 1, "why_wrong": ["nope", null]}')""")
    db.execute("INSERT INTO item_concepts (item_id, concept_id) VALUES ('i1', 'c1')")
    db.execute("""INSERT INTO items (id, mode, item_type, level_id, ordinal, difficulty,
                  grader, payload, answer_key)
                  VALUES ('i2', 'drill', 'lexicon', 'L1', 20, 1, 'choice',
                  '{"prompt": "p2", "choices": ["a", "b"]}',
                  '{"correct_index": 0}')""")
    db.execute("INSERT INTO item_concepts (item_id, concept_id) VALUES ('i2', 'c2')")
    db.execute("INSERT INTO players (id, handle) VALUES (1, 'tester')")
    db.commit()
    return db
