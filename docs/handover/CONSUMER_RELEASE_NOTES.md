# Consumer release notes for the weekly planner

Read these dated operational notes at every source sync, before weekly model
analysis. They describe releases that affect weekly use and any required action.
Source sync does not transfer private weights or registry changes: those still
arrive only through an authorised private transfer. A code release does not
promote a model.

Each future release that changes weekly-relevant behaviour must add a dated
entry here in the same pull request as the change.

## 2026-10-28 — PR42: intentional manager-state validation hardening

Released in commit `eba32263c847297da8d3055e160f7c564db00b4c`.
`season_engine.prepare` now rejects a recorded manager state in these cases:

| Recorded state | Exact error message |
|---|---|
| `free_transfers` exceeds the season profile's `ft_cap`. | `Transfer bank exceeds season cap` |
| A `used_chips` entry `(name, start)` does not match a chip window's name and start in the season profile. | `Chip history differs from season profile` |
| A used chip's window start is at or after the planning gameweek. | `Chip history must precede the origin` |

For a used-chip token, `start` means the **window start**, not the gameweek when
the chip was played. These checks are intentional. If a recorded history fails,
fix it from confirmed manager records and the matching season profile; never
loosen a check or invent missing history to make a plan run.

`rolling_planner` now takes the free-transfer cap from the season rules rather
than a fixed value. The configured cap is **5 in 2026-27**; use the profile for
the season being analysed.

Selection-report fields are additive. The existing `expected_before_hits` and
`expected_after_hits` values retain their previous meanings, both gross of
transfer charges. Added explicit gross/net fields and transfer-charge fields
make that accounting clear; they do not change the legacy values.

## 2026-10-28 — PR47: market-strength research

Released in commit `a0fbc6f98b2020981a07310fb85b5ea42b1f15e6`.
Research only; no consumer action. The challenger failed its player-development
gates. Approved **1.0.0** and weekly defaults are unchanged.

## 2026-10-29 — PR48: expected-return training-target research

Released in commit `8f8bfed6b086e5a41b6d1f2257af24b39c705724`.
Research only; no consumer action. Admission passed, but the challenger failed
four development gates. Approved **1.0.0** and weekly defaults are unchanged.
