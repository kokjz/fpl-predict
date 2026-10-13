# fpl-predict

Local, leakage-aware Fantasy Premier League forecasting and evaluation. This repository contains the engine, synthetic tests, public model metadata and experiment protocols. It contains no manager squad, screenshots, credentials, downloaded datasets, forecasts or model binaries.

## Install

Python 3.12 is required. From a clean checkout:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
```

Use an editable checkout for development; standard wheels also bundle the registry and protocols. No credentials are needed to fetch public FPL data. GitHub credentials are supplied by your local Git client, never by project configuration.

## Runtime workspace

```sh
export FPL_PREDICT_HOME="$PWD/var"
.venv/bin/fpl-predict init
```

The default is `var/` in the current working directory. It is ignored by Git; an external private directory can also be selected. Imports never create directories. Keep real team files in this workspace or another private location, never in source/examples/tests. Do not run data refreshes or training in CI.

## Approved model

The engine registry identifies the approved v1.0.0 artifact by SHA256. Model binaries are intentionally excluded from Git. If you already hold the matching trusted artifact:

```sh
.venv/bin/fpl-predict install-model /path/to/trusted-model.joblib
```

Installation checks the expected hash before copying, without deserializing. Prediction subsequently uses trusted executable serialization; do not load arbitrary downloaded model files. The public metadata does not establish a season-points or captaincy advantage. See [validation](docs/validation.md).

## Data, training and evaluation

```sh
.venv/bin/fpl-predict download-history
.venv/bin/fpl-predict build-features
.venv/bin/fpl-predict train --reproduce
```

Historical downloads pin a source revision and check hashes. Training is an explicit local operation and writes experimental outputs; it does **not** promote a model to the approved registry. Existing evaluated artifacts are never silently overwritten. The experiment protocols are bundled in `src/fpl_predict_resources/`.

The optional planning and evaluation commands are:

```sh
.venv/bin/fpl-predict refresh
.venv/bin/fpl-predict forecast --team-state /path/to/private/team.json
.venv/bin/fpl-predict score --forecast /path/to/frozen/forecast --gw GAMEWEEK
.venv/bin/fpl-predict decision-trial --help
```

These commands are examples, not scheduled jobs or permission to change an FPL account. Forecasting currently checks the 2026/27 schema and refuses another season until reviewed. Predictions use completed matches, recent-season form and pooled historical patterns. Current injury/role information requires documented review; optional minute scaling is illustrative, not a calibrated conditional model. Longer horizons and one-transfer/chip comparisons are planning approximations.

Freeze forecasts before deadlines. Score only when official results are finished and checked, and retain model/last-five/recency comparisons on identical eligible players. Never retune on already-seen outcomes and describe them as untouched tests. [Development workflow](CONTRIBUTING.md), [security and privacy](SECURITY.md), [data provenance](docs/data.md).

## Lightweight research and external comparisons

The [open-source comparison](docs/open_source_comparison_2026-10-14.md) inspects six
systems, reports a matched retrospective Dastan benchmark, and preserves six
rejected lightweight adaptations. Approved v1.0.0 remains the default. Research
tooling is opt-in, uses two computation threads and checks a soft runtime/memory
budget; no automatic retraining or model promotion is performed.

```sh
.venv/bin/fpl-predict search-lightweight --output-dir "$FPL_PREDICT_HOME/experiments/I3_new"
.venv/bin/python tools/compare_dastan.py --help
```

The search requires this project's trusted historical caches and a fresh output
directory. The archived-export comparator optionally needs a Parquet reader;
routine forecasts do not. All data, fitted artifacts and individual predictions
stay in the ignored/external workspace. See the predeclared [I3 protocol](docs/I3_PROTOCOL.md).

## Repository layout

- `src/`: engine modules and CLI; public registry/protocol resources.
- `tests/`: offline synthetic leakage, formation, scoring, registry and runtime checks.
- `tools/check_repository.py`: Git-index privacy audit.
- `docs/`: methodology, validation limits and third-party data provenance.
- `.github/`: pinned, read-only test workflow and dependency-update configuration.
- `var/`: ignored private runtime, never tracked.

The flat engine module names preserve compatibility with the existing approved artifact. Feature definitions and learned model weights are unchanged by packaging. The MIT license covers this repository's code, not third-party datasets or Premier League trademarks; this project is unaffiliated with the Premier League.
