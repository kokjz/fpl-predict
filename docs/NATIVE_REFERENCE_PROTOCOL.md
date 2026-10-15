# Native-window cutoff feature pilot v1 — pre-fit declaration

Declared15October2026 before fitting. This is a separately named retrospective
feature-bundle pilot, `native-window-cutoff-hgb7-v1`, not original Dastan or
OpenFPL predictions, a32-head ensemble reproduction, or an approved model.

## Fixed experiment

- Full native window/statistic names:286 predictors. Rebuild from canonical raw
  FPL/Understat match observations; never repair/reuse released rolling values.
- Train2020/21–2024/25 plus2025/26GW1–19. ReserveGW20–27 without selection,
  early stopping, calibration or validation refit. TestGW28–38. Outcomes reused.
- One pooled full-points HistGradientBoostingRegressor:7leaves,200iterations,
  learning rate0.05,L2=20,min leaf60,no early stopping,seed20260921. Recency
  half-life730.5days. Clip fixture means to[0,22]. No search or second model.
- **Primary:** player-GW RMSE among snapshot-known candidates, built before
  outcome scoring. Candidate=at least3season-history records and last5mean
  minutes>=45. Report MAE/bias/ranking and descriptive paired4GW-block intervals.
  Also report all candidates and all players, including unknown snapshot coverage.
- Reference: exact frozen, training-only incumbent-method full-score export from
  the prior pilot, aligned on fixture keys, outcomes and candidate predicate.
  Last-five full-point history is another baseline. Neither comparison establishes
  net transfer/chip/captaincy/season-points gains or external-model superiority.

## Explicit reconstruction differences

All match histories are queried **strictly before deadline minus3hours**, including
opponents, defensive-action allowed histories and league context. Both fixtures
of a double share histories; opponent/venue context can still differ. Prefix-sum
indices use explicit nanosecond units, missing-aware means and float32 output to
avoid large per-row Python dictionaries. No full-feature dataframe per model head.

Player history uses stable FPL codes across seasons rather than potentially shared
Understat IDs; source-stat joins still require audited date/team identities.
Availability windows reset each season. Team/opponent windows use prior EPL
history across seasons. Current league ranks use only completed results; historical
rank windows are reconstructed at each past match with the same completion lag.
Ties use points/GD/GF/name, an approximation to full official tie-break rules.
Rest and14-day congestion are measured at the common deadline, not a final or
unverified future kickoff. Missing defensive actions remain unknown, not zero.

Raw unmapped/missing numeric observations remain NaN. Known non-appearance event
statistics can be zero; unavailable mapped appearance records fail preparation.
No prediction row is dropped because its outcome or minutes are inconvenient.

Snapshot features use only the38 verified2025/26 bootstrap captures. **All seven
snapshot fields are explicitly missing (-1) in older training seasons.** This is
a declared missing-history variant, not the release's richer historical snapshot
panel. No incumbent features fill that gap. For2025/26 use captured `now_cost`,
selected-by-percent times total managers (approximate selection count), event
transfer balance, `ep_next`, status risk, chance and news presence. Genuine zero
remains distinct from missing. Codes absent at capture stay unknown; do not infer
deadline ineligibility or selectively retrieve nearer captures after seeing errors.

## Readiness, reproducibility and budgets

Require complete raw mapped-appearance/team coverage and reconciled source joins,
fixed row identities, coherent chronological splits, no future source maximum,
and agreement with the frozen reference's full outcomes/candidate pool. Freeze
policy, code/library versions, source proof and all file hashes before launch.
Stop rather than silently substitute fields, drop rows or change training scope.

Run through the resource/storage watchdog:two numerical threads,4GiB observed RSS
comfort limit,30minutes,512MiB growth,2GiB project cap,5GiB free headroom. These
are sampled limits, not OS quotas or proof of a need for other hardware. Save
private predictions/aggregate evidence and failure records; no trained binary or
registry change. A failed/incomplete job is not a benchmark score.

Even after event-time checks, current provider responses can include historical
statistical corrections; old training deadlines are reconstructed and target
membership has a manual source trail rather than complete kickoff archives.
Thus full historical operational benchmark eligibility remains **false**. This
pilot can assess feature-bundle error/cost under a disclosed regime; it cannot
retroactively certify original systems or become an untouched test. Any later
architecture reproduction/feature ablation needs its own prospective declaration.
