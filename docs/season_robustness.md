# Historical robustness and decision diagnostics

This package examines persistent season-management policies, not independent
weekly resets. Its [fixed protocol](season_robustness_protocol_2026-10-24.json)
was declared before scoring the new common-opening cases. One reused outcome
season and several openings remain dependent evidence, not independent seasons.

The source-checkout tool `tools/diagnose_season_path.py` checks frozen action
hashes, source/model clocks, carried finances, actual settlement and totals before
attributing errors, hits, chip components, appearance groups and plan revisions.
It reports optimistic within-owned hindsight XI/captain headroom. These gaps use
outcomes and are **not attainable forecasts, causal losses, training targets or
policy recommendations**. They must never be passed to a decision-visible input.
Different policies own different players, so their owned-cohort RMSEs are not a
fair cross-model prediction ranking. Earlier common-cohort comparisons remain
separate.

Run tools from a source checkout with `PYTHONPATH=src`. All input/output paths in
these examples are placeholders for private, immutable evidence outside Git:

```sh
PYTHONPATH=src python tools/diagnose_season_path.py \
  --decisions /private/decisions.json.gz --decisions-sha256 ACTUAL_SHA256 \
  --outcomes /private/outcomes.json.gz --outcomes-sha256 ACTUAL_SHA256 \
  --season-dir /private/completed/season --horizon 6 \
  --output /private/new_diagnostics.json
```

`tools/run_season_robustness.py lock` accepts `--decisions`, `--outcomes`,
`--protocol` and a new `--output` outside this checkout. It records source/input,
runtime and protocol hashes and creates two source-only common opening squads.
The `arm` command takes those same files plus `--lock`, `--lock-sha256`, `--seed`,
`--policy` and a fresh `--output`. The Solio adaptation additionally requires
explicit `--native-python`, `--solio-source` and `--solio-site-packages` matching
the source-pinned [native admission](native_planner.md). Run one arm at a time
under the existing process-group/storage watchdog; the tool itself is not an OS
quota. Every completed native proposal is admitted canonically; raw attempts and
expected failures are retained. Do not reuse or overwrite a failed destination.
All frozen sources and inputs are checked again after each arm.

The new seeds and budget are fixed in the protocol. Both opening states are used
by H1, H6 and rule-adapted Solio with common forecasts and chip resources.
Retain all arms, negative results and timeouts. Do not promote a model from the
best starting state or relabel reused outcomes as an untouched audit.

An additional season must independently pass roster/quote, calendar-as-known,
prior-only history/forecast, hidden outcomes and rule/chip admission. In particular,
2024/25's Assistant Manager chip and single seasonal Free Hit/Bench Boost/Triple
Captain inventory differ from the existing two-set profile. Historical
post-match player rows do not establish pre-deadline registration, prices or
availability, and missing news is not proof of fitness. Pinned archive capture
claims remain distinct from independent publication certification.

No forecast weights or weekly defaults change through these read-only diagnostics
or research runners. Prospective private-team evidence stays outside this public
repository. Further changes require a separate predeclared, justified trial;
previous failed conditional/expected-selector variants are not silently repeated.

## Additional-season market receipts

`tools/audit_historical_markets.py` verifies38pinned market files against a
checksummed manifest: bounded lossless decode, compressed/content hashes, origin
before event deadline, unique listed player IDs, club and positive integer prices.
It also reports the observed chip/manager inventory. The output explicitly does
not admit a whole-season replay. It requires `--manifest`, `--manifest-sha256`,
`--source-root` and a new private `--output`. Missing fixture-as-known, forecast,
outcome or rule admission cannot be replaced by a successful market audit.

## Matched-state numerical diagnosis

The separate[source-checkout probe](../tools/probe_solver_comparison.py)and
[fixed protocol](solver_comparison_protocol_2026-10-24.json)compare standing and
admitted Solio cores at the same ten frozen H6states: both new seeds, each at
GW1/6/16/30/38. The diagnosis was declared after the six season scores were known;
it is not an untouched outcome test. Each solver gets two seconds, the same
restricted-pool procedure, forecasts and retained chip schedule. Only decision
files are read; there is no outcome/settlement argument. A separate integer-ledger
verifier checks complete plans and common mean objectives. Actual gains in
conditional objective are not realised season-point gains or permission to
switch policy automatically.

Run it after the historical batch is terminal under the existing two-thread,
120second/4GiB process-group and storage watchdog. Supply `--decisions`,
`--reference` (the six-arm root), `--lock`, `--lock-sha256`, `--protocol`,
`--protocol-sha256`, a new private `--output`, and the three explicit native
runtime/source arguments described above. It retains all twenty cases, ten frozen
inputs, raw native RPCs, conditional bounds and failed attempts. Injected test
callbacks are clearly labelled mechanical and are never numerical evidence.
