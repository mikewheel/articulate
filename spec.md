# Articulate

## A game for becoming fluent in financial statements

Working title. The name is the thesis: financial statements *articulate* (each links to the others through accounting identities), and the goal is to become articulate in the language. Alternates: *Ten-K*, *Going Concern*.

Status: design spec v0.1, with a technical outline for an autonomous coding agent (Section 11).

---

## 1. Pitch

You play an analyst. The levels are real companies, pulled from EDGAR. You learn accounting the way you learn a language: by producing it under mild pressure, with immediate feedback, and with every term tied to what it means for someone deciding whether to invest. Nothing unlocks by grinding. The only key to the next area is demonstrated mastery of the concepts behind it.

## 2. Design goals and non-goals

Goals

- Fluency over trivia. The player should read a 10-K the way a fluent speaker reads a newspaper: fast, skipping what does not matter, stopping on what does.
- Real data as early as possible. Synthetic companies for the first hours, then real filings with structured (XBRL) answer keys, then real filings where the answer is in a footnote.
- Every number carries a "so what". No task ends at computing a ratio. The follow-up is always what it implies and what would change your mind.
- Exact ground truth wherever it exists. Synthetic ledgers and XBRL facts give deterministic answer keys. An LLM grades prose only, never numbers.
- Sessions fit the device. Two-minute drills on a phone, forty-minute cases on a desktop.
- Honest scoring. Proper scoring rules for forecasts, mastery estimates for skills, no score inflation from repetition.

Non-goals

- Not a trading or stock-picking simulator. The forecasting mode measures calibration, not returns.
- Not a CFA exam prep product. It borrows the curriculum's structure and item formats and does not claim affiliation. CFA Institute owns the CFA marks; naming and marketing should say "CFA-style" at most, and never use the mark in the product name.
- No real money, no purchasable advantages, no engagement tricks that reward showing up over learning.

## 3. Learning targets

The target is the CFA Level I and Level II Financial Statement Analysis topic areas (12 learning modules at Level I, 6 at Level II in the 2026 curriculum) plus the working vocabulary an investor or corporate finance person uses daily. Grouped as competency bands. Each band is a region of the concept graph (Section 6).

| Band | You can... | Roughly maps to |
|---|---|---|
| A. Alphabet | Classify any line item to statement and section. Read a journal entry and say what happened. State the accounting-equation effects of a transaction. | L1: Introduction to FSA |
| B. Grammar (articulation) | Derive the indirect cash flow statement from two balance sheets and an income statement. Roll forward retained earnings, PP&E, debt, equity. Explain why CFO differs from net income for a given company. | L1: Analyzing income statements, balance sheets, cash flow statements I and II |
| C. Vocabulary (policies) | Explain and adjust for revenue recognition choices, inventory methods (FIFO/LIFO, LIFO reserve), capitalization vs expensing, depreciation choices, leases, deferred taxes, contingencies. | L1: Inventories, long-term assets, income taxes, long-term liabilities and equity |
| D. Fluency (analysis) | Compute and interpret liquidity, solvency, activity, profitability, and valuation ratios; DuPont; common-size and trend analysis; peer comparison with industry context. | L1: Financial analysis techniques |
| E. Accent (quality) | Detect earnings management and reporting quality problems from patterns: accruals, DSO and DIO drift, capitalized costs, reserve releases, non-GAAP gaps, auditor signals. | L1: Financial reporting quality; L2: Evaluating quality of financial reports |
| F. Dialects (L2 topics) | Handle intercorporate investments (equity method, consolidation, NCI), pensions and share-based comp, multinational operations (translation vs remeasurement), financial institutions, and IFRS vs US GAAP differences. | L2: Intercorporate investments, employee compensation, multinational operations, financial institutions |
| G. Composition (modeling) | Build a driver-based three-statement projection that balances, with sensitivity; derive FCFF and FCFE; sanity-check against history and peers. | L1: Introduction to financial statement modeling; L2: Financial statement modeling, integration of FSA techniques |
| H. Pragmatics | Read MD&A, notes, the auditor's report (CAMs), 8-Ks, proxies. Know where things are disclosed and why. Ask the questions a good buy-side analyst asks on a call. | Cuts across; closest to L2 integration |

Module names shift slightly year to year. The mapping is a design aid, not a promise.

## 4. Core loop

A session opens with a queue built by the learner model:

1. Due drills (spaced repetition, 1 to 3 minutes).
2. Two or three puzzles matched to current ratings (5 to 10 minutes each).
3. One case, run, or forecast set if the player has time (20 to 45 minutes).

Each attempt produces feedback within seconds. A wrong answer shows the articulation chain that would have produced the right one (the specific identity or note the player missed), never just the value. Ratings and schedules update. Unlocks fire when a region of the concept graph crosses a mastery threshold.

Time scales: drills daily, puzzles most days, cases weekly, seasons monthly.

## 5. Modes

Each mode lists the borrowed mechanic, what it teaches, and where ground truth comes from.

### 5.1 Drills

What you do: rapid micro-tasks on a phone.

