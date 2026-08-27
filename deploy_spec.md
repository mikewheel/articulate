# Deploying Articulate to AWS

Design spec v0.1 — companion to `spec.md`. How the local prototype becomes
`https://articulate.michaelwheeler.ai`, provisioned through
[`mikewheel/cloud-account-foundry`](https://github.com/mikewheel/cloud-account-foundry),
for under a dollar a month of AWS spend.

## 1. Goals and constraints

- **Audience**: a portfolio project. Fewer than 100 people will ever touch it;
  Michael is the only regular user. Traffic is effectively zero most days.
- **Cost**: pennies to low dollars per month. No always-on compute unless it
  buys real simplicity. Anthropic API usage is the one genuinely variable cost
  and gets its own controls (§6).
- **Domain**: `articulate.michaelwheeler.ai` with TLS.
- **Operations**: one maintainer who does not want to patch servers. Deploys
  happen from GitHub Actions in this repo via OIDC — no long-lived AWS keys —
  exactly the pattern the foundry already establishes for downstream repos.
- **Provisioning**: the AWS account, Terraform backend, and this repo's deploy
  role all come from the foundry's manifest-driven control plane. This spec
  deliberately frames every step as "what the foundry gives us" vs "what we
  build in this repo" vs "what the foundry is missing" (§7).

## 2. What the app needs from a host

From the current codebase (see `docs/DATA_MODEL.md`):

| Concern | Today (laptop) | Property that matters for hosting |
|---|---|---|
| Web/API | FastAPI + uvicorn, one process | Stateless request handling, Python 3.12+ |
| Game content | `articulate.db` content tables, rebuilt from JSON | **Read-only at runtime** — can ship inside the deploy artifact |
| Player state | Same SQLite file: `players`, `attempts`, `concept_mastery`, `review_schedule`, `call_transcripts` | The only **writes**; tiny volume (rows per click, one regular player) |
| LLM calls | `ANTHROPIC_API_KEY` from `.env`; mock fallback | Server-side secret; per-request cost; abuse surface |
| Bulk data (`data/`) | 3GB companyfacts + edgar_bulk.db | **Not needed at runtime** — only by generators that write `content/` JSON. Stays a laptop/CI concern |
| Static frontend | Served by FastAPI from `web/` | Cacheable |

The schema was built with a content/player-state split from day one, so the
serverless adaptation below is contained: swap the player-state tables behind a
small store interface, leave everything else alone.

## 3. Recommended architecture: serverless, scale-to-zero

```
Route53/DNS ──► CloudFront (TLS via ACM, caches /static/*)
                    │
                    ▼
              Lambda Function URL ──► FastAPI app (Mangum adapter, zip package)
                                        ├─ content: SQLite file bundled read-only in the package
                                        ├─ player state: DynamoDB (on-demand, single table)
                                        └─ Anthropic Messages API (key from SSM/env)
```

**Why this shape.** At near-zero traffic, anything always-on is the entire
bill. Lambda + DynamoDB + CloudFront all sit inside always-free tiers at this
usage, so the floor cost is DNS + storage residue. Cold starts (~1–2s for a
zip-packaged FastAPI app) are irrelevant for a portfolio audience of one.

**Component choices, and what they rule out:**

- **Lambda, zip-packaged (not container image).** Pure-Python deps (fastapi,
  mangum, anthropic, httpx, boto3) plus the ~5MB content SQLite fit far under
  the 250MB unzipped limit. Zip also dodges a real foundry constraint: the
  per-repo deploy role has **no `ecr:*`** (§7, gap 5), so container-image
  Lambdas can't even be pushed from this repo today.
- **Function URL behind CloudFront**, not API Gateway. Function URLs are free;
  API Gateway would add $1.00/million requests and a second custom-domain
  mechanism. CloudFront provides the TLS custom domain, caches `/static/*` and
  `GET /` (the app already serves immutable-ish assets), and keeps the Lambda
  origin locked down via OAC (SigV4 to the Function URL) so the function is not
  directly reachable.
- **DynamoDB on-demand for player state.** Single table, keyed
  `PK=player#<id>`, `SK=attempt#<ts>` / `mastery#<concept>` /
  `review#<item>` / `call#<scenario>#<turn>`. The access patterns in
  `mastery.py`/`app.py` are all per-player lookups — a textbook single-table
  fit. Writes at human click-rate cost fractions of a cent per month.
- **Content SQLite ships in the artifact.** CI runs `scripts/build_db.py`
  against `content/` and bundles the resulting content-only DB. A deploy IS a
  content release — same philosophy as today (`content as JSON in git, DB as
  build artifact`), now with the artifact immutable per deploy.
- **Rejected: EFS-mounted SQLite** (adds VPC + mount targets + ~$0.30/mo floor
  and cold-attach latency for zero benefit at this scale), **App Runner**
  (~$5/mo idle floor), **Fargate** (~$9/mo always-on).

**Cost estimate (us-east-1, monthly):**

| Line | Est. |
|---|---|
| Lambda (always-free: 1M req + 400k GB-s) | $0.00 |
| CloudFront (always-free: 1TB egress, 10M req) + ACM cert | $0.00 |
| DynamoDB on-demand + storage (<1GB) | ~$0.02 |
| S3: deploy artifacts + TF state (baseline bucket exists) | ~$0.03 |
| CloudWatch logs (14-day retention set explicitly) | ~$0.05 |
| SSM standard parameters (API key) | $0.00 |
| Route53 hosted zone — **only if** we delegate the subdomain (§5) | $0.50 |
| **AWS total** | **~$0.10–0.60** |
| Anthropic API (the real variable): ~$0.02–0.05 per LLM-graded answer / CFO turn at claude-opus-4-8 prices | usage-driven; capped by §6 |

**Fallback option, documented for honesty:** a Lightsail $3.50/mo instance (or
t4g.nano + EBS ≈ $4) runs the app *exactly as it exists today* — SQLite on
disk, uvicorn, Caddy for TLS — zero code changes. Choose it only if the
player-state port (§4) turns out unpleasant; it trades ~$40/yr and OS patching
for skipping ~a day of code. The serverless path is the recommendation.

## 4. Code changes required in this repo

1. **Player-state store interface** (`src/articulate/state_store.py`): extract
   the ~10 SQL touchpoints for the five player tables behind a
   `SqliteStateStore` (default, keeps local dev and all 51 tests unchanged)
   and a `DynamoStateStore` (Lambda). Selected by env var. The content-table
   reads (`items`, `levels`, `concepts`, `facts`, `call_scenarios`) stay
   SQLite everywhere.
2. **Lambda entrypoint**: `handler = Mangum(app)`; add `mangum` to
   requirements. The `.env` loader already yields to real env vars, so Lambda
   env config Just Works; `ANTHROPIC_API_KEY` arrives via SSM→env at deploy.
3. **CI build step**: `build_db.py` (content only) → zip with deps → S3 →
   `aws lambda update-function-code`. Terraform owns everything except the
   code blob (standard `ignore_changes` on `s3_key`/version, or
   plan+apply on infra changes and a fast code-only lane).
4. **Access + budget guard** (§6): invite-code check and a DynamoDB-backed
   daily LLM budget counter — both tiny middleware.
5. **`infra/` Terraform**: Lambda, execution role, Function URL, CloudFront +
   OAC, ACM cert (us-east-1), DynamoDB table, log group with retention, SSM
   parameter references. State goes to the baseline-provisioned bucket
   (`TF_STATE_BUCKET`/`TF_LOCK_TABLE` repo variables, per the foundry's
   generated-workflow convention).

Estimated scope: the state store is the only real work; the rest is boilerplate.

## 5. DNS and TLS

`michaelwheeler.ai` is not managed anywhere in the foundry (§7, gap 4), so two
workable wirings — **open question for Michael which applies** (§8):

- **Option A — record in the existing DNS host** (wherever the apex lives
  today, e.g. the registrar or a Route53 zone in another account): one CNAME
  `articulate` → the CloudFront distribution domain, plus one CNAME for ACM
  DNS validation. Cheapest ($0), two manual records, done.
- **Option B — delegate the subdomain**: create a Route53 hosted zone for
  `articulate.michaelwheeler.ai` in the articulate account (Terraform-managed,
  +$0.50/mo) and add its four NS records at the parent once. After that, all
  DNS for the project is code in this repo — cert validation, future records,
  no more parent-zone touches.

Recommendation: **B** if the parent zone is annoying to touch or Michael wants
the project self-contained; **A** if pennies matter more than tidiness.

## 6. Access control and LLM cost safety

A public endpoint that fans out to claude-opus-4-8 is a "free tokens for
strangers" faucet. Defense in depth, all cheap:

1. **Invite code**: `ARTICULATE_INVITE_CODE` env var; the UI asks once and
   stores it alongside the player handle; the API requires it on the three
   LLM-backed routes (rubric grading, CFO ask, classifier) and optionally on
   `/api/attempt` generally. Deterministic graders can stay open — they leak
   nothing and cost nothing. Portfolio viewers still see the full game; they
   only need the code (shared in Michael's resume/link) to play LLM items.
2. **Daily budget breaker**: a DynamoDB counter of LLM calls/day; past N
   (say 300), the app flips to the offline mock — which the codebase already
   treats as a first-class degradation mode (`llm_mock` provenance, UI badge).
3. **Anthropic-side cap**: workspace spend limit in the Anthropic console
   (manual, §8) as the true backstop.
4. **No WAF**: at $5+/mo it costs more than the rest of the stack combined;
   CloudFront default protections + the above are proportionate to the risk.

## 7. The foundry: what it gives us, and the gaps found

### What the foundry provides out of the box

- `projects/articulate.yaml` manifest → **Deploy AWS Foundation** workflow
  creates a dedicated `articulate` child account (Organizations), tags it,
  and baselines it: Terraform state bucket + lock table, and a **per-repo
  OIDC deploy role** trusted for `repo:mikewheel/articulate:*` — no
  long-lived keys anywhere. The role's policy already covers most of §3:
  `lambda:*`, `s3:*`, `dynamodb:*`, `logs:*`, `cloudwatch:*`, `ssm:*`,
  `secretsmanager:*`, `events:*`, plus scoped IAM role/policy management with
  a deny-wall around foundry-managed roles.
- Downstream-repo wiring that sets the Actions variables this repo's deploy
  workflow will consume: `DEPLOY_ROLE_ARN`, `AWS_ACCOUNT_ID`, `AWS_REGION`,
  `TF_STATE_BUCKET`, `TF_LOCK_TABLE`.
- Terratest verification of the account + baseline, and agent skills that
  document the agent-vs-human split for every step.

### Gaps and friction found (each with a proposed fix)

1. **`provision-repos.sh` hard-fails on pre-existing repos.** Step 1 treats
   "repository already exists" as an error (`FAILED_REPOS`), so the AWS
   track cannot *adopt* `mikewheel/articulate`, which exists. Meanwhile the
   Snowflake track's shared `ensure-repo.sh` already has the right semantics
   ("created"/"exists", no-op when present). **Fix**: have the AWS
   provisioning script use `ensure-repo.sh`; on `exists`, skip the starter
   Terraform/workflow commit but still set the five Actions variables.
   **Workaround meanwhile**: put the `github:` block in the manifest anyway —
   the *baseline* still creates the OIDC role (it's manifest-driven, not
   repo-driven) — and set the five variables on this repo by hand with `gh`.
2. **The repo deploy role is missing `iam:PassRole`.** The legacy
   `TerraformDeploymentUser` policy has it, but the OIDC role's
   `AllowProjectDeployment` list does not — and `lambda:CreateFunction`
   requires passing the execution role, so any Lambda deploy from a
   downstream repo fails today. **Fix** (small foundry PR): add
   `iam:PassRole` to the role policy, ideally conditioned
   `iam:PassedToService = lambda.amazonaws.com` to keep the
   privilege-escalation posture.
3. **No `cloudfront:*` or `acm:*` in the deploy role.** The custom-domain
   HTTPS front door in §3 is undeployable from this repo until they're added.
   **Fix**: extend `AllowProjectDeployment` with `cloudfront:*` and `acm:*`
   (ACM is regionally quirky — cert must be in us-east-1 for CloudFront,
   which is conveniently the foundry default region).
4. **The foundry has no DNS story.** No `route53:*` in the deploy role, no
   hosted zones anywhere in the stacks, and `michaelwheeler.ai`'s parent zone
   lives outside the foundry entirely. **Fix, minimal**: add `route53:*` to
   the deploy role to unblock Option B's project-local zone. **Fix, proper
   (future foundry work)**: a `dns:` manifest block — parent zone location +
   subdomain delegations the baseline creates — so "give project X
   subdomain Y" becomes declarative like everything else.
5. **No `ecr:*` in the deploy role** — container-image Lambda/ECS paths are
   blocked from downstream repos. Not needed for this spec's zip path, but
   worth noting in the policy docs so the constraint is discoverable *before*
   someone designs around images (or add `ecr:*` alongside fix 2/3).
6. **No downstream secrets pattern.** The foundry wires variables but has no
   convention for runtime secrets like `ANTHROPIC_API_KEY`. This spec uses a
   GitHub Actions secret → Terraform → SSM SecureString + Lambda env, set
   once by hand. A foundry-level convention (e.g. "downstream repos get an
   SSM path `/apps/<project>/*` and the deploy role gets `ssm:PutParameter`
   scoped to it" — the role already has `ssm:*`, so really just a documented
   convention) would remove the improvisation.
7. **Minor**: the auto-generated starter workflow is Terraform-only
   (plan-on-PR / apply-on-main). This app also needs a build-artifact step
   (content DB + zip). Not a blocker — this repo authors its own workflow —
   but if the foundry grows more app-shaped projects, a second starter
   template ("terraform + build artifact") would fit its philosophy.

## 8. Rollout plan

Phased, in the foundry's agent-vs-human idiom. Phases 2–5 are a day or two of
work total; phase 1 is minutes once the open questions are answered.

| # | Step | Agent can do | Human (Michael) must do |
|---|---|---|---|
| 0 | Answer open questions below | — | ✅ |
| 1a | Foundry PR for gaps 1–4 (PassRole, cloudfront/acm/route53, ensure-repo adoption) | ✅ author + merge | review |
| 1b | `projects/articulate.yaml` manifest; dispatch **Deploy AWS Foundation**; verify | ✅ | supply a unique `account_email` |
| 1c | Set the five Actions variables on this repo (workaround for gap 1 if 1a not merged) | ✅ `gh variable set` | — |
| 2 | Code: state-store interface + Dynamo impl + Mangum + guards (§4, §6), with tests offline as ever | ✅ | — |
| 3 | `infra/` Terraform + deploy workflow in this repo | ✅ | — |
| 4 | Secrets: `ANTHROPIC_API_KEY` as repo Actions secret; Anthropic workspace spend cap | ✅ set from local `.env` if authorized | set the spend cap (console) |
| 5 | DNS: Option A records at the parent, or Option B NS delegation | Option B zone via TF ✅ | the one parent-zone/registrar edit |
| 6 | Deploy, smoke-test `https://articulate.michaelwheeler.ai`, play a level | ✅ | enjoy |

### Open questions for Michael

1. **Account email** — a unique address for the new AWS account
   (plus-addressing like `mbw+articulate-aws@mbw.dev` is fine if your mail
   accepts it).
2. **Where does `michaelwheeler.ai` DNS live today** (registrar? a Route53
   zone in some account — e.g. wherever `travel.michaelwheeler.ai` points)?
   Decides Option A vs B in §5.
3. **Invite-gate scope** — LLM routes only (recommended: viewers can play all
   deterministic content anonymously) or the whole game behind the code?
4. **OU + tags** — which organizational unit the account lands in, and any
   tag conventions you want on it.
5. **Anthropic key** — reuse the current key or mint a per-deployment key in
   its own workspace (recommended: separate workspace = separate spend cap
   and revocability).

## 9. Out of scope for this spec

- The bulk-data pipeline (`data/`, 3GB) stays local/CI-only; regenerating
  `content/items/daily_generated.json` remains a laptop task that lands as a
  normal content commit → deploy.
- Multi-region, autoscaling concerns, real auth (Cognito etc.), CDN cache
  invalidation strategy beyond "new deploy, new artifact".
- Snowflake: the game has no analytical workload that justifies it. If a
  play-analytics itch develops, the foundry's Snowflake track can add a
  database later; nothing here forecloses it.
