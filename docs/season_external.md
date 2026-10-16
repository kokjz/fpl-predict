# Matched external season forecasting

The [season-comparison protocol](../src/fpl_predict_resources/season_external_protocol.json)
extends the continuous 38-GW benchmark to independently fitted forecasting
references. Existing models trained through the evaluation season's GW19 must
not be backcast into its opening weeks.

Each core learner fits 2020/21–2023/24. Where its published recipe requires early
stopping or calibration, 2024/25 supplies that validation; 2025/26 labels never
fit or select the forecaster. The core/native HGB learners have fixed parameters
and do not use validation for selection. The permitted information horizon is
shared, while intrinsic calibration, weighting and fit usage differ.

The named references are the standing-method core HGB, native-window HGB,
Dastan-architecture adaptation, OpenFPL's fixed 40-member cv1 adaptation and the
AIrsenal-inspired conjugate/Poisson component reference. The latter is not
AIrsenal's original BPL or complete manager. Architecture/feature reconstruction,
source gaps and missing older snapshots prevent claims of exact native-system
reproduction. See [attribution](../THIRD_PARTY_NOTICES.md).

The native HGB adapter drops features entirely missing in its training data and
records that fitted mask. Query values never determine retention. This avoids an
all-NaN binning failure in the numerical runtime without inventing observations
or changing the estimator's parameters. The failed initial fit is retained.

## Matching information and scoring

`season_external.fixture_targets` creates all origin-known fixture targets from
the same admitted market/bootstrap/calendar. `gameweek` identifies the origin;
`target_gameweek` identifies the forecast week. Training history and current
roster information stay frozen at that origin for every target.

`NativeHistory.transform_at_origins` queries histories at `inputs_as_of`, with
the existing three-hour completion buffer, rather than the later physical FPL
deadline. A snapshot may equal its own observed origin but must precede the
physical deadline. The legacy strict deadline API remains unchanged. The adapter
marks next-GW EP, chance and news fields unknown for later targets; an origin's
next-GW projection is never silently repeated as a future target's value.

Historical DC awards are removed from both core labels and point-history
features. The same separately declared origin EWDC component, capped by the
prior-only standing appearance head, is added to every learner after prediction.
That common component uses pre-2025 weights and as-of observed rates. Other
historical scoring differences remain limitations. This is a harmonised scoring
adaptation, not a claim that the external released models implement this layer.

The common experimental official-zero policy affects the current GW only.
Missing news stays unknown; later forecasts do not assert a recovery date.
Provider-mutable historical statistics, reconstructed older training deadlines
and publisher/capture timestamps remain explicit retrospective caveats.

## Reusable Python contracts

`origin_features` builds native features for an admitted query, `scoring_core`
removes identified DC awards, `fit_reference` fits the fixed native/Dastan/OpenFPL
learners and `aggregate` sums fixture means into a complete `Horizon`, including
origin-known doubles and blanks. Component and standing-model fitting reuse
their existing modules. No downloaded model is executed or registry changed.
XGBoost 3.2.0 remains an explicitly installed optional research dependency.

The protocol fixes own-opening and common-neutral-opening season tracks, common
six-GW planner and budgets, plus a separate coherent one-week official projection
comparison. Use retained-plan bounds and unknown counts from the current planner,
not raw attempt gaps. The earlier 2,295-point pilot used a different fit/source;
it is not a substitute for a new matched baseline.

Before season-path scoring, a further standing-method control is explicitly
included: the existing five-prior-season forecast, rerun with the new planner on
both opening tracks. It distinguishes matched four-season fitting from the
closest eligible standing-method history usage. The deployed artifact cannot be
backcast into its own training season. All 16 paths are reported; neither control
is chosen retrospectively to make a competitor comparison look better.

The common roster is fixed only in the first period. Later provisional transfers
retain access to the full market. This is enforced in the solver, rather than
by disabling non-opening players throughout the planning horizon. The contract
was checked before any common-opening management path was scored.

The first fixed experiment attempted all sixteen paths. One own-opening path
failed when a short baseline solve could not certify an optimal opening roster.
That failure remains part of the evidence. A source-only minimum-cost flow
routine now provides a legal, affordable opening fallback if that solve fails;
it does not fix the main solver's squad or claim the best predicted points.
Existing held-squad fallbacks are unchanged. The revised experiment reruns all
sixteen paths with the same frozen forecasts and budgets, rather than retrying
only a failed method or choosing parameters after inspecting scores.

Archived official EP has complete observed coverage here, but its publisher's
training lineage is unreported. Its one-week track is an as-of-source comparator,
not a claim of the same fitted-label split as the five reconstructed learners.
An inherited local envelope cutoff does not certify the publisher's training.

The protocol and tests preceded the evaluation. The [complete season report](SEASON_EXTERNAL_RESULTS_2026-10-16.md),
[aggregate](season_external_results.json) and [dated source inventory](season_external_sources.json)
retain every initial/revised arm, secondary errors and bounded-search limitations.
The revised sixteen paths reconcile independently across all 608 deadlines.
These measured named-reference comparisons do not establish native planner
compatibility or model/policy qualification. Common-forecast external planner
comparisons and end-to-end native-system admission remain separate work.

Primary sources checked 16 October 2026: [Dastan](https://github.com/qazybekb/smartplayfpl-dastan),
[OpenFPL](https://github.com/daniegr/OpenFPL),
[AIrsenal](https://github.com/alan-turing-institute/AIrsenal) and
[Open FPL Solver](https://github.com/solioanalytics/open-fpl-solver).
