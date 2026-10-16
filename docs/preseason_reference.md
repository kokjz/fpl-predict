# Preseason forecasting references

The experimental season planner needs meaningful forecasts before current-season
form exists. Its season-reset feature store otherwise gives very similar GW1
values to many players. `preseason_reference.apply` supplies two explicit research
references without changing the saved forecaster, its training features or the
normal weekly workflow.

The carryover reference links a deadline roster to the immediately preceding
season using stable player codes. Season-local player and club numbers are not
cross-season identities. It uses at most 24 recent, compatible-position fixture
records, with a four-match half-life and two pseudo-observations at the reset
forecast's per-fixture mean. Carryover fades linearly to zero after six completed
current-season records. A changed position or missing prior record retains the
reset forecast. Transfers, injuries and changed roles remain unresolved inputs;
this is a fixture-neutral point-rate reference, not a news-aware model.

For scoring, prior core points exclude defensive-contribution awards. Where those
awards are missing, a fixed 0.12 outfield award probability (zero for keepers)
is used explicitly. Other changes in scoring rules are not reconstructed. These
constants are a fixed experimental specification, not fitted or calibrated gains.

The second reference uses finite **pre-deadline official `ep_next`** values for
the origin gameweek only. This is already a player-gameweek total: do not multiply
it by double-gameweek fixtures or repeat it across the horizon. Verified
origin-calendar blanks remain zero. Later gameweeks use carryover/reset values.
Callers must verify that the bootstrap's next event is the origin gameweek.

```python
from preseason_reference import apply

# base: admitted Horizon; market: matching immutable Market; fixtures: pinned
# origin-known calendar. Never use an archive's post-match xP as official EP.
reference, audit = apply(
    base, market, fixtures, history, roster,
    source_as_of=market.as_of,
    source_hashes={"prior_history": history_sha256, "roster": bootstrap_sha256},
    official=True,
)
```

`history` requires `season`, `code`, `fixture`, `ts`, `position`, `points_core`
and `dc_hit`. `roster` requires `id`, `code`, `position` and optionally `ep_next`.
Prior archive rosters may supply an identity bridge only; do not import their
final prices, selection status or season aggregates. Only records earlier than
the origin minus a three-hour completion buffer are admitted. The caller remains
responsible for trustworthy publication timestamps and pinned input hashes;
accepting a timestamp string does not independently prove historical availability.

The returned horizon covers the same players/gameweeks as the base, preserves
training provenance and carries explicit reference identity. Per-player audit
records disclose linkage, position compatibility, fade weights and official
replacement coverage. No file, model, registry or account is changed by this API.

The [fixed evaluation protocol](../src/fpl_predict_resources/preseason_protocol.json)
compares the reset control, carryover and official-origin reference on six
historical opening gameweeks. Forecast errors and a one-deadline initial-squad
diagnostic do not establish season-management superiority or approve a model.
Full-season comparisons with Dastan/OpenFPL require their own admissible early
forecasts/refits; a model fitted through GW19 cannot be backcast into GW1.

Research grounding checked 16 October 2026: scikit-learn's
[chronological evaluation guidance](https://scikit-learn.org/stable/modules/cross_validation.html)
and the historical data publisher's [source documentation](https://github.com/vaastav/Fantasy-Premier-League).
Keep training and all transformations earlier than evaluation origins; do not
interpret reused historical results as untouched holdouts.
