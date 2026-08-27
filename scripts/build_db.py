#!/usr/bin/env python
"""Validate content/ against the contract and (re)build articulate.db.

Usage:
    .venv/bin/python scripts/build_db.py           # validate + build
    .venv/bin/python scripts/build_db.py --check   # validate only
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from articulate import DB_PATH
from articulate.content import ContentError, load_content, load_into_db
from articulate.db import connect, init_schema


def main() -> int:
    check_only = "--check" in sys.argv
    try:
        bundle = load_content()
    except ContentError as e:
        print(f"CONTENT INVALID\n{e}", file=sys.stderr)
        return 1
    print(f"content valid: {len(bundle['concepts'])} concepts, "
          f"{len(bundle['levels'])} levels, {len(bundle['companies'])} companies, "
          f"{len(bundle['facts'])} facts, {len(bundle['items'])} items, "
          f"{len(bundle['call_scenarios'])} call scenarios")
    if check_only:
        return 0
    conn = connect(DB_PATH)
    init_schema(conn)
    counts = load_into_db(conn, bundle)
    conn.close()
    print(f"built {DB_PATH.name}: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
