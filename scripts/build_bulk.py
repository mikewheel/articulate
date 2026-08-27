#!/usr/bin/env python
"""Process data/companyfacts.zip through the normalize layer into
data/edgar_bulk.db (regenerable local artifact, git-ignored).

Tables:
  bulk_companies(cik, name, ticker)          ticker from company_tickers.json
  bulk_facts(cik, period_end, fiscal_year, item, value)
  bulk_quality(cik, period_end, fiscal_year, bs_ok, cf_ok, admitted)

Usage: .venv/bin/python scripts/build_bulk.py [--limit N]
"""

import json
import sqlite3
import sys
import time
import zipfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from articulate.normalize import normalize_company  # noqa: E402

DATA = ROOT / "data"
ZIP = DATA / "companyfacts.zip"
DB = DATA / "edgar_bulk.db"
TICKERS = DATA / "company_tickers.json"
USER_AGENT = "Articulate/0.1 (contact: mbw@mbw.dev)"

SCHEMA = """
CREATE TABLE IF NOT EXISTS bulk_companies (
    cik INTEGER PRIMARY KEY, name TEXT NOT NULL, ticker TEXT);
CREATE TABLE IF NOT EXISTS bulk_facts (
    cik INTEGER NOT NULL, period_end TEXT NOT NULL, fiscal_year INTEGER NOT NULL,
    item TEXT NOT NULL, value REAL NOT NULL,
    PRIMARY KEY (cik, period_end, item));
CREATE TABLE IF NOT EXISTS bulk_quality (
    cik INTEGER NOT NULL, period_end TEXT NOT NULL, fiscal_year INTEGER NOT NULL,
    bs_ok INTEGER NOT NULL, cf_ok INTEGER NOT NULL, admitted INTEGER NOT NULL,
    PRIMARY KEY (cik, period_end));
CREATE INDEX IF NOT EXISTS idx_bulk_facts_year ON bulk_facts (fiscal_year, item);
"""


def load_tickers() -> dict:
    if not TICKERS.exists():
        resp = httpx.get("https://www.sec.gov/files/company_tickers.json",
                         headers={"User-Agent": USER_AGENT},
                         follow_redirects=True, timeout=60)
        resp.raise_for_status()
        TICKERS.write_bytes(resp.content)
    raw = json.loads(TICKERS.read_text())
    out = {}
    for row in raw.values():
        out.setdefault(int(row["cik_str"]), row["ticker"])  # first listing wins
    return out


def main() -> int:
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    tickers = load_tickers()
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)
    conn.execute("DELETE FROM bulk_companies")
    conn.execute("DELETE FROM bulk_facts")
    conn.execute("DELETE FROM bulk_quality")

    z = zipfile.ZipFile(ZIP)
    names = z.namelist()
    if limit:
        names = names[:limit]
    started = time.time()
    processed = companies_kept = years_admitted = 0
    for n, member in enumerate(names, 1):
        try:
            data = json.loads(z.read(member))
        except (json.JSONDecodeError, zipfile.BadZipFile):
            continue
        result = normalize_company(data)
        processed += 1
        if not result["years"] or result["cik"] is None:
            continue
        cik = int(result["cik"])
        rows_f, rows_q = [], []
        for end, year in result["years"].items():
            rows_q.append((cik, end, year["fiscal_year"],
                           int(year["quality"]["bs_ok"]), int(year["quality"]["cf_ok"]),
                           int(year["quality"]["admitted"])))
            years_admitted += year["quality"]["admitted"]
            for item, value in year["facts"].items():
                rows_f.append((cik, end, year["fiscal_year"], item, value))
        if not rows_f:
            continue
        companies_kept += 1
        conn.execute("INSERT OR REPLACE INTO bulk_companies VALUES (?,?,?)",
                     (cik, result["name"] or "", tickers.get(cik)))
        conn.executemany("INSERT OR REPLACE INTO bulk_facts VALUES (?,?,?,?,?)", rows_f)
        conn.executemany("INSERT OR REPLACE INTO bulk_quality VALUES (?,?,?,?,?,?)", rows_q)
        if n % 2000 == 0:
            conn.commit()
            rate = n / (time.time() - started)
            print(f"{n}/{len(names)} ({rate:.0f}/s), kept {companies_kept}, "
                  f"admitted years {years_admitted}", flush=True)
    conn.commit()
    total_years = conn.execute("SELECT COUNT(*) FROM bulk_quality").fetchone()[0]
    admitted = conn.execute("SELECT COUNT(*) FROM bulk_quality WHERE admitted=1").fetchone()[0]
    facts = conn.execute("SELECT COUNT(*) FROM bulk_facts").fetchone()[0]
    print(f"done in {time.time() - started:.0f}s: {companies_kept} companies, "
          f"{total_years} company-years ({admitted} admitted, "
          f"{100 * admitted / max(total_years, 1):.0f}%), {facts} facts -> {DB.name}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
