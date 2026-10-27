# Daily and gameweek operating workflow

Updated **27 October 2026**. This guide connects iterative engine improvement
with weekly squad planning. Read [HYBRID_WORKFLOW.md](HYBRID_WORKFLOW.md) for
role boundaries and [WEEKLY_SOURCE_SYNC.md](WEEKLY_SOURCE_SYNC.md) for the
mandatory source/artifact preflight. These are user-triggered workstreams;
no daily job, automatic messaging, account action or monitoring is configured.

## Two workstreams, separate responsibilities

| Role | Responsibility | Normal involvement |
|---|---|---|
| Architect, user-selected Opus5.5 / Medium | Bounded research design, chronological validation, result interpretation and next-package priority | Initial setup and normal checkpoints at Medium; High as needed within the architect conversation |
| Programmer, intended GPT-6.1 Sol | Implementation, bounded runs, independent audits, tests, coherent commits/PRs and release handoff | Throughout the authorised research package; one implementation writer |
| Weekly planning chat, normally user-selected GPT-6.1 Sol / Medium | News, approved-model forecasts, transfers, selection, captaincy, chips and finalised-GW assessment | Each authorised planning/review cycle; no routine architect handoff required |
| User | Confirmed manager state and execution, goals and unresolved material choices | Team updates and cross-chat/device handoffs where required |

Verify actual model, role and access; these intended choices do not establish
vendor superiority. Small engineering fixes may stay with one capable chat.
There is no requirement to run an experiment, retrain or consult the architect
every day. A research package need not finish within one gameweek.

## Active research days and package cycle

1. **Resume safely.** Read the one canonical private coordination packet:
   ACTIVE_PACKAGE.json, versioned/hashed PACKAGE_BRIEF.md and RESUME_CURRENT.md.
   Verify source, owner and actual process state before writing or retrying work.
   Retrieve relevant original evidence in stages rather than ingesting all logs.
2. **Define or reuse one bounded design.** The architect records the hypothesis,
   data/source clocks, chronological splits, comparator, acceptance gates,
   permitted fits/search and resource limits before outcome-dependent work.
   Existing authorised repairs do not require redesign or per-commit approval.
3. **Implement and evaluate.** The programmer owns the worktree and executes
   the agreed scope, testing and committing/pushing at coherent milestones.
   Check storage/resource limits during active jobs. Preserve failures and all
   comparison cases. Resolve material scientific deviations before dependent
   new work while continuing unaffected engineering.
4. **Review evidence at a logical boundary.** Write RESULTS_PACKET.md with exact
   commits, artifact/data hashes, commands, all results/losses, resources,
   limitations and remaining work. The architect checks underlying evidence
   where needed and interprets season-level decision value, point/probability
   quality, downside and compute cost. Better component error alone is not
   sufficient proof of better squad management.
5. **Release and record approval scope.** The programmer resolves findings,
   reviews the diff/privacy, completes required checks, merges and synchronises
   main, then cleans branches only after dependency checks. Update the private
   operational handoff and the public result/status documentation as appropriate.
   Record code release, research qualification and model/policy approval
   separately. A useful negative experiment can be a completed release.
6. **Leave a restart record.** Update private context, decisions and resume notes
   with current ownership, source, process handles, completed checks and next
   action before stopping, compaction or switching chats. Do not claim an
   architect review happened if it remains pending.

Choose the next package from supported defects and research evidence. Do not
retune on inspected outcomes and call them untouched. Retraining or promotion
requires justified chronological validation and the existing point-relevance,
season-management and integrity gates appropriate to its scope. One bad GW
does not automatically justify either. Live results support ongoing review;
they are not a completion dependency for historical research packages.

## Weekly squad-planning cycle

The timings below are relative to the **verified actual deadline**, not fixed
weekdays; compressed schedules may combine stages. Display UK and Singapore
time when giving a deadline. Preserve unknown selling prices, pending transfers
and other unconfirmed manager facts.

