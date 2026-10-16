# Season-management foundation readiness

16 October2026. The rules/state/replay foundation is implemented. An adaptive
multiweek planner, fullhistorical season-points benchmark and competitor season
comparisons remain subsequent stages; this report does not claim those outcomes.

[Aggregate audit](SEASON_READINESS_2026-10-16.json) ·
[Interfaces and rules](season_management.md)

## Verified mechanics

A known-answer synthetic38GWseason scores932points:38×24regularpoints, two
BenchBoost increments of8 and twoTripleCaptain increments of2. All eight chips
are used legally; Wildcard/FreeHit do not create points by themselves in this
constant-return example. This tests mechanics rather than model accuracy.

Other tests cover initialbudget, half-profit selling and loss quotes, retained
purchase prices/cash afterFreeHit, permanentWildcard changes, FTbanking/topup,
hits, chipwindows/expiry/consecutiveFreeHit restrictions, legalautosubs, captain
fallback/negativecaptains/card-onlyevents, double/blank totals, held-player source
gaps, club-transfer exceptions and input/outcome separation. Supplied-action CLI
requires38GWs, sourcechecksums and newoutputpaths. No automatic model promotion,
currentforecast or account action occurs.

## Historical source admission

All38cached2025/26bootstrap sources verify against pinned hashes and predeadline
capture claims. Active15player/chip/transfer settings match the executed profile.
Thirteen early snapshots contain a provisional16player secondFreeHit override;
it is removed fromGW14, before that chip becomes usable atGW20. The audit flags
this unsupported future configuration rather than silently assuming it was a
verified15player forward-planning input. Current2026/27APIprofilematches.

The old calendar evidence started inFebruary2026. This package finds11unique
pinned fixtureCSVversions published before the38market origins, beginning with
1August2025revision46277afda009b340e738336dabc4b0822dd80c57. Together with previously
reviewed dated fixture announcements, **all38GWfixturememberships match** the
actualseason. Sourcechecksums, timestamps, outcome-field screens and path limits
are checked before admitting calendars. Futurematch-result contamination fails.

Only fixtureID,event,homeclub,awayclub,kickoff fields can become schedule inputs;
result fields are read separately only for contamination screening. Commit dates
and cached sourcecaptures remain publisherprovenanceclaims, not independently
witnessedfirstpublication. These are inspected retrospective sources.

Structured availability has35published prefixes,GW4–38. GW1–3remain unknown and
must not be labelled healthy or unavailable. No full origin×targetGWforecastgrid
exists yet; the train-throughGW19reference cannot be backcast intoGW1–19. Earlier
external archives likewise do not establish38GWmanagement performance.

## Next stage and cost

Next build origin-safe horizon forecasts and the rolling planner, using this
state engine and the admitted per-origin calendar versions. Preserve unknown
availability and unsupported futurechipsettings. Then integrate chipstrategy,
run fullseason baselines and compare eligible external forecast/planning systems.
The overall season-management goal remains active.

No training or historical management score was run here. Downloads reused cached
metadata and losslessly compressed calendar versions, with projectgrowth/free
space checks aftereachfetch. A conservative initial500kBfilelimit stopped one
fetch; the bounded4MiBlimit accommodates nested fixturestatistics, which never
enter decision views. No GPU/remotecompute/paidservice or rawdata redistribution.
Allsourcebytes, unique failures and provenance remain outsideGit.
