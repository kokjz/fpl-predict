# Conditional-prospective phase 1: sanity passed, research models frozen

The unchanged conditional availability forecaster passes its pre-registered retrospective sanity gate. Both models are frozen privately for a future prospective test. **Approved 1.0.0, the registry and weekly defaults remain unchanged.** This is research evidence, with no 2026/27 forecasts, outcomes or availability values inspected and no prospective performance claim.

[Protocol](conditional_prospective_protocol_2026-11-04.json) · [Frozen learner hashes](conditional_prospective_freeze_2026-11-05.json) · [Aggregate receipts](conditional_prospective_results_2026-11-05.json)

## Fixed design and admission

Control is corrected CORE (49 features), unchanged HGB7, points_core and clipping [0,20]. The candidate uses unchanged conditional_forecaster.fit/predict: learned appearance with the two availability signals times points conditional on appearing, plus a training-only card prior. Only core_xp is compared; dc_xp and expected_points are descriptive. This is not multiplication of an unconditional points prediction. DC and training targets come from the same established loader, joined by season/fixture/fpl_code. Parsed corrected CORE bytes reach both methods unchanged.

Protocol commit `0f4124619f074f706c49d16f6b8676faace53daf` was pushed before real calculations; LF SHA256 `080ae509da85dd471b6040b7c6df1f2d8470261e6dc0bc5057a2eaf72de7f1ab`. Numerical source `487f0f127dd3b1cc761f114ec55c635960c5f0dd` had both exact-head CI runs green before the single guarded admission. Its PR CI had initially stayed pending despite successful steps; it finalized on its own before continuation, without cancellation or rerun.

All 35 GW4–38 prefixes pass the unchanged exact-prefix/commit-time and bootstrap identity rule. GW1–3 are no_source/unknown, giving 38 census rows. The 27,553 keyed source labels exactly reproduce PR65. Git commit time remains publisher history, not independent certification. No new source retrieval was needed. Older seasons are entirely unknown; 2025/26 has 12,129 unknown rows out of 29,747 (40.77%). Known zero and unknown stay distinct.

Corrected CORE/control export parity passes on all 163,072 rows, as do the candidate prefix bytes. All required training columns exist; DC labels are observed only where supplied by the loader, with per-season coverage in the JSON. The Stage B control predictions match PR65 on all 15,572 fixtures both as raw arrays and through the original CSV boundary by key.

## Gate B: inspected 2025/26 GW20–38

Both methods train through 2025/26 GW19 on the same earlier rows and recency weights. These outcomes were inspected repeatedly in earlier packages: this is a sanity check, not independent or prospective evidence.

| Candidate player-GW measure | Control | Conditional | Maximum allowed | Result |
|---|---:|---:|---:|---|
| RMSE | 2.81507608 | 2.77631709 | 2.81507608 | PASS |
| MAE | 2.07178440 | 2.03865230 | 2.08214332 | PASS |

Across 4,055 candidate player-GWs, RMSE changes -1.377% and MAE -1.599%. NDCG@10 is descriptive: 0.39532323 versus 0.40057066. Bias is 0.03925292 versus 0.08493480. Candidate fixture RMSE is 2.78564714 versus 2.74761917, and MAE 2.04557612 versus 2.01480644. All-player and per-position diagnostics are in the JSON.

| Window | Control RMSE | Conditional RMSE | Control MAE | Conditional MAE | Control NDCG@10 | Conditional NDCG@10 |
|---|---:|---:|---:|---:|---:|---:|
| GW20-27 | 2.79855404 | 2.75749416 | 2.05484697 | 2.00566495 | 0.34793459 | 0.36236816 |
| GW28-38 | 2.82746810 | 2.79042362 | 2.08455341 | 2.06352122 | 0.42978769 | 0.42835430 |

The unchanged mean selector, realised full points and autosubs on the same 20 opening-GW20 squads (seed 20260921) give conditional-minus-control -2.75 points over GW20–38, range -20 to +17. Selection uses core-point forecasts for both methods, with no added DC forecast. This descriptive negative squad result is a real prospective risk; it is not a full season management comparison and does not change the sanity gate. No expected-bench selector was run.

Against the rounded PR26 published tables, current GW20–27 conditional RMSE/MAE/NDCG differences are -0.13118584/-0.15647505/+0.00859816; GW28–38 differences are -0.15082638/-0.17492878/-0.01803570. The anchor and corrected CORE differ, so this is descriptive, not exact PR26 reproduction. Both methods' differences are retained in the JSON.

## Freeze and prospective boundary

Stage F trains on all 163,072 original rows through 2025/26. Six learner hashes (one control, five conditional), the training-row and feature hashes, and card prior are published in the immutable linked freeze record. The weighted card-only prior has 11 events among 96407 nonappearance rows: rate 0.00010256300620, mean core return -1.145275788600. Fitted binaries remain private and outside the approved registry.

The first commit publishing these hashes is `1b5991d75a6aa7456b2c26f264e3df17b506e68f`, successfully pushed at **2026-11-04T16:35:10.588041+00:00**. This completion timestamp conservatively follows remote acceptance. The first deadline strictly later is **2026/27 GW10**, **2026-11-06T18:30:00+00:00** (7 November 2026, 02:30 Asia/Singapore).

Deadline source: an already-admitted official FPL bootstrap captured **2026-10-23T15:42:30.936207+00:00**, SHA256 `14277c02079a4a0f339f3bfba8d754a3b75656c5ae7cc5105f460f6f162e88d1`. A selective reader kept only event id/deadline_time, skipped every other value without decoding it, stopped after events, and never traversed player availability. No new FPL read was needed. This uses the retained calendar rather than fresh schedule verification, an explicit limitation. No 2026/27 outcome, prediction or availability value was decoded, saved or inspected.

The pre-registered phase 2 is a separate package after 2026/27 GW38, with no interim scoring: frozen models, exact-prefix availability and corrected as-of features from GW10 through GW38; complete vaastav outcomes else official event-live; registry gates 2–7, including nonnegative fixed-squad delta. NDCG and reproducible forecasts from approved 1.0.0 are descriptive. A full pass only permits consideration of a separate promotion brief, including a weekly-planner change to prevent double counting availability.

## Resources and status

One admission, two B fits, one aggregate and two F fits completed serially: 378.078s combined, peak job committed memory 1378906112 bytes, two threads. Every job stayed within 4 GiB/900s, fresh-baseline growth of 2 GiB and at least 5 GiB free; all left zero active processes. Per-job storage growth and resource receipts are in the JSON. No real-run retry or source retrieval. Legacy numerical runtime is Python3.12.16/NumPy2.3.5/pandas2.2.3/sklearn1.9.1; Ubuntu CI uses NumPy2.5.4. Cross-runtime model portability and future forecast accuracy are not established here.

No raw source labels, private snapshot, fitted binaries or individual forecasts are published. Approved 1.0.0 remains approved. Architect pre-merge review: **PENDING**. Stop before merge, tag and branch cleanup; no promotion follows from this code publication.
