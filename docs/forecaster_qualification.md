# Conditional forecaster-only qualification

This fixed experiment separates PR26's promising conditional forecaster from its
unqualified expected bench selector. Small credible improvements can justify
adoption. NDCG is a diagnostic here, not an additional promotion veto. The
previous experiment's failed ranking progression is preserved, not reclassified.

The [frozen policy](../src/fpl_predict_resources/forecaster_qualification_protocol.json)
retains standing registry promotion requirements: two earlier development folds,
two historical audit seasons, paired error uncertainty, practical points,
contemporary scoring, current retrospective corroboration and integrity. Candidate
selection used inspected 2025 results; no window is called untouched. No settings,
thresholds, blends or seeds are searched. Failure of development stops expanded
fits, not publication of the result. Existing fixed 2025 predictions still support
external error/owned/reset/rolling comparisons and saved-artifact compatibility.

The persistable model uses shared conditional core/minutes/DC returns, a learned
structured appearance head and a training-only rare card prior. No appearance
covariates enter conditional core returns. Older seasons have explicitly missing
availability. Current labels are learned covariates for their next GW only;
further-horizon inputs remain missing. No article collection, NLP or future
injury labels are invented. Normal mean selection and manual sensitivities stay
unchanged. Code merge does not approve weights or install a model.

Only trusted, hash-verified local artifacts may be deserialised; hashes do not
make an unknown pickle safe. Save exact versions and reload-test in the matching
environment. See [scikit-learn persistence](https://scikit-learn.org/stable/model_persistence.html)
and [leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage),
checked 16 October 2026. Source-only tests never download training data.

## Run and artifact interface

```sh
fpl-predict qualify-forecaster --manifest /path/to/admitted-head-manifest.json \
  --sha256 MANIFEST_SHA256 --output /path/to/new-qualification --trust-local-cache
```

The command rechecks the exact existing source/cache manifest, runs the two fixed
development folds and writes immutable source/protocol hashes, forecasts and
aggregate metrics. It never updates the registry. Use the same audited local
history/features and `conditional_forecaster.fit(d, x, train_mask)` to reproduce
the fixed train-through-2025-GW19 candidate; fit only admitted earlier rows.
Apply the earlier published source-admission adapter for availability covariates.
Save trusted research artifacts outside Git and verify reload parity/metadata.
Core residual intervals can be calculated on the fixed development window only;
zero default offsets are deliberately uncalibrated and must not be called intervals.

For retained practical replay, `forecaster_qualification.join_market` attaches
conditional forecasts and source times to the exact admitted market using stable
season/GW/player keys and checks reference/outcome/price/roster metadata. Run the
existing `selection-benchmark` command with all six methods on that result;
no new external fits are required. Preserve the documented outside-roster error
rows, independently verified blanks and original neutral scenario schedule.

[Completed results](FORECASTER_QUALIFICATION_RESULTS_2026-10-16.md) include the
failed development qualification, artifact parity, current-input compatibility
and full owned/reset/rolling retained external replay. This package does not
install weights or remove any standing promotion gate.
