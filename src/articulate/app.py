"""Local game server: FastAPI + static frontend.

Run:  .venv/bin/uvicorn articulate.app:app --app-dir src --reload
Game integrity: answer keys, why_wrong, tells, and hidden issues never leave
the server; hints are fetched one at a time and counted.
"""

import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import DB_PATH, WEB_DIR
from .db import connect
from .graders import grade, parse_item_row
from .llm import get_client, make_judge
from .mastery import level_states, schedule_review, update_mastery

app = FastAPI(title="Articulate (local)")

_llm = get_client()
_judge = make_judge(_llm)


def db():
    path = app.state.db_path if hasattr(app.state, "db_path") else DB_PATH
    if not path.exists():
        raise HTTPException(500, "articulate.db missing — run scripts/build_db.py")
    return connect(path)


def get_player(conn, handle: str) -> int:
    row = conn.execute("SELECT id FROM players WHERE handle=?", (handle,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO players (handle) VALUES (?)", (handle,))
    conn.commit()
    return cur.lastrowid


def public_item(row, conn) -> dict:
    item = parse_item_row(row)
    hints = conn.execute(
        "SELECT COUNT(*) FROM item_hints WHERE item_id=?", (item["id"],)).fetchone()[0]
    return {
        "id": item["id"], "mode": item["mode"], "item_type": item["item_type"],
        "ordinal": item["ordinal"], "difficulty": item["difficulty"],
        "grader": item["grader"], "payload": item["payload"], "hint_count": hints,
    }


@app.get("/api/state")
def state(player: str):
    conn = db()
    try:
        pid = get_player(conn, player)
        levels = level_states(conn, pid)
        llm_mode = "live" if _llm.source == "llm" else "mock"
        daily = conn.execute(
            "SELECT COUNT(*) FROM items WHERE mode='daily'").fetchone()[0]
        return {"player_id": pid, "handle": player, "levels": levels,
                "daily_items": daily, "llm": llm_mode}
    finally:
        conn.close()


@app.get("/api/level/{level_id}")
def level(level_id: str, player: str):
    conn = db()
    try:
        pid = get_player(conn, player)
        meta = conn.execute("SELECT * FROM levels WHERE id=?", (level_id,)).fetchone()
        if meta is None:
            raise HTTPException(404, "no such level")
        states = level_states(conn, pid)
        mine = next(s for s in states if s["id"] == level_id)
        if not mine["unlocked"]:
            raise HTTPException(403, "level locked — master the previous level first")
        rows = conn.execute(
            "SELECT * FROM items WHERE level_id=? ORDER BY ordinal", (level_id,)).fetchall()
        items = [public_item(r, conn) for r in rows]
        attempts = conn.execute(
            """SELECT item_id, MAX(correct) AS best FROM attempts
               WHERE player_id=? AND item_id IN
               (SELECT id FROM items WHERE level_id=?) GROUP BY item_id""",
            (pid, level_id)).fetchall()
        progress = {a["item_id"]: bool(a["best"]) for a in attempts}
        return {"level": dict(meta), "state": mine, "items": items, "progress": progress}
    finally:
        conn.close()


@app.get("/api/daily")
def daily(player: str):
    conn = db()
    try:
        get_player(conn, player)
        rows = conn.execute(
            "SELECT * FROM items WHERE mode='daily' ORDER BY ordinal").fetchall()
        return {"items": [public_item(r, conn) for r in rows]}
    finally:
        conn.close()


@app.get("/api/item/{item_id}/hint/{n}")
def hint(item_id: str, n: int):
    conn = db()
    try:
        row = conn.execute(
            "SELECT text FROM item_hints WHERE item_id=? AND ordinal=?",
            (item_id, n)).fetchone()
        if row is None:
            raise HTTPException(404, "no more hints")
        return {"text": row["text"], "ordinal": n}
    finally:
        conn.close()


class AttemptIn(BaseModel):
    player: str
    item_id: str
    submitted: dict
    hints_used: int = 0


@app.post("/api/attempt")
def attempt(body: AttemptIn):
    conn = db()
    try:
        pid = get_player(conn, body.player)
        row = conn.execute("SELECT * FROM items WHERE id=?", (body.item_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "no such item")
        item = parse_item_row(row)
        result = grade(item, body.submitted, judge=_judge)
        conn.execute(
            """INSERT INTO attempts (player_id, item_id, submitted, score, max_score,
               correct, feedback, grader_source, hints_used)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (pid, body.item_id, json.dumps(body.submitted), result["score"],
             result["max_score"], int(result["correct"]),
             json.dumps(result["feedback"]), result["grader_source"],
             body.hints_used))
        ratio = result["score"] / result["max_score"] if result["max_score"] else 0.0
        if body.hints_used:
            ratio *= max(0.5, 1 - 0.15 * body.hints_used)
        mastery = update_mastery(conn, pid, body.item_id, ratio)
        schedule_review(conn, pid, body.item_id, result["correct"])
        conn.commit()
        return {"result": result, "explanation": item["explanation"],
                "mastery": mastery, "levels": level_states(conn, pid)}
    finally:
        conn.close()


class AskIn(BaseModel):
    player: str
    question: str


@app.post("/api/call/{scenario_id}/ask")
def call_ask(scenario_id: str, body: AskIn):
    conn = db()
    try:
        pid = get_player(conn, body.player)
        row = conn.execute(
            "SELECT * FROM call_scenarios WHERE id=?", (scenario_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "no such scenario")
        scenario = dict(row)
        scenario["fact_sheet"] = json.loads(scenario["fact_sheet"])
        scenario["hidden_issues"] = json.loads(scenario["hidden_issues"])
        asked = conn.execute(
            """SELECT COUNT(*) FROM call_transcripts
               WHERE player_id=? AND scenario_id=? AND role='analyst'""",
            (pid, scenario_id)).fetchone()[0]
        if asked >= scenario["max_questions"]:
            raise HTTPException(409, "the call is over — no questions left")
        transcript = [dict(t) for t in conn.execute(
            """SELECT role, content FROM call_transcripts
               WHERE player_id=? AND scenario_id=? ORDER BY turn""",
            (pid, scenario_id)).fetchall()]
        reply = _llm.cfo_reply(scenario, transcript, body.question)
        turn = len(transcript)
        conn.execute(
            """INSERT INTO call_transcripts (player_id, scenario_id, turn, role, content, issues_hit)
               VALUES (?,?,?,?,?,?)""",
            (pid, scenario_id, turn, "analyst", body.question,
             json.dumps(reply["issues_hit"])))
        conn.execute(
            """INSERT INTO call_transcripts (player_id, scenario_id, turn, role, content, issues_hit)
               VALUES (?,?,?,?,?,'[]')""",
            (pid, scenario_id, turn + 1, "cfo", reply["reply"]))
        conn.commit()
        remaining = scenario["max_questions"] - asked - 1
        return {"reply": reply["reply"], "questions_remaining": remaining,
                "cfo_name": scenario["cfo_name"], "llm": reply["source"]}
    finally:
        conn.close()


@app.get("/api/call/{scenario_id}/debrief")
def call_debrief(scenario_id: str, player: str):
    """Coverage summary, revealed once the questions are spent."""
    conn = db()
    try:
        pid = get_player(conn, player)
        row = conn.execute(
            "SELECT * FROM call_scenarios WHERE id=?", (scenario_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "no such scenario")
        issues = json.loads(row["hidden_issues"])
        rows = conn.execute(
            """SELECT issues_hit FROM call_transcripts
               WHERE player_id=? AND scenario_id=? AND role='analyst'""",
            (pid, scenario_id)).fetchall()
        asked = len(rows)
        if asked < row["max_questions"]:
            raise HTTPException(409, "the call is still live")
        hit = set()
        for r in rows:
            hit.update(json.loads(r["issues_hit"]))
        return {"cfo_name": row["cfo_name"],
                "issues": [{"id": i["id"], "summary": i["summary"],
                            "uncovered": i["id"] in hit} for i in issues],
                "coverage": len(hit) / len(issues) if issues else 0.0}
    finally:
        conn.close()


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
