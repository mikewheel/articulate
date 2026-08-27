"""Content validation and DB loading.

The contract these functions enforce is docs/CONTENT_FORMAT.md. Everything
under content/ is validated together (cross-references included) before a
single row is written; a rebuild replaces content tables in one deferred-FK
transaction so player state survives.
"""

import json
from collections import defaultdict
from pathlib import Path

from . import CONTENT_DIR

BANDS = set("ABCDEFGH")
MODES = {"drill", "sudoku", "forge", "lineup", "forensics", "earnings_call", "daily"}
ITEM_TYPES = {
    "sort", "journal", "translate", "lexicon", "sudoku", "ratio_build",
    "ratio_interpret", "lineup_match", "forensic_case", "cfo_question",
    "daily_filing",
}
GRADERS = {"choice", "numeric", "grid", "mapping", "llm_rubric"}
LEVEL_IDS = ["L1", "L2", "L3", "L4", "L5", "L6", "L7"]

# Spec Appendix A, plus catch-all lines authors may need to make totals tie.
CANONICAL_ITEMS = {
    # income statement
    "revenue", "cost_of_revenue", "gross_profit", "sga", "rnd", "da",
    "operating_income", "interest_expense", "interest_income",
    "other_nonoperating", "pretax_income", "income_tax", "net_income",
    "net_income_to_common", "eps_diluted", "shares_diluted",
    # balance sheet
    "cash", "short_term_investments", "receivables", "inventory",
    "other_current_assets", "total_current_assets", "ppe_net",
    "operating_lease_rou", "goodwill", "intangibles", "deferred_tax_assets",
    "other_noncurrent_assets", "total_assets", "payables", "accrued",
    "deferred_revenue", "debt_current", "operating_lease_current",
    "total_current_liabilities", "debt_noncurrent",
    "operating_lease_noncurrent", "deferred_tax_liabilities",
    "other_noncurrent_liabilities", "total_liabilities", "common_and_apic",
    "retained_earnings", "aoci", "treasury_stock", "nci", "total_equity",
    # cash flow
    "cfo", "da_addback", "sbc", "working_capital_change", "capex",
    "acquisitions", "cfi", "debt_issued", "debt_repaid", "buybacks",
    "dividends", "cff", "fx_effect", "net_change_cash",
}


class ContentError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        preview = "\n".join(errors[:25])
        more = f"\n… and {len(errors) - 25} more" if len(errors) > 25 else ""
        super().__init__(f"{len(errors)} content error(s):\n{preview}{more}")


def _load_json(path: Path, errors: list[str]):
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        errors.append(f"{path.name}: cannot load ({e})")
        return None


def load_content(content_dir: Path = CONTENT_DIR) -> dict:
    """Read every content file, validate against the contract, return the
    bundle as plain dicts. Raises ContentError listing every problem found."""
    errors: list[str] = []
    bundle = {
        "concepts": _load_json(content_dir / "concepts.json", errors) or [],
        "levels": _load_json(content_dir / "levels.json", errors) or [],
        "companies": [],
        "facts": [],
        "items": [],
        "call_scenarios": [],
    }
    for path in sorted(content_dir.glob("companies_*.json")):
        bundle["companies"] += _load_json(path, errors) or []
    for path in sorted(content_dir.glob("facts_*.json")):
        bundle["facts"] += _load_json(path, errors) or []
    for path in sorted((content_dir / "items").glob("*.json")):
        loaded = _load_json(path, errors) or []
        for item in loaded:
            item.setdefault("_file", path.name)
        bundle["items"] += loaded
    scenarios_path = content_dir / "call_scenarios.json"
    if scenarios_path.exists():
        bundle["call_scenarios"] = _load_json(scenarios_path, errors) or []

    _validate(bundle, errors)
    if errors:
        raise ContentError(errors)
    return bundle


def _validate(b: dict, errors: list[str]) -> None:
    concept_ids = _validate_concepts(b["concepts"], errors)
    _validate_levels(b["levels"], errors)
    company_ids = _validate_companies(b["companies"], errors)
    _validate_facts(b["facts"], company_ids, errors)
    scenario_ids = _validate_scenarios(b["call_scenarios"], company_ids, errors)
    _validate_items(b["items"], concept_ids, scenario_ids, errors)


