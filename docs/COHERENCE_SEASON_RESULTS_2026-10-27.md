# Appearance calibration: final numerical result

The single predeclared appearance correction **fails the season-points
criterion**. Calibration minus existing availability-aware H6 gives
**−26, −2, +5, −104 net points**, equal-season mean **−31.75**. Approved
forecaster 1.0.0, its weights and normal weekly defaults remain unchanged.
Source review and release are tracked separately in the
[handover checkpoint](handover/CHECKPOINT.json).

## All target-year comparisons

Each row averages two identical numerical repetitions. Starts are the two
predeclared common openings, identified by their fixed seeds. Transfer-hit
points are already deducted. Repetitions are reproducibility checks, not new
football evidence.

| Season | Opening seed | Calibrated − availability H6 (primary) | Calibrated − mean H6 | Calibrated − adapted Solio |
|---|---:|---:|---:|---:|
| 2024/25 | 20261070 | −26 | −1 | +18 |
| 2024/25 | 20261071 | −2 | +20 | +20 |
| 2025/26 | 20261070 | +5 | −62 | −21 |
| 2025/26 | 20261071 | −104 | −58 | −82 |
| Equal-season mean | | **−31.75** | **−25.25** | **−16.25** |

The primary season means are −14 and −49.5. Its mean is not positive,
2025/26 falls below the unchanged −19 season floor, and the −104 opening
falls below the unchanged −38 opening floor. Component probability gains
therefore do not qualify this candidate for historical season-policy support.
The earlier zero-negative criterion and all dated earlier results remain
unchanged; no threshold is relaxed after observing a loss.

The [complete numerical checkpoint](handover/RESEARCH_STOPPING_RESULTS.json)
retains all 22 case means, comparisons and evidence hashes. It records 20 new
paths plus 24 hash-verified retained controls, 1,672 settlements and 836 equal
full-plan repeat fingerprints across 22 pairs. Independent original audits
reconcile 9,372 retained financial periods, 4,260 expected-objective periods
and 12,336 native proposal periods. Of 1,672 selected-plan conditional bounds,
760 remain unknown; global chip and season bounds remain unknown.

## What improved, and what did not

The [component results](COHERENCE_CALIBRATION_RESULTS_2026-10-26.md) show
equal-season Brier reductions of 2.59% across listed players and 6.83% in
frozen proposed-squad unions. Unconditional point means and their MAE/RMSE are
unchanged. Explicit zeros and official flags remain unchanged. Marginal
calibration does not identify dependence or validate conditional returns.

Frozen-roster selection effects of +2.50 for mean H6 and +4.25 for adapted
Solio are selection-only overlays; they do not establish adaptive management
gains. The separate older 2023/24 uncalibrated extension loses 9 and 65 points
against mean H6. It adds source/rule coverage, not a third calibrated target
year. The descriptive three-year mean for uncalibrated availability-aware H6
(decisionH6) minus mean H6 (standingH6) is −8.00.

## Provenance, failures and limits

Numerical source is `9e26851a92371690848e3811c6e120026dd33011`, preserved
in the ancestry of tag `research-handover-2026-10-27`. The protocol/fit source
is `39f19c977816794134c44c3844cc66632354a320`. Receiving repair commits
must not replace those numerical attributions. The
[calibration protocol](appearance_calibration_protocol_2026-10-26.json) fixes
the one candidate and all gates. No new fit, search or completed-path rerun
was needed for the receiving validation.

The first season attempt retains a safety-timeout failure after two settled
deadlines: about 13.6 minutes wall time versus 44.3 active seconds. Suspend is
plausible, not proven. The second attempt retains 14 completed paths and a
seven-origin interrupted prefix; the interruption cause is unknown. The final
attempt reuses verified completed paths and preserves both prefix comparisons.
Failed and partial paths never count as additional completed cases.

Both calibrated target years were previously inspected. Openings within a
season are dependent, archive/Git clocks are publisher claims, and early
eligibility and outcome revisions retain their stated limitations. The
2024/25 action space excludes Assistant Manager. Adapted Solio uses a common
forecast/outer chip framework; this is not an untouched original manager or a
new Dastan/OpenFPL forecast-accuracy comparison. Common openings test squad
maintenance, not initial squad construction. Prior-only historical models
must never replace or backcast the deployment artifact into its training years.

## Bounded source repairs

PR42 rejects used-chip tokens whose window starts at or after the current
origin in engine preparation, native admission and the independent ledger
audit. The generic bootstrap audit derives extra transfer capacity from the
season's free-transfer cap minus one. Selection reports retain legacy
`expected_before_hits`/`expected_after_hits` values, both gross of transfer
charges, and add explicit original/selected gross and net values plus
`transfer_hit_points`. These changes clarify admission/reporting; they do not
change a valid state's decision objective or historical frozen report bytes.

Receiving validation compares repaired and numerical-source behavior over
all 44 saved paths and independently reconciles their ledgers/scoring, without
executing a planner or solver. Receiving runtime compatibility, final source
review/CI and scientific interpretation have separate recorded statuses.
Neither source publication nor a later merge promotes a model or policy.
