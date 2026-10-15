# Fixed conditional architecture reference — 15 October 2026

**Retain the approved champion.** One fixed 32-head CPU reference completed under
the [pre-fit protocol](CONDITIONAL_REFERENCE_PROTOCOL.md). It slightly reduced
error but worsened top-player ranking. It is a named adaptation on rebuilt
inputs, **not a reproduction or accuracy ranking of original Dastan/OpenFPL**.

## Comparable retrospective results

All methods share 9,043 evaluation fixture rows/8,713 player-GWs in 2025/26 GW28–38.
Primary 2,312 snapshot-known candidates use strictly prior season-history>=3 and
last-five mean minutes>=45. No prediction rows were removed because of outcomes.
Training 147,500 rows throughGW19;6,529 validation rows inGW20–27 supply only the
declared early stopping,band calibration and direct-blend selection. No validation
refit, test-based selection, second seed, tuning or trained binary save occurred.

| Candidate player-GW metric | Conditional architecture variant | Incumbent-method reference | Native-window HGB variant |
| --- | ---: | ---: | ---: |
| RMSE | 2.95404 | 2.97780 | 2.95586 |
| MAE | 2.18962 | 2.25493 | 2.24939 |
| Mean prediction minus actual | -0.01070 | +0.08593 | +0.20469 |
| Mean within-GW Spearman | 0.42047 | 0.38965 | 0.42446 |
| Mean within-GW NDCG@10 | 0.38433 | 0.47252 | 0.41481 |

Candidate RMSE improved 0.798% against the frozen incumbent-method reference;
against the simpler native-window HGB it improved only 0.062%. Descriptive paired
four-GW-block 95%RMSE-difference intervals (1,000 draws,seed 20261015):
[-0.03407,-0.01366] versus incumbent-method,[-0.01844,+0.01635] versus nativeHGB.
The latter includes zero. MAE and bias improved, but neither stronger overall
Spearman nor lower error guarantees better selections among the best options.
No fixed-squad points, transfer/chip policy or season benefit was measured in
this architecture reference. It cannot bypass the failed I4 development gate.

All-player RMSE1.83991 versus 1.86552/1.84762 and MAE0.91062 versus 0.94534/0.93139
are secondary diagnostics, not substitutes for candidate evidence. All-candidate
and snapshot-known candidate cohorts happen to coincide. The intervals condition
on fixed predictions and do not remove training/selection uncertainty or test reuse.

## Measured resource cost

Whole supervised job 90.93 seconds,peak observed process-group RSS1,586,872,320 bytes
(1.478 GiB),two CPU threads. Feature build 25.38 seconds; all 32 head fits total 62.80
seconds. Four positional prediction batches total 0.0817 seconds for 9,043 fixture
rows, excluding feature creation/load/source refresh and earlier validation
selection. Best iteration across heads ranged over early-stopped fits, with
maximum 1,365; published caps of 2,000/6,000 trees were not all exhausted.

This establishes feasibility for **this bounded method and dataset** on modest
local compute. It is not a timing guarantee for bigger searches or an exact
reproduction in the publisher's environment. No GPU/cloud/paid compute was used.
Disk growth during the job was 903,471 bytes; no model binaries were retained.
The optional dependency was isolated; normal package and weekly runtime unchanged.

Research environment:Python 3.12.14,NumPy 2.3.5,pandas 2.2.3,scikit-learn 1.9.1,
XGBoost 3.2.0. Upstream package versions differ in other components, so the report
records actual versions rather than claiming bitwise reproduction.

## Reproducibility and remaining limits

Pre-fit source commit `4acfb37e34a4b12e8a4610c8832d706687d5c54a`.
All raw/control/prediction/optional-library bytes were checked before the worker.

| Private frozen artifact | SHA256 |
| --- | --- |
| Pre-fit manifest | `899d1f0fda57a60e6449b212346a8dda8c8538d2238c27765b5b6a44fe951c0b` |
| Per-head progress | `9fd626866380759f9190938d0625244fc36f4d36da0e28061f78885fa65d8535` |
| Predictions | `dd1a4bf9da6dd39a2c16df289071f62359e74484884c0c2ccbc75ba9668d8637` |
| Results | `4d6f14b2efd365f78e70d1a7e24a04ba17757114d434cd68218156be664e0db0` |

The 286 feature definitions use independently repaired cutoffs/source joins,stable
player histories and approximate league ties. Two mapped training appearances
remain unknown,25 played observations unmapped, older seven snapshot fields
explicitly missing; numeric NaNs are filled only inside the upstream-style model
transform. Provider corrections and historical schedule/publication knowledge
remain imperfect. No observation-age weighting is applied here, matching the
inspected external trainer; the contrasts measure named whole methods, not the
isolated causal effect of architecture. `benchmark_eligible=false` remains.

Original OpenFPL-labelled forecasts endGW24, not this later window, and exporter,
training/selection and capture lineage remain insufficient for original-system
admission. Current shipped weights cannot be applied backwards. Existing earlier
published comparisons remain separate retrospective evidence. Complete original
system parity/season-points claims therefore remain unresolved, not established
by this new three-method table.

## Work-plan consequence

Stop this fixed reference without further seeds/blend/hyperparameter trials.
No I4 finalist exists, so no candidate stability/operational-promotion package is
triggered. Preserve the approved model; use this finding to prioritise source
quality, decision relevance and genuinely future evidence over a larger ensemble.
The remaining prospective workflow must freeze actual future forecasts before
deadlines and score only finalised results. Future evidence cannot be generated
or retroactively manufactured in this research session.
