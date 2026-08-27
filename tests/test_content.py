"""Contract tests over the real content/ directory, plus loader behavior."""

import json

import pytest

from articulate import CONTENT_DIR
from articulate.content import (CANONICAL_ITEMS, ContentError, load_content,
                                load_into_db)

CONTENT_READY = (CONTENT_DIR / "levels.json").exists()
needs_content = pytest.mark.skipif(not CONTENT_READY,
                                   reason="content/ not fully authored yet")


@pytest.fixture(scope="module")
def bundle():
    return load_content()


@needs_content
def test_content_validates(bundle):
    assert len(bundle["concepts"]) >= 40
    assert len(bundle["levels"]) == 7
    assert len(bundle["items"]) >= 60


@needs_content
def test_concept_graph_acyclic_and_bands(bundle):
    # load_content already raises on cycles; sanity-check bands present
    bands = {c["band"] for c in bundle["concepts"]}
    assert {"A", "B", "C", "D", "E", "F"} <= bands


@needs_content
def test_every_level_has_items(bundle):
    by_level = {}
    for item in bundle["items"]:
        if item.get("level_id"):
            by_level.setdefault(item["level_id"], []).append(item)
    for level_id in ("L1", "L2", "L3", "L4", "L5", "L6"):  # extend as L7 items land
        assert len(by_level.get(level_id, [])) >= 5, f"{level_id} is underpopulated"


@needs_content
def test_facts_are_canonical_and_identities_hold(bundle):
    # identity checks run inside load_content; assert facts exist for both kinds
    kinds = {c["kind"] for c in bundle["companies"]}
    assert kinds == {"synthetic", "real"}
    for f in bundle["facts"]:
        assert f["item"] in CANONICAL_ITEMS


@needs_content
def test_loader_roundtrip_and_player_state_survives(db, bundle):
    counts = load_into_db(db, bundle)
    assert counts["items"] == len(bundle["items"])
    # create player state, rebuild, confirm it survives
    db.execute("INSERT INTO players (id, handle) VALUES (9, 'keeper')")
    item_id = bundle["items"][0]["id"]
    db.execute("""INSERT INTO attempts (player_id, item_id, submitted, score, max_score,
                  correct, feedback, grader_source)
                  VALUES (9, ?, '{}', 1, 1, 1, '{}', 'deterministic')""", (item_id,))
    db.commit()
    load_into_db(db, bundle)
    assert db.execute("SELECT COUNT(*) FROM attempts WHERE player_id=9").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM items").fetchone()[0] == len(bundle["items"])


def test_validator_rejects_bad_content(tmp_path):
    (tmp_path / "items").mkdir()
    (tmp_path / "concepts.json").write_text(json.dumps([
        {"id": "a", "name": "A", "band": "A", "prereqs": ["b"]},
        {"id": "b", "name": "B", "band": "Z", "prereqs": ["a"]},
    ]))
    (tmp_path / "levels.json").write_text("[]")
    with pytest.raises(ContentError) as excinfo:
        load_content(tmp_path)
    text = str(excinfo.value)
    assert "bad band" in text and "cycle" in text and "expected ids" in text


def test_validator_rejects_untied_balance_sheet(tmp_path):
    (tmp_path / "items").mkdir()
    (tmp_path / "concepts.json").write_text("[]")
    (tmp_path / "levels.json").write_text("[]")
    (tmp_path / "companies_x.json").write_text(json.dumps([
        {"id": "co", "name": "Co", "kind": "synthetic"}]))
    (tmp_path / "facts_x.json").write_text(json.dumps([
        {"company_id": "co", "fiscal_year": 2024, "item": "total_assets", "value": 100.0},
        {"company_id": "co", "fiscal_year": 2024, "item": "total_liabilities", "value": 40.0},
        {"company_id": "co", "fiscal_year": 2024, "item": "total_equity", "value": 50.0},
    ]))
    with pytest.raises(ContentError) as excinfo:
        load_content(tmp_path)
    assert "balance sheet off" in str(excinfo.value)
