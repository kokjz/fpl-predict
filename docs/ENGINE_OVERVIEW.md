# Engine overview and project context

<p align="center"><img src="assets/logo.svg" alt="fpl-predict logo" width="160"></p>

# fpl-predict

An open-source Python engine for forecasting Fantasy Premier League points and evaluating FPL decisions against historical results.

fpl-predict combines recent player form, playing-time patterns and fixture context in small tree-based models. It produces expected points and participation estimates, supports squad-level comparisons, and keeps forecast evaluation separate from model selection. It is intended for FPL analysis and reproducible research; it does not make transfers or operate an FPL account.

**Project status:** experimental, with a command-line interface. Python 3.12 is required. Source, tests and evaluation protocols are included; historical datasets and trained model binaries are not distributed. A fresh installation can run the tests and reproduce training experiments. Forecasting additionally requires a trusted model artifact approved by the runtime registry; see [model setup](USAGE.md#model-setup).

For a receiving model-improvement chat or a cross-device weekly workflow, start
with the [handover index](../HANDOVER.md) and its explicit checkpoint/approval scope.

## What it does

- Predicts fixture-level core points, defensive-contribution points, expected minutes, appearance probability and probability of playing at least 60 minutes.
- Aggregates fixtures into gameweeks, including blanks and doubles.
- Compares legal starting XIs, captain/vice-captain choices, bench order, individual transfers and conditional Triple Captain/Bench Boost opportunities for a supplied squad.
- Supports documented, gameweek-specific minutes and availability scenarios.
- Scores forecasts saved before the deadline against finalised results, with points error, playing-time diagnostics and a matched official FPL projection baseline where available.

It is a forecasting and decision-support engine, not a complete season optimiser. Transfer chains, saved-transfer option value, expected automatic substitutions and joint chip scheduling are not fully optimised.

## How the engine works

1. **Collect data.** Public FPL endpoints provide player metadata, fixtures and match histories. Historical training data come from the [Vaastav FPL archive](https://github.com/vaastav/Fantasy-Premier-League). Downloads retain source revisions, timestamps and file hashes.
2. **Build features available before the deadline.** Player, team and opponent statistics use four- and twelve-match half-lives. Features include position, venue, playing time, attacking statistics, saves and team results. Player names/IDs, same-match outcomes and archived lookahead projections are excluded from model inputs. Double-gameweek fixtures share a history cutoff.
3. **Fit pooled models.** Histogram gradient-boosted trees learn patterns shared across players. Separate estimators cover core points, minutes, participation and defensive-contribution awards. Training examples have a two-year age half-life. The core model uses shallow seven-leaf trees; no GPU or hosted inference service is required.
4. **Forecast and evaluate.** Fixture forecasts are summed into gameweeks and optionally compared within a squad. The model registry checks approval status and artifact hashes. Evaluation uses chronological splits; a merged code change or a newer experiment does not automatically replace the approved model.


## Limitations

- Historical archives contain corrected outcomes, not complete pre-deadline news, schedule and selling-price snapshots.
- Current rules, fitness, expected roles and fixture changes require review; the model does not independently verify news sources.
- Minute scaling and double-gameweek appearance independence are approximations. Empirical point intervals do not capture every source of uncertainty.
- Lower prediction error does not guarantee more FPL points. Transfer/chip comparisons are conditional, and the engine does not execute decisions.

## Documentation and contributing

- [Validation](validation.md), [data sources](data.md) and [availability reviews](availability_workflow.md)
- [Open-source comparisons](open_source_comparison_2026-10-14.md) and [bounded experiment protocol](I3_PROTOCOL.md)
- [Contributing](../CONTRIBUTING.md) and [security](../SECURITY.md)

Source is in `src/`, offline tests in `tests/`, and repository utilities in `tools/`. Contributions should include relevant validation and preserve chronological evaluation, artifact integrity and the distinction between code changes and model approval.

## License

[MIT](../LICENSE) for the code. External datasets and Premier League trademarks retain their own terms. This project is unaffiliated with the Premier League.


Back to the [project overview](../README.md).
