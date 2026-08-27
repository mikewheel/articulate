"""Grading.

Deterministic graders own every number (spec §2: an LLM grades prose only,
never numbers). The llm_rubric grader delegates to a judge callable with the
signature judge(prompt, context, model_answer, rubric, response) -> dict
{"hits": [rubric ids], "feedback": str, "source": "llm_mock"|"llm"} —
see llm.py for the mock and real implementations.
"""

import json


def grade(item: dict, submitted: dict, judge=None) -> dict:
    """item: a row from `items` with payload/answer_key already parsed.
    Returns {score, max_score, correct, feedback, grader_source}."""
    grader = item["grader"]
    payload, key = item["payload"], item["answer_key"]
    if grader == "choice":
        return _grade_choice(payload, key, submitted)
    if grader == "numeric":
        return _grade_numeric(key, submitted)
    if grader == "grid":
        return _grade_grid(payload, key, submitted)
    if grader == "mapping":
        return _grade_mapping(payload, key, submitted)
    if grader == "llm_rubric":
        if judge is None:
            raise ValueError("llm_rubric item requires a judge")
        return _grade_rubric(payload, key, submitted, judge)
    if grader == "probability":
        return _grade_probability(key, submitted)
    raise ValueError(f"unknown grader {grader!r}")


def _result(score, max_score, correct, feedback, source="deterministic"):
    return {"score": float(score), "max_score": float(max_score),
            "correct": bool(correct), "feedback": feedback,
            "grader_source": source}


def _grade_choice(payload, key, submitted):
    idx = submitted.get("index")
    correct_idx = key["correct_index"]
    correct = idx == correct_idx
    feedback = {"correct_index": correct_idx,
                "correct_choice": payload["choices"][correct_idx]}
    if not correct and isinstance(idx, int) and 0 <= idx < len(payload["choices"]):
        why = (key.get("why_wrong") or [])
        feedback["why_wrong"] = why[idx] if idx < len(why) else None
    return _result(1 if correct else 0, 1, correct, feedback)


def numeric_matches(value, target, tol_abs=None, tol_rel=None) -> bool:
    if not isinstance(value, (int, float)):
        return False
    tolerance = 0.0
    if tol_abs is not None:
        tolerance = max(tolerance, tol_abs)
    if tol_rel is not None:
        tolerance = max(tolerance, abs(target) * tol_rel)
    return abs(value - target) <= tolerance


def _grade_numeric(key, submitted):
    value = submitted.get("value")
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = None
    correct = numeric_matches(value, key["value"],
                              key.get("tolerance_abs"), key.get("tolerance_rel"))
    return _result(1 if correct else 0, 1, correct, {"value": key["value"]})


def _grade_grid(payload, key, submitted):
    cells = key["cells"]
    tol = key.get("tolerance_abs", 0.5)
    given = submitted.get("cells") or {}
    per_cell, right = {}, 0
    for cell, target in cells.items():
        raw = given.get(cell)
        try:
            raw = float(raw)
        except (TypeError, ValueError):
            raw = None
        good = numeric_matches(raw, target, tol_abs=tol)
        per_cell[cell] = {"correct": good, "expected": target, "got": raw}
        right += good
    correct = right == len(cells)
    return _result(right, len(cells), correct, {"cells": per_cell})


def _grade_mapping(payload, key, submitted):
    mapping = key["map"]
    given = submitted.get("map") or {}
    per_key, right = {}, 0
    labels = payload["right"]
    for k, target in mapping.items():
        good = given.get(k) == target
        per_key[k] = {"correct": good, "expected": labels[target],
                      "tell": (key.get("tells") or {}).get(k)}
        right += good
    correct = right == len(mapping)
    return _result(right, len(mapping), correct, {"assignments": per_key})


def _grade_rubric(payload, key, submitted, judge):
    response = (submitted.get("text") or "").strip()
    rubric = key["rubric"]
    max_points = sum(r["points"] for r in rubric)
    if not response:
        return _result(0, max_points, False,
                       {"rubric": [], "note": "empty response",
                        "model_answer": key["model_answer"]})
    verdict = judge(prompt=payload.get("prompt", ""),
                    context=payload.get("context"),
                    model_answer=key["model_answer"],
                    rubric=rubric,
                    response=response)
    hits = set(verdict.get("hits", []))
    points = sum(r["points"] for r in rubric if r["id"] in hits)
    correct = points >= key["pass_points"]
    feedback = {
        "rubric": [{"id": r["id"], "description": r["description"],
                    "points": r["points"], "hit": r["id"] in hits}
                   for r in rubric],
        "judge_feedback": verdict.get("feedback", ""),
        "model_answer": key["model_answer"],
    }
    return _result(points, max_points, correct, feedback,
                   source=verdict.get("source", "llm_mock"))


def _grade_probability(key, submitted):
    """Brier scoring (spec §5.7): a proper scoring rule, so the best strategy
    is reporting your true belief. 'Correct' means beating the base rate."""
    try:
        p = float(submitted.get("p"))
    except (TypeError, ValueError):
        p = None
    if p is None or not 0.0 <= p <= 1.0:
        return _result(0, 1, False, {"note": "probability must be in [0, 1]"})
    outcome = 1.0 if key["outcome"] else 0.0
    brier = (p - outcome) ** 2
    base_brier = (key["base_rate"] - outcome) ** 2
    correct = brier <= base_brier
    feedback = {
        "outcome": key["outcome"],
        "base_rate": key["base_rate"],
        "brier": round(brier, 4),
        "base_brier": round(base_brier, 4),
        "resolution": key["resolution"],
        "source": key.get("source"),
        "company": key.get("company"),
    }
    return _result(1 - brier, 1, correct, feedback)


def parse_item_row(row) -> dict:
    """sqlite Row from `items` -> dict with payload/answer_key parsed."""
    item = dict(row)
    item["payload"] = json.loads(item["payload"])
    item["answer_key"] = json.loads(item["answer_key"])
    return item
