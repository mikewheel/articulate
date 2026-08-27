#!/usr/bin/env python
"""Generate a year of Daily Filing items from the bulk store.

Draws from data/edgar_bulk.db (admitted company-years only), fetches SIC codes
for the candidate pool from the EDGAR submissions API (cached, rate-limited,
proper User-Agent), computes clue stats + pool percentiles, and writes
content/items/daily_generated.json — 365 deterministic items that /api/daily
rotates through by calendar date alongside the authored dailies.

Usage: .venv/bin/python scripts/gen_daily.py
"""

import json
import random
import sqlite3
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "edgar_bulk.db"
SIC_CACHE = ROOT / "data" / "sic_cache.json"
OUT = ROOT / "content" / "items" / "daily_generated.json"
USER_AGENT = "Articulate/0.1 (contact: mbw@mbw.dev)"
SEED = 20260827
POOL_MIN_REVENUE = 2_000.0   # $2B — recognizable names
POOL_SIZE = 420
N_ITEMS = 365

SIC_DIVISIONS = [
    (100, 999, "agriculture"), (1000, 1499, "mining and energy extraction"),
    (1500, 1799, "construction"), (2000, 3999, "manufacturing"),
    (4000, 4899, "transportation and logistics"), (4900, 4999, "utilities"),
    (5000, 5199, "wholesale distribution"), (5200, 5999, "retail"),
    (6000, 6799, "finance, insurance, or real estate"), (7000, 8999, "services"),
]


def sic_division(sic):
    if sic is None:
        return "an unclassified industry"
    for lo, hi, name in SIC_DIVISIONS:
        if lo <= sic <= hi:
            return name
    return "an unclassified industry"


def load_pool(conn):
    rows = conn.execute("""
        SELECT c.cik, c.name, c.ticker, q.period_end, q.fiscal_year
        FROM bulk_companies c
        JOIN bulk_quality q ON q.cik = c.cik AND q.admitted = 1
        WHERE c.ticker IS NOT NULL
          AND q.period_end = (SELECT MAX(period_end) FROM bulk_quality q2
                              WHERE q2.cik = c.cik AND q2.admitted = 1)
    """).fetchall()
    pool = []
    for cik, name, ticker, end, fy in rows:
        facts = dict(conn.execute(
            "SELECT item, value FROM bulk_facts WHERE cik=? AND period_end=?",
            (cik, end)))
        if facts.get("revenue", 0) < POOL_MIN_REVENUE:
            continue
        prior = conn.execute(
            """SELECT q.period_end FROM bulk_quality q WHERE q.cik=? AND q.admitted=1
               AND q.period_end < ? ORDER BY q.period_end DESC LIMIT 1""",
            (cik, end)).fetchone()
        prior_facts = dict(conn.execute(
            "SELECT item, value FROM bulk_facts WHERE cik=? AND period_end=?",
            (cik, prior[0]))) if prior else {}
        pool.append({"cik": cik, "name": name.strip(), "ticker": ticker,
                     "period_end": end, "fiscal_year": fy,
                     "f": facts, "prior": prior_facts})
    pool.sort(key=lambda x: -x["f"]["revenue"])
    return pool[:POOL_SIZE]


def fetch_sics(pool):
    cache = json.loads(SIC_CACHE.read_text()) if SIC_CACHE.exists() else {}
    client = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30,
                          follow_redirects=True)
    fetched = 0
    for company in pool:
        key = str(company["cik"])
        if key not in cache:
            try:
                resp = client.get(
                    f"https://data.sec.gov/submissions/CIK{company['cik']:010d}.json")
                resp.raise_for_status()
                data = resp.json()
                cache[key] = {"sic": int(data["sic"]) if data.get("sic") else None,
                              "sic_desc": data.get("sicDescription")}
                fetched += 1
                time.sleep(0.12)
            except Exception:
                cache[key] = {"sic": None, "sic_desc": None}
        company["sic"] = cache[key]["sic"]
        company["sic_desc"] = cache[key]["sic_desc"]
    SIC_CACHE.write_text(json.dumps(cache))
    if fetched:
        print(f"fetched SIC for {fetched} companies")


def pct(value, values):
    below = sum(1 for v in values if v < value)
    return round(100 * below / max(len(values) - 1, 1))


def ratio(f, num, den):
    if f.get(den) and f.get(num) is not None and f[den] != 0:
        return f[num] / f[den]
    return None


def scale_bucket(revenue):
    for hi, label in ((5_000, "between $2B and $5B"), (20_000, "between $5B and $20B"),
                      (75_000, "between $20B and $75B"), (10**9, "above $75B")):
        if revenue < hi:
            return label


