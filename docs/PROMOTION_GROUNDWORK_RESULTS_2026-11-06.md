# Conditional promotion groundwork — 6 November 2026

**GROUNDWORK_READY_NO_DRY_RUN. Architect pre-merge review: PENDING.**
Approved **1.0.0** and the registry are unchanged. No action now; inert until a conditional
champion is registered by a separately approved promotion. No promotion is made here.

The [write-once policy](conditional_promotion_policy_2026-11-06.md) was frozen in
`b20ed76eaf08609b0e9ec1306f8fbf5444b8bc14` before implementation. It selects the unchanged
passing conditional or equal-blend recipe after phase 2, with an annual production refit,
fixed acceptance checks and fallback to the frozen passing model. Both phase-2 failures
mean no promotion. Approved 1.0.0 remains the rollback version. Phase 2 is unchanged.

The [adapter](champion_availability.md) now supports conditional forecasts, horizons and
approved decision appearance views. It learns the official next-GW label as a covariate;
later GWs use missing labels. Next-GW manual availability/minutes output scaling is refused.
A sourced pre-deadline chance/out replacement changes the input label and records both
official and replacement values. The adaptive sensitivity path enforces the same rule on
conditional Horizons. Existing non-conditional outputs and sensitivity behaviour are retained.

## Verification and limitations

- Synthetic reference captured with weekly source still identical to base `2a2212a`, on
  test-only harness commit `e643ae0135bdfa433c92eb9638e45fcdf0711613` after exact-head CI succeeded.
- Canonical synthetic output bytes match across forecast fixture/player-GW/planning outputs,
  direct horizon means and approved decision mean/appearance views. Reference SHA256:
  `8e1c98046fcb5e2ed4d063156a2a26bfb54f99a8b77993df184a7a16d387b23c`.
- A stand-in with the real `predict(x,pos)` signature and availability covariates verifies
  2 next-GW labelled rows and 4 later missing rows in the horizon case, and 15/15 in the
  forecast case. Replacement affects only its target; double-fixture labels cover both matches.
  P6 refusals, source/timing/identity admission, both-label provenance and later-GW sensitivity pass.
- Rolling and adaptive planning, season action validation, CLI horizon planning and saved-forecast
  decision trials accept the conditional result. Approved mean and appearance views reproduce
  the same means. The stand-in is a plumbing fixture, not a calibrated forecast.
- Local targeted suite: 142 passed, 4 optional integration checks skipped. Exact implementation
  CI is green on `24f23f0ebdcd31fbbe65722f517adc5d17e35b0e`. Ubuntu CI also runs the full suite and wheel check.
- The first guarded inventory attempt failed because the harness selected the LATEST file.
  Its outputs were preserved. A separately authorised correction was tested and committed;
  the second attempt passed without further retry. Inventory and feasibility contents match.
- Successful inventory job: 3.250s, peak committed memory
  234278912 bytes, package 53394 bytes,
  2 threads, no residual workers. No fit or accuracy metric was computed.

**DRY_RUN_INFEASIBLE:** the current forecast entry point has no admitted historical source
adapter and requires its current-season sentinel and per-player snapshot files. The approved
bridge also needs a truthful artifact existence observation before origin. No historical
adapter, relabelled bootstrap or fabricated observation was created. The fit and dry-run
budgets were withdrawn: **0 fits and 0 dry runs**.

**No real conditional artifact has been loaded through `champion_availability`.** This is left
to the frozen policy's P4 pre-season smoke check during separately authorised promotion.
No prospective content was read, and no performance or production-readiness claim is made
from the synthetic checks. Protected modules, frozen records and approved weights are unchanged.

The [JSON record](PROMOTION_GROUNDWORK_RESULTS_2026-11-06.json) includes source identities,
policy hashes, CI references, resource counts and all verification limits. PR73 remains
subject to architect pre-merge review and explicit user merge authority.
