# Optional conditional architecture reference

This is one fixed retrospective Dastan-architecture **adaptation on rebuilt
inputs**, not an original-system reproduction or an approved model. Read the
[immutable pre-fit protocol](CONDITIONAL_REFERENCE_PROTOCOL.md), the source
[native contracts](native_reference.md), and [attribution](../THIRD_PARTY_NOTICES.md).

The default package/weekly workflow does not require XGBoost. Use an isolated
research environment and explicitly install the `reference` extra if running this
command. It pins XGBoost3.2.0 to match the inspected external method; changing
package versions requires a new manifest and an explicitly named variant.
Do not load distributed model weights to reconstruct historical predictions.

```sh
fpl-predict conditional-reference prepare \
  --players private/players.csv --teams private/teams.csv \
  --snapshots private/snapshots.csv --reference private/incumbent-reference.csv \
  --provenance private/source-proof.json \
  --native-predictions private/frozen-native-hgb.csv --output private/manifest.json

fpl-predict conditional-reference run --manifest private/manifest.json \
  --manifest-sha256 RECORDED_SHA256 --directory private/new-job
```

Preparation hashes all raw inputs and both prior prediction exports, verifies
full-score/key/cohort parity and training/validation class populations, and freezes
code/policy/library versions before fitting. Histories are rebuilt at common
cutoffs; no released rolling columns or current-season planning inputs are read.

Supervise the worker with the [runner](experiment_runner.md), all frozen inputs
declared, expected `head_progress.jsonl`, `predictions.csv` and `results.json`,
two threads,4GiB/30minutes and the protocol's storage limits. The command itself
does not enforce OS quotas. Each of32heads records size,best iteration and time.
A failed/incomplete method is unranked; never score a partially completed ensemble.
Outputs are write-once; no binary, forecast pointer or registry is written.

Validation alone determines early stopping/calibration/blends; the inspected
evaluation window is scored once without choosing a winner for promotion. Keep
the original OpenFPL early archive and original published-system claims separate.
