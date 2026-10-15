# Availability evidence and prospective diagnostics

Research found that participation/role information and honest matched evaluation
are useful next steps. They do not require more expensive fitting. These changes
preserve approved v1's weights and feature definitions; they do not establish an
accuracy or season-points improvement.

Each normal refresh now writes `availability_observations.json` beside the raw
bootstrap snapshot, with its retrieval timestamp, source URL/hash, official
status/news/chance label and next-GW projection. Unknown manual minutes stay blank.
Official 75% labels are observations, not calibrated model start probabilities.
No next event at season end means no next-GW baseline, rather than a refresh error.
All observations live in the ignored/external runtime; no snapshot is overwritten.

A separately researched review may be supplied to the forecast command using
`--availability-review /path/to/private/review.json`. Its explicit format is:

```json
{
  "schema_version": 1,
  "GW": 7,
  "recorded_at_utc": "2026-10-15T12:00:00Z",
  "players": [
    {
      "id": 123,
      "minutes": 65,
      "reason": "Illustrative scenario, not a real player assessment",
      "source_url": "https://example.org/club-news",
      "published_at_utc": "2026-10-15T10:00:00Z",
      "checked_at_utc": "2026-10-15T11:00:00Z"
    }
  ]
}
```

IDs and dates above are synthetic. Supply actual known publication/check times,
a cited HTTP(S) source and a reason; do not invent missing timestamps. Review
recording must precede generation and the GW deadline. Unknown/duplicate IDs,
nonfinite assumptions, post-deadline/future evidence and conflicting legacy
overrides are rejected. A valid review applies only to the upcoming GW; later
GW projections retain their previous assumptions. Publication/check times are
user-supplied evidence, not independently verified by the engine. URLs are stored
without fetching them and must contain no embedded login credentials.

An optional `availability` factor from 0–1 and `minutes` from 0–90 use the existing
illustrative sensitivity scaling. They are not a newly calibrated conditional
model. Keep actual news separate from judgment about playing time. Legacy
`--overrides` scenarios still work; sourced reviews do not silently replace the
base `LATEST` forecast. The manifest records the complete review and latest input
timestamp while preserving the API snapshot timestamp separately.

Future frozen forecasts include FPL's unadjusted `ep_next` only for its labelled
next GW. It is not extrapolated, multiplied per fixture in doubles, changed by our
manual overrides or imputed to zero when absent. Finalised scoring compares all
methods on identical available baseline rows and reports coverage. Existing
forecasts without this field remain scoreable, with zero official-baseline coverage.

Finalised scoring also measures player-GW minute MAE/RMSE and appearance Brier
score/reliability bins. Minutes and points sum double fixtures; the appearance
event is any minutes, not whether two short appearances sum to 60. Double-GW
appearance probabilities still assume independent fixture appearances, an existing
approximation. Empty cohorts report zero rows and null errors. No probability
recalibration is performed from these outcomes. Frozen input/generation timing,
finished/data-checked safeguards and write-once outcome reports remain enforced.

Normal forecasting uses the canonical standalone checkout with an explicitly
selected private `FPL_PREDICT_HOME`. This feature does not run a refresh, forecast,
new training cycle or background monitor on installation. Use it during the next
authorised weekly review, after gathering current direct club news.

Primary grounding:
- https://github.com/alan-turing-institute/AIrsenal (recent minutes and availability handling)
- https://github.com/qazybekb/smartplayfpl-dastan/blob/main/docs/METHODOLOGY.md (deadline anchoring and evaluation boundaries)
- https://github.com/qazybekb/smartplayfpl-dastan/blob/main/docs/BASELINES.md (paired FPL projection and participation diagnostics)
- https://fantasy.premierleague.com/api/bootstrap-static/ (official observations and projection source)


The optional [participation audit](participation_audit.md) adds actual-point error attribution and fixed predeadline evidence checks without changing forecasts. Its external-evidence schema records direct club/league/press observations separately from numerical assumptions. The [news/availability probe](NEWS_AVAILABILITY_RESULTS_2026-10-16.md) measures source value against a fixed recent-form appearance control; it does not promote a model or validate a points multiplier.
