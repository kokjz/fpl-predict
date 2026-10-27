# Market-implied team strength: admission checkpoint

This is a **data-admission checkpoint**, with no Stage-B or player-model fit,
score, Gate-B verdict or promotion. The
[frozen admission protocol](market_strength_protocol_2026-10-28.json) records
the fixed market specification and unresolved points. A complete executable
Stage-B declaration must resolve them before any evaluation. Existing approved
forecaster 1.0.0 and weekly defaults remain unchanged.

Only football-data.co.uk Premier League E0 CSVs for 2019/20–2023/24 were
downloaded. Raw bytes, retrieval receipts, exact fixture exceptions and derived
lambdas remain outside Git. No later audit season was downloaded or scored.

Original download pins (complete retrieval receipts remain outside Git):

| Season/source | SHA256 |
|---|---|
| [2019/20](https://www.football-data.co.uk/mmz4281/1920/E0.csv) | `100037618b94f94057400bb02bf6bac4ef74ddaa58cde4b38370839c39caee61` |
| [2020/21](https://www.football-data.co.uk/mmz4281/2021/E0.csv) | `5afe63f69401457b8354eaacee24f9a3e520b3c3af6329564a9783e20d789c62` |
| [2021/22](https://www.football-data.co.uk/mmz4281/2122/E0.csv) | `335afcbabeb2939fa10ab39ba3e8215072d0b577cb8d0705c1e44c56e934e703` |
| [2022/23](https://www.football-data.co.uk/mmz4281/2223/E0.csv) | `8442792d3b614c94ea3cf381bd2736805889cc1713169035368fff19c3d02380` |
| [2023/24](https://www.football-data.co.uk/mmz4281/2324/E0.csv) | `b2e057b0ed959f198b0f63d2391c01239f3608e6de5db68edab3f88e04d07ff3` |

| Season | Market rows | FPL date/team matches | Complete preferred closing odds | Mean squared probability residual | Maximum squared residual |
|---|---:|---:|---:|---:|---:|
| 2019/20 | 380 | 0; source unavailable | 380 | 0.000174406 | 0.001426378 |
| 2020/21 | 380 | 380 | 380 | 0.000169401 | 0.000632626 |
| 2021/22 | 380 | 380 | 380 | 0.000176901 | 0.000683084 |
| 2022/23 | 380 | 380 | 380 | 0.000141307 | 0.000408733 |
| 2023/24 | 380 | 380 | 380 | 0.000126467 | 0.000417321 |

All five files contain `AvgCH/AvgCD/AvgCA` and
`AvgC>2.5/AvgC<2.5`, with complete groups on every row. Each also contains
the declared non-closing fallback columns; no fallback or exclusion was needed.
Proportional overround removal and deterministic bounded independent-Poisson
inversion succeeded on 1,900 rows. Residuals measure agreement with market
probabilities, **not predictive performance**. No residual-based exclusions or
parameter tuning were made.

The explicit name map covers every observed club. Available FPL histories give
380/380 unique fixtures per season for 2020/21–2023/24, matched by date and both
teams with season-specific team/fixture IDs. Five matched fixtures have kickoff
clock differences between the CSV and canonical FPL records: one in 2020/21
(−15 minutes), one in 2021/22 (+30), two in 2022/23 (−15 each), and one in
2023/24 (−30). Exact records are retained for chronological admission review.

There is no already-held 2019/20 FPL fixture/team source in this transfer.
All 380 exact unmatched source rows are retained, rather than guessed IDs or a
silent removal of the required warm-up season. This requires an explicit
admission decision before that season can feed ratings.

## Material definition issue before Stage B

The hash-verified frozen I4 team file provides 760 team-match rows per season
for 2020/21–2023/24, with complete team xG/xGA. Arm U therefore cannot be dropped
as an unavailable source.

The brief specifies team/opponent **EW** xG "(I4 definition)". Actual I4
`NativeHistory.WindowIndex.means` and the frozen I4 manifest use equal-weight
arithmetic windows **1, 3, 5, 10, 38**: twenty team/opponent xG/xGA columns.
These are not EW(4,12) histories. I4 also indexes this history across seasons,
while `fpl_model.FeatureStore.team` uses season-specific EW goal histories.
The historical `native_history.py` and `native_development.py` blobs at I4's
release `f6ddbec` exactly match the frozen manifest's source hashes.
Choosing either interpretation would alter the comparator behind Gate B.
The engineer has not selected a substitute or started a fit. The architect
must specify the exact U operator/windows and any prior/reset semantics first.
I4 arithmetic windows also retain NaN when no prior observation exists. Its HGB
learner accepts that missingness, whereas the specified Stage-B Poisson GLM
does not. A finite cold-start policy and common cohort must be declared before
fitting; no implicit zero fill, invented prior or arm-specific row drop is used.

## Engineering and limits

Synthetic tests cover probability normalisation/fallback, lambda recovery
(including bounds), deterministic ridge/projection, unknown-team neutrality,
strict cutoff/target-match rejection and explicit name/fixture mapping. The
projection API accepts no target-match odds. An initial synthetic boundary test
needed tighter numerical stopping tolerance before any real-data inversion;
that failed test and the final fixed tolerance are retained.

Admission took 15.53 seconds. A Windows monitor observed only the venv launcher
RSS, so Python-worker/group peak memory is **unknown**; no four-GiB qualification
is claimed. A correctly qualified process guard is required before Stage B.
No supervised-POSIX compatibility claim follows from this Windows check.

This checkpoint makes no claim about team-goal deviance, clean-sheet Brier,
calibration slope, player error, season points or market superiority. Stage-B
fits: **0/6**. Stage-C fits: **0/4**. Gate B: **UNRUN**. The prior failed
appearance-calibration result, all approval gates and historical evidence remain
unchanged. No fit/search/extra arm or audit-season extension is authorised by
these admission findings.
