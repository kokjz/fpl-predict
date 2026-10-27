# Optional architect/programmer workflow

Updated **27 October 2026**. This supersedes the earlier assumption that the
Windows takeover would be managed entirely by one Claude Sonnet session. One
capable coding chat remains a supported fallback; no automatic orchestration,
cross-chat messaging or model switching is introduced.

## Assessment and suggested allocation

The split is reasonable as a workflow trial. The user selected **Claude Opus5.5
/ Medium**, including initial intake/setup, with **High as needed** for a
specific harder question within that architect conversation. This supersedes
the earlier Sonnet-first recommendation; read
[ARCHITECT_MODEL_POLICY.md](ARCHITECT_MODEL_POLICY.md). Use GPT-6.1 Sol
for implementation, local execution, tests, audits, documentation and Git/PR
work. A programmer also exercises engineering judgment; an architect is not an
oracle or a replacement for original evidence. These are assistance roles, not
changes to the FPL prediction model or production policy.

OpenAI describes GPT-6.1 Sol as suitable for complex coding while balancing cost;
its documented default reasoning effort is Medium. Anthropic positions Opus5.5
for complex sustained judgment and Sonnet5.5 for faster scoped work. Neither
publisher establishes superiority on this project's ML planning or implementation.
Actual model/effort/account/tool availability must be verified by each chat.
[OpenAI model](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
[OpenAI selection guidance](https://developers.openai.com/api/docs/guides/model-selection),
[Anthropic Sonnet](https://www.anthropic.com/claude-sonnet-5-5),
[Anthropic Opus](https://www.anthropic.com/claude-opus-5-5).

At the checked date, standard API input/output prices per million tokens are
Sol $2/$10, Sonnet $2/$10 and Opus $4/$20. Equal nominal prices do not measure
tokens/rework per task, and API prices do not determine subscription allowance.
Claude Pro usage is shared across its chat/Code surfaces. There is no measured
FPL-project saving or quality ranking between these LLMs yet. Do not promise
one, buy credits, invoke paid APIs or switch plans/models automatically.
[Sol pricing](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
[Anthropic pricing in announcement](https://www.anthropic.com/claude-sonnet-5-5),
[Pro usage](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan).

See [the claim-by-claim review](HYBRID_CLAIMS_REVIEW.md) for model-version,
DeepSWE, cache-pricing and ML-scope qualifications. Matching cache-hit prices do
not establish a Sol-versus-Sonnet cost advantage, and caches are not shared
between vendors. No feature-engineering or tuning task is authorised by an
outside model's illustrative example.

For active research days, the complete gameweek cycle and two-way release/defect
handoffs, read [OPERATING_CADENCE.md](OPERATING_CADENCE.md). Neither workstream
requires daily retraining or a routine architect hop for weekly squad planning.

## Roles and boundaries

| Role | Owns | Boundaries |
|---|---|---|
| Architect: user-selected Opus5.5 / Medium; High as needed | Research question, origin-safe feature/data design, chronological validation, declared comparisons/gates, scope/budgets, result interpretation and next-package recommendation | Reads verified evidence; does not start an unapproved search, rewrite outcome-dependent criteria, operate a second code writer or confer production approval |
| Programmer: user-selected GPT-6.1 Sol | Implement the authorised package; validate data/source, run bounded commands/audits, preserve failures, test, inspect diffs/privacy, commit/push/PR/review/merge/cleanup and produce evidence | Flags scientific/design conflicts; does not silently change the hypothesis, cohorts, budget, fit scope, primary comparison or approval status |
| Weekly planner | Authorised squad/transfer/captain/bench/chip planning and finalised-GW review | Uses reviewed remote main plus approved private registry/artifact; no independent engine tuning/promotion |
| User | Goals, permissions, model/account choice and resolution of genuinely material unresolved choices | No repeated permission request for already authorised routine work |

No LLM opinion, cross-model agreement or code merge is a model/policy promotion.
Existing scientific, artifact, error/decision/integrity and Git gates remain.
Independent arithmetic checks still matter; two LLMs seeing the same reused
outcomes do not provide a new independent season or a causal experiment.

## One canonical package, one implementation writer

Use one private coordination directory outside the public checkout, for example
`coordination/`. Actual briefs/results can include private paths or manager
context, so keep them private. Only the empty reusable templates here are public.

- `ACTIVE_PACKAGE.json`: package ID, brief revision/hash, source base/head,
  branch/PR, source-lock status, approved artifact hash, current owner, status,
  next action and evidence locations.
- `PACKAGE_BRIEF.md`: complete authorised specification and acceptance criteria;
  start from [the template](templates/PACKAGE_BRIEF_TEMPLATE.md).
- `RESULTS_PACKET.md`: run/test/evidence inventory, every effect/loss/failure,
  deviations and exact remaining work; use [the template](templates/RESULTS_PACKET_TEMPLATE.md).
- `DECISION_LOG.md` and `RESUME_CURRENT.md`: dated decisions, reasons, latest
  source/model state and compact next-step context. Never erase a rejected trial.

Before acting, both chats read the active package and verify its ID/revision/hash
and current source against the actual repository. Chat memory and an old copied
message are not the source of truth. The programmer owns the research worktree
and runs. The architect normally reads evidence and writes its owned private
planning/interpretation notes. Do not have both editing the same checkout or
coordination file at once. Transfer ownership explicitly between logical stages;
use a separate clean source view for reading if another task owns the worktree.

If the chats do not share a filesystem, the user transfers the small versioned
brief/results packets privately. Attach source/data/artifact hashes and required
evidence excerpts, never just an unversioned prose summary. Missing execution
access does not prevent planning, but that chat cannot claim it ran tests or
performed Git operations. The architect must request/read underlying evidence
when needed to judge an anomaly, not blindly accept a favourable summary.

## Package cycle

1. **Design or reuse the existing design.** Architect records one bounded brief
   before new outcome-dependent experiments. Preserve the user-authorised scope,
   primary comparator, chronological splits, source/data clocks, fit/search limits
   and existing gates. Record unresolved assumptions. Existing PR42 fixes already
   have an authorised plan; another architect round is not a prerequisite to
   begin those routine fixes.
2. **Implement and execute.** Programmer verifies the accepted brief/source, then
   completes coherent code/tests/docs in the appropriate existing or fresh PR.
   Log ordinary engineering choices and proceed. Do not route every file, commit
   or test to the architect. If a scientific change is necessary, record a narrow
   deviation/question before dependent new work and resolve it with the user's
   designated architect or user; continue unaffected work.
3. **Return evidence.** Programmer writes a compact results packet containing
   exact commits, model/data hashes, commands, measured resources, test results,
   aggregate and all-case comparisons, failures, coverage and unknown bounds.
   Larger immutable logs/data stay on disk behind hashes/indexes. No invented
   token usage, unrun forecasts or retrospective best-run selection.
4. **Interpret at a logical checkpoint.** Architect reviews the declared question
   using that evidence, including losses, uncertainty, reused years and changed
   assumptions. Record acceptance/rejection/remaining uncertainty and any bounded
   next proposal. This is scientific review, not automatic registry promotion.
   If an optional architect review is unavailable, label it pending; routine
   already-authorised fixes/tests/PR preparation can continue. Never falsely
   claim cross-model review or create a new mandatory approval for every change.
5. **Release and hand off.** Apply normal diff/privacy/check/merge/source-sync and
   branch cleanup SOP. Code release, research qualification and artifact/policy
   promotion have separate recorded states. Update private operational context
   and the weekly release handoff. User-authorised source/model compatibility
   checks precede any weekly advice.

## Usage economy and safety

Keep architecture exchanges at experiment/package boundaries. Send the architect
a concise brief/results packet first; retrieve the full evidence only as needed.
Keep the programmer's source/test context separate from long planning debates.
Both use staged loading, bounded tool output and durable on-disk resume notes.
Before compaction or changing chats, save hashes/owner/process handles and next
commands; after resuming, revalidate actual source/process state before retries.
No automatic agents, inter-chat messages, cloud bridge or paid API router.

Prefer a shared local verified Windows/WSL workspace for the current POSIX
watchdog, subject to each application's real access. Model choice does not fix
path/runtime compatibility. Preserve original records; derived relocation files
get new provenance. Do not copy native environments or change resource guards.

Assess the workflow on the next already-authorised package: record actual
elapsed implementation/review time, avoidable rework, defects caught, handoff
overhead and available per-product usage readings. Missing token/usage telemetry
is unknown; mixed account activity makes quota percentages confounded. Compare
with prior comparable work cautiously, without rerunning scientific studies just
to evaluate the LLM workflow. Keep the split when useful; use one chat for small
tasks when handoff overhead dominates. No benchmark claim is needed to try it.

The immediate research checkpoint remains unchanged: all20new+24retained paths
are complete, calibration fails season-points qualification, approved1.0.0 is
unchanged, and PR42 review fixes/valid-state audits/final publication remain.
