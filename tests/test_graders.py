import pytest

from articulate.graders import grade, numeric_matches


def make_item(grader, payload, answer_key):
    return {"grader": grader, "payload": payload, "answer_key": answer_key}


class TestChoice:
    item = make_item("choice",
                     {"prompt": "Where does cash live?",
                      "choices": ["Income statement", "Balance sheet"]},
                     {"correct_index": 1, "why_wrong": ["Cash is a position, not a flow.", None]})

    def test_correct(self):
        result = grade(self.item, {"index": 1})
        assert result["correct"] and result["score"] == 1

    def test_wrong_includes_why(self):
        result = grade(self.item, {"index": 0})
        assert not result["correct"]
        assert result["feedback"]["why_wrong"] == "Cash is a position, not a flow."
        assert result["feedback"]["correct_choice"] == "Balance sheet"

    def test_missing_index(self):
        assert not grade(self.item, {})["correct"]


class TestNumeric:
    def test_tolerances(self):
        assert numeric_matches(100.4, 100, tol_abs=0.5)
        assert not numeric_matches(100.6, 100, tol_abs=0.5)
        assert numeric_matches(102, 100, tol_rel=0.02)
        assert not numeric_matches(103, 100, tol_rel=0.02)
        assert not numeric_matches(None, 100, tol_abs=1)

    def test_grade_accepts_string_input(self):
        item = make_item("numeric", {"prompt": "?", "unit": "x"},
                         {"value": 3.0, "tolerance_rel": 0.02})
        assert grade(item, {"value": "2.95"})["correct"]
        assert not grade(item, {"value": "abc"})["correct"]


class TestGrid:
    item = make_item("grid",
                     {"statements": []},
                     {"cells": {"net_income": 75.0, "closing_re": 445.0}, "tolerance_abs": 0.5})

    def test_all_correct(self):
        result = grade(self.item, {"cells": {"net_income": 75, "closing_re": 445}})
        assert result["correct"] and result["score"] == 2

    def test_partial(self):
        result = grade(self.item, {"cells": {"net_income": 75, "closing_re": 400}})
        assert not result["correct"]
        assert result["score"] == 1
        assert result["feedback"]["cells"]["closing_re"]["correct"] is False
        assert result["feedback"]["cells"]["closing_re"]["expected"] == 445.0


class TestMapping:
    item = make_item("mapping",
                     {"left": [{"key": "A"}, {"key": "B"}], "right": ["Grocer", "Bank"]},
                     {"map": {"A": 0, "B": 1}, "tells": {"A": "thin margins"}})

    def test_correct(self):
        assert grade(self.item, {"map": {"A": 0, "B": 1}})["correct"]

    def test_feedback_carries_tell(self):
        result = grade(self.item, {"map": {"A": 1, "B": 0}})
        assert result["score"] == 0
        assert result["feedback"]["assignments"]["A"]["tell"] == "thin margins"


class TestProbability:
    item = make_item("probability",
                     {"prompt": "Bankruptcy within 24 months?", "context": "dossier",
                      "as_of": "2007-01-29"},
                     {"outcome": True, "base_rate": 0.02,
                      "resolution": "Filed Chapter 11.", "source": "8-K Item 1.03",
                      "company": "Example Corp"})

    def test_confident_right_beats_base_rate(self):
        result = grade(self.item, {"p": 0.7})
        assert result["correct"]
        assert abs(result["score"] - (1 - 0.09)) < 1e-9
        assert result["feedback"]["resolution"] == "Filed Chapter 11."

    def test_hedge_below_base_rate_fails(self):
        # outcome true, base rate 0.02: predicting 0.01 is worse than base
        assert not grade(self.item, {"p": 0.01})["correct"]

    def test_proper_scoring_rewards_honesty(self):
        # score is monotone in distance from outcome
        s = [grade(self.item, {"p": p})["score"] for p in (0.2, 0.5, 0.9)]
        assert s[0] < s[1] < s[2]

    def test_invalid_probability(self):
        assert not grade(self.item, {"p": 1.7})["correct"]
        assert not grade(self.item, {})["correct"]


class TestRubric:
    item = make_item("llm_rubric",
                     {"prompt": "Explain the change."},
                     {"model_answer": "Depreciation falls, earnings rise, cash unchanged.",
                      "rubric": [
                          {"id": "mech", "points": 1, "description": "depreciation expense falls"},
                          {"id": "sowhat", "points": 2, "description": "earnings quality implication"},
                      ],
                      "pass_points": 2})

    def test_requires_judge(self):
        with pytest.raises(ValueError):
            grade(self.item, {"text": "hi"})

    def test_scores_from_judge_hits(self):
        judge = lambda **kw: {"hits": ["mech", "sowhat"], "feedback": "good", "source": "llm_mock"}
        result = grade(self.item, {"text": "some answer"}, judge=judge)
        assert result["correct"] and result["score"] == 3
        assert result["grader_source"] == "llm_mock"
        assert result["feedback"]["rubric"][0]["hit"] is True

    def test_empty_response_fails_without_judge_call(self):
        called = []
        judge = lambda **kw: called.append(1)
        result = grade(self.item, {"text": "   "}, judge=judge)
        assert not result["correct"] and not called

    def test_below_pass_points(self):
        judge = lambda **kw: {"hits": ["mech"], "feedback": "", "source": "llm_mock"}
        result = grade(self.item, {"text": "answer"}, judge=judge)
        assert result["score"] == 1 and not result["correct"]
