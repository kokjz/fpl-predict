# Appearance/return coherence and decision isolation

The [repeatability study](SEARCH_REPEATABILITY_RESULTS_2026-10-25.md) establishes
repeatable fixed-work decisions on its measured runtime. It does not establish
that the availability-aware objective improves expected season points generally.
Its positive average versus H6 includes a material losing start, and selection-only
changes lose in both newer-year starts for both saved H6 and adapted Solio rosters.

The [frozen diagnostic protocol](coherence_protocol_2026-10-26.json) separates
appearance probabilities, implied points conditional on appearing and joint
appearance assumptions before another candidate is chosen. Forecast means and
sources remain fixed; this stage fits nothing and changes no normal defaults.

For a fixed player-GW, the selector represents the unconditional point mean as
`mu = p_play * conditional_return`, omitting a separate card-only probability.
Computing `conditional_return = mu / p_play` preserves that identity, but does not
establish calibration of either head. A low appearance probability combined with
a positive mean can imply a large conditional return. The diagnostic checks that
assumption against separately supplied outcomes; it does not clip or adjust means
or multiply an unconditional mean by an appearance probability.

Cohorts are selected from frozen origins and proposed actions before new residual
calculations. The first of the two already identical repetitions avoids treating
numerical reruns as new football evidence. Current-origin and longer-lead results
are separate; role unions and per-case views retain overlapping-exposure limits.
Observed-player conditional residuals are diagnostic subsets, not eligibility
rules that would have been knowable before a deadline.

[Brier and calibration guidance](https://scikit-learn.org/stable/modules/calibration.html)
motivates reporting reliability bins and counts alongside overall probability
error. [Chronological splitting](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)
prevents training on later origins when a correction is subsequently assessed.
The [predict-then-optimise research](https://arxiv.org/abs/1710.08005v5) motivates
evaluating decisions alongside forecast error; its guarantees do not establish
results for this FPL policy, and this stage implements no decision-focused fit.
Sources checked 26 October 2026.

The next control changes only the executed lineup/captain/bench selection while
preserving transfer/chip proposals. An older-season admission audit and at most
one diagnosis-supported correction follow under separately frozen evaluation
criteria. Previously inspected years are never relabelled untouched, previous
failed gates remain failed, and merging tooling does not promote model weights.