- Sort: drag a line item into the right statement and section.
- Journal: given an event, pick the entry; given an entry, describe the event.
- Translate: an accounting sentence ("recorded a $40M valuation allowance against deferred tax assets") to plain English ("management doubts it will earn enough taxable income to use the deductions") to investor implication (a bearish tell about future profitability; check the MD&A for why).
- Lexicon: term recall, both directions.

Mechanic: Duolingo-style micro-sessions; Anki-style scheduling (FSRS). Streaks count learning days, not app opens.

Teaches: Band A, parts of C and H. Translate is the drill that produces fluency. It forces production of meaning, not recognition of a definition.

Ground truth: authored item bank plus generated variants from the synthetic ledger (5.13).

### 5.2 Statement Sudoku (articulation puzzles)

What you do: a set of three statements with cells blanked. Fill them using accounting identities only. Early puzzles blank a few cells (net income, closing retained earnings). Late puzzles blank the entire cash flow statement and ask you to derive it from two balance sheets and the income statement.

Mechanic: constraint deduction (Sudoku, Picross, Into the Breach's perfect-information puzzles). Every puzzle is verified to have a unique solution, so a stuck player is always missing an identity, never information. A hint reveals which identity, not which number.

Teaches: Band B. The statements are one system. A player who can rebuild a cash flow statement from scratch never again confuses CFO with net income.

Ground truth: synthetic companies (exact by construction), then real company-years that pass the pipeline's identity checks, with XBRL facts as the key.

Feedback: on solve, the flow board animates. Net income flows into retained earnings, D&A flows back into CFO, capex flows into PP&E. The picture makes the identities memorable.

### 5.3 Ratio Forge

What you do: assemble ratios from line items (a crafting recipe: numerator, denominator, averaging rule), then apply them to a real company and answer the interpretation question ("interest coverage fell from 9x to 3x while EBIT grew; what happened?").

Mechanic: crafting and recipe unlocks (Minecraft, Factorio). Each recipe carries metadata: inputs, CFA module, and the conditions under which the ratio misleads. Unlocking a recipe requires using its ingredients correctly, not collecting them.

Teaches: Band D. The interpretation step is mandatory. The DuPont decomposition is a boss recipe.

Ground truth: XBRL facts with per-ratio tolerance. Interpretation is graded against a rubric (LLM) with structured output.

### 5.4 Lineup (match the company)

What you do: four anonymized common-size statements and a few ratios; four company or industry labels; match them. Then explain the tell (the grocer has thin margins and fast inventory turns; the software company has deferred revenue and no inventory; the airline has heavy PP&E and lease liabilities; the bank looks like nothing else).

Mechanic: deduction and pattern matching. This is the classic B-school "identify the industry" exercise turned into a timed game with a daily version (5.10).

Teaches: Band D intuition. Numbers become a gestalt. After a hundred lineups an unfamiliar balance sheet reads as "a retailer" at a glance.

Ground truth: the XBRL frames API gives one concept across every filer for a period, so anonymized peer sets and percentile ranks come straight from real data.

### 5.5 Forensics

What you do: statements and notes with something wrong in them. Find the manipulated or misleading item, name the technique, and cite the evidence (which ratio moved, which note contradicts which number). Cases escalate from one clean injected manipulation in a synthetic company to real historical filings where the SEC later acted.

Mechanic: inspection with a growing rulebook (Papers, Please) and deduction with required justification (Return of the Obra Dinn: you commit to who, what, and how, and get confirmation only when all three are right). Bosses are real cases: Enron's FY2000 10-K, WorldCom's capitalized line costs, Lehman's Repo 105 (via the bankruptcy examiner's report against the FY2007 10-K), GE's 2020 SEC settlement (long-term care reserves and GE Power), Kraft Heinz's 2021 settlement (procurement accounting), Under Armour's 2021 settlement (pull-forward sales), Luckin Coffee (foreign private issuer, fabricated sales, 2020 settlement). Boss framing must stick to what public SEC actions and court records establish.

Teaches: Band E, and Band C in reverse (you learn a policy by seeing it abused).

Ground truth: for synthetic cases the injector knows what it did. For real cases, 8-K Item 4.02 (non-reliance on prior financials), 10-K/A restatements, and SEC Accounting and Auditing Enforcement Releases supply labels. The Beneish M-score, Sloan accruals ratio, Altman Z, and Piotroski F-score are unlockable screens the player can run for a time cost.

### 5.6 Earnings Call

What you do: question a CFO played by an LLM. The CFO holds the company's normalized statements and a hidden list of issues (from injectors, or from real disclosures) and is instructed to answer truthfully but evasively. You have a limited number of questions. Score is coverage of the hidden issues plus question quality (specific, evidence-based, follow-ups that press on evasions). A rival sell-side variant argues the bull case and you rebut it from the filing.

