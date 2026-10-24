# Season decision-value experiment

This package isolates whether availability-aware selection improves historical
season points while keeping every unconditional point forecast unchanged.
It is optional research; importing it does not fit a model, change a registry or
make an FPL account action. Read the [fixed protocol](season_decision_value_protocol_2026-10-24.json).

## Mechanism and controls

The [earlier conditional-selection study](CONDITIONAL_SELECTION_RESULTS_2026-10-16.md)
changed conditional returns and appearance forecasts. Its combined expected
selector did not establish a realised gain and was not promoted. This experiment
uses the exact frozen means from the [two-season management study](EXPECTED_SEASON_POINTS_RESULTS_2026-10-24.md),
then replays the original prior-only appearance heads at each original origin.
The older study's different forecasts/windows remain separate evidence.

For each scheduled fixture, the fixed research assumption mixes the raw appearance
estimate with a small neutral prior: `p = 0.98 * raw_p + 0.01`. This is numerical
regularisation, not a calibrated probability improvement. Current-origin official
zero labels and known calendar blanks stay zero. Multiple fixture appearances
are independent in the primary player-gameweek marginal. Historical news or
recoveries learned after the origin are never imported.

The conditional return is reconstructed as `unconditional_mean / p_any` when
`p_any > 0`; it is an assumption, not a newly learned conditional-return model.
The unconditional mean is never multiplied by appearance again. Zero probability
with a nonzero mean is rejected. The primary distribution omits predicted
zero-minute/card-only events; realised scoring still retains those events and
their distinct autosub/captain-fallback rules. A fixed shared-appearance stress
preserves all marginals; its correlation weight is not estimated or tuned.

The new selector exhausts legal XIs, ordered outfield benches and captain/vice
pairs. Bench Boost counts all fifteen once, without adding automatic substitutes.
Triple Captain doubles the extra armband bonus, including its vice fallback.
Ordinary weeks reuse the previous exact selector. Controls are the saved mean
selection and the previous chip-unaware expected selector on the same new inputs;
the latter is a controlled implementation adaptation, not a replay of the old
study's conditional model or its original measured result.

## Ordered plan

1. Freeze protocol, source receipts, resource limits and private protected state.
2. Verify the selector against exhaustively enumerated synthetic outcomes and
   the season scorer. Replay appearance sidecars only after matching every
   original point mean and checking model/source/feature clocks.
3. Freeze all three selections before reading outcomes on every held squad in
   the four saved H6 paths: 152 panels across two seasons/two common starts each.
   Positive equal-season mean gain, declared downside limits, integrity and mean
   selection time at most one second permit deeper integration; failure is
   retained and does not trigger parameter search or a forced promotion.
4. Only if that test passes, integrate expected-value ranking of feasible
   multiweek roster/chip proposals. Original inner mean objectives and their
   conditional bounds must stay distinct from the changed ranking objective;
   no old mean-objective dual is a certificate for the new objective.
5. Report selection overlays for all twelve frozen H1/H6/adapted-Solio paths.
   These commit changed lineups on unchanged transfers/rosters/chips and are
   explicitly conditional overlays, not a new adaptive transfer-policy result.
   If step 4 is admitted, run fresh uniform matched H6/current, H6/challenger and
   adapted-Solio continuous season policies with the fixed common starts/budgets.
6. Assess policy qualification separately from forecaster weights. Diagnose
   remaining availability/conditional-return/preseason losses before further
   fits; source-audit any additional historical coverage before claiming it.
7. Publish complete results, losses, source/method limitations, tests and cost;
   update operational handoffs after reviewed release and branch cleanup.

Both years already have research exposure. Two starts per year are not four
independent seasons. The 2024/25 profile excludes Assistant Manager for every
policy. These are named shared-input external-core adaptations; original full
external managers, global optimality and future points gains are not established.

## Admitted integration stage

The fixed-roster pilot passed its predeclared progression rule: H6 selection-only
differences were +9, +4, −3 and +13 points, equal-season mean +5.75. All twelve
overlay paths retained the same realised totals for the legacy and chip-aware
expected selectors, so an isolated chip-aware realised gain is not established.
Those overlays do not establish adaptive transfer/chip-policy improvement.

The [separate integration protocol](season_decision_integration_protocol_2026-10-24.json)
declares sixteen fresh continuous paths before scoring: H1, H6, changed H6 and
adapted Solio, two common openings in each year. The changed policy reranks
bounded feasible mean-MILP proposals by expected autosub/vice-aware value across
the detailed horizon, plus the unchanged coarse chip reserve. It optimises the
lineup for each proposed roster, commits only the first action, then replans.
It does not solve the exact global expected-value transfer problem.

Selector time counts inside the same outer search budget; fewer completed chip
probes are a possible cost. Expected-value dual/global bounds remain unknown.
Raw inner mean-objective bounds are preserved separately, and the engine's
mechanical mean-admission value is distinguished from the decision value used
to rank plans. Existing weekly defaults remain unchanged.

An unchanged squad may legally exceed three players from a club following a
real club move. The optional research selector can omit that club-count check
only after the season engine admits the financial/transfer transition; new
transfers still require the ordinary club limit. Structural XI/squad checks
are always enforced, and default selector validation remains strict.

## Reproduction and resources

Use a source checkout with `PYTHONPATH=src`. The offline
[preparation tool](../tools/prepare_decision_availability.py) requires a checksummed
manifest, explicit executable-cache trust and a new output outside the checkout.
Each season declares trusted history/model/decision inputs, optional derived
history corrections, 38 admitted origin calendar views, official-zero identity
lists and source receipts. Raw inputs, fitted artifacts and individual evidence
are not bundled. Original source-date/revision limitations remain applicable.

Numerical jobs run serially under the process-group/storage watchdog: two CPU
threads, 4 GiB sampled process-group memory, 900 seconds per job, project growth
at most 384 MiB and at least 5 GiB free storage. No optional GPU/cloud dependency
is introduced. The primary fixed-roster pilot and any subsequent adaptive study
have separate source locks and immutable output destinations.

Rules research refreshed 24 October 2026: [official FPL help](https://fantasy.premierleague.com/help/faqs)
and [official captain/vice FAQ](https://www.premierleague.com/en/news/4661030).
Historical rules remain separately admitted. Evaluation follows the
[leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html) and
[chronological validation guidance](https://scikit-learn.org/stable/modules/cross_validation.html).
