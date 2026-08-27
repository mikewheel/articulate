import json

import pytest
from fastapi.testclient import TestClient

from articulate.db import connect, init_schema


@pytest.fixture
def client(tmp_path):
    path = tmp_path / "api.db"
    conn = connect(path)
    init_schema(conn)
    conn.execute("INSERT INTO concepts (id, name, band) VALUES ('c1', 'C1', 'A')")
    conn.execute("INSERT INTO levels (id, ordinal, band, title, tagline, narrative_intro) "
                 "VALUES ('L1', 1, 'A', 'Week One', 'tag', 'intro text')")
    conn.execute("INSERT INTO levels (id, ordinal, band, title, prereq_level_id, min_mastery) "
                 "VALUES ('L2', 2, 'B', 'Week Two', 'L1', 0.6)")
    conn.execute("""INSERT INTO items (id, mode, item_type, level_id, ordinal, difficulty,
                    grader, payload, answer_key, explanation)
                    VALUES ('i1', 'drill', 'sort', 'L1', 10, 1, 'choice',
                    '{"prompt": "p", "choices": ["a", "b"]}',
                    '{"correct_index": 1, "why_wrong": ["because", null]}', 'so what')""")
    conn.execute("INSERT INTO item_concepts (item_id, concept_id) VALUES ('i1', 'c1')")
    conn.execute("INSERT INTO item_hints (item_id, ordinal, text) VALUES ('i1', 0, 'think position vs flow')")
    conn.execute("INSERT INTO companies (id, name, kind) VALUES ('co', 'Co', 'synthetic')")
    conn.execute("""INSERT INTO call_scenarios (id, company_id, cfo_name, cfo_persona,
                    fact_sheet, hidden_issues, max_questions) VALUES
                    ('call1', 'co', 'Pat', 'evasive',
                     '{"revenue_fy3": 1180.0}',
                     '[{"id": "iss1", "summary": "extended payment terms to distributors",
                        "reveal_threshold": "asks about payment terms"}]', 2)""")
    conn.commit()
    conn.close()

    from articulate.app import app
    app.state.db_path = path
    with TestClient(app) as tc:
        yield tc
    del app.state.db_path


def test_state_creates_player(client):
    out = client.get("/api/state", params={"player": "mike"}).json()
    assert out["handle"] == "mike"
    assert out["levels"][0]["unlocked"] is True
    assert out["levels"][1]["unlocked"] is False
    assert out["llm"] in ("mock", "live")


def test_level_never_leaks_answer_key(client):
    out = client.get("/api/level/L1", params={"player": "mike"}).json()
    text = json.dumps(out)
    assert "answer_key" not in text
    assert "correct_index" not in text
    assert "why_wrong" not in text
    assert out["items"][0]["payload"]["choices"] == ["a", "b"]


def test_locked_level_denied(client):
    res = client.get("/api/level/L2", params={"player": "mike"})
    assert res.status_code == 403


def test_hint_endpoint(client):
    assert client.get("/api/item/i1/hint/0").json()["text"] == "think position vs flow"
    assert client.get("/api/item/i1/hint/1").status_code == 404


def test_attempt_flow_updates_mastery(client):
    out = client.post("/api/attempt", json={
        "player": "mike", "item_id": "i1", "submitted": {"index": 1}}).json()
    assert out["result"]["correct"] is True
    assert out["explanation"] == "so what"
    assert out["mastery"]["c1"] > 0
    wrong = client.post("/api/attempt", json={
        "player": "mike", "item_id": "i1", "submitted": {"index": 0}}).json()
    assert wrong["result"]["correct"] is False
    assert wrong["result"]["feedback"]["why_wrong"] == "because"


def test_call_flow_and_question_budget(client):
    first = client.post("/api/call/call1/ask", json={
        "player": "mike", "question": "Did you extend payment terms to distributors?"}).json()
    assert first["questions_remaining"] == 1
    assert first["reply"]
    client.post("/api/call/call1/ask", json={"player": "mike", "question": "Anything else?"})
    over = client.post("/api/call/call1/ask", json={"player": "mike", "question": "One more?"})
    assert over.status_code == 409
    debrief = client.get("/api/call/call1/debrief", params={"player": "mike"}).json()
    assert debrief["issues"][0]["uncovered"] is True
    assert debrief["coverage"] == 1.0


def test_debrief_blocked_while_live(client):
    res = client.get("/api/call/call1/debrief", params={"player": "mike"})
    assert res.status_code == 409
