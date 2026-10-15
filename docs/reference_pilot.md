# Bounded incumbent-method reference pilot

This is a retrospective research command, separate from the approved model and
weekly forecasts. It fits three fixed `hgb7` components (core points, appearance,
defensive-contribution probability) with the incumbent's 730.5-day recency
weights and prediction caps. It does not fit unused minutes/60-minute models,
select hyperparameters, refit on validation or save/promote a model binary.

The fixed policy trains on 2020/21–2024/25 plus 2025/26 GW1–19, reserves GW20–27,
and reports full-score GW28–38 errors. DC uses training observations only.
Primary scores aggregate double fixtures into player-gameweeks and use the
pre-deadline history predicate `n_history >= 3 and last5_minutes >= 45`.
Secondary scores include all players. Both simple baselines add lagged DC to
core-point averages, rather than comparing core predictions with full outcomes.
Paired four-GW block intervals are descriptive; these outcomes were already
inspected, so they are not independent tests or evidence of season-points gains.

## Explicit readiness limitation

The current local cache reconstructs a GW cutoff as its earliest final kickoff
minus 90 minutes. Historical fixture assignments, positions, clubs and statistical
corrections may contain hindsight. Timestamp assertions and source hashes cannot
reconstruct what the schedule actually showed before each deadline. Therefore
this variant sets **`benchmark_eligible: false`**. It can check methods, targets,
pipeline cost and baseline errors; it cannot rank verified historical operational
systems. It does not satisfy the stricter source-knowledge gate in
[the common-window plan](BENCHMARK_RUN_PLAN.md).

This explicit variant was declared before fitting. Do not relax the main plan to
admit it. The cache audit checks recorded source maxima, split completion gaps,
full/core target consistency, fixed-window coverage, stable player-code mapping,
and equal candidate/deadline values across a player's double fixtures. Source
maxima must cover player, own-team **and opponent** history. They remain supplied
evidence rather than independent proof; independently rebuild/check local caches
against pinned raw sources before trusting them.

## Usage

Use a private workspace. Pickles can execute code: **never download an external
pickle and pass the trust flag**. The inputs must be locally created and trusted.
Commands have no network access or automatic operational workspace initialisation.

```sh
fpl-predict reference-pilot prepare \
  --history private/history.pkl --features private/features.pkl \
  --players private/2025-26/players_raw.csv \
  --output private/pilot-manifest.json --trust-local-cache
```

Preparation audits without fitting/scoring, then writes the manifest exclusively.
Keep it immutable. It records input hashes, ordered split-key hashes, policy,
code hashes and library versions. Record its SHA-256 before running:

```sh
fpl-predict reference-pilot run \
  --manifest private/pilot-manifest.json --manifest-sha256 RECORDED_SHA256 \
  --directory private/new-run --trust-local-cache
```

Run the latter command through the [experiment watchdog](experiment_runner.md),
declaring the manifest and all input files/hashes, and expected `predictions.csv`
and `results.json`. Use an absolute output directory inside its new job directory.
The worker limits numerical libraries to two threads; the supervisor separately
samples wall time, process-group RSS and project disk growth. Initial comfort
limits are 30 minutes, 4 GiB RSS, 512 MiB growth, 2 GiB project size and 5 GiB free.
These are neither OS quotas nor evidence a machine needs replacement. Failed or
partial runs cannot count as completed experiments.

The manifest and runner logs contain private local paths. Predictions and
outcomes are private outputs, never repository fixtures. Only reviewed aggregate
results and public source provenance belong in documentation. Keep the original
manifest/run metadata outside Git; do not edit it to match a later code version.

Next steps depend on verified historical schedule/feature snapshots, qualifying
external reference inputs and a declared comparable refit policy. More seeds,
folds or challengers are separate decisions after this bounded pilot, not an
automatic search or model promotion.
