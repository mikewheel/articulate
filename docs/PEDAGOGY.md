# Articulate — Pedagogy Notes

How the level design implements the learning science in spec §7. This document
is the rationale for the item mixes in `content/levels.json` and
`content/items/*.json`; if an item bank drifts from these principles, the bank
is wrong, not the principles.

## The five principles in play

**1. Retrieval practice (the testing effect; Roediger & Karpicke 2006).**
Every item in every level requires producing an answer before seeing one.
There is no "lesson screen" followed by a quiz; the item *is* the lesson, and
the explanation arrives only after an attempt. Sort, journal, and lexicon
drills are pure retrieval of the alphabet; sudoku is retrieval of identities
under constraint; translate is retrieval of *meaning*, which is the hardest
and most valuable kind.

**2. Worked examples that fade (expertise reversal; Kalyuga et al. 2003).**
Scaffolding helps novices and hurts intermediates, so it is spent early and
withdrawn on schedule. Concretely: the first sudoku in L1 names its two
identities in the intro text; the second names them only in hints; the third
names nothing and blanks four cells. The same fade runs across levels — L2
sudokus stop labeling subtotals, and by L5 the player is handed raw statements
and a bad feeling. Hints everywhere point at the *concept or identity*, never
the value, so a hint converts a failure into a smaller worked example instead
of an answer key.

**3. Interleaving (Rohrer & Taylor 2007).** Item types are shuffled, not
blocked. In L1 the ordinal sequence never presents more than two items of the
same type in a row: a sort, then a lexicon, then a journal entry, then a
translate, then a sudoku that quietly requires all of them. Blocking would let
the player answer from local context ("this is the journal section, so think
debits"); interleaving forces the discrimination step — *what kind of problem
is this* — which is the skill a real filing demands, since a 10-K does not
announce which chapter it is testing.

**4. Immediate, diagnostic feedback.** Every wrong choice carries a
`why_wrong` that names the specific misconception (e.g. "dividends are a
distribution of profit, not a cost of earning it — they never touch the
income statement"), and every explanation ends with the investor "so what."
The player is never told merely that they are wrong, and never told merely the
right value: they are told which definition or identity would have produced
it. This is the spec's rule that errors are answered with the missed identity,
implemented at the item level.

**5. Production over recognition.** Multiple choice is a concession to speed
in Band A, where the target *is* recognition (classifying line items on
sight). But even L1 embeds production: four translate items graded by rubric
require the player to generate plain English and an implication in their own
words, and three sudoku grids require producing numbers no choice list
contains. The production share rises every level — L2 is mostly grids, L3
mixes rubric prose with numeric adjustments, L5 is an open forensic argument
and free-text questions to a CFO. Recognition gets you reading; production
gets you fluent.

## Why each level's mix is what it is

- **L1 (Band A) — ~10 sort, 6 journal, 5 lexicon, 4 translate, 3 sudoku.**
  Band A is vocabulary and orthography, so the bulk is fast retrieval drills
  (sort/lexicon) that build automaticity — classification must become cheap
  before articulation can become possible. Journal items force the
  double-entry mechanics in both directions (event→entry and entry→event),
  because reading an entry is a different retrieval path from writing one.
  Translate appears early, at low dosage, to establish from week one that
  every mechanic has a meaning and every meaning has an investor consequence.
  The three mini-sudokus are a deliberate preview of Band B: they prove to the
  player that the drills compose into something, which is the motivational
  hook (competence, in self-determination terms) that carries them to L2.
- **L2 (Band B) — sudoku set plus translate.** Articulation is a system
  skill, so it is taught by constraint deduction, where a stuck player is
  always missing an identity and never information. Translate items make the
  player say *why* CFO differs from net income, converting the puzzle skill
  into an analyst sentence.
- **L3 (Band C) — translate, numeric adjustments, journal.** Policies are
  meaning-laden choices, so the production-heavy formats dominate: restate a
  number, then say what the choice reveals about management.
- **L4 (Band D) — forge and lineup on real data.** Ratios are recipes;
  interpretation is mandatory; real messy data is used because transfer from
  clean textbook data to filings is poor (spec §7, transfer).
- **L5 (Band E) — one forensic case plus an earnings call.** Synthesis under
  adversarial conditions: name the technique, cite the evidence, ask the
  question. Nothing new is introduced; everything prior is composed.

## The ramp inside L1, specifically

L1's 28 items run ordinals 10–280, easy→hard within each type and overall,
with difficulty tags 1→3:

- **Ordinals 10–100 (near-guided).** Unambiguous classifications (Cash,
  Revenue, Accounts payable), a one-line journal entry with one plausible
  distractor pattern, lexicon terms defined almost verbatim from the concept
  descriptions, and a first sudoku whose two identities are named in its own
  intro. Success rate here should be high; the purpose is encoding and
  format-learning, not discrimination.
- **Ordinals 110–180 (scaffolding thinning).** Items where the surface reading
  misleads: dividends paid (feels like an expense, is financing),
  deferred revenue (has "revenue" in the name, is a liability), entry→event
  reversals, accrued wages (an expense with no cash). Hints still name the
  governing concept. The second sudoku moves the identities out of the intro
  and into hints, and blanks a cell mid-statement rather than at the bottom.
- **Ordinals 190–280 (unscaffolded).** The classically tricky classifications
  (accumulated depreciation, treasury stock, dividends payable, right-of-use
  asset), journal items requiring two-step reasoning (declaring vs paying a
  dividend; recognizing previously deferred revenue), a translate item with a
  genuine tension in it (dividends exceeding net income), and a final sudoku
  with four blanks, an inference chain three identities long, and an intro
  that names nothing. By design these approximate the ~70% success target the
  matchmaker will later maintain (desirable difficulty; Bjork).

Two constraints hold across the whole bank: no item tests trivia without an
investor consequence in its explanation, and no hint ever contains a value —
hints buy the player a concept, and the player still has to spend it.
