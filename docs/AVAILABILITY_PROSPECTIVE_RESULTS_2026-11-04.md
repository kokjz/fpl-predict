# Availability-prospective phase1: sanity gate failed

The structured availability arm fails the pre-registered retrospective sanity gate because candidate MAE worsens beyond the 0.5% limit. **Approved 1.0.0 remains unchanged.** No prospective models were frozen and no 2026/27 data or predictions were read or generated.

[Protocol](availability_prospective_protocol_2026-11-04.json) · [Aggregate receipts and metrics](availability_prospective_results_2026-11-04.json)

## Fixed design and source admission

Corrected CORE control (49 features) versus the same HGB7 learner plus availability chance and missingness (51 features). Both train on 2020/21 through 2025/26 GW19 and test GW20–38, with identical rows, recency weights and two threads. Labels are covariates; known zero remains distinct from unknown. These outcomes were already inspected in earlier studies, so this is a sanity check, not prospective evidence.

Protocol freeze `8541a64182bac745a78864fd0d1336a4b9b7c2f8` was pushed before calculations; LF SHA256 `5d6a3fce13a1ce1c8baacbfb6724ae375b329d63be0c3086ba541d8fb95feab5`. Numerical implementation `0b83e318865eb2573df956ae12565573057f324c` passed exact-head CI before the single guarded admission and two serial fit jobs.

All 35 GW4–38 exact Git prefixes passed source/bootstrap identity and deadline checks using the unchanged admission helper. GW1–3 are explicitly `no_source`/unknown, making exactly 38 census rows. Reusing the same hash-verified proof, archive, bootstrap snapshots and helper reproduces the earlier study’s admitted observations; all 35 source-audit records match. Git publication time is publisher history, not independently certified time.

The corrected control matches PR64 byte-for-byte across all 163,072 rows. Candidate first49 feature columns preserve those exact control bytes. Older seasons remain entirely unknown; 2025/26 has 12,129 unknown rows out of 29,747 (40.77%). No new archive retrieval was needed.

## Gate B: inspected GW20–38

| Candidate player-GW measure | Control | Availability | Threshold | Pass |
|---|---:|---:|---:|---|
| RMSE | 2.81507608 | 2.79494177 | 2.81507608 | True |
| MAE | 2.07178440 | 2.09869962 | 2.08214332 | False |
| NDCG@10 | 0.39532323 | 0.40414489 | 0.39137000 | True |

Candidate player-GW RMSE changes -0.715%, MAE +1.299%, and NDCG@10 +2.232%. The MAE guardrail fails, so Gate B passes only two of three criteria. Bias rises from 0.03925 to 0.16355.

Fixture RMSE is 2.78564714 versus 2.76671722; fixture MAE is 2.04557612 versus 2.07317387. Per-position diagnostics are in the JSON. Twenty fixed opening-GW20 squads give a descriptive mean availability-minus-control delta of -3.40 points over GW20–38 (range -15 to +14). Both use core-point forecasts for selection and realised full points/autosubs for settlement, with no added DC forecast. This is not a full-season management comparison.

The control prediction hash is new for this training window. Existing PR60/PR64 predictions use a different training cutoff and cannot serve as same-row method parity receipts; the underlying corrected control feature arrays do match.

## Decision and resources

Do not proceed to Stage F. There are no frozen model hashes, freeze push time or first prospective gameweek. The pre-registered phase2 plan remains recorded in the protocol but has no frozen candidates from this package. Any new experiment requires a new brief; no thresholds or features were revised after observing this result.

One admission, two fits and one aggregate job completed in 227.843s combined, peak job committed memory 1254174720 bytes. Every job used a fresh storage baseline, grew less than 2GiB and left zero active processes. No real-run retries, new retrievals or 2026/27 content reads. Legacy runtime: Python3.12.16, NumPy2.3.5, pandas2.2.3, scikit-learn1.9.1; full Ubuntu CI uses NumPy2.5.4. Per-job resource receipts are in the JSON.

The archive and bootstrap data remain private. No fitted binaries, raw source labels or news text are published. Registry, production defaults and weekly pipeline remain unchanged. Architect pre-merge review: **PENDING**.