def build_clues(company, pool):
    f, prior = company["f"], company["prior"]
    gm_pool = [x for x in (ratio(c["f"], "gross_profit", "revenue") for c in pool) if x is not None]
    ppe_pool = [x for x in (ratio(c["f"], "ppe_net", "total_assets") for c in pool) if x is not None]
    clues = [
        f"A US filer in {sic_division(company['sic'])}; revenue {scale_bucket(f['revenue'])}; "
        f"fiscal year ends in month {int(company['period_end'][5:7])}."]
    gm = ratio(f, "gross_profit", "revenue")
    nm = ratio(f, "net_income", "revenue")
    line2 = []
    if gm is not None:
        line2.append(f"gross margin {gm * 100:.0f}% ({pct(gm, gm_pool)}th percentile of large filers)")
    elif "cost_of_revenue" not in f:
        line2.append("reports no cost-of-goods line at all")
    if nm is not None:
        line2.append(f"net margin {nm * 100:.1f}%")
    clues.append("Margins: " + "; ".join(line2) + "." if line2 else "Margins: undisclosed.")
    shape = []
    ppe = ratio(f, "ppe_net", "total_assets")
    if ppe is not None:
        shape.append(f"PP&E is {ppe * 100:.0f}% of assets ({pct(ppe, ppe_pool)}th pct)")
    if f.get("inventory"):
        shape.append(f"inventory {ratio(f, 'inventory', 'total_assets') * 100:.0f}% of assets")
    else:
        shape.append("carries no inventory")
    if f.get("goodwill"):
        shape.append(f"goodwill {ratio(f, 'goodwill', 'total_assets') * 100:.0f}% of assets")
    clues.append("Balance-sheet shape: " + "; ".join(shape) + ".")
    cash = []
    if f.get("net_income") and f.get("cfo") is not None and f["net_income"] != 0:
        cash.append(f"CFO is {f['cfo'] / f['net_income']:.1f}x net income")
    if f.get("capex") is not None and f.get("revenue"):
        cash.append(f"capex {abs(f['capex']) / f['revenue'] * 100:.0f}% of revenue")
    if f.get("rnd") and f.get("revenue"):
        cash.append(f"R&D {f['rnd'] / f['revenue'] * 100:.0f}% of revenue")
    clues.append("Cash and spend: " + ("; ".join(cash) + "." if cash else "undisclosed."))
    if prior.get("revenue"):
        growth = (f["revenue"] / prior["revenue"] - 1) * 100
        clues.append(f"Revenue growth vs prior year: {growth:+.0f}%; "
                     f"equity is {'negative' if f.get('total_equity', 1) < 0 else 'positive'}.")
    else:
        clues.append(f"Total assets ${f['total_assets'] / 1000:.0f}B; "
                     f"equity is {'negative' if f.get('total_equity', 1) < 0 else 'positive'}.")
    clues.append(f"Final clue: SEC classifies it under '{company['sic_desc'] or 'n/a'}'; "
                 f"FY{company['fiscal_year']} revenue ${f['revenue'] / 1000:.1f}B.")
    return clues


def pick_decoys(company, pool, rng):
    same_division = [c for c in pool if c is not company
                    and sic_division(c["sic"]) == sic_division(company["sic"])]
    similar_size = sorted((c for c in pool if c is not company),
                          key=lambda c: abs(c["f"]["revenue"] - company["f"]["revenue"]))
    decoys, seen = [], {company["name"]}
    for source in (same_division, similar_size[:30]):
        rng.shuffle(source)
        for c in source:
            if c["name"] not in seen and len(decoys) < 3:
                decoys.append(c)
                seen.add(c["name"])
    return decoys[:3]


def why_wrong_for(decoy, company):
    d, f = decoy["f"], company["f"]
    d_gm, gm = ratio(d, "gross_profit", "revenue"), ratio(f, "gross_profit", "revenue")
    if d_gm is not None and gm is not None and abs(d_gm - gm) > 0.08:
        return (f"{decoy['name']} runs a {d_gm * 100:.0f}% gross margin — "
                f"the margin clue points elsewhere.")
    if abs(d["revenue"] - f["revenue"]) / f["revenue"] > 0.4:
        return (f"{decoy['name']}'s revenue is ${d['revenue'] / 1000:.0f}B — "
                f"the wrong size for the scale clue.")
    return (f"{decoy['name']} is classified under "
            f"'{decoy['sic_desc'] or 'a different industry'}' — the final clue rules it out.")


def main() -> int:
    if not DB.exists():
        print("run scripts/build_bulk.py first", file=sys.stderr)
        return 1
    conn = sqlite3.connect(DB)
    pool = load_pool(conn)
    print(f"pool: {len(pool)} companies with revenue >= ${POOL_MIN_REVENUE / 1000:.0f}B")
    fetch_sics(pool)
    rng = random.Random(SEED)
    picks = rng.sample(pool, min(N_ITEMS, len(pool)))
    items = []
    for n, company in enumerate(picks):
        decoys = pick_decoys(company, pool, rng)
        if len(decoys) < 3:
            continue
        options = [company] + decoys
        rng.shuffle(options)
        correct = options.index(company)
        why = [None if c is company else why_wrong_for(c, company) for c in options]
        clues = build_clues(company, pool)
        items.append({
            "id": f"daily_gen_{n:03d}",
            "mode": "daily", "item_type": "daily_filing", "level_id": None,
            "ordinal": 1000 + n, "concept_ids": ["industry_patterns", "common_size"],
            "difficulty": 3, "grader": "choice",
            "payload": {
                "prompt": "Which company is this?",
                "context": "\n".join(f"Clue {i + 1}: {c}" for i, c in enumerate(clues)),
                "choices": [c["name"] for c in options],
            },
            "answer_key": {"correct_index": correct, "why_wrong": why},
            "hints": [{"concept_id": "industry_patterns",
                       "text": "Read the balance-sheet shape before the margins: it narrows the industry fastest."}],
            "explanation": (f"{company['name']} ({company['ticker']}), FY ending "
                            f"{company['period_end']}. Generated from SEC bulk company "
                            f"facts; stats computed against a pool of {len(pool)} large filers."),
        })
    OUT.write_text(json.dumps(items, indent=1))
    print(f"wrote {len(items)} generated dailies -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
