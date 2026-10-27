# Market-implied team strength: Stage-B result

**Gate B passes in both development folds. Stop for architect review before
Stage C.** The market arm has lower held-out team-goal Poisson deviance than
both fixed controls in each fold. This is a component result; no player-point,
season-management, approved-model or weekly-default qualification follows.
Approved forecaster 1.0.0 and its artifact remain unchanged.

The [full scalar results](market_strength_stage_b_results_2026-10-28.json) retain
every arm, diagnostic, block and resource result. The
[Stage-B protocol](market_strength_stage_b_protocol_2026-10-28.json) was committed
at `44d69f2e843edea4f056dd1d86d0d7e8a91a5923` before any real feature/cohort/model
calculation, LF SHA256
`2bff608e5cf10aadbcbfc7f01e08110c3a917c8b7e3f2bf4445d831af2e8200d`.
Numerical implementation source is
`c2dfbe490a01d56f206d72133a3533decf41e720`; later reporting commits do not replace it.
The original [admission protocol](market_strength_protocol_2026-10-28.json)
remains unchanged.

## All six declared fits

| Test season | Arm | Train rows | Test rows | Poisson deviance | Clean-sheet Brier | Rate calibration slope | Rate intercept |
|---|---|---:|---:|---:|---:|---:|---:|
| 2022/23 | C | 1,520 | 760 | 1.238266412 | 0.193423021 | 0.942078101 | 0.123297028 |
| 2022/23 | U | 1,520 | 760 | 1.228277646 | 0.191994157 | 0.870353572 | 0.191149863 |
| 2022/23 | M | 1,520 | 760 | **1.216549254** | **0.190356943** | 0.937654392 | 0.124976615 |
| 2023/24 | C | 2,280 | 760 | 1.135871853 | 0.161165419 | 1.007600686 | 0.193891660 |
| 2023/24 | U | 2,280 | 760 | 1.128871579 | 0.160614525 | 1.012150922 | 0.202316952 |
| 2023/24 | M | 2,280 | 760 | **1.089205763** | **0.159174136** | 0.974478948 | 0.211339259 |

C uses the incumbent team/opponent EW(4,12) realised goals, season reset and
prior 1.35 with mass 4. U adds Understat xG/xGA with **that same operator**.
The frozen I4 source is reused, not its arithmetic window definition. M adds
natural logs of market-implied goals for and against. Each arm includes home
and a fitted intercept, train-only standardisation and one unregularised
Poisson GLM with the declared settings. There was no tuning, extra seed, arm,
imputation, row drop or refit. The six fits used 14–48 iterations each.

Rate calibration is the predeclared algebraic OLS diagnostic
`actual_goals ~ intercept + predicted_goals`, not another fitted log-link GLM.
Clean-sheet Brier evaluates `exp(-predicted_goals)` against zero goals for the
opponent's clean sheet. The complete two-sided fixture cohort gives the same
aggregate Brier after swapping team/opponent roles. These diagnostic choices
were frozen before scoring and do not alter Gate B.

All arms underpredict the higher 2023/24 scoring level: actual mean goals per
team-match are 1.639474, versus prediction means C 1.434677, U 1.419904 and
M 1.465536. Lower deviance does not establish complete calibration.

## Paired four-GW diagnostics

Negative differences favour M. Intervals use the fixed calendar blocks and
delete-one-block jackknife specified before scoring, with no random seed.

| Test season | Comparison | Mean deviance difference | Descriptive 95% interval |
|---|---|---:|---:|
| 2022/23 | M − C | −0.021717158 | [−0.062013523, +0.018579207] |
| 2022/23 | M − U | −0.011728392 | [−0.055196015, +0.031739231] |
| 2023/24 | M − C | −0.046666090 | [−0.075917890, −0.017414289] |
| 2023/24 | M − U | −0.039665816 | [−0.065385502, −0.013946129] |

