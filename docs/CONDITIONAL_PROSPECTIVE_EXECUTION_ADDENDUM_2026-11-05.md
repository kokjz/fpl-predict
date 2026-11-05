# Conditional-prospective: phase 2 execution addendum (pre-registration)

5 November 2026. **This is a pre-registration only. Nothing was fitted, read or computed, and approved 1.0.0 remains unchanged.**

[Addendum record](conditional_prospective_execution_addendum_2026-11-05.json) · [Frozen protocol](conditional_prospective_protocol_2026-11-04.json) · [Freeze record](conditional_prospective_freeze_2026-11-05.json) · [Blend addendum](CONDITIONAL_PROSPECTIVE_BLEND_ADDENDUM_2026-11-05.md) · [Fplcache results](FPLCACHE_AVAILABILITY_RESULTS_2026-11-05.md)

## Why
The frozen protocol leaves four phase 2 details open. Fixing them now means none of them is decided after 2026/27 results exist:
- **Fixed squads (gate 6):** the protocol gives no 2026/27 squad specification, and the phase 1 selector is hard-wired to 2025/26 GW20.
- **Label code path:** the unchanged incumbent code only attaches 2025/26 labels, and the fplcache code refuses seasons after 2025/26.
- **Missing label weeks:** the protocol names one label source (AIrsenal) and says nothing about weeks it does not cover.
- **Runtime:** the freeze record does not say which runtime must load the frozen models.

## What it fixes
- **Fixed squads:**
  - the selector released with the fplcache study, whose 2025/26 replica reproduced phase 1's squads exactly;
  - season 2026/27, opening at the first prospective gameweek (GW10), through GW38;
  - 20 squads, seed 20260921, a £100.0m budget, and the unchanged pool, legality and autosubstitution rules;
  - the same squads for every arm. Too few legal squads stops the package; nothing is re-drawn.
- **Labels:**
  - AIrsenal under the protocol's rule, joined by permanent player code (the identity lesson from the fplcache study);
  - encoding unchanged;
  - attached by a new module that must first reproduce the 2025/26 signals exactly.
- **Missing label weeks:**
  - a gameweek with no AIrsenal observation uses the fplcache snapshot chosen by the fplcache study's rules. The two sources agreed on 99.84% of 2025/26 keys.
  - The fallback applies per gameweek, never per player.
  - No 2026/27 coverage of either archive has been checked.
- **Calendar:** weeks without fixtures have no rows; double gameweeks are summed per player; deadlines are re-verified at phase 2.
- **Runtime:** the frozen models are loaded only in Python 3.12.16 with scikit-learn 1.9.1, NumPy 2.3.5 and pandas 2.2.3.
  - A later readiness package records a prediction-hash check on past data.
  - Phase 2 must reproduce that hash before scoring; a mismatch stops it, with no refit.

## What it does not change
- the frozen models, protocol, freeze record and blend addendum;
- the candidates, window (GW10–GW38) and gates.

Any further gap found at phase 2 stops the package. Its fix must be mechanical, chosen without looking at candidate results, and disclosed as post-registration.
