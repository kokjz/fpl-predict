# Development-only native history study

`fpl-predict native-development` runs the fixed [I4 protocol](NATIVE_DEVELOPMENT_PROTOCOL.md).
It compares 146 FPL-window or 256 richer-window inputs and one participation
composition with a refitted incumbent control, on two early development seasons.
No historical later audit, operational model, current squad or registry is used.

Provide explicit private CSV paths: canonical players/teams as documented for
[native-reference](native_reference.md), plus a control CSV and provenance JSON.
The control must contain stable `season,gameweek,fixture,fpl_code` keys (input
`GW` is accepted), `element,pos,team_id,value,ts,cutoff,total_points,points_core,minutes`,
every `fpl_model.CORE_FEATURES` column, and `source_max_ts`. `value` is used only
through a strictly earlier match for retrospective squad affordability proxies,
never as a predictor. Team IDs and seasonal elements serve only joins/replay.
Provenance must record actual source/cache hashes and audit limitations; the
command hashes its bytes, which does not independently certify those assertions.

```sh
fpl-predict native-development prepare \
  --players private/players.csv --teams private/teams.csv \
  --control private/control.csv --provenance private/provenance.json \
  --output private/i4-manifest.json

fpl-predict native-development run --manifest private/i4-manifest.json \
  --manifest-sha256 RECORDED_SHA256 --directory private/new-job
```

Preparation verifies coverage/context/source cutoffs without fitting or scoring;
it freezes policy, code, environment, input hashes and all 40 squad panels. Source
records later than 2023/24 are removed before rebuilding histories. Later control
rows are rejected. Required mapped development appearance gaps fail readiness.
No missing-snapshot or realised-outcome exclusion defines the prediction pool.

Run the worker using the [resource/storage supervisor](experiment_runner.md)
with all manifest/input hashes, expected `predictions.csv`/`results.json`, and
the declared limits. The command itself is not an operating-system resource
quota. Outputs are write-once. Partial/failed runs cannot be scored as complete.
Reports include all rejected challengers; no trained binary is saved. A development
finalist is only a nomination for further checks, never a model promotion.