The 2022/23 intervals include zero. They are descriptive intervals over
dependent, reused development data with unequal final block lengths, not
independent-season inference or a significance gate. The unchanged gate is
strictly lower full-precision mean deviance versus **both** controls in **each**
fold; it passes without using rounded values or these intervals as thresholds.

## Cohort and chronology

The common cohort has 3,040 team-match rows across 2020/21–2023/24, with all
380 fixtures and both sides per year. Train 2020/21–2021/22, test 2022/23;
then train through 2022/23, test 2023/24. All arms share keys, official FPL
score targets and origin cutoffs; the common proof hash is
`d6b1469ffac9272fa5da8d4849163837e147500ac230e4dc759bdaaed5c5b034`.
Any non-finite feature or target would abort, not change this cohort.

For 2020/21–2023/24, a history match is admitted only when the **later** of its
CSV and FPL UTC kickoffs is strictly before the GW deadline minus three hours.
The 380 unjoined 2019/20 rows are explicitly admitted as history-only football-data
date/club identities, never as official FPL identities, train rows or targets.
No new download was required. All clubs use the same audited canonical names.
No target-match or future-match odds/results enter features. Already completed
matches from the current test season may enter a later origin's histories;
test seasons never fit that fold's GLM or scaler. All 3,040 source-max checks pass.

| Target season | C/U no-prior-history rows each | M neutral-team rows | Promoted-club team-match rows |
|---|---:|---:|---:|
| 2020/21 | 20 | 3 | 114 |
| 2021/22 | 20 | 1 | 114 |
| 2022/23 | 20 | 2 | 114 |
| 2023/24 | 20 | 2 | 114 |

There are three promoted clubs per year, each contributing 38 rows. Market
neutrality depends on no matches in the 730-day window, which differs from
promotion status. Prior/history-only distinctions are preserved, not backfilled
with a target's observed performance.

## Runtime, qualification and preserved failures

The receiving Windows guard assigns the venv launcher while suspended to a
job object; its actual Python worker and descendants inherit the job. It
enforces a four-GiB aggregate committed-memory cap, samples wall time and
growth/free space, and terminates the entire job on a violation. Qualification
demonstrated descendant accounting, denied oversized allocation, time termination
and growth termination. This replaces the earlier launcher-only RSS monitor;
that shortfall and the failed synthetic counter assertion remain in evidence.
Windows job semantics are documented by
[Microsoft](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).
The native peak counter on a denied allocation may reflect the refused attempt;
such a job is invalid. It is not labelled as successful resident-RSS usage.

All eight real jobs (feature build, six fits and aggregation) completed with zero
remaining descendants and no guard violation. Build wall time was 6.235 seconds;
each fit job took about 2.70–2.72 seconds including startup, with measured fit
sections about 0.094–0.110 seconds. Maximum native job-memory peak was
263,675,904 bytes, below four GiB. Numerical thread-pool readings were two for
every fit. Batch elapsed about 46.94 seconds. Accounted package bytes including
a conservative 16-MiB reserve were 122,253,267, below 256 MiB; free space remained
above five GiB. Storage accounting covers all designed new worker outputs and
known package roots; the guard is not a filesystem/network security sandbox.

No real fit failed or was repeated; all six exclusive fit-ledger slots completed.
Previous setup, numerical-tolerance, newline-hash and guard-qualification test
failures remain preserved. No Stage-A inversion rerun was used to replace
telemetry. Product pins and original approved-artifact bytes are unchanged.

## Required next boundary

Stage-C player development is **UNRUN: 0/4 fits**, pending mandatory architect
review. This result does not establish player-point RMSE, ranking, fixed-squad
value, season-policy gains or forecast accuracy in later seasons. Both held-out
seasons are reused development evidence. Market collection clocks, corrected
historical xG/FPL data, reconstructed deadlines, promoted-team cold starts and
the independent-Poisson approximation remain limitations. No 2024/25 or 2025/26
data was downloaded or scored, and no season paths were run. Nothing is promoted.
