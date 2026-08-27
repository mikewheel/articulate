"""Articulate: a game for becoming fluent in financial statements. Local v0."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "articulate.db"
SCHEMA_PATH = PROJECT_ROOT / "db" / "schema.sql"
CONTENT_DIR = PROJECT_ROOT / "content"
WEB_DIR = PROJECT_ROOT / "web"
