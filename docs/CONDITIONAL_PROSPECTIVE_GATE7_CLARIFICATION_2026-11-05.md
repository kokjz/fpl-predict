# Conditional-prospective: gate 7 clarification (pre-registration)

5 November 2026. **This is a pre-registration only. Nothing was fitted, read or computed, and approved 1.0.0 remains unchanged.**

[Clarification record](conditional_prospective_gate7_clarification_2026-11-05.json) · [Frozen protocol](conditional_prospective_protocol_2026-11-04.json) · [Blend addendum](CONDITIONAL_PROSPECTIVE_BLEND_ADDENDUM_2026-11-05.md) · [Execution addendum](CONDITIONAL_PROSPECTIVE_EXECUTION_ADDENDUM_2026-11-05.md)

## Why
Gate 7 compares each candidate's full-scoring forecast with official FPL points. The protocol does not name each arm's full forecast, and the blend addendum defines only the blend's core forecast. The engineer found this gap while building the phase 2 code and stopped before computing anything.

## What it fixes
Gate 7 uses each arm's full forecast:
- **Control:** its core prediction, since the frozen control has no defensive-contribution head.
- **Conditional:** its `expected_points` (core plus defensive contribution).
- **Blend:** half the control's full forecast plus half the conditional's `expected_points`.
  - Every blend gate input is then the equal-weight average of the two models' inputs for that same gate.
  - Gates 2–4 and 6 already use core forecasts.

The statistic is RMSE over player-gameweek sums against official `total_points`, as in the fplcache study.

## What it does not change
- The frozen models, protocol and earlier addenda.
- The candidates, window, thresholds and decision rule.
- No blend full-scoring value has been computed on any data.
