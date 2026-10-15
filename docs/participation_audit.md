# Participation-risk audit

The [comparison diagnosis](comparison_interpretation.md) motivates reviewing non-appearance errors before changing model weights. This optional read-only tool adds point-error attribution to existing minutes/probability diagnostics and an evidence preflight for an already generated forecast. It never fits, calibrates, forecasts, chooses a squad, fetches news, changes the registry or applies overrides.

## Finalised historical forecast

```sh
fpl-predict participation-audit history --forecast /path/to/frozen/forecast \
  --origin /path/to/forecast/bootstrap.json --outcome /path/to/finalised/snapshot \
  --gw 7 --output /path/to/new/history-audit.json
```

The adapter requires predeadline input/generation times and outcomes marked finished/data-checked. It verifies unique player/fixture identities, stable player codes/positions, finite values and probability bounds, and hashes retained inputs. Missing history files fail. A retained official history with no rows for that completed GW is explicitly counted and summed as zero under the endpoint's recorded-history convention; missing files never imply zero.

Both all forecasts and the predeadline candidate cohort receive point-error decomposition by actual minutes, reliability/Brier summaries, fixed predicted-probability bands (0–0.5,0.5–0.8,0.8–0.95,0.95–1), and predicted-minutes bands (<30,30–60,60+). Each band reports non-appearances and its contribution to total point MSE. The 0.8 boundary is a descriptive heuristic, not a tuned transfer rule. Probabilities mean any minutes, rather than starting or 60+. Cards alone do not mean minutes. Doubles sum points/minutes and retain the existing approximate aggregate appearance probability. Realised-minute groups are diagnostic only, never future selectors.

A single GW cannot justify recalibration or prove a points gain. Brier score mixes calibration/discrimination; reliability bins and sample size matter too. Old archives missing v1 p_play cannot diagnose matched probability calibration; p60 must not substitute for it. Unconditional point forecasts must not simply be multiplied by p_play again.

## Predeadline evidence preflight

After the weekly chat is authorised to refresh news and generate its normal forecast:

```sh
fpl-predict participation-audit preflight --forecast /path/to/new/forecast \
  --snapshot /path/to/fresh/official/snapshot --as-of 2026-10-17T09:00:00Z \
  --gw 7 --output /path/to/new/preflight.json
```

Dates and paths are illustrative. Inputs, forecast generation, and explicit `--as-of` must precede the verified GW deadline. Snapshot must name that GW as next/unfinished, its manifest must bind bootstrap bytes and a public official FPL bootstrap URL, and it cannot be older than forecast generation. Review candidates plus optional owned/non-candidate IDs supplied with repeated `--include-id`. Unknown IDs fail; outputs stay private.

Optional `--review /path/to/sourced/review.json` uses the existing timestamped [availability review schema](availability_workflow.md). Flags cover status/news/chance observations, changes since the frozen forecast, missing/stale review and stale inputs. Official percentages are not calibrated probabilities; status `a`/blank news do not certify health. A sourced sensitivity assumption does not silently clear a flag or establish a start.

Freshness heuristics are fixed review prompts: snapshot <=6h old, forecast <=24h old, manual evidence check <=24h old. They are not learned accuracy guarantees. The output says `review_required` or `no_machine_detected_issues`, never fitness clearance. Press-conference/fixture completeness is not certified. Future outcomes cannot influence the preflight, which reads only supplied predeadline evidence. No override or planning decision is automatic.

## Next-cycle decision

Keep the approved model and existing sourced sensitivity workflow. The weekly chat should review plausible targets, owned players and prospective captains for current role/fitness evidence, preserve base and scenario forecasts, freeze the comparison before deadline and assess finalised outcomes afterward. No schedule/background monitor/cross-chat message is created.

Earlier hurdle/richer-participation challengers failed development gates. Isolate source freshness, refit frequency or conditional-return modelling one factor at a time in future chronological development studies, with error, ranking and legal-decision gates and a genuinely later audit. This package performs diagnostics and workflow checks, not another search on inspected comparison outcomes.
