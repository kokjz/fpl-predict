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


## Measured diagnostic checkpoint

The [complete no-fit diagnostic](COHERENCE_AUDIT_2026-10-26.md) and
[all declared groups](coherence_audit_results_2026-10-26.json) are now available.
The surrounding implementation/qualification package remains in progress.

## First-action selection control

The opt-in `selection_control.FirstActionSelection(mean_manager, availability)`
API calls the explicit mean manager once and changes only the first lineup,
bench order, captain and vice. Buys, sells, chip use and every subsequent
provisional action are preserved; the engine verifies the immediate financial
transition. Only origin-current appearance cells are used by this control.

The retained mean objective is recomputed for mechanical admission. A valid
source upper bound can be rebased to this feasible mean-valued plan because
its mean problem is unchanged; it does not certify the expected selection
objective or global chip search. Original trials/scenario scores are explicitly
labelled as proposals. A previous optimality/gap flag is not copied as proof
for a changed plan. The full-horizon availability reranker is a separate policy.

Source-checkout diagnostics require the checkout's `src` on `PYTHONPATH`, for
example `PYTHONPATH=src python tools/appearance_return_audit.py --help`. Supply
explicit private input/output paths and hashes; no runtime/team discovery or
source download is implicit. The new control is research-only and changes no
normal CLI/default policy. Frozen replay equivalence is a conditional control,
not by itself a fresh adaptive solver benchmark or future-points estimate.

## Older historical admission

The optional `tools/prepare_season_2023.py` audits all 38 origin sources and final
listed-player outcomes before fitting anything. Its default is admission only;
`--fit` additionally creates a private fixed-recipe prior-only reference from
2020/21–2022/23. Explicit hashes and local-cache trust are required. It never
installs an operational model. The 2023/24 year has previous validation exposure
and is not an untouched holdout.

The separately tested 2023/24 rule profile uses a two-transfer bank, resets next
entitlement to one after Wildcard/Free Hit, and has Wildcard windows GW2–20 and
GW21–38. Annual Free Hit/Bench Boost/Triple Captain have no later AFCON topup.
See the [official transfer-rule change](https://www.premierleague.com/en/news/4058895),
[historical Free Hit explanation](https://www.premierleague.com/en/news/1153106)
and [2023/24 Wildcard deadline](https://www.premierleague.com/en/news/3841904).
The adapted Solio core compiles a separate, structure-checked historical FT AST;
newer years retain the previous default AST. This is an explicit historical
adaptation, not an original-manager reproduction.

Git-versioned fixture metadata is selected strictly before each market snapshot;
raw result/stat columns are kept outside forecasting. The one current-GW
membership difference is the subsequently abandoned Bournemouth–Luton fixture:
it remains scheduled in the GW17 forecast, while the evaluator applies the
[official void/autosub ruling](https://www.premierleague.com/en/news/3830180).
No later cancellation or replay date is backfilled into the earlier forecast.
Archive/Git dates remain publisher claims and early status-based eligibility is
an explicit proxy. Admission and synthetic solver checks do not establish
season-points performance.

## One declared calibration experiment

The [frozen protocol](appearance_calibration_protocol_2026-10-26.json) specifies
one prior-season Platt mapping, with point means exactly unchanged. Historical
training labels come from cumulative API minute increments at the next
predeadline snapshot, after the current event is marked finished/data checked.
These are noisy source-time proxies: later revisions to earlier minutes may
contaminate an increment. Negative changes and missing identities are excluded
and counted; later corrected outcomes never select training rows. GW38 is not
used for training. Fit2023/24→test2024/25 and fit2024/25→test2025/26 remain
strictly separated. Explicit zero/news flags and calendar blanks are preserved.
`tools/calibrate_appearance.py` requires a new private output folder and input
hashes; it does not read target outcomes or alter the registry. This is research,
not a calibrated current-season release or a demonstrated points gain.

The [reproduction guide](coherence_reproduction.md) describes source-only manifests,
commands, counter-label clocks and independent replay audits. The
[July2023 launch guide](https://www.premierleague.com/en/news/3568527) also
corroborates the historical chip windows and transfer resets before the opening
deadline, subject to the same publisher/revision limitations.
