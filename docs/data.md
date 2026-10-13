# Data provenance and boundaries

Public live data: the official `https://fantasy.premierleague.com/api/` endpoints for bootstrap metadata, fixtures and player histories. Snapshot requests are not atomic, can be cached and may change during post-match corrections. Persist timestamps and SHA256 hashes in the private runtime. Final evaluation requires official `finished` and `data_checked` flags.

Historical source: [Vaastav FPL archive](https://github.com/vaastav/Fantasy-Premier-League). Downloads pin a Git revision and preserve file hashes. Final corrected archives do not reproduce every historical pre-deadline injury, fixture and selling-price observation. The downloader uses a public GitHub endpoint with its applicable rate limits, no token in source. Observe upstream licensing/terms; this repository grants no rights to redistribute external data.

Manager data: pass a private file explicitly when planning is requested. Keep it outside tracked source. Public team pages do not expose pending transfers or exact selling prices. Never fabricate unknown manager facts.

Historical split protocols and public registry are in `src/fpl_predict_resources/`; data itself is excluded. Previously inspected evaluation seasons are no longer pristine tests for subsequent adaptive changes.
