# Conditional promotion policy — 6 November 2026

Frozen before implementation. No promotion or weekly action is authorised here.

**P1. Scope.** The policy applies only after the authorised phase 2 package has recorded its outcome under the unchanged protocol, blend addendum, a2 and a3. Nothing in this policy changes how phase 2 is scored.

**P2. Outcome → recipe:**
- **Conditional PASS:** the production recipe is `conditional_forecaster.fit`, unchanged.
- **Conditional FAIL and `blend_equal` PASS:**
  - core = 0.5 × control-recipe core + 0.5 × conditional `core_xp`;
  - full = 0.5 × control full + 0.5 × conditional `expected_points`, as in a3.

  Both recipes are unchanged.
- **Both FAIL:** no promotion. 1.0.0 stays, and this policy expires.

**P3. Refit choice, decided now.**
- **The production artifact is a refit** of the passing recipe:
  - **Data:** all admitted seasons 2020/21–2026/27.
  - **Labels:** fplcache pre-deadline availability labels for 2021/22 onward. Use code-keyed identity and the per-GW fplcache fallback where AIrsenal is missing, as a2 fixed for phase 2. 2020/21 has no labels and stays `availability_missing = 1`.
  - **Recipe:** unchanged, including `sample_weights`, learners and seeds.
- **Rationale, recorded in the policy:**
  - **The frozen model saw few labels.** The frozen phase 1 candidate was trained on 2020/21–2025/26 (163,072 rows), with availability labels only where AIrsenal had them (from September 2025).
  - **fca showed labels drive the gain:** with fplcache labels, the same recipe passed retrospectively on 2022/23–2024/25 (RMSE −1.76%, MAE −3.18%, fixed squads +2.48). The label-free arm was about 0, and more labelled seasons helped.
  - **Precedent:** refitting a validated recipe on all data is how 1.0.0 itself was built (`train.py`: held-out validation, then the final core fitted on all seasons).
- **Cadence:** fitted once, before 2027/28 GW1, then once a year before each season (user decision of 6 November 2026, after in-season-refit NO_HARM). No mid-season refits.

**P4. Refit acceptance checks (no tuning, and no outcome-based selection).** All must pass:
1. a deterministic rebuild: two builds give identical prediction hashes on a fixed row set;
2. leakage, label-coverage and identity receipts for every season;
3. the recipe metadata matches the phase-2-passing recipe;
4. a descriptive comparison with the frozen phase 2 model on a fixed historical row set: correlation and mean absolute difference, reported only;
5. a pre-season smoke forecast on the 2027/28 bootstrap: finite values, coverage counts, and the P6 rules enforced.

No accuracy gate is computed on 2026/27, because that season is training data for the refit. Do not create any other candidate, arm, seed or hyperparameter.

**P5. Fallback and rollback:**
- If any P4 check fails, promote the frozen phase-2-passing model unchanged.
- 1.0.0 stays in the registry as the rollback version.
- Registration needs a separately authorised promotion package, with a CONSUMER_RELEASE_NOTES entry and a weekly-planner update.

**P6. Weekly double-counting rule for a `requires_availability` champion** (implemented in Part I):
- **Next GW:** the official `chance_of_playing_next_round` enters only as the learned covariate. Manual output scaling (`availability` factor or `minutes` override) is **refused** for next-GW rows.
- **Manual news input for the next GW:** the only allowed manual input is a sourced, pre-deadline replacement label: `chance` in {0, 25, 50, 75, 100}, or `out` = 0. It is passed to the model as the covariate in place of the official label, and both values are recorded in provenance. Its schema and timing rules are the same as for the existing availability review.
- **Later GWs:** the model sees missing availability, so the existing illustrative sensitivity stays allowed and unchanged.
- **Non-conditional champions (1.0.0):** behaviour is unchanged.
