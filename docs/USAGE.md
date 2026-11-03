# Full setup and usage

## Install

The commands below require Git, Python 3.12 and a POSIX shell:

```sh
git clone https://github.com/kokjz/fpl-predict.git
cd fpl-predict
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
```

The default tests use synthetic fixtures and run offline. Integration checks that require separately prepared historical data or model artifacts are skipped on a fresh checkout. Python and numerical dependencies are pinned in [pyproject.toml](../pyproject.toml).

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

**Training does not install or approve its output for forecasting.** A newly trained file is not guaranteed to match the published artifact hash. Model promotion requires evidence against the [promotion gates](../src/model_registry.py), an immutable version/artifact record and a corresponding runtime registry update. There is currently no one-command promotion workflow or bundled model download.

### Install a matching approved artifact

If you have obtained a trusted artifact matching the approved registry entry:

```sh
.venv/bin/fpl-predict install-model /path/to/trusted-model.joblib
```

Installation verifies the expected SHA256 before copying the file. Forecasting verifies the registered artifact again before loading it. The default model version and expected hash are documented in [validation](validation.md). Do not load arbitrary downloaded Joblib/Pickle model files: their deserialisation can execute code.

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

`forecasts/LATEST` identifies the latest base forecast. Optional sourced scenarios use `--availability-review /path/to/review.json`; scenario runs preserve the base pointer. See the [review schema](availability_workflow.md) and `forecast --help` for details.

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
.venv/bin/fpl-predict selection-benchmark --help
.venv/bin/fpl-predict participation-audit --help
.venv/bin/fpl-predict news-probe --help
.venv/bin/fpl-predict incumbent-availability --help
.venv/bin/fpl-predict availability-points --help
.venv/bin/fpl-predict availability-benchmark --help
.venv/bin/fpl-predict conditional-integration --help
.venv/bin/fpl-predict integration-study --help
.venv/bin/python tools/compare_dastan.py --help
```

Research and model-selection data must remain separate from later evaluation data. Previously inspected test seasons are not untouched holdouts for new adaptive experiments.


Back to the [project overview](../README.md).