Mechanic: adversarial dialogue with hidden information (social deduction games; Phoenix Wright's "present evidence"). Follow-ups unlock disclosures, so pressing is rewarded.

Teaches: Band H. Knowing what to ask is a different skill from knowing what a number is, and it is the skill that separates readers from analysts.

Ground truth: the issues list is deterministic. Question-to-issue mapping is done by a classifier with recorded test fixtures. The LLM's evasions are constrained by a fact sheet so it cannot invent numbers.

### 5.7 Hindsight

What you do: a real filing shown as of its filing date, with nothing from the future. You give probabilities on resolvable questions: restatement within two years, going-concern doubt or bankruptcy within three, goodwill impairment next fiscal year, auditor change, next-year revenue growth bucket. Resolution comes from later EDGAR data. You are scored with a proper scoring rule (Brier) and shown your calibration curve over time. A "conviction" bankroll grows with calibrated forecasts and shrinks with overconfident ones.

Mechanic: prediction market and calibration training; bankroll management from poker. Under a proper scoring rule the highest expected score comes from reporting your true belief, which is the same lesson poker teaches about honest probability estimates.

Teaches: Band E applied under uncertainty, and the discipline of separating "this looks bad" from "this will blow up". It also teaches base rates, because most ugly filings do not restate.

Ground truth: 8-K Items 4.02 (non-reliance), 4.01 (auditor change), 1.03 (bankruptcy); 10-K/A filings; XBRL GoodwillImpairmentLoss and revenue facts in later periods.

### 5.8 Model Studio

What you do: build a driver-based three-statement projection in a grid with live checks (balance sheet balances, cash ties to the cash flow statement, interest computed on average debt without a circularity blowup). Then a sensitivity table, then FCFF and a simple DCF. Compare your forecast against what happened and against a ghost (an expert model, or the population of other players).

Mechanic: construction with verification (Zachtronics: Opus Magnum, Shenzhen I/O), including the post-solve histogram showing your solution's complexity and error versus everyone else's.

Teaches: Band G. A model that balances is the closest thing to writing an essay in the language.

Ground truth: identity checks are exact. Forecast error is measured against later XBRL facts.

### 5.9 Filing Season (runs)

What you do: a seeded weekly run. You are dealt six companies in sequence with a budget of analyst-hours per company. Actions cost hours: pull the ratio dashboard (1), read a specific note (2), run a forensic screen (2), ask the CFO a question (3), build a quick model (4). After spending your hours you make a call (rating plus a written thesis) and are scored against the answer key. Companies get harder; hours get scarcer. Before the run you choose a loadout of tools you have unlocked.

Mechanic: roguelike run structure with meta-progression (Slay the Spire, Hades): short, seeded, replayable, with permanent unlocks earned by mastery rather than by run count. Resource management forces prioritization, which is the actual job.

Teaches: the analyst's protocol as a habit. Business model, income statement trend, balance sheet quality, cash versus earnings, the notes that matter (revenue recognition, debt, leases, contingencies, related parties), MD&A and the non-GAAP reconciliation, auditor's report, screens, valuation. The run's card sequence mirrors this order.

Ground truth: mixed synthetic and real. Leaderboard per seed.

### 5.10 Daily Filing

What you do: one anonymized real company per day, the same for everyone. Guess the industry, then the company, in at most six clues. Each clue reveals another ratio or a line from the notes. Share the result as a grid.

Mechanic: Wordle. Cheap to build, social, and a reason to open the app daily that is also a real exercise.

Teaches: Band D gestalt reading.

Ground truth: XBRL.

### 5.11 Sandbox

Any ticker, every tool, no score. The sandbox is where the game becomes a research tool the player keeps using after they have learned the material.

### 5.12 Cross-cutting item types

These appear inside several modes.

- Tag Archaeology: map a company's custom XBRL extension tags to canonical line items using labels and the presentation structure. A real skill for anyone who works with XBRL, and a way to turn the game's own data problem into content.
- Restatement Autopsy: diff a 10-K/A against the original 10-K; identify what changed, by how much, and why (the 8-K 4.02 gives the stated reason).
- Comparative Reading: a 20-F filer (IFRS) and a 10-K filer (US GAAP) in the same industry; find the differences that matter (LIFO prohibited under IFRS, development cost capitalization under IAS 38, interest classification flexibility on the cash flow statement, inventory write-down reversals).
- Note Hunt: which note answers this question, and what does it say. Trains the reflex of knowing where things live.

### 5.13 Scope by release

- MVP: Drills, Statement Sudoku, Ratio Forge, Lineup, Daily Filing. Synthetic data first, then real.
- v1: Forensics with synthetic injectors and one curated boss.
- v2: Earnings Call and Hindsight.
- v3: Model Studio and Filing Season.

## 6. Progression, ratings, and economy

Concept graph. A DAG of roughly 200 concepts. Each has prerequisites, a band, a CFA module tag, and the item types that exercise it. The graph is data (YAML), validated acyclic by a test, and rendered in-game as a map. Outer Wilds is the reference: what you know is the only progression.

```yaml
- id: re_rollforward
  name: Retained earnings roll-forward
  band: B
  cfa: L1.balance_sheets
  prereqs: [net_income_definition, dividends_declared]
  item_types: [sudoku, translate]
- id: indirect_cfo
  name: Derive CFO by the indirect method
  band: B
  cfa: L1.cash_flow_I
  prereqs: [re_rollforward, accrual_vs_cash, noncash_charges]
  item_types: [sudoku, forge]
- id: lifo_reserve_adjustment
  name: Convert LIFO inventory and COGS to FIFO
  band: C
  cfa: L1.inventories
  prereqs: [inventory_methods, indirect_cfo]
  item_types: [forge, translate, forensics]
```

Ratings. Each concept carries a Glicko-2 rating for the player, updated per attempt against the item's difficulty rating (Lichess puzzle ratings are the model). Items get difficulty ratings the same way, from population results, seeded by the generator's structural difficulty estimate. Matchmaking picks items where the player's win probability is around 70 percent. That keeps the game in the flow channel and keeps ratings informative.

Scheduling. Drills use FSRS. Puzzles and cases are selected by a policy that interleaves concepts and prefers concepts whose rating deviation is high (the model is uncertain) or whose rating has decayed (not seen in a while).

Unlocks. A tool, recipe, mode, or region unlocks when the ratings in its prerequisite region exceed a threshold with low deviation. No unlock is purchasable or grindable.

Career tiers. Associate, Analyst, Senior Analyst, Portfolio Manager. Tiers correspond loosely to Level I, Level II, and integration. A mock mode presents item sets in CFA format (a vignette followed by three-option multiple-choice questions) generated from real filings, for players who want exam feel. Multiple choice is confined to this mode.

Economy. Two scarce resources, both inside modes: analyst-hours (Filing Season) and conviction (Hindsight). No global currency. Cosmetics and titles are the only rewards outside mastery, and they are earned by mastery.

Feedback and juice. Fast, specific, physical: the flow-board animation on solve, a low "balance" tone when a balance sheet balances, a red pulse on the row that broke an identity. Vlambeer's principle: the same correct answer should feel better than a form submission.

## 7. Why this teaches

Mapping mechanics to learning research.

- Retrieval practice. Every mode requires producing an answer before seeing one (the testing effect: Roediger and Karpicke 2006). Drills, sudoku, and forge are pure retrieval.
- Spacing. FSRS scheduling for drills; ratings decay toward uncertainty over time so old regions get revisited (Cepeda et al. 2006).
- Interleaving. Queues mix statements, policies, and interpretation rather than blocking by chapter (Rohrer and Taylor 2007).
- Worked examples that fade. Early puzzles show most cells and explain each identity; later ones show few and explain none. This follows the expertise reversal effect (Kalyuga, Ayres, Chandler, and Sweller 2003): scaffolding helps novices and hurts experts, so it must fade as ratings rise.
- Immediate, diagnostic feedback. Errors are answered with the missed identity or note, not the correct value alone.
- Desirable difficulty and flow. Rating-matched items keep success near 70 percent (Bjork on desirable difficulties; Csikszentmihalyi's flow channel; Jenova Chen's dynamic difficulty).
- Transfer. Real filings are messy: custom tags, odd fiscal years, restated priors, notes that contradict tables. Learning on clean textbook data does not transfer to messy data. Learning on messy data does.
- Production, not recognition. Translate drills, written theses, and CFO questions require generating language.
- Deliberate practice. The rating system localizes weakness to a concept and the scheduler drills it (Ericsson, Krampe, and Tesch-Römer 1993), with a machine doing the coach's job of choosing the next exercise.
- Motivation. Self-determination theory (Ryan and Deci; Rigby and Ryan on games): autonomy (choose the mode, the ticker, the loadout), competence (visible mastery, no grind), relatedness (Daily Filing, seeded runs, ghosts).
- Calibration. Proper scoring rules train honest probability estimates, a skill most finance curricula skip.

What the design refuses to do, because it would undo the above: reward speed over understanding outside explicitly timed modes; let a language model be the source of truth for a number; let multiple choice leak out of the mock mode; award anything for repetition of already-mastered material.

## 8. EDGAR integration

### 8.1 Sources

- XBRL company facts: `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`. Every standard-taxonomy fact a filer has reported, with period, unit, form, filing accession, filed date, and a `frame` field. Covers us-gaap, ifrs-full, dei, and srt. Company-specific extension tags are not included, which is the main cause of gaps.
- XBRL frames: `https://data.sec.gov/api/xbrl/frames/{taxonomy}/{concept}/{unit}/{period}.json`, with periods like `CY2023` (annual duration), `CY2023Q3` (quarterly duration), `CY2023Q4I` (instant). One concept across all filers for one period, snapping each filer's nearest reporting date into the calendar period. This powers Lineup, percentile ranks, and peer sets. The snapping must be disclosed anywhere a comparison is shown.
- Company concept: `https://data.sec.gov/api/xbrl/companyconcept/CIK##########/{taxonomy}/{concept}.json` for targeted pulls.
- Submissions: `https://data.sec.gov/submissions/CIK##########.json`. Filing index per company: forms, dates, accession numbers, primary documents, SIC code, fiscal year end.
- Bulk: `https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip` and `https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip`. The pipeline should prefer these to per-company API calls.
- Financial Statement Data Sets (quarterly zips from SEC DERA: sub, num, pre, tag). Include custom tags and presentation structure. The source for Tag Archaeology and for "as-filed" values.
- Full-text search: `https://efts.sec.gov/LATEST/search-index?q=...` with form and date filters. Filings from 2001 onward. Used to find "material weakness", "going concern", "non-reliance", and to build Note Hunt items.
- Ticker to CIK: `https://www.sec.gov/files/company_tickers.json`.
- Filing documents (10-K, 10-Q, 8-K, 10-K/A, 20-F, DEF 14A, S-1) as HTML for note-reading tasks, parsed into sections (Item 7 MD&A, Item 8 statements and notes, Item 9A controls).
- Labels for Forensics and Hindsight: 8-K Items 4.01, 4.02, 1.03; 10-K/A; SEC AAERs (the dataset behind Dechow, Ge, Larson, and Sloan 2011).

Fair access. At most 10 requests per second and a User-Agent header naming the application and a contact email. Browser JavaScript cannot set User-Agent, so every EDGAR call is server-side; the web client never talks to sec.gov. Cache aggressively and refresh from bulk files nightly. The client enforces the limit and a test proves it.

Reference documentation: `https://www.sec.gov/search-filings/edgar-application-programming-interfaces`, `https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data`, `https://www.sec.gov/about/developer-resources`.

### 8.2 Normalization (the hard part)

Filers tag the same idea differently. Revenue alone appears under several us-gaap concepts depending on era and industry. Company facts repeat across filings (a 10-K restates the prior year; a 10-K also summarizes the quarters). The normalization layer maps XBRL concepts to a canonical schema of about 60 line items (Appendix A) with:

- an ordered list of candidate tags per canonical item,
- derivation rules when no tag matches (gross profit from revenue and cost of revenue; total debt from current plus non-current plus finance leases),
- period logic: instant vs duration, fiscal years that are not calendar years, quarterly vs year-to-date durations, and a choice between the earliest-filed value ("as filed") and the latest-filed value ("as restated") for the same period,
- sign conventions,
- a quality score per company-year from the identity checks, and a quarantine list for filers whose facts do not reconcile.

Keep the raw facts with accession and filed date. Do not dedupe on `frame` alone; that discards restatement history, which is content (Restatement Autopsy).

This layer is a curated mapping table plus rules, with golden tests over a few dozen filers across industries and eras. The mapping table is the piece that needs a person with accounting judgement; the agent can propose entries from the presentation linkbase and labels, and a human approves.

### 8.3 Synthetic vs real

- Synthetic companies come from a transaction simulator: an industry template and a sequence of events (credit sales, collections, purchases, payroll, capex, depreciation, debt, interest, tax, dividends, buybacks, leases, share-based comp) producing a general ledger and three statements that balance by construction. Answer keys are exact. Manipulation injectors (capitalize operating costs, extend useful lives, channel stuffing, cookie-jar reserves, related-party sales, bill-and-hold) each have a known signature in the ratios.
- Real companies enter once they pass the identity checks. Difficulty rises with tag messiness, fiscal-year oddities, and the need to read notes.
- Delisted, bankrupt, and acquired companies stay in the data because EDGAR keeps them, and they are the best teaching material.

## 9. Content pipeline

- Generated items are unlimited (synthetic and XBRL-backed).
- Curated cases are few and expensive: bosses, guided cases, and the first hundred drills. Author them by hand.
- LLM-assisted authoring produces vignettes and interpretation questions from real filings, with human review before an item enters the bank. Difficulty is seeded by the generator and refined by play data.
- Every item carries: concept ids, band, ground-truth source, tolerance, difficulty, seed, and a verifier.

## 10. Risks and caveats

- XBRL normalization will consume more effort than any game mechanic. Budget for it and keep the quarantine list honest.
- LLM grading of prose drifts. Pin model versions, keep a human-labeled golden set, and gate releases on an agreement metric.
- The CFO agent can be gamed and can hallucinate. Constrain it to a fact sheet and check every number in its reply against that sheet before display.
- A forecasting mode can slide into a trading game. Keep the questions about reporting outcomes, not prices.
- Scope. Eleven modes is a roadmap, not an MVP. The first playable is drills plus sudoku plus forge on synthetic data.
- Trademarks. Do not use "CFA" in the product name or imply endorsement.
- Data licensing is not a risk: SEC filings and the EDGAR APIs are public domain. Fair-access compliance is the only obligation.

## 11. Technical outline for an autonomous coding agent (TDD)

### 11.1 Stack

One language for the whole repo so the agent does not context-switch. Default: TypeScript. Python (FastAPI, pytest, Hypothesis) is an equal choice and the plan below does not depend on it. Pick one and tell the agent.

- Monorepo: pnpm workspaces and Turborepo.
- Tests: Vitest for unit and property tests (fast-check), Playwright for end-to-end, a separate `evals/` suite for anything that calls an LLM.
- Backend: Node with Fastify, Drizzle ORM, Postgres (SQLite in local dev and CI).
- Frontend: React with Vite; D3 for the flow board and calibration curves; a virtualized grid component for statements and models.
- LLM: Anthropic SDK behind an interface with an in-memory fake for unit tests.
- Scheduling and ratings: `ts-fsrs` and a Glicko-2 package, both wrapped so they can be swapped.
- Data: a nightly job pulls `companyfacts.zip`, `submissions.zip`, and the quarterly Financial Statement Data Sets, normalizes, scores, and writes the item-ready store.
- Graph store: the concept graph is a YAML file loaded into memory. Neo4j is not needed for v1; revisit only if the graph grows past what a file and a topological sort handle comfortably.

### 11.2 Repo layout

```
apps/
  api/          HTTP API, sessions, queues, leaderboards
  web/          React client
  pipeline/     nightly EDGAR ingest and normalization job
packages/
  engine/       statements, identities, ratios, adjustments, screens (pure functions, no I/O)
  synth/        transaction simulator, ledger, manipulation injectors
  edgar/        SEC client: rate limiting, caching, User-Agent, typed responses
  normalize/    XBRL to canonical schema, period logic, quality scores
  puzzles/      generators and verifiers per mode
  learner/      concept graph, Glicko-2, FSRS, item selection
  grader/       deterministic graders and the LLM rubric grader
  npc/          CFO and rival agents, question classifier
  schema/       shared types, zod schemas, canonical line items, concept graph YAML
fixtures/
  edgar/        recorded API responses (small, curated)
  golden/       normalized statements for reference filers
evals/          LLM eval datasets and runners (not in CI)
docs/
  SPEC.md       this document
  INVARIANTS.md accounting identities as executable tests
  TASKS.md      ordered task list with acceptance tests
  QUESTIONS.md  questions the agent needs a human to answer
  adr/          decisions
AGENTS.md       rules for the coding agent
```

### 11.3 Invariants (the backbone of the test suite)

Write these first, as property tests against `synth` and as data-quality tests against `normalize`.

- Trial balance: debits equal credits after every event.
- Balance sheet: assets equal liabilities plus equity every period.
- Cash flow: CFO + CFI + CFF + FX effect equals the change in cash.
- Indirect CFO derived from the income statement and balance sheet deltas equals direct CFO from cash events (synthetic only).
- Retained earnings roll-forward: opening + net income - dividends +/- other equals closing.
- PP&E roll-forward: opening + capex - depreciation - disposals +/- impairments equals closing.
- DuPont: ROE equals net margin x asset turnover x equity multiplier, exactly, on average balances.
- Every generated puzzle has exactly one solution, and `verify(solve(puzzle))` holds for 1,000 seeds.
- Every injector moves its signature metric in the documented direction.
- Real company-years admitted to the item bank satisfy the balance sheet identity within 0.5 percent of total assets and the cash flow identity within 1 percent of the cash change.

Example, to set the tone for the agent:

```ts
it("balance sheet balances after every event", () => {
  fc.assert(
    fc.property(arbCompany(), (c) => {
      for (const p of c.periods) {
        const bs = statements(c.ledger, p).balanceSheet;
        expect(bs.total_assets).toBeCloseTo(bs.total_liabilities + bs.total_equity, 6);
      }
    })
  );
});
```

### 11.4 Package-by-package acceptance tests

engine

- Ratio library: each ratio is a pure function with metadata (inputs, formula string, CFA module, misleading-when notes). Tests cover a hand-computed table for one synthetic company, plus invariance properties (a dimensionless ratio is unchanged when every input is scaled by the same constant).
- Cash flow derivation from an income statement plus two balance sheets.
- Analyst adjustments: LIFO to FIFO given a LIFO reserve; operating lease capitalization for pre-2019 periods; share-based comp add-back reversal; one-time item removal.
- Screens: Beneish M-score, Sloan accruals ratio, Altman Z, Piotroski F-score, each checked against a published worked example.

synth

- The simulator emits a general ledger; statements are computed from the ledger, never hand-assembled.
- Industry templates produce ratio profiles inside expected bands (a retailer template's inventory turns fall in a retail-like range).
- Injectors are composable and reversible; applying and reversing yields the original ledger.

edgar

- A token bucket enforces 10 requests per second (a test fires 50 calls and asserts elapsed time and ordering).
- Every request carries the User-Agent header.
- A cache hit returns without network. Global fetch is replaced in test setup so any unit test that opens a socket fails.
- Typed parsers for company facts, frames, submissions, and full-text search, tested on recorded fixtures.
- A `record-fixtures` script is the only code allowed to touch the network. It is run by a human.

normalize

- Golden tests: 30 reference filers across industries and eras, normalized output compared to checked-in golden files, with a reviewed diff on any change.
- Tag fallback order is data, exercised by table-driven tests.
- Period logic: fiscal years ending in odd months; duration vs instant; quarterly vs year-to-date; earliest-filed vs latest-filed values.
- Quality scoring and quarantine.

puzzles

- Each generator is deterministic given a seed, emits a verifier, and has a difficulty estimate monotone in the number of inference steps.
- Statement Sudoku: represent the identities as a linear system over the blanked cells; a puzzle is valid iff the system has a unique solution (rank equals the number of blanks).
- Lineup: anonymization strips identifiers and rescales; the four companies are mutually distinguishable by at least two ratios.
- Forensics: the injected issue is recoverable from the emitted evidence set.

learner

- The concept graph loads, is acyclic, and every concept has at least one item type.
- Glicko-2 converges on a simulated learner of known skill within a bounded number of attempts; ratings never update from unverifiable attempts.
- FSRS scheduling matches the reference implementation on a published test vector.
- The selection policy never serves an item whose prerequisites are below threshold, and an interleaving property holds over any window.

grader

- Numeric tolerance (relative and absolute), multiple choice, set and ordered-set, grid equality with per-cell tolerance.
- The LLM rubric grader returns structured JSON (score, rubric hits, feedback). Unit tests use recorded responses. `evals/` measures agreement with a human-labeled set; the release gate is a minimum agreement statistic (for example quadratic-weighted kappa at or above 0.7).

npc

- The CFO agent cannot state a number absent from its fact sheet: a post-check extracts numbers from the reply and rejects the reply if any is missing. Evasions are drawn from a typed list.
- The question classifier maps player questions to issue ids with recorded fixtures; coverage scoring is deterministic given the classifier output.

api and web

- Contract tests per endpoint with zod schemas.
- Playwright smoke: open the app, complete one drill, solve one sudoku, see the flow animation, see the rating change.

### 11.5 Milestones as vertical slices

Each milestone ends with a demo the agent can run and a checklist a human confirms.

1. M0 Scaffold: monorepo, CI, lint, test runner, `AGENTS.md`, `INVARIANTS.md`, `TASKS.md`, empty packages each with one failing placeholder test.
2. M1 Engine and synth: invariants green; a CLI prints a synthetic company's three statements and a ratio table.
3. M2 Sudoku: generator, verifier, web grid, flow animation. Playable end to end on synthetic data.
4. M3 EDGAR and normalize: client with fixtures; nightly pipeline on bulk data; 30 golden filers; Ratio Forge on real companies.
5. M4 Learner: concept graph, ratings, FSRS, session queue; drills in a phone-width layout; Daily Filing and Lineup.
6. M5 Forensics: injectors, evidence sets, first five synthetic cases, one curated boss.
7. M6 Earnings Call and Hindsight: NPC with the fact-sheet constraint; forecast questions resolved from later filings; calibration curve.
8. M7 Model Studio and Filing Season: grid with live checks; runs with hours and loadouts; seeded leaderboards.

### 11.6 Agent operating procedure

Encode in `AGENTS.md`.

1. Take the next task from `TASKS.md`. Each task names its acceptance tests.
2. Write the tests first. Run them. They must fail for the intended reason.
3. Implement the smallest change that makes them pass. Run the package suite, then the full suite.
4. Refactor with the suite green. Commit with the task id. Mark the task done.
5. Never call the network from tests. Never hand-edit fixtures or golden files; regenerate them with the scripts and include the diff summary in the commit message.
6. All randomness is seeded. Every generator has a verifier and a seed-sweep test.
7. Any accounting identity learned while implementing goes into `INVARIANTS.md` as a test in the same commit.
8. LLM calls go through the interfaces in `packages/grader` and `packages/npc`. Unit tests use the fake. Real calls only in `evals/`, behind an environment variable.
9. When a task needs a human (a mapping decision in `normalize`, a rubric label set, a playtest), write the question to `docs/QUESTIONS.md`, stub the dependency with a clearly marked placeholder that has its own failing test, and continue with the next task.
10. Stop and ask before adding a dependency, changing the schema, or touching a golden file.

Sample `TASKS.md` entries, to show the shape:

```
[ ] T-011 synth: ledger posts double-entry events
    tests: synth/ledger.test.ts :: "debits equal credits after each event"
           synth/ledger.test.ts :: "rejects unbalanced entry"
[ ] T-012 synth: statements from ledger
    tests: synth/statements.test.ts :: "balance sheet balances every period" (property)
           synth/statements.test.ts :: "cash flow ties to change in cash" (property)
[ ] T-013 engine: indirect CFO derivation
    tests: engine/cashflow.test.ts :: "indirect CFO equals direct CFO for synthetic ledgers" (property)
[ ] T-020 puzzles: sudoku generator with uniqueness check
    tests: puzzles/sudoku.test.ts :: "every generated puzzle has rank == blanks" (1000 seeds)
           puzzles/sudoku.test.ts :: "hint names an identity, never a value"
```

### 11.7 Where the agent will need a human

- The canonical tag mapping and its exceptions. The agent proposes; a person with accounting judgement approves.
- Rubrics and the labeled set for the LLM grader.
- Boss case write-ups, which must stay inside the public record.
- Game feel: animation timing, sound, difficulty pacing. Playtests, not tests.
- Confirmation that fair-access compliance and CFA-adjacent naming have been reviewed.

---

## Appendix A. Canonical line items (subset)

Income statement: revenue, cost_of_revenue, gross_profit, sga, rnd, da, operating_income, interest_expense, interest_income, other_nonoperating, pretax_income, income_tax, net_income, net_income_to_common, eps_diluted, shares_diluted.

Balance sheet: cash, short_term_investments, receivables, inventory, other_current_assets, total_current_assets, ppe_net, operating_lease_rou, goodwill, intangibles, deferred_tax_assets, total_assets, payables, accrued, deferred_revenue, debt_current, operating_lease_current, total_current_liabilities, debt_noncurrent, operating_lease_noncurrent, deferred_tax_liabilities, total_liabilities, common_and_apic, retained_earnings, aoci, treasury_stock, nci, total_equity.

Cash flow: cfo, da_addback, sbc, working_capital_change, capex, acquisitions, cfi, debt_issued, debt_repaid, buybacks, dividends, cff, fx_effect, net_change_cash.

Each item carries: candidate tags in priority order, derivation rule, sign, instant or duration.

## Appendix B. Sample items

B.1 Statement Sudoku (Band B, early)

Given: revenue 1,000; cost of revenue 600; SG&A 250; D&A 50; tax rate 25 percent; opening retained earnings 400; dividends 30; no other items.
Blank: net income, closing retained earnings.
Solution path: gross profit 400; operating income 100; pretax 100; tax 25; net income 75; closing retained earnings 445.
Hint on stuck: "Retained earnings roll-forward."

B.2 Forensics (Band E, synthetic)

Evidence: revenue +30 percent; receivables +85 percent; DSO from 45 to 78 days; allowance for doubtful accounts down 20 percent; CFO flat.
Answer: revenue quality problem consistent with channel stuffing or premature recognition. Evidence: DSO expansion outpacing growth, an allowance moving the wrong way, cash not following earnings. Next question for the CFO: were customer payment terms extended this quarter?

B.3 Translate (Band C)

Prompt: "The company changed the estimated useful life of its data center equipment from four years to six."
Plain English: it will depreciate the same cost over more years.
Implication: lower depreciation expense and higher reported earnings with no change in cash. Check whether the change coincides with a margin miss.

B.4 Hindsight (Band E)

As of filing: FY2007 10-K for a mortgage originator. Question: probability of an 8-K Item 4.02 or a bankruptcy filing within 24 months. Resolved from EDGAR.

## Appendix C. References

Game design

- Papers, Please (Lucas Pope, 2013); Return of the Obra Dinn (Lucas Pope, 2018): inspection and deduction with commitment.
- Slay the Spire (Mega Crit, 2019); Hades (Supergiant, 2020): runs and meta-progression.
- Outer Wilds (Mobius Digital, 2019): knowledge-gated progression.
- Opus Magnum and Shenzhen I/O (Zachtronics): build, verify, compare histograms.
- Into the Breach (Subset Games, 2018): perfect-information puzzles.
- Lichess puzzle ratings; Glicko-2 (Glickman).
- Wordle (Josh Wardle, 2021); Duolingo: daily, shareable, short.
- Jenova Chen, "Flow in Games" (2006); Csikszentmihalyi, Flow (1990).
- Ryan, Rigby, and Przybylski, "The Motivational Pull of Video Games" (2006); Rigby and Ryan, Glued to Games (2011).
- Vlambeer, "The Art of Screenshake" (2013).

Learning science

- Roediger and Karpicke, "Test-Enhanced Learning" (2006).
- Cepeda, Pashler, Vul, Wixted, and Rohrer, "Distributed Practice in Verbal Recall Tasks" (2006).
- Rohrer and Taylor, "The Shuffling of Mathematics Problems Improves Learning" (2007).
- Kalyuga, Ayres, Chandler, and Sweller, "The Expertise Reversal Effect" (2003).
- Bjork, "Memory and Metamemory Considerations in the Training of Human Beings" (1994), on desirable difficulties.
- Corbett and Anderson, "Knowledge Tracing" (1995), if BKT is preferred to ratings.
- FSRS, the open-source spaced repetition scheduler used by Anki.
- Ericsson, Krampe, and Tesch-Römer, "The Role of Deliberate Practice in the Acquisition of Expert Performance" (1993).

Accounting and finance

- CFA Institute, Level I and Level II curricula, Financial Statement Analysis topic areas (2026 topic outlines: https://www.cfainstitute.org/sites/default/files/docs/programs/cfa-program/2026-l1-topics-combined.pdf).
- Beneish, "The Detection of Earnings Manipulation" (1999).
- Sloan, "Do Stock Prices Fully Reflect Information in Accruals and Cash Flows about Future Earnings?" (1996).
- Altman (1968); Piotroski (2000).
- Dechow, Ge, Larson, and Sloan, "Predicting Material Accounting Misstatements" (2011).
- Schilit, Financial Shenanigans. Mulford and Comiskey, The Financial Numbers Game.

EDGAR

- API documentation: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- Accessing EDGAR data and fair access: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
- Developer resources: https://www.sec.gov/about/developer-resources
- Full-text search: https://efts.sec.gov/LATEST/search-index
- Financial Statement Data Sets: SEC Division of Economic and Risk Analysis (search sec.gov for the current page).