def _validate_concepts(concepts, errors) -> set:
    ids = set()
    for c in concepts:
        cid = c.get("id", "?")
        if cid in ids:
            errors.append(f"concept {cid}: duplicate id")
        ids.add(cid)
        if c.get("band") not in BANDS:
            errors.append(f"concept {cid}: bad band {c.get('band')!r}")
    for c in concepts:
        for p in c.get("prereqs", []):
            if p not in ids:
                errors.append(f"concept {c['id']}: unknown prereq {p!r}")
    # acyclicity via Kahn's algorithm
    indeg = {c["id"]: 0 for c in concepts}
    dependents = defaultdict(list)
    for c in concepts:
        for p in c.get("prereqs", []):
            if p in indeg:
                indeg[c["id"]] += 1
                dependents[p].append(c["id"])
    queue = [i for i, d in indeg.items() if d == 0]
    seen = 0
    while queue:
        node = queue.pop()
        seen += 1
        for d in dependents[node]:
            indeg[d] -= 1
            if indeg[d] == 0:
                queue.append(d)
    if seen != len(indeg):
        errors.append("concept graph has a cycle")
    return ids


def _validate_levels(levels, errors) -> None:
    found = [lv.get("id") for lv in levels]
    if sorted(found) != sorted(LEVEL_IDS):
        errors.append(f"levels.json: expected ids {LEVEL_IDS}, found {found}")
        return
    by_id = {lv["id"]: lv for lv in levels}
    for lv in levels:
        unlock = lv.get("unlock") or {}
        prereq = unlock.get("prereq_level")
        if prereq is not None and prereq not in by_id:
            errors.append(f"level {lv['id']}: unknown prereq_level {prereq!r}")
        if not lv.get("title") or not lv.get("narrative_intro"):
            errors.append(f"level {lv['id']}: missing title or narrative_intro")


def _validate_companies(companies, errors) -> set:
    ids = set()
    for co in companies:
        cid = co.get("id", "?")
        if cid in ids:
            errors.append(f"company {cid}: duplicate id")
        ids.add(cid)
        if co.get("kind") not in ("synthetic", "real"):
            errors.append(f"company {cid}: bad kind {co.get('kind')!r}")
    return ids


def _validate_facts(facts, company_ids, errors) -> None:
    seen = set()
    grouped = defaultdict(dict)  # (company, fy) -> {item: value}
    for f in facts:
        key = (f.get("company_id"), f.get("fiscal_year"), f.get("item"),
               f.get("basis", "as_filed"))
        if key in seen:
            errors.append(f"facts: duplicate row {key}")
        seen.add(key)
        if f.get("company_id") not in company_ids:
            errors.append(f"facts: unknown company {f.get('company_id')!r}")
        if f.get("item") not in CANONICAL_ITEMS:
            errors.append(f"facts: non-canonical item {f.get('item')!r} "
                          f"({f.get('company_id')} FY{f.get('fiscal_year')})")
        if not isinstance(f.get("value"), (int, float)):
            errors.append(f"facts: non-numeric value for {key}")
        else:
            grouped[(f["company_id"], f["fiscal_year"])][f["item"]] = f["value"]
    for (co, fy), vals in grouped.items():
        _check_identities(co, fy, vals, errors)


def _check_identities(co, fy, v, errors) -> None:
    label = f"{co} FY{fy}"
    a, l, e = v.get("total_assets"), v.get("total_liabilities"), v.get("total_equity")
    if a is not None and l is not None and e is not None:
        if abs(a - (l + e)) > max(0.005 * abs(a), 0.5):
            errors.append(f"{label}: balance sheet off (A={a}, L+E={l + e})")
    parts = [v.get(k) for k in ("cfo", "cfi", "cff")]
    if all(p is not None for p in parts) and v.get("net_change_cash") is not None:
        total = sum(parts) + (v.get("fx_effect") or 0.0)
        delta = v["net_change_cash"]
        if abs(total - delta) > max(0.01 * abs(delta), 1.0):
            errors.append(f"{label}: cash flow does not tie (sum={total}, Δcash={delta})")
    r, c, g = v.get("revenue"), v.get("cost_of_revenue"), v.get("gross_profit")
    if r is not None and c is not None and g is not None:
        if abs(g - (r - c)) > max(0.005 * abs(r), 0.5):
            errors.append(f"{label}: gross profit inconsistent (g={g}, r−c={r - c})")


def _validate_scenarios(scenarios, company_ids, errors) -> set:
    ids = set()
    for s in scenarios:
        sid = s.get("id", "?")
        ids.add(sid)
        if s.get("company_id") not in company_ids:
            errors.append(f"scenario {sid}: unknown company {s.get('company_id')!r}")
        if not isinstance(s.get("fact_sheet"), dict) or not s["fact_sheet"]:
            errors.append(f"scenario {sid}: fact_sheet must be a non-empty object")
        issues = s.get("hidden_issues")
        if not isinstance(issues, list) or not issues:
            errors.append(f"scenario {sid}: hidden_issues must be a non-empty list")
        else:
            for issue in issues:
                if not all(k in issue for k in ("id", "summary", "reveal_threshold")):
                    errors.append(f"scenario {sid}: malformed hidden issue")
    return ids


