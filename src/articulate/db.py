"""SQLite connection and schema helpers."""

import sqlite3
from pathlib import Path

from . import DB_PATH, SCHEMA_PATH


def connect(path: Path | str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()


CONTENT_TABLES = [
    # deletion order respects foreign keys
    "call_scenarios",
    "item_hints",
    "item_concepts",
    "items",
    "facts",
    "companies",
    "levels",
    "concept_prereqs",
    "concepts",
]


def clear_content(conn: sqlite3.Connection) -> None:
    """Remove content tables only; player state survives rebuilds.

    Does not commit: callers wrap clear + reload in one transaction with
    deferred foreign keys, so attempts referencing re-inserted items survive.
    """
    for table in CONTENT_TABLES:
        conn.execute(f"DELETE FROM {table}")
