# Historical external-method comparison: frozen protocol, 15 October 2026

Declared before fitting the new reference predictions. Historical outcomes are
already inspected/reused; this is retrospective method research, not an untouched
holdout, original-system ranking, current-season forecast, or promotion trial.

## Admission and bounded scope

Assess pinned public source, licence, training AND model-selection cutoff, model
input semantics, scoring rules, historical feature availability and update cadence.
A release timestamp alone does not establish training lineage. Source claims are
recorded as claims; mutable provider corrections do not become contemporary records.
No automatic download or deserialisation of external model binaries is implemented.
Use either admissible released-weight inference, verified archived predictions, or
an explicitly named independently fitted adaptation. Never backdate current weights.
Unsupported original-system routes close with reasons instead of blocking work.

OpenFPL ad055ba7270145ce8ecc1f19581423493b1357e7 supplies a notebook,
feature schema, model filenames and search logs. Original 2024/25 inference is
not admitted here: the retained older inputs lack its required contemporary
availability field; scaler/model training-selection membership is not independently
certified by the paper. The release contains250models/750,955,806bytes across
five folds and five roles. No full binary collection is required or downloaded.
The assistant-manager role is outside the shared player universe.

The independent OpenFPL adaptation uses all ten final published cv1 members per
player position (40serial XGBoost fits), chosen before new scores. Preserve their
published tree/depth/rate/subsampling/regularisation settings, seed42, 30-round
validation early stopping, training-only MinMax input/target scaling, positional
quantile-balanced weights (2/3/4/3bins, 95thpercentile cap, meanone), and median
aggregation. Use published GK196/outfield206 feature names on our prior rebuilt
histories. Missing numbers becomezero only inside the model; historical availability
is explicitly -1unknown, otherwise0–1. Four older seasons have no snapshots.
Class edges/weights and cap/normalisation come from training only; validation
weights apply that mapping. This differs from unknown upstream weighting details.
The published club-based CV/search is replaced by the declared chronological
train/validation split. Five-fold ensemble/search and trained binary reuse are
not claimed. XGBoost3.2.0 is the already isolated optional runtime, not the original
3.0.2 environment. Full2025/26points include DC, unlike original training rules.

The distinct AIrsenal-inspired reference uses the pinned closed-form player
Dirichlet minute-scaled goal/assist/neither update with prior35goals and epsilon.2
per year (explicit time-unit adaptation). Recent three listed match minute
observations, includingzeros, form an equally weighted distribution. Only explicit
zero predeadline chance overrides minutes. Unknown chance is not healthy certainty.
A regularised Poisson attack/defence/home model replaces bpl-next/NumPyro Dixon–Coles;
fitalpha1, 365.25day half-life, 500iterations/tolerance1e-7, goal means clipped.05–6.
Pooled training involvement and position residual/save priors are frozen; individual
counts update analytically from only observations before each deadline minus3h.
All special points (bonus/DC/cards/penalties/etc.) are an empirical per90residual
shrunk by900prior minutes; no contemporary DC is invented in older seasons.
Clean-sheet/conceded/save components use analytic Poisson expectations averaged
across the minute distribution. No-history minutes priors45/42/38/35byposition
are fixed in advance. This is not the complete AIrsenal forecast or a causal
ablation of the Dirichlet component. Other source families receive documented
admission/disposition; not every model family requires a new rewrite or fit.

## Shared data, timing and evaluation

Reuse exactly the hashed canonical native-gapmask-v1 raw inputs and frozen
incumbent/native-HGB/conditional-reference outputs. No released rolling columns.
Train2020/21–2024/25plus2025/26GW1–19; validationGW20–27 for OpenFPL early
stopping only; evaluateGW28–38. Do not refit on validation. Team and pooled priors
fit training only; player posterior/history windows may read completed observations
available before each target deadline. This online analytic update is part of the
component method; no held-out scores select parameters. Native histories use
strict deadline-minus3h queries; selected snapshot captures must precede deadlines.
Retain two declared mapped training-source gaps,25unmappedplayed rows and all
older missing snapshots. These provider/publication limitations remain; the
strict original-system benchmark admission flag staysfalse.

All five methods share9,043fixture rows/8,713player-GWs. Primary candidates are
snapshot-known,>=3prior season records,last5minutes>=45 (2,312player-GWs under
prior audited inputs). Exact keys/outcomes/cohort/finite coverage must reconcile
before results; no outcome-based row removal. Sum doubles before player-GW errors.
Report RMSE primary, MAE/bias, within-GW Spearman/NDCG10, all-player secondary,
and descriptive paired4GWblock intervals. Reused windows remain reused.

Freeze20legal squads from GW28candidate metadata/prices before fitting, seed
20261015, uniform position sampling,2GK/5DEF/5MID/3FWD,clubcap3,budget1000tenths.
Hold each squad across11evaluationGWs, compare XI/captain/vice/autosubs using
identical squads and realised outcomes. Report missing-coverage panels explicitly;
no selection of favourable squads/weeks. Correlated retrospective fixed squads
are not a transfer/chip simulator, season-points proof or a promotion gate.

Freeze a write-once manifest with input/source/recipe/environment hashes and
squads. TwoCPUthreads,4GiB sampled process-group RSS,30minutes total job,
project<=2GiB,growth<=512MiB,free>=5GiB. Check storage throughout. First completed
head establishes measured cost; no extra members/seeds/searches or budget changes
after results. Keep failed/incomplete runs unranked. No binary save or champion
registry change. Compare actual resource cost, not assumed PC/GPU requirements.

Sources: https://arxiv.org/html/2508.09992v1 ,
https://github.com/daniegr/OpenFPL/tree/ad055ba7270145ce8ecc1f19581423493b1357e7 ,
https://github.com/alan-turing-institute/AIrsenal/tree/212a0aa478fe885808355dc5f08f81f8f9822893 .
MIT attribution is in THIRD_PARTY_NOTICES.md; raw data/binaries stay outside Git.

## Engineering amendment v2: goalkeeper scoring, before corrected fit

Final review found the component decomposition used6points for goalkeeper goals
in every season. Official rules changed to10from2024/25:
https://www.premierleague.com/en/news/4059044 . Correct historical residuals by
season (6through2023/24,10since2024/25) and use10for the2025/26forecast component.
This is a scoring defect repair, not a parameter/feature search after test results.
The original completed run and outputs stay immutable; its component scores are
superseded for this defect regardless of whether the repair improves metrics.

Retain the original OpenFPL predictions exactly, bound to the original frozen
manifest, completed supervisor record/output checksum and identical seven base
input entries/recipe/policy (only the declared component scoring amendment may
differ). A new write-once v2manifest precedes the one corrected component fit.
No40member refit, new seed, changed prior, calibration or selection is allowed.
The CLI accepts frozen-openfpl/parent-manifest/parent-run together for this explicit
reuse; parent hash/coverage/target/cohort checks fail closed. Re-score all methods
and the same deterministic squads. Record both jobs' resources and preserve the
first run as invalid component evidence, not as a selectable alternative.
