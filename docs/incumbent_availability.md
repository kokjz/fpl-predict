# Incumbent availability ablation

Optional research tests published structured availability against the **full
incumbent participation method**, rather than a small form-only control. It never
loads the saved champion, replaces the registry or makes live forecasts.

The fixed [protocol](../src/fpl_predict_resources/incumbent_availability_protocol.json)
uses two otherwise identical HGB7 regressors, original 49 performance features,
identical recency weights, and five earlier seasons plus 2025/26 GW1–19.
The augmented arm adds chance label and explicit missingness: zero differs from
unknown. Official percentages are learned covariates, never assigned probabilities.
No text or return-gameweek fields, tuning, or validation refit are used.

## Source and temporal boundary

Supply trusted locally generated caches, stable ID bridge, historical availability
CSV archive and reviewed exact-prefix proof. The command rechecks all 35 GW4–38
prefixes and bootstrap hashes, identities, positions, recorded deadlines and
publication before both source and cache cutoffs. All original fixture rows remain;
unmatched sources and older seasons stay unknown. Input, protocol, code and actual
environment hashes, split audits and coverage enter a frozen manifest. Git times
remain publisher evidence, not independent time certification.

```sh
fpl-predict incumbent-availability prepare \
  --history /path/to/trusted/history.pkl --features /path/to/trusted/features.pkl \
  --players /path/to/players_raw.csv --archive /path/to/attributes.csv.gz \
  --proof /path/to/reviewed-prefix-proof.json --output /path/to/new-manifest.json \
  --trust-local-cache
fpl-predict incumbent-availability run \
  --manifest /path/to/new-manifest.json --sha256 MANIFEST_SHA256 \
  --output /path/to/new-results --trust-local-cache
```

Pickles can execute code: hashes cannot make untrusted caches safe. Use the resource
supervisor for bounded runs. No automatic downloads, runtime initialisation or
fitted-binary saves occur.

## Scores and stopping

Validation GW20–27 and reused audit GW28–38 share fitted heads. Primary: candidate
**fixture-level** mean per-GW Brier difference, augmented minus control, with a
four-GW descriptive block interval. No independence assumption combines DGW fixture
probabilities. Report pooled all/candidate Brier, reliability, >=0.8 misses and
per-GW exactly matched-coverage misses. Minutes models stay unchanged. Brier
improvement alone does not establish improved calibration.

Both windows must improve candidate pooled Brier at least 0.5%, avoid worse
all-player Brier, and have interval upper bound below zero to proceed. This is an
experiment progression gate, **not** model promotion. Failure stops this fixed
hypothesis without more settings on the same outcomes. Success permits a separately
frozen unconditional points-feature augmentation and decision evaluation. Never
multiply unconditional point forecasts by appearance probability again.

This refits the incumbent method, not the saved champion already trained on
2025/26. Outcomes are inspected/reused, upstream statistics mutable and cache
schedule cutoffs reconstructed. One season of news cannot satisfy existing
multi-season promotion gates. Future frozen shadow validation is maintenance,
not a calendar blocker for this implementation.

Grounding checked 16 October 2026: [probability calibration](https://scikit-learn.org/stable/modules/calibration.html)
distinguishes reliability from discrimination and requires disjoint calibration
data; [temporal cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split)
supports chronological boundaries. No random calibration CV is used.

## Measured head result and locked points extension — 16 October 2026

[Aggregate head results](INCUMBENT_AVAILABILITY_HEAD_RESULTS_2026-10-16.json)
were measured after protocol commit `07214b9`: 147,500 identical training rows,
6,529 validation and 9,043 audit fixture rows; every original row retained.

| Candidate fixture Brier | Control | + availability | Relative reduction |
|---|---:|---:|---:|
| GW20–27 development | 0.096781 | 0.069681 | 28.0% |
| GW28–38 reused audit | 0.102229 | 0.081202 | 20.6% |

Both fixed progression gates passed. Audit mean per-GW difference −0.020696,
descriptive four-GW interval [−0.024059, −0.018069]. At exactly matched coverage,
nonappearances fell from166 to136 across1,973 candidate fixture selections.
These are fixture selections, not distinct owned players or realised squad points.
This establishes incremental historical component value over the **full method**,
not production promotion or proof of superior calibration at every band.

Preparation and fitting took41.87s, peak sampled RSS1.43GiB, two threads. Each
head fit took about12s and15,572-row inference0.02–0.03s. Actual environment:
Python3.12.14/NumPy2.3.5/pandas2.2.3/scikit-learn1.9.1, differing from current
package NumPy/pandas pins.

The [points protocol](../src/fpl_predict_resources/incumbent_availability_points_protocol.json)
is fixed before points scoring. `availability-points` fits the original unconditional
core target with/without the same two features and fixed HGB7/weights. The DC
learner is shared, capped at each arm's own appearance probability. Minutes/p60
models are not refitted. No conditional model, post-hoc probability multiplier,
calibration search or fitted-binary save. Supply original manifest, qualified head
report and predictions with checksums; see `fpl-predict availability-points --help`.

Report both windows' player-GW errors/rankings, all arms, and matched historical
external/practical comparisons onGW28–38 with retained external forecasts and
identical neutral policy. No external retraining is needed. Original2024/25Dastan
cannot receive fabricated news from a source starting2025: keep those results
separate. A point-error win without legal selection support or existing
multi-season evidence will not replace the approved champion.

### Reproduce the external comparison

`fpl-predict availability-benchmark --help` accepts points predictions/report,
head manifest, retained five-method fixture forecasts and original listed market,
each with SHA256. It rejects target, position, candidate, coverage, control and
market-total conflicts. Only verified blanks receive zero forecasts. Every arm
uses identical neutral scenarios, selector, price quotes and owned/reset/rolling
policies; adding a model leaves the other methods' decisions unchanged. Outputs
include errors, uncertainty, scores/actions and the complete scenario schedule.

News was newer than the price snapshot in three evaluation weeks, but still
predeadline. The adapter retains `quote_as_of` and advances `inputs_as_of` to the
latest admitted source: it does not claim news existed at the earlier quote time.
Prices remain the same retrospective execution approximation for all methods.
Compare at a common deadline with unequal source feeds; extra source value does
not establish equal-input architecture superiority. Historical source limits remain.

A first external-replay attempt stopped **before scoring** because fixture-history
forecasts include23 player-gameweeks absent from the retained predeadline listed
market. These rows stay in every method's error metrics; all methods use the same
original listed roster for selection. The adapter now reports this uniform
source-based restriction explicitly instead of requiring the future fixture-history
universe to equal the earlier published roster. Missing listed nonblank forecasts
still fail; missing listings are never inferred from realised minutes or points.
The initial failure is retained and no forecast, outcome or scenario changed.
