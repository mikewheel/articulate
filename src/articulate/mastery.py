"""Mastery tracking and level unlocking.

Simplified stand-in for the spec's Glicko-2 + FSRS learner model (§6): each
concept holds an EMA of attempt scores in [0,1]. A level unlocks when its
prerequisite level's concepts average >= min_mastery AND every item in the
prerequisite level has been attempted at least once. Documented trade-off in
docs/DATA_MODEL.md §4-5.
"""

from datetime import datetime, timedelta, timezone

EMA_K = 0.35
FIRST_ATTEMPT_WEIGHT = 0.6  # first signal moves further than the steady state


def update_mastery(conn, player_id: int, item_id: str, score_ratio: float) -> dict:
    """Apply one attempt's score to every concept the item exercises."""
    now = datetime.now(timezone.utc).isoformat()
    updated = {}
    rows = conn.execute(
        "SELECT concept_id FROM item_concepts WHERE item_id = ?", (item_id,)
    ).fetchall()
    for row in rows:
        cid = row["concept_id"]
        current = conn.execute(
            "SELECT mastery, attempts FROM concept_mastery WHERE player_id=? AND concept_id=?",
            (player_id, cid)).fetchone()
        if current is None:
            mastery = FIRST_ATTEMPT_WEIGHT * score_ratio
            attempts = 1
            conn.execute(
                """INSERT INTO concept_mastery
                   (player_id, concept_id, mastery, attempts, last_attempt_at)
                   VALUES (?,?,?,?,?)""",
                (player_id, cid, mastery, attempts, now))
        else:
            mastery = current["mastery"] + EMA_K * (score_ratio - current["mastery"])
            mastery = min(1.0, max(0.0, mastery))
            attempts = current["attempts"] + 1
            conn.execute(
                """UPDATE concept_mastery SET mastery=?, attempts=?, last_attempt_at=?
                   WHERE player_id=? AND concept_id=?""",
                (mastery, attempts, now, player_id, cid))
        updated[cid] = round(mastery, 4)
    return updated


def schedule_review(conn, player_id: int, item_id: str, correct: bool) -> None:
    """SM-2-flavored scheduling: drives the 'due drills' queue."""
    now = datetime.now(timezone.utc)
    row = conn.execute(
        "SELECT * FROM review_schedule WHERE player_id=? AND item_id=?",
        (player_id, item_id)).fetchone()
    if row is None:
        interval, ease, reps, lapses = (1.0, 2.5, 1, 0) if correct else (0.25, 2.5, 1, 1)
    elif correct:
        ease = min(3.0, row["ease"] + 0.05)
        interval = max(1.0, row["interval_days"]) * ease
        reps, lapses = row["reps"] + 1, row["lapses"]
    else:
        ease = max(1.3, row["ease"] - 0.2)
        interval, reps, lapses = 0.25, row["reps"] + 1, row["lapses"] + 1
    due = (now + timedelta(days=interval)).isoformat()
    conn.execute(
        """INSERT INTO review_schedule (player_id, item_id, due_at, interval_days, ease, reps, lapses)
           VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(player_id, item_id) DO UPDATE SET
             due_at=excluded.due_at, interval_days=excluded.interval_days,
             ease=excluded.ease, reps=excluded.reps, lapses=excluded.lapses""",
        (player_id, item_id, due, interval, ease, reps, lapses))


def level_mastery(conn, player_id: int, level_id: str) -> dict:
    """Mean mastery over the concepts exercised by a level's items, plus
    attempt coverage (fraction of the level's items attempted)."""
    concept_rows = conn.execute(
        """SELECT DISTINCT ic.concept_id FROM item_concepts ic
           JOIN items i ON i.id = ic.item_id WHERE i.level_id = ?""",
        (level_id,)).fetchall()
    concept_ids = [r["concept_id"] for r in concept_rows]
    if not concept_ids:
        return {"mastery": 0.0, "coverage": 0.0, "concepts": {}}
    placeholders = ",".join("?" * len(concept_ids))
    mastery_rows = conn.execute(
        f"""SELECT concept_id, mastery FROM concept_mastery
            WHERE player_id=? AND concept_id IN ({placeholders})""",
        (player_id, *concept_ids)).fetchall()
    by_concept = {r["concept_id"]: r["mastery"] for r in mastery_rows}
    mean = sum(by_concept.get(c, 0.0) for c in concept_ids) / len(concept_ids)

    total_items = conn.execute(
        "SELECT COUNT(*) FROM items WHERE level_id=?", (level_id,)).fetchone()[0]
    attempted = conn.execute(
        """SELECT COUNT(DISTINCT item_id) FROM attempts
           WHERE player_id=? AND item_id IN (SELECT id FROM items WHERE level_id=?)""",
        (player_id, level_id)).fetchone()[0]
    coverage = attempted / total_items if total_items else 0.0
    return {"mastery": mean, "coverage": coverage,
            "concepts": {c: round(by_concept.get(c, 0.0), 4) for c in concept_ids}}


def level_states(conn, player_id: int) -> list[dict]:
    """Every level with its unlock status for this player."""
    levels = conn.execute("SELECT * FROM levels ORDER BY ordinal").fetchall()
    out = []
    for lv in levels:
        stats = level_mastery(conn, player_id, lv["id"])
        if lv["prereq_level_id"] is None:
            unlocked = True
        else:
            prereq = next(x for x in out if x["id"] == lv["prereq_level_id"])
            unlocked = (prereq["mastery"] >= lv["min_mastery"]
                        and prereq["coverage"] >= 0.999)
        completed = stats["coverage"] >= 0.999 and stats["mastery"] >= lv["min_mastery"]
        out.append({"id": lv["id"], "ordinal": lv["ordinal"], "band": lv["band"],
                    "title": lv["title"], "tagline": lv["tagline"],
                    "unlocked": unlocked, "completed": completed,
                    "mastery": round(stats["mastery"], 4),
                    "coverage": round(stats["coverage"], 4)})
    return out
