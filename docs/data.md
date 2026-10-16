# Data provenance and boundaries

Public live data: the official `https://fantasy.premierleague.com/api/` endpoints for bootstrap metadata, fixtures and player histories. Snapshot requests are not atomic, can be cached and may change during post-match corrections. Persist timestamps and SHA256 hashes in the private runtime. Final evaluation requires official `finished` and `data_checked` flags.

Historical source: [Vaastav FPL archive](https://github.com/vaastav/Fantasy-Premier-League). Downloads pin a Git revision and preserve file hashes. Final corrected archives do not reproduce every historical pre-deadline injury, fixture and selling-price observation. The downloader uses a public GitHub endpoint with its applicable rate limits, no token in source. Observe upstream licensing/terms; this repository grants no rights to redistribute external data.

Manager data: pass a private file explicitly when planning is requested. Keep it outside tracked source. Public team pages do not expose pending transfers or exact selling prices. Never fabricate unknown manager facts.

Historical split protocols and public registry are in `src/fpl_predict_resources/`; data itself is excluded. Previously inspected evaluation seasons are no longer pristine tests for subsequent adaptive changes.


## Historical structured availability

The [incumbent availability study](INCUMBENT_AVAILABILITY_RESULTS_2026-10-16.md)
uses official FPL observations syndicated in AIrsenal's 2025/26 attributes archive.
All 35 GW4–38 exact Git prefixes, bootstrap hashes, stable identities, positions
and publication-before-cutoff boundaries are rechecked. Missing labels stay
explicitly unknown; earlier seasons are never filled from later news. This is
not a historical independent club-news or injury-history corpus. No raw text or
underlying archive is redistributed. Git dates are publisher evidence with the
limitations stated in the report. Historical fixture statistics may be corrected
after the match; cached schedule cutoffs are reconstructed, not independently
certified historical information sets.

A price capture can precede an admitted news observation. The external replay
retains the original quote timestamp, advances the comparison source cutoff and
requires both to precede the deadline. It preserves all error rows, while every
selection method shares the original listed roster and verified blank handling.


The [conditional integration follow-up](CONDITIONAL_SELECTION_RESULTS_2026-10-16.md)
retains the rare zero-minute card penalty instead of assuming every nonappearance
scores zero. Both arms use the same pooled, training-only card-event prior. The
selector separates minutes-based captain fallback from minutes-or-cards autosub
eligibility. Audit neutral metadata and anchor values are copied from the
previously admitted market, with round-trip numeric reads; development opens
its own squads from earlier metadata. No later roster is used in development.
