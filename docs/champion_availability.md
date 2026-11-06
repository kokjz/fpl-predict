# Conditional champion availability

No action now; inert until a conditional champion is registered by a separately approved promotion.
Approved 1.0.0 keeps its existing forecast and sensitivity behaviour.

`champion_availability` admits the official bootstrap at the prediction origin and reuses
the unchanged `conditional_forecaster.current_availability` encoding. The next game's
`chance_of_playing_next_round` is a learned covariate. Later gameweeks receive
`availability_chance = 0` and `availability_missing = 1`. A label of zero does not force
the fitted model's output to zero.

For a conditional champion, next-GW manual `availability` factors and `minutes` overrides
are refused. The same protection applies to next-GW news sensitivity scenarios made
from a conditional Horizon. Later-GW illustrative sensitivities remain available.

Manual next-GW news must replace the input label, with `chance` in `{0,25,50,75,100}`
or `out: 0`. Use the existing availability review envelope:

```json
{
  "schema_version": 1,
  "GW": 20,
  "recorded_at_utc": "2026-01-01T10:00:00Z",
  "players": [{
    "id": 1,
    "chance": 25,
    "reason": "Synthetic example of a sourced replacement",
    "source_url": "https://example.org/news",
    "published_at_utc": "2026-01-01T09:00:00Z",
    "checked_at_utc": "2026-01-01T09:30:00Z"
  }]
}
```

Every source must be public, and publication/check/recording must precede the deadline
in the existing validator's order. Recording must also precede forecast generation.
Provenance retains the original official label, replacement label, source, timestamps
and affected fixture count. Unknown or duplicate identities, position conflicts,
post-deadline snapshots and inconsistent origin clocks are refused.

`forecast.run` uses its existing `--availability-review` option. The horizon and approved
projection APIs accept `bootstrap`, `bootstrap_as_of` and `label_review`; their bootstrap
clock must match the market origin. Their existing `review` argument retains the previous
sensitivity schema, which is refused for a conditional next GW. Do not supply both review
types. Approved artifact hashes, status, version and existence-observation admission still
apply before any approved projection. No historical observation can be invented for a new fit.

Rolling, adaptive and season planning consume the resulting admitted Horizon. CLI dispatch
and saved-forecast decision trials retain their existing admission checks. A conditional
Horizon carries the P6 marker in its source provenance through serialisation and planning.

This package verifies synthetic plumbing and non-conditional byte parity only. No real
conditional artifact was loaded through the adapter. The historical dry run is infeasible
without new source adapters; its fit and dry-run budgets were withdrawn. Actual-artifact
loading remains a required pre-season smoke check in a separately authorised promotion,
under the [frozen promotion policy](conditional_promotion_policy_2026-11-06.md).
