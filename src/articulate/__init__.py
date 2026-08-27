"""Articulate: a game for becoming fluent in financial statements. Local v0."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    """Load KEY=VALUE pairs from the git-ignored .env at the project root.
    Existing environment variables win."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()
DB_PATH = PROJECT_ROOT / "articulate.db"
SCHEMA_PATH = PROJECT_ROOT / "db" / "schema.sql"
CONTENT_DIR = PROJECT_ROOT / "content"
WEB_DIR = PROJECT_ROOT / "web"