def _validate_items(items, concept_ids, scenario_ids, errors) -> None:
    seen = set()
    for it in items:
        iid = it.get("id", "?")
        where = f"{it.get('_file', '?')}:{iid}"
        if iid in seen:
            errors.append(f"{where}: duplicate item id")
        seen.add(iid)
        if it.get("mode") not in MODES:
            errors.append(f"{where}: bad mode {it.get('mode')!r}")
        if it.get("item_type") not in ITEM_TYPES:
            errors.append(f"{where}: bad item_type {it.get('item_type')!r}")
        if it.get("grader") not in GRADERS:
            errors.append(f"{where}: bad grader {it.get('grader')!r}")
            continue
        level = it.get("level_id")
        if level is not None and level not in LEVEL_IDS:
            errors.append(f"{where}: bad level_id {level!r}")
        if level is None and it.get("mode") != "daily":
            errors.append(f"{where}: only daily items may omit level_id")
        if not isinstance(it.get("difficulty"), int) or not 1 <= it["difficulty"] <= 5:
            errors.append(f"{where}: difficulty must be int 1..5")
        refs = it.get("concept_ids") or []
        if not refs:
            errors.append(f"{where}: no concept_ids")
        for cid in refs:
            if cid not in concept_ids:
                errors.append(f"{where}: unknown concept {cid!r}")
        for h in it.get("hints", []):
            if "text" not in h:
                errors.append(f"{where}: hint missing text")
            if h.get("concept_id") is not None and h["concept_id"] not in concept_ids:
                errors.append(f"{where}: hint references unknown concept {h['concept_id']!r}")
        payload, key = it.get("payload") or {}, it.get("answer_key") or {}
        checker = _PAYLOAD_CHECKS.get(it.get("grader"))
        if checker:
            checker(where, payload, key, errors)
        if it.get("item_type") == "cfo_question":
            if payload.get("scenario_id") not in scenario_ids:
                errors.append(f"{where}: unknown scenario_id {payload.get('scenario_id')!r}")


def _check_choice(where, payload, key, errors):
    choices = payload.get("choices")
    if not isinstance(choices, list) or len(choices) < 2:
        errors.append(f"{where}: choice needs >=2 choices")
        return
    idx = key.get("correct_index")
    if not isinstance(idx, int) or not 0 <= idx < len(choices):
        errors.append(f"{where}: correct_index out of range")
    why = key.get("why_wrong")
    if why is not None and len(why) != len(choices):
        errors.append(f"{where}: why_wrong length != choices length")
    if not payload.get("prompt"):
        errors.append(f"{where}: missing prompt")


def _check_numeric(where, payload, key, errors):
    if not payload.get("prompt"):
        errors.append(f"{where}: missing prompt")
    if not isinstance(key.get("value"), (int, float)):
        errors.append(f"{where}: numeric answer_key.value missing")
    if key.get("tolerance_abs") is None and key.get("tolerance_rel") is None:
        errors.append(f"{where}: numeric needs a tolerance")


def _check_grid(where, payload, key, errors):
    statements = payload.get("statements")
    if not isinstance(statements, list) or not statements:
        errors.append(f"{where}: grid needs statements")
        return
    keys, blanks = [], set()
    for st in statements:
        for row in st.get("rows", []):
            keys.append(row.get("key"))
            if row.get("blank"):
                blanks.add(row.get("key"))
                if row.get("value") is not None:
                    errors.append(f"{where}: blank row {row.get('key')!r} has a value")
            elif not isinstance(row.get("value"), (int, float)):
                errors.append(f"{where}: visible row {row.get('key')!r} lacks a numeric value")
    if len(keys) != len(set(keys)):
        errors.append(f"{where}: duplicate row keys")
    cells = key.get("cells") or {}
    if set(cells) != blanks:
        errors.append(f"{where}: answer_key.cells {sorted(cells)} != blanks {sorted(blanks)}")
    if not blanks:
        errors.append(f"{where}: grid has no blanks")
    for k, val in cells.items():
        if not isinstance(val, (int, float)):
            errors.append(f"{where}: cell {k!r} answer not numeric")
    if not isinstance(key.get("tolerance_abs"), (int, float)):
        errors.append(f"{where}: grid needs tolerance_abs")


def _check_mapping(where, payload, key, errors):
    left, right = payload.get("left"), payload.get("right")
    if not isinstance(left, list) or not isinstance(right, list) or not left or not right:
        errors.append(f"{where}: mapping needs left and right lists")
        return
    left_keys = [entry.get("key") for entry in left]
    mapping = key.get("map") or {}
    if set(mapping) != set(left_keys):
        errors.append(f"{where}: map keys != left keys")
    for k, v in mapping.items():
        if not isinstance(v, int) or not 0 <= v < len(right):
            errors.append(f"{where}: map[{k!r}] out of range")
    if len(set(mapping.values())) != len(mapping):
        errors.append(f"{where}: map assigns one label twice")


