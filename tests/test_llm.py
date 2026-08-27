from articulate.llm import (MockLLM, fact_sheet_numbers, numbers_in_text,
                            reply_respects_fact_sheet)

SCENARIO = {
    "cfo_name": "Test CFO",
    "cfo_persona": "evasive",
    "fact_sheet": {"revenue_fy3": 1180.0, "dso_fy3": 78, "note": "signed 2 new distributors"},
    "hidden_issues": [
        {"id": "channel_stuffing",
         "summary": "extended payment terms to distributors in the fourth quarter",
         "reveal_threshold": "asks specifically about payment terms or distributor incentives"},
        {"id": "reserve_release",
         "summary": "cut the allowance for doubtful accounts despite receivables growth",
         "reveal_threshold": "asks about the allowance or bad debt reserve"},
    ],
    "max_questions": 5,
}


def test_numbers_extraction():
    assert numbers_in_text("Revenue was $1,180M and DSO hit 78.5 days") == [1180.0, 78.5]


def test_fact_sheet_numbers_include_strings():
    nums = fact_sheet_numbers(SCENARIO["fact_sheet"])
    assert 1180.0 in nums and 78.0 in nums and 2.0 in nums


def test_reply_respecting_fact_sheet():
    assert reply_respects_fact_sheet("Revenue came in at 1180, up nicely.",
                                     SCENARIO["fact_sheet"])
    assert not reply_respects_fact_sheet("Margins were 43.7 percent.",
                                         SCENARIO["fact_sheet"])


def test_mock_cfo_never_states_foreign_numbers():
    mock = MockLLM()
    for question in ("What was revenue?", "Talk to me about margins and cash conversion.",
                     "Why did receivables grow 80 percent?"):
        result = mock.cfo_reply(SCENARIO, [], question)
        assert reply_respects_fact_sheet(result["reply"], SCENARIO["fact_sheet"]), result


def test_mock_cfo_reveals_issue_on_targeted_question():
    mock = MockLLM()
    result = mock.cfo_reply(SCENARIO, [], "Did you extend payment terms to distributors this quarter?")
    assert "channel_stuffing" in result["issues_hit"]


def test_mock_cfo_deflects_vague_question():
    mock = MockLLM()
    result = mock.cfo_reply(SCENARIO, [], "How do you feel about the year?")
    assert result["issues_hit"] == []


def test_mock_judge_is_deterministic_and_rewards_content():
    mock = MockLLM()
    rubric = [
        {"id": "mech", "points": 1,
         "description": "states that depreciation expense falls because the cost spreads over more years"},
        {"id": "sowhat", "points": 2,
         "description": "flags the earnings quality implication: higher profit with no cash change"},
    ]
    good = ("Depreciation expense falls since the cost is spread over more years, "
            "so profit looks higher with no change in cash — an earnings quality flag.")
    bad = "The company changed something about its equipment."
    good_result = mock.judge("p", None, "model", rubric, good)
    assert set(good_result["hits"]) == {"mech", "sowhat"}
    assert mock.judge("p", None, "model", rubric, good) == good_result
    assert mock.judge("p", None, "model", rubric, bad)["hits"] == []
