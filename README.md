# fpl-predict

An open-source Python engine for forecasting Fantasy Premier League points and evaluating FPL decisions against historical results.

fpl-predict combines recent player form, playing-time patterns and fixture context in small tree-based models. It produces expected points and participation estimates, supports squad-level comparisons, and keeps forecast evaluation separate from model selection. It is intended for FPL analysis and reproducible research; it does not make transfers or operate an FPL account.

**Project status:** experimental, with a command-line interface. Python 3.12 is required. Source, tests and evaluation protocols are included; historical datasets and trained model binaries are not distributed. A fresh installation can run the tests and reproduce training experiments. Forecasting additionally requires a trusted model artifact approved by the runtime registry; see [model setup](#model-setup).

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

Official injury percentages are retained as observations, not treated as calibrated start probabilities. Sourced minutes overrides use illustrative scaling rather than a separately validated conditional model. See the [availability workflow](docs/availability_workflow.md).

## Performance and other options

The published v1 historical evaluation used 163,072 player-match records from 2020/21–2025/26. On 15,308 eligible candidate records across the 2024/25 and 2025/26 expanding-window tests:

| Method | Core-points RMSE ↓ | Core-points MAE ↓ |
|---|---:|---:|
| fpl-predict v1 | **2.900** | **2.101** |
| Last-five average | 3.175 | 2.365 |
| Recency average | 2.982 | 2.108 |

Eligibility uses prior history and lagged minutes, rather than selecting players by their eventual performance. Core points exclude the separately modelled defensive-contribution award. These results do not establish a captaincy or full-season points advantage. [Validation details and limitations](docs/validation.md).

Related open-source projects take different approaches:

| Project | Approach | Relationship to fpl-predict |
|---|---|---|
| [OpenFPL](https://github.com/daniegr/OpenFPL) | Position-specific tree ensembles using FPL and Understat features | A broader ensemble approach; its published test window and cohorts differ, so headline errors are not directly comparable. |
| [Dastan](https://github.com/qazybekb/smartplayfpl-dastan) | Participation and conditional-return models blended with direct point predictions | A richer forecasting benchmark with retained historical predictions. |
| [AIrsenal](https://github.com/alan-turing-institute/AIrsenal) | Team-scoreline and player-involvement models connected to squad/transfer optimisation | A broader team-management framework using event-based forecasting. |

A separate matched retrospective comparison against Dastan covers 17,622 player-gameweeks in 2024/25 GW15–38. On the 5,145 players/gameweeks meeting fpl-predict's pre-deadline candidate criteria:

| Method | Full-points RMSE ↓ | Full-points MAE ↓ |
|---|---:|---:|
| fpl-predict v1 | 2.9765 | 2.1354 |
| Dastan | **2.8910** | **2.0204** |

Dastan had about 2.9% lower RMSE on those matched records. Training policies and feature sets differ, and this is an archived retrospective comparison, not a prospective competition. Do not compare this table directly with the core-points table above: the periods and targets differ. [Comparison methods, provenance and aggregate results](docs/open_source_comparison_2026-10-14.md).

For shared-row comparisons against other systems, see the [external benchmark
protocol](docs/BENCHMARK_PROTOCOL.md), [source readiness inventory](docs/benchmark_sources.json)
and [local import workflow](docs/benchmark_workflow.md). The optional
`fpl-predict benchmark` command validates local exports and produces aggregate
coverage/error/ranking reports and [bounded evaluation diagnostics](docs/benchmark_evaluation.md).
An explicit [resource-controlled runner](docs/experiment_runner.md) is available
for separately authorised experiments. These tools do not promote models.

## Install

The commands below require Git, Python 3.12 and a POSIX shell:

```sh
git clone https://github.com/kokjz/fpl-predict.git
cd fpl-predict
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
```

The default tests use synthetic fixtures and run offline. Four integration checks require separately prepared data/artifacts and are skipped on a fresh checkout. Python and numerical dependencies are pinned in [pyproject.toml](pyproject.toml).

Initialise a workspace for downloaded data, model artifacts and generated reports:

```sh
export FPL_PREDICT_HOME="$PWD/var"
.venv/bin/fpl-predict init
.venv/bin/fpl-predict --help
```

`FPL_PREDICT_HOME` defaults to `var/` under the current working directory. Keep the variable set when running commands from another directory. `var/` is excluded from Git; another directory can be used instead. Public FPL data retrieval does not require FPL login credentials or a paid API key.

## Model setup

### Reproduce training and evaluation

```sh
.venv/bin/fpl-predict download-history
.venv/bin/fpl-predict build-features
.venv/bin/fpl-predict train --reproduce
```

These commands download the historical dataset, build lagged feature caches, and run the documented training/evaluation protocol. Outputs go under `$FPL_PREDICT_HOME/artifacts/`; repeats with an existing evaluated artifact use a separate reproduction directory. Training is an explicit operation, not part of a normal data refresh.

**Training does not install or approve its output for forecasting.** A newly trained file is not guaranteed to match the published artifact hash. Model promotion requires evidence against the [promotion gates](src/model_registry.py), an immutable version/artifact record and a corresponding runtime registry update. There is currently no one-command promotion workflow or bundled model download.

### Install a matching approved artifact

If you have obtained a trusted artifact matching the approved registry entry:

```sh
.venv/bin/fpl-predict install-model /path/to/trusted-model.joblib
```

Installation verifies the expected SHA256 before copying the file. Forecasting verifies the registered artifact again before loading it. The default model version and expected hash are documented in [validation](docs/validation.md). Do not load arbitrary downloaded Joblib/Pickle model files: their deserialisation can execute code.

## Forecast for a squad

Once an approved artifact is installed, refresh the public data:

```sh
.venv/bin/fpl-predict refresh
```

Create your squad JSON at `$FPL_PREDICT_HOME/squad.json` with these fields:

| Field | Required content |
|---|---|
| `players` | Exactly 15 objects, each with the current FPL `id` and `selling_price_tenths` |
| `bank_tenths` | Available bank balance in tenths of a million; `10` means £1.0m |
| `free_transfers` | Number of available free transfers |

Use current player IDs from the bootstrap snapshot and your actual selling prices, which may differ from market prices. The squad must have two goalkeepers, five defenders, five midfielders and three forwards, with at most three players per club. Store account-specific inputs outside tracked source.

```sh
.venv/bin/fpl-predict forecast --team-state "$FPL_PREDICT_HOME/squad.json"
```

Each run writes a new directory under `$FPL_PREDICT_HOME/forecasts/` containing:

- `fixture_predictions.json` and `player_gameweek_predictions.json`: points, minutes, probabilities and baseline estimates.
- `planning.json`: lineup and transfer/chip comparisons for the supplied squad.
- `REPORT.md`: a readable forecast summary.
- `manifest.json`: input/model provenance, timestamps and assumptions.

`forecasts/LATEST` identifies the latest base forecast. Optional sourced scenarios use `--availability-review /path/to/review.json`; scenario runs preserve the base pointer. See the [review schema](docs/availability_workflow.md) and `forecast --help` for details.

**Season support:** live forecasting currently checks the 2026/27 data schema. Another season requires a rules/schema review before use. Forecasts beyond the next gameweek are planning approximations, not equally validated multiweek predictions.

## Evaluate a saved forecast

Keep the forecast created before the relevant deadline. After all results are officially finished and checked, refresh the outcomes and score that saved directory:

```sh
.venv/bin/fpl-predict refresh
.venv/bin/fpl-predict score --forecast /path/to/saved/forecast --gw 7
```

Replace the example directory and gameweek with the saved run being evaluated. Scoring rejects late-generated forecasts and unfinished/unchecked outcomes, and refuses to overwrite an existing outcome report for the same snapshot. Reports include points errors, minutes errors, appearance diagnostics and official-projection coverage. Missing official projections remain missing; paired methods use identical rows.

Additional research commands expose their options through:

```sh
.venv/bin/fpl-predict decision-trial --help
.venv/bin/fpl-predict search-lightweight --help
.venv/bin/python tools/compare_dastan.py --help
```

Research and model-selection data must remain separate from later evaluation data. Previously inspected test seasons are not untouched holdouts for new adaptive experiments.

## Limitations

- Historical archives contain corrected outcomes, not complete pre-deadline news, schedule and selling-price snapshots.
- Current rules, fitness, expected roles and fixture changes require review; the model does not independently verify news sources.
- Minute scaling and double-gameweek appearance independence are approximations. Empirical point intervals do not capture every source of uncertainty.
- Lower prediction error does not guarantee more FPL points. Transfer/chip comparisons are conditional, and the engine does not execute decisions.

## Documentation and contributing

- [Validation](docs/validation.md), [data sources](docs/data.md) and [availability reviews](docs/availability_workflow.md)
- [Open-source comparisons](docs/open_source_comparison_2026-10-14.md) and [bounded experiment protocol](docs/I3_PROTOCOL.md)
- [Contributing](CONTRIBUTING.md) and [security](SECURITY.md)

Source is in `src/`, offline tests in `tests/`, and repository utilities in `tools/`. Contributions should include relevant validation and preserve chronological evaluation, artifact integrity and the distinction between code changes and model approval.

## License

[MIT](LICENSE) for the code. External datasets and Premier League trademarks retain their own terms. This project is unaffiliated with the Premier League.
