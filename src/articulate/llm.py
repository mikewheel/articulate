"""LLM judge and LLM characters, behind one interface.

Two implementations:

- MockLLM: deterministic, offline. Used whenever ANTHROPIC_API_KEY is unset so
  the whole game is playable without keys. The rubric judge does stemmed
  keyword overlap; the CFO replies from templates. Attempts graded this way are
  recorded with grader_source="llm_mock" so they can be re-graded later.
- AnthropicLLM: real calls through the Anthropic Messages API (model
  claude-opus-4-8), structured output via output_config json_schema for the
  judge. Activated automatically once ANTHROPIC_API_KEY is set.

Spec §11.4 invariant, enforced for BOTH implementations: the CFO cannot state
a number absent from its fact sheet. `numbers_in_text` + `fact_sheet_numbers`
implement the post-check; a violating reply is replaced by a safe deflection.
"""

import json
import os
import re

ANTHROPIC_MODEL = "claude-opus-4-8"

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "that", "this", "is", "are", "was", "were", "be", "as", "by", "it", "its",
    "at", "from", "has", "have", "had", "will", "would", "should", "than",
    "into", "about", "their", "they", "there", "which", "what", "when", "how",
    "why", "not", "no", "but", "if", "so", "such", "these", "those", "states",
    "shows", "mentions", "notes", "identifies", "links", "explains",
}


def _stem(word: str) -> str:
    word = word.lower()
    for suffix in ("ization", "ations", "ation", "ings", "ing", "edly", "ed",
                   "es", "s", "ly"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def _content_stems(text: str) -> set:
    words = re.findall(r"[a-zA-Z][a-zA-Z'-]+", text)
    return {_stem(w) for w in words if w.lower() not in _STOPWORDS and len(w) > 2}


def numbers_in_text(text: str) -> list[float]:
    """Extract numeric values from prose ('$1,180M', '78 days', '4.2%')."""
    out = []
    for match in re.findall(r"-?\$?([\d,]+(?:\.\d+)?)", text):
        cleaned = match.replace(",", "")
        try:
            out.append(float(cleaned))
        except ValueError:
            continue
    return out


def fact_sheet_numbers(fact_sheet: dict) -> set:
    nums = set()
    for value in fact_sheet.values():
        if isinstance(value, (int, float)):
            nums.add(round(float(value), 4))
        elif isinstance(value, str):
            nums.update(round(n, 4) for n in numbers_in_text(value))
    return nums


def reply_respects_fact_sheet(reply: str, fact_sheet: dict) -> bool:
    """True iff every number in the reply appears in the fact sheet.
    Small integers (years-style or counts <= 12) are tolerated as rhetoric."""
    allowed = fact_sheet_numbers(fact_sheet)
    for num in numbers_in_text(reply):
        if round(num, 4) in allowed:
            continue
        if num == int(num) and (0 <= num <= 12 or 1900 <= num <= 2100):
            continue
        return False
    return True


SAFE_DEFLECTION = ("I don't have that exact figure in front of me — I'd point "
                   "you to the numbers in the filing.")


# ------------------------------------------------------------------- mock --

class MockLLM:
    """Deterministic offline stand-in. Not a real grader: keyword overlap only."""

    source = "llm_mock"

    def judge(self, prompt, context, model_answer, rubric, response):
        response_stems = _content_stems(response)
        hits = []
        for criterion in rubric:
            target = _content_stems(criterion["description"])
            overlap = len(target & response_stems)
            needed = 2 if len(target) >= 4 else 1
            if overlap >= needed:
                hits.append(criterion["id"])
        feedback = ("[offline mock grader: keyword match] Matched "
                    f"{len(hits)}/{len(rubric)} rubric points. Compare your "
                    "answer with the model answer below — the mock grader "
                    "only checks vocabulary, not reasoning.")
        return {"hits": hits, "feedback": feedback, "source": self.source}

    def cfo_reply(self, scenario, transcript, question):
        question_stems = _content_stems(question)
        fact_sheet = scenario["fact_sheet"]
        issues_hit = []
        for issue in scenario["hidden_issues"]:
            target = _content_stems(issue["summary"] + " " + issue["reveal_threshold"])
            if len(target & question_stems) >= 2:
                issues_hit.append(issue["id"])

        if issues_hit:
            # concede obliquely, never restating the internal summary (it can
            # carry numbers outside the fact sheet, and the full reveal belongs
            # to the debrief, not the call)
            reply = ("That's… a fair read of the line you're pointing at. "
                     "I'll acknowledge the quarter had some timing benefit in it — "
                     "we made accommodations we don't expect to repeat, and we "
                     "expect that metric to normalize over the coming quarters. "
                     "I'm not going to litigate program terms on this call.")
        else:
            keys = sorted(fact_sheet)
            pick = keys[len(question) % len(keys)] if keys else None
            value = fact_sheet.get(pick)
            if isinstance(value, (int, float)):
                reply = (f"What I can tell you is that {pick.replace('_', ' ')} "
                         f"came in at {value:g}, which we're pleased with. "
                         "Beyond that I'd rather not get ahead of the filing.")
            else:
                reply = ("That's a fair question. " + (str(value) if value else "")
                         + " I'd frame it as consistent with the strategy we laid out.")
        if not reply_respects_fact_sheet(reply, fact_sheet):
            reply = SAFE_DEFLECTION
        return {"reply": reply, "issues_hit": issues_hit, "source": self.source}


# ------------------------------------------------------------------- real --

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "hits": {"type": "array", "items": {"type": "string"}},
        "feedback": {"type": "string"},
    },
    "required": ["hits", "feedback"],
    "additionalProperties": False,
}


