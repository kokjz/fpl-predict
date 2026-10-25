# Appearance calibration: component results

26 October 2026. The [protocol](appearance_calibration_protocol_2026-10-26.json)
was fixed before the two calibration fits and their target-year evaluations.
This is a historical research checkpoint; the continuous-season matrix is running
separately. **No model or normal planning default is promoted.**

A single two-parameter Platt mapping is fitted on the preceding year's archived
next-origin minute-increment labels. The older three-year reference and all
38 source/calendar/rule origins are separately
[admitted](historical_2023_admission.json). The 2023/24 and 2024/25 training cohorts
contain 18,458 and 18,653 eligible observations. Each has one disagreement with
later final appearance histories; this diagnostic never removes or changes a
fitted row. Negative counter revisions, official zeros and calendar blanks are
excluded from training with counts retained in the [fit receipts](appearance_calibration_fits.json).
Training clocks are archive claims, not independently witnessed timestamps.

| Test season | Fixed current-origin cohort | Original Brier | Calibrated Brier | Relative reduction |
|---|---|---:|---:|---:|
| 2024/25 | All listed players | 0.086601 | 0.084017 | 2.98% |
| 2025/26 | All listed players | 0.076551 | 0.074863 | 2.20% |
| 2024/25 | Frozen proposed-squad union | 0.047491 | 0.042992 | 9.47% |
| 2025/26 | Frozen proposed-squad union | 0.065243 | 0.062512 | 4.19% |

Equal-season relative reductions average **2.59%** for all listed players and
**6.83%** for the proposed-squad unions. Both satisfy the declared component
criterion. Brier includes discrimination and outcome uncertainty; the full
[aggregate](appearance_calibration_component_results.json) retains fixed
reliability bins/counts and every season/cohort, including adverse changes.
Overlapping player/origin/role observations are not independent seasons.

Point means are **exactly unchanged**, so their MAE/RMSE are unchanged. Implied
conditional-return bias in the proposed unions moves from −0.010 to −0.147 in
2024/25 and +0.080 to −0.055 in 2025/26. A better appearance marginal does not
itself validate the conditional return or the whole expected-scoring model.
Explicit zero-support/official flags and raw pre-mixture probabilities remain
unchanged over all 316,570 appearance cells. No injury flag is automatically
cleared and unconditional point forecasts are never multiplied by appearance
probability.

On the eight saved mean-manager paths, new first-action selections preserve all
transfers, chips, future proposals and finances. Versus the original uncalibrated
expected selector, H6 effects are **+4, −2, −2, +10** (mean +2.50); adapted-Solio
effects are **+1, −2, +16, +2** (mean +4.25). These are conditional frozen-roster
overlays, **not adaptive season-policy gains or causal recoverable points**.
All 304 scores and 1,704 financial periods reconcile independently.

The joint diagnostic also retains original/calibrated count residuals and
same-club/different-club residual products over all 456 frozen current-squad
panels. Marginal calibration and dependence remain confounded; this is not an
identified correlation correction or an independent-sample significance test.

A separate scalar audit reconciles 208 metric/bin values and every probability
mapping; both fits satisfy the penalised logistic stationarity check. The
component job took about 67 seconds with maximum sampled process-group memory
below 707 MiB. Two tiny calibration fits plus source/cohort preparation took
about seven seconds below 610 MiB. The [20 source-only preflight cases](coherence_preflight_results.json)
reproduce all ten full-decision fingerprints. Numerical source:
`9e26851a92371690848e3811c6e120026dd33011`; fit/preflight source:
`39f19c977816794134c44c3844cc66632354a320`.

The next declared evaluation is eight calibrated candidate season paths on the
two existing target years and twelve older-year policy paths, with matched
frozen controls and two solver repetitions. The original mean/−19-season/
−38-opening criteria remain unchanged. Reused outcomes, restricted 2024/25
no-Assistant-Manager rules, bounded search, noisy labels and unequal historical
source coverage limit inference. This adds no new Dastan/OpenFPL forecasting
comparison: point forecasts are identical, and the new external management
comparison is explicitly the adapted Solio core under common controls, not an
original complete external manager.