def _check_rubric(where, payload, key, errors):
    if not payload.get("prompt"):
        errors.append(f"{where}: missing prompt")
    if not key.get("model_answer"):
        errors.append(f"{where}: llm_rubric needs model_answer")
    rubric = key.get("rubric")
    if not isinstance(rubric, list) or not rubric:
        errors.append(f"{where}: llm_rubric needs rubric list")
        return
    total = 0
    for entry in rubric:
        if not all(k in entry for k in ("id", "points", "description")):
            errors.append(f"{where}: malformed rubric entry")
        total += entry.get("points") or 0
    pass_points = key.get("pass_points")
    if not isinstance(pass_points, (int, float)) or pass_points > total:
        errors.append(f"{where}: pass_points missing or exceeds rubric total {total}")


_PAYLOAD_CHECKS = {
    "choice": _check_choice,
    "numeric": _check_numeric,
    "grid": _check_grid,
    "mapping": _check_mapping,
    "llm_rubric": _check_rubric,
}


# ------------------------------------------------------------------ loading --

def load_into_db(conn, bundle: dict) -> dict:
    """Replace content tables with the validated bundle. Returns row counts."""
    from .db import clear_content
    conn.execute("PRAGMA defer_foreign_keys = ON")
    clear_content(conn)

    for c in bundle["concepts"]:
        conn.execute(
            "INSERT INTO concepts (id, name, band, cfa, description) VALUES (?,?,?,?,?)",
            (c["id"], c["name"], c["band"], c.get("cfa"), c.get("description", "")))
    for c in bundle["concepts"]:
        for p in c.get("prereqs", []):
            conn.execute(
                "INSERT INTO concept_prereqs (concept_id, prereq_id) VALUES (?,?)",
                (c["id"], p))

    for lv in sorted(bundle["levels"], key=lambda x: x["ordinal"]):
        unlock = lv.get("unlock") or {}
        conn.execute(
            """INSERT INTO levels (id, ordinal, band, title, tagline,
               narrative_intro, narrative_outro, prereq_level_id, min_mastery)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (lv["id"], lv["ordinal"], lv["band"], lv["title"],
             lv.get("tagline", ""), lv.get("narrative_intro", ""),
             lv.get("narrative_outro", ""), unlock.get("prereq_level"),
             unlock.get("min_mastery", 0.6)))

    for co in bundle["companies"]:
        conn.execute(
            """INSERT INTO companies (id, name, ticker, cik, kind, industry,
               sic, fye_month, description) VALUES (?,?,?,?,?,?,?,?,?)""",
            (co["id"], co["name"], co.get("ticker"), co.get("cik"), co["kind"],
             co.get("industry"), co.get("sic"), co.get("fye_month"),
             co.get("description", "")))

    for f in bundle["facts"]:
        conn.execute(
            """INSERT INTO facts (company_id, fiscal_year, period_end, item,
               value, unit, basis, source_tag, source_form, source_accession)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (f["company_id"], f["fiscal_year"], f.get("period_end"), f["item"],
             f["value"], f.get("unit", "USD_millions"),
             f.get("basis", "as_filed"), f.get("source_tag"),
             f.get("source_form"), f.get("source_accession")))

    for s in bundle["call_scenarios"]:
        conn.execute(
            """INSERT INTO call_scenarios (id, company_id, cfo_name,
               cfo_persona, fact_sheet, hidden_issues, max_questions)
               VALUES (?,?,?,?,?,?,?)""",
            (s["id"], s["company_id"], s["cfo_name"], s["cfo_persona"],
             json.dumps(s["fact_sheet"]), json.dumps(s["hidden_issues"]),
             s.get("max_questions", 5)))

    for it in bundle["items"]:
        conn.execute(
            """INSERT INTO items (id, mode, item_type, level_id, ordinal,
               difficulty, grader, payload, answer_key, explanation)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (it["id"], it["mode"], it["item_type"], it.get("level_id"),
             it.get("ordinal", 0), it["difficulty"], it["grader"],
             json.dumps(it["payload"]), json.dumps(it["answer_key"]),
             it.get("explanation", "")))
        for cid in it.get("concept_ids", []):
            conn.execute(
                "INSERT INTO item_concepts (item_id, concept_id) VALUES (?,?)",
                (it["id"], cid))
        for n, h in enumerate(it.get("hints", [])):
            conn.execute(
                "INSERT INTO item_hints (item_id, ordinal, concept_id, text) VALUES (?,?,?,?)",
                (it["id"], n, h.get("concept_id"), h["text"]))

    conn.commit()
    counts = {}
    for table in ("concepts", "levels", "companies", "facts", "items", "call_scenarios"):
        counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    return counts