class AnthropicLLM:
    """Real grading and characters via the Anthropic Messages API."""

    source = "llm"

    def __init__(self):
        import anthropic
        self._client = anthropic.Anthropic()
        self._fallback = MockLLM()

    def judge(self, prompt, context, model_answer, rubric, response):
        rubric_text = "\n".join(
            f"- id={r['id']} ({r['points']} pt): {r['description']}" for r in rubric)
        system = (
            "You grade short free-text answers for a financial-statement-analysis "
            "learning game. Grade prose quality of reasoning only — never award a "
            "point for a numeric claim unless the criterion explicitly asks for it. "
            "Award a rubric criterion only if the response genuinely demonstrates "
            "it. Return the ids of satisfied criteria and one or two sentences of "
            "specific, teaching feedback in the voice of a dry, seasoned analyst.")
        user = (f"Question:\n{prompt}\n\n"
                + (f"Context:\n{context}\n\n" if context else "")
                + f"Rubric:\n{rubric_text}\n\n"
                + f"Reference answer (do not require exact match):\n{model_answer}\n\n"
                + f"Player response:\n{response}")
        message = self._client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2048,
            system=system,
            output_config={"format": {"type": "json_schema", "schema": JUDGE_SCHEMA}},
            messages=[{"role": "user", "content": user}],
        )
        if message.stop_reason == "refusal":
            return self._fallback.judge(prompt, context, model_answer, rubric, response)
        text = next(b.text for b in message.content if b.type == "text")
        data = json.loads(text)
        valid_ids = {r["id"] for r in rubric}
        return {"hits": [h for h in data["hits"] if h in valid_ids],
                "feedback": data["feedback"], "source": self.source}

    def cfo_reply(self, scenario, transcript, question):
        fact_sheet = scenario["fact_sheet"]
        issues = scenario["hidden_issues"]
        system = (
            f"You are {scenario['cfo_name']}, CFO, on a mock earnings call in a "
            f"financial-analysis training game. Persona: {scenario['cfo_persona']}\n\n"
            "Rules:\n"
            "- Answer truthfully but evasively; never state a falsehood.\n"
            "- You may ONLY state numbers that appear in the FACT SHEET below. "
            "If asked for any other number, deflect to the filing.\n"
            "- The HIDDEN ISSUES are real problems you know about. If a question "
            "is specific and evidence-based enough to meet an issue's reveal "
            "threshold, concede part of it grudgingly; otherwise deflect.\n"
            "- Two to four sentences per reply.\n\n"
            f"FACT SHEET:\n{json.dumps(fact_sheet, indent=2)}\n\n"
            f"HIDDEN ISSUES:\n{json.dumps(issues, indent=2)}")
        history = [{"role": ("user" if t["role"] == "analyst" else "assistant"),
                    "content": t["content"]} for t in transcript]
        message = self._client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            system=system,
            messages=history + [{"role": "user", "content": question}],
        )
        if message.stop_reason == "refusal":
            return self._fallback.cfo_reply(scenario, transcript, question)
        reply = next((b.text for b in message.content if b.type == "text"), "")
        if not reply_respects_fact_sheet(reply, fact_sheet):
            reply = SAFE_DEFLECTION
        # issue coverage: classify with the mock's deterministic matcher so
        # scoring stays reproducible (spec §5.6: mapping is a classifier with
        # fixtures, not the character model)
        issues_hit = self._fallback.cfo_reply(scenario, transcript, question)["issues_hit"]
        return {"reply": reply, "issues_hit": issues_hit, "source": self.source}


def get_client():
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return AnthropicLLM()
        except Exception:
            return MockLLM()
    return MockLLM()


def make_judge(client=None):
    """Adapter matching the judge callable signature graders.grade expects."""
    client = client or get_client()

    def judge(prompt, context, model_answer, rubric, response):
        return client.judge(prompt, context, model_answer, rubric, response)

    return judge
