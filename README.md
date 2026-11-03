<p align="center"><img src="docs/assets/logo.svg" alt="fpl-predict logo" width="160"></p>

# fpl-predict

An open-source Python engine for forecasting Fantasy Premier League points and evaluating FPL decisions against historical results.

fpl-predict combines recent player form, playing-time patterns and fixture context in small tree-based models. It produces expected points and participation estimates, supports squad-level comparisons, and keeps forecast evaluation separate from model selection. It is intended for FPL analysis and reproducible research; it does not make transfers or operate an FPL account.

**Project status:** experimental, with a command-line interface. Python 3.12 is required. Source, tests and evaluation protocols are included; historical datasets and trained model binaries are not distributed. A fresh installation can run the tests and reproduce training experiments. Forecasting additionally requires a trusted model artifact approved by the runtime registry; see [model setup](#model-setup).


For a receiving model-improvement chat or a cross-device weekly workflow, start
with the [handover index](HANDOVER.md) and its explicit checkpoint/approval scope.

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
Full engine context and caveats: [engine overview](docs/ENGINE_OVERVIEW.md).

## Performance vs competitors

The published v1 historical evaluation used 163,072 player-match records from 2020/21–2025/26. On 15,308 eligible candidate records across the 2024/25 and 2025/26 expanding-window tests:

| Method | Core-points RMSE ↓ | Core-points MAE ↓ |
|---|---:|---:|
| fpl-predict v1 | **2.900** | **2.101** |
| Last-five average | 3.175 | 2.365 |
| Recency average | 2.982 | 2.108 |

Eligibility uses prior history and lagged minutes, rather than selecting players by their eventual performance. Core points exclude the separately modelled defensive-contribution award. These results do not establish a captaincy or full-season points advantage. [Validation details and limitations](docs/validation.md).
A separate matched retrospective comparison against Dastan covers 17,622 player-gameweeks in 2024/25 GW15–38. On the 5,145 players/gameweeks meeting fpl-predict's pre-deadline candidate criteria:

| Method | Full-points RMSE ↓ | Full-points MAE ↓ |
|---|---:|---:|
| fpl-predict v1 | 2.9765 | 2.1354 |
| Dastan | **2.8910** | **2.0204** |

On that same candidate cohort, v1 achieved higher **top-10 ranking quality**
(mean NDCG@10 **0.4937 versus 0.4878**, leading in 13 of 24 GWs). This is a
planning-relevant historical strength: it rewards putting high-return options
near the top, although it does not enforce squad constraints. The small lead has
an exploratory uncertainty interval spanning zero.

Dastan had about 2.9% lower RMSE on those matched records. Training policies and feature sets differ, and this is an archived retrospective comparison, not a prospective competition. Do not compare this table directly with the core-points table above: the periods and targets differ. [Comparison methods, provenance and aggregate results](docs/open_source_comparison_2026-10-14.md).

- [OpenFPL](https://github.com/daniegr/OpenFPL) uses position-specific tree ensembles with FPL and Understat features; its published test window and cohorts differ, so headline errors are not directly comparable.
- [AIrsenal](https://github.com/alan-turing-institute/AIrsenal) uses team-scoreline and player-involvement models connected to squad/transfer optimisation.

The [full benchmarks](docs/BENCHMARKS.md) retain the Dastan error decomposition, selection comparisons, source distinctions and uncertainty.

## Research programme

Pre-registered studies use fixed gates and publish negative results. A code merge does not promote a model: **approved 1.0.0 and weekly defaults remain unchanged**. See the [research results index](docs/RESEARCH_RESULTS.md) for dated outcomes and reports.

The optional [season-management system](docs/season_management.md) carries squad state across 38 deadlines; its [results and limitations](docs/SEASON_MANAGEMENT_RESULTS.md) remain separate from forecast-error benchmarks.

## Install

The commands below require Git, Python 3.12 and a POSIX shell:

```sh
git clone https://github.com/kokjz/fpl-predict.git
cd fpl-predict
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
export FPL_PREDICT_HOME="$PWD/var"
.venv/bin/fpl-predict init
```

The default tests use synthetic fixtures and run offline. Historical datasets and trained model binaries are not distributed. [Full setup and workspace instructions](docs/USAGE.md#install).

## Model setup

Forecasting requires a trusted artifact matching the approved registry entry:

```sh
.venv/bin/fpl-predict install-model /path/to/trusted-model.joblib
```

Installation verifies the expected SHA256 before copying the file. Forecasting verifies the registered artifact again before loading it. Do not load arbitrary downloaded Joblib/Pickle model files: their deserialisation can execute code.

**Training does not install or approve its output for forecasting.** See [reproduction and model setup](docs/USAGE.md#model-setup), [validation](docs/validation.md) and the [promotion gates](src/model_registry.py).

## Forecast for a squad

Once an approved artifact is installed, refresh the public data and supply your squad JSON:

```sh
.venv/bin/fpl-predict refresh
.venv/bin/fpl-predict forecast --team-state "$FPL_PREDICT_HOME/squad.json"
```

The [full usage guide](docs/USAGE.md#forecast-for-a-squad) documents the required 15-player squad, selling prices, bank, free transfers, output files and optional sourced scenarios. Store account-specific inputs outside tracked source.

**Season support:** live forecasting currently checks the 2026/27 data schema. Another season requires a rules/schema review before use. Forecasts beyond the next gameweek are planning approximations, not equally validated multiweek predictions.

## Evaluate a saved forecast

Keep the forecast created before the relevant deadline. After all results are officially finished and checked:

```sh
.venv/bin/fpl-predict refresh
.venv/bin/fpl-predict score --forecast /path/to/saved/forecast --gw 7
```

Scoring rejects late-generated forecasts and unfinished/unchecked outcomes, and refuses to overwrite an existing outcome report for the same snapshot. [Scoring details and research commands](docs/USAGE.md#evaluate-a-saved-forecast).

## Limitations

- Historical archives contain corrected outcomes, not complete pre-deadline news, schedule and selling-price snapshots.
- Current rules, fitness, expected roles and fixture changes require review; the model does not independently verify news sources.
- Minute scaling and double-gameweek appearance independence are approximations. Empirical point intervals do not capture every source of uncertainty.
- Lower prediction error does not guarantee more FPL points. Transfer/chip comparisons are conditional, and the engine does not execute decisions.
## Documentation and contributing

- [Research results](docs/RESEARCH_RESULTS.md), [benchmarks](docs/BENCHMARKS.md) and [season management](docs/SEASON_MANAGEMENT_RESULTS.md)
- [Full usage](docs/USAGE.md), [engine overview](docs/ENGINE_OVERVIEW.md) and [handover / weekly workflow](HANDOVER.md)
- [Validation](docs/validation.md), [data sources](docs/data.md) and [availability reviews](docs/availability_workflow.md)
- [Contributing](CONTRIBUTING.md) and [security](SECURITY.md)

Source is in `src/`, offline tests in `tests/`, and repository utilities in `tools/`. Contributions should include relevant validation and preserve chronological evaluation, artifact integrity and the distinction between code changes and model approval.

## License

[MIT](LICENSE) for the code. External datasets and Premier League trademarks retain their own terms. This project is unaffiliated with the Premier League.
