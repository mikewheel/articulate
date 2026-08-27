from articulate.mastery import level_mastery, level_states, schedule_review, update_mastery


def record_attempt(db, player, item, score, max_score=1.0):
    db.execute("""INSERT INTO attempts (player_id, item_id, submitted, score, max_score,
                  correct, feedback, grader_source)
                  VALUES (?, ?, '{}', ?, ?, ?, '{}', 'deterministic')""",
               (player, item, score, max_score, 1 if score >= max_score else 0))


def test_mastery_rises_with_correct_answers(seeded_db):
    first = update_mastery(seeded_db, 1, "i1", 1.0)
    assert 0 < first["c1"] < 1
    second = update_mastery(seeded_db, 1, "i1", 1.0)
    assert second["c1"] > first["c1"]


def test_mastery_falls_on_miss(seeded_db):
    update_mastery(seeded_db, 1, "i1", 1.0)
    high = update_mastery(seeded_db, 1, "i1", 1.0)["c1"]
    low = update_mastery(seeded_db, 1, "i1", 0.0)["c1"]
    assert low < high


def test_mastery_only_touches_items_concepts(seeded_db):
    update_mastery(seeded_db, 1, "i1", 1.0)
    row = seeded_db.execute(
        "SELECT COUNT(*) FROM concept_mastery WHERE player_id=1 AND concept_id='c2'"
    ).fetchone()[0]
    assert row == 0


def test_level_mastery_and_coverage(seeded_db):
    stats = level_mastery(seeded_db, 1, "L1")
    assert stats["mastery"] == 0.0 and stats["coverage"] == 0.0
    update_mastery(seeded_db, 1, "i1", 1.0)
    record_attempt(seeded_db, 1, "i1", 1.0)
    stats = level_mastery(seeded_db, 1, "L1")
    assert stats["coverage"] == 0.5      # one of two items attempted
    assert 0 < stats["mastery"] < 1      # mean over c1 (some) and c2 (zero)


def test_level_states_unlock_chain(seeded_db):
    seeded_db.execute("""INSERT INTO levels (id, ordinal, band, title, prereq_level_id, min_mastery)
                         VALUES ('L2', 2, 'B', 'Second', 'L1', 0.6)""")
    states = level_states(seeded_db, 1)
    assert states[0]["unlocked"] is True
    assert states[1]["unlocked"] is False
    # master both items several times and attempt everything
    for _ in range(6):
        update_mastery(seeded_db, 1, "i1", 1.0)
        update_mastery(seeded_db, 1, "i2", 1.0)
    record_attempt(seeded_db, 1, "i1", 1.0)
    record_attempt(seeded_db, 1, "i2", 1.0)
    states = level_states(seeded_db, 1)
    assert states[0]["completed"] is True
    assert states[1]["unlocked"] is True


def test_schedule_review_intervals(seeded_db):
    schedule_review(seeded_db, 1, "i1", correct=True)
    row = seeded_db.execute(
        "SELECT * FROM review_schedule WHERE player_id=1 AND item_id='i1'").fetchone()
    assert row["interval_days"] == 1.0 and row["lapses"] == 0
    schedule_review(seeded_db, 1, "i1", correct=True)
    row2 = seeded_db.execute(
        "SELECT * FROM review_schedule WHERE player_id=1 AND item_id='i1'").fetchone()
    assert row2["interval_days"] > row["interval_days"]
    schedule_review(seeded_db, 1, "i1", correct=False)
    row3 = seeded_db.execute(
        "SELECT * FROM review_schedule WHERE player_id=1 AND item_id='i1'").fetchone()
    assert row3["interval_days"] < 1 and row3["lapses"] == 1