| Stage | Work | Durable output |
|---|---|---|
| After official GW finalisation | Score the forecasts actually frozen before deadline against confirmed outcomes and the predesignated baseline. Assess the actual executed squad separately from hypothetical or fixed-squad benchmarks. Separate forecast/minutes issues, transfer/selection/chip decisions and ordinary match variance. | Dated review, original snapshot references and any supported defect packet |
| Early or midweek | Confirm squad, bank, free transfers and chips. Refresh current-season rules, fixtures, relevant blanks/doubles and available club/league news. Review provisional transfers and multi-GW/chip scenarios within approved policy scope. | Provisional plan, uncertainties and explicit conditions for revision |
| Close to deadline | Refresh injuries, suspensions, likely minutes, press updates, prices and confirmed manager changes. Rerun affected scenarios using the approved model and permitted manual sensitivities. | One recommended transfer/XI/captain/vice/bench/chip plan plus relevant alternatives and change conditions |
| Before deadline | Freeze inputs/news evidence, forecasts, selected primary comparison and recommendations with source/model hashes and input/generation/deadline timestamps. Recheck remote source and private registry before final advice; preserve and identify earlier runs if anything changes. | Auditable pre-deadline decision record |
| After user execution confirmation | Record transfers, prices, selection and chips actually confirmed. Keep recommendations distinct from actions and retain earlier snapshots. | Updated confirmed manager state for the next cycle |

Inspect new screenshots under the standing workflow: name by displayed GW/type,
preserve bytes and original/new checksums, avoid overwrites, and archive only
after that GW is confirmed concluded during a subsequent authorised review.

Before **every model-analysis invocation**, including finalised-GW review and
each forecast/sensitivity/horizon/chip/selection run, fetch and safely synchronise
a clean reviewed main to origin/main, verify exact equality, and independently
verify the approved private registry/artifact/runtime and release handoff. Record
the source/model/input clocks. Preserve dirty/diverged/other-chat work or use a
separate clean reviewed checkout; never force/reset over it. Resolve freshness
or compatibility problems before claiming latest-source analysis.

Plan several GWs ahead with a remaining-season transfer/chip resource view,
execute the current decision and revise as information changes. Optional research
policies remain within their explicit qualification/approval scope; merging
infrastructure does not make it a weekly default. The weekly chat records engine
defects but does not independently tune, retrain, promote or edit engine source.

## Handoffs between improvement and planning

**Weekly planning to improvement:** keep a compact private, versioned defect
packet with expected versus observed behaviour, affected player/GW/fixture IDs,
frozen input/forecast/source/model hashes and clocks, confirmed outcomes,
reproduction details and uncertainty. The architect prioritises a bounded
investigation; an observed miss is evidence to diagnose, not proof of a bug.
Keep personal squad/history outside the public repository.

**Improvement to weekly planning:** provide the merged source commit, approval
scope, evidence/limitations, whether weights changed, approved model/version/hash,
dependency/schema/command changes, migration steps and the next weekly action.
Publish non-private source/docs through the reviewed PR. Private registries,
artifacts and operational context use an explicitly private channel. A pull
does not transfer private weights or manager context. If weights are unchanged,
say so; if required approved assets are unavailable, resolve compatibility
before using the release for analysis.

Use shared files or user-facilitated private transfer. There is no automatic
cross-device filesystem sync or cross-chat delivery. Both research roles share
one active coordination packet, with explicit ownership and revision/hash;
the weekly chat uses its own manager context and a released-source checkout.
For usage economy, keep architecture exchanges at meaningful boundaries,
retrieve only needed evidence and record available usage honestly; no fixed
token allowance or measured workflow saving is promised.

## Immediate receiving checkpoint

A short Opus5.5 / Medium architect intake can confirm the existing brief.
Read ARCHITECT_MODEL_POLICY.md; the earlier Sonnet-first intake is superseded. The programmer
then qualifies receiving source/runtime/private artifact and completes the
already-authorised PR42 R1/R2/R3 repairs, valid-state tests and negative-result
publication. Routine repairs need no new architecture gate. All20new+24retained
historical paths are complete; do not rerun them or fit a new candidate merely
for migration. Calibration failed season-points qualification. Approved
forecaster1.0.0 is unchanged; consult the current registry/checkpoint for its
immutable hash and any later explicitly recorded promotion.
