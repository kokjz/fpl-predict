# News/availability experiment — 16 October 2026 Singapore

**Published availability information improved a fixed appearance-model prototype. It does not yet justify changing the production model.** Independent club-news evidence can now be recorded for review, without automatically changing a forecast.

The [pre-fit protocol and reproduction workflow](news_availability_probe.md) were published in source commit `aeb928e` before scores. The experiment reuses inspected historical outcomes; it is not an untouched test, a Dastan reproduction, or evidence that news caused the original matched Dastan gap. [Full aggregate results, reliability bins, source admission and hashes](NEWS_AVAILABILITY_RESULTS_2026-10-16.json) are retained alongside this report.

## What was tested

A fixed logistic appearance control uses prior minutes/appearance, history depth, time since the last fixture and position. Three arms add structured chance/missingness, training-only news TF-IDF, or both. All four share identical rows, regularisation, chronological folds and target: any minutes in the GW. No tuning or model/arm selection follows the results. No production probabilities, unconditional point forecasts or registry weights are overwritten; no fitted binary is saved.

Training:2025/26 GW4–19,12,027rows/3,460candidates. Validation reporting only:GW20–27,6,427rows/1,743candidates. Descriptive test:GW28–38,8,690rows/**2,312predeadline candidates**. The source experiment is conditional on common roster/fixture-history coverage, with409unmatched fixture-history rows excluded uniformly; it does not invent zeros or claim a complete financial selection universe.

| Fixed arm | Validation candidate Brier ↓ | Test candidate Brier ↓ | Test all-player Brier ↓ | Candidate high-probability misses / rows at p>=0.8 |
| --- | ---: | ---: | ---: | ---: |
| Prior-form control | 0.10044 | 0.10654 | 0.09170 | 190 / 1,975 |
| + structured availability | 0.07272 | **0.08448** | **0.07725** | 171 / 2,067 |
| + news text | 0.07233 | 0.08454 | 0.07917 | **157 / 2,017** |
| + both, declared primary arm | **0.07211** | 0.08463 | 0.07735 | 165 / 2,067 |

The combined arm reduces pooled candidate Brier by **20.6%** versus this form control; structured-only reduces it by20.7%. The declared primary mean-per-GW candidate Brier difference (combined minus control) is **-0.02162**, with descriptive four-GW block interval **[-0.02814,-0.01635]**. This is a single predeclared component contrast on reused outcomes, without correcting a broad family of future model searches. Reliability and sample counts remain necessary: Brier reflects discrimination and uncertainty as well as calibration.

News text adds **no incremental Brier improvement over structured chance labels** in this test: combined0.08463 versus structured-only0.08448. Do not hide that negative incremental finding or select text settings using this window. Absolute miss counts use different numbers classified as high probability; these are descriptive diagnostics, not an equal-coverage classifier contest or a transfer rule.

## What “external news” means here

The historical archive is maintained by AIrsenal, but the underlying news/chance fields are **official FPL-syndicated observations**, not independently collected club articles. Exact Git byte-prefix/identity/deadline checks now cover all35required GWs4–38. Git timestamps remain publisher evidence; historical publication/correction completeness is not independently certified. Data/vocabulary/player rows remain outside this repository.

The inspected Dastan release uses FPL predeadline availability signals and performance data; it does not establish a dedicated independent club-news/injury-history system. Its published availability-only ablation is small relative to the overall architecture difference and belongs to its own evaluation protocol. The positive source-value result here makes timely availability a plausible mechanism worth investigating, not proof of the reason original Dastan outperformed v1 on RMSE. In particular, this source series begins in2025and cannot explain the retained2024/25comparison causally.

The new evidence preflight accepts structured, timestamped **club/league/press** observations researched by the operator, even where official FPL status remains `a`. It records reported out/doubtful/available/unknown and source/publication/check times. These remain evidence requiring interpretation; they never become numerical start probabilities or silently clear flags. See the [schema](news_availability_probe.md#independent-news-evidence-without-automatic-model-changes). Historical independent club coverage and injury timelines remain untested research inputs, not secretly substituted FPL fields.

## Practical decision

Use the existing approved model, current direct news and sourced minutes/availability sensitivity workflow for the next authorised planning cycle. Run the new evidence preflight on that cycle's actual frozen forecast and fresh snapshot; include owned non-candidates explicitly. The read-only history audit later attributes point errors and checks probability reliability. No weekly forecasts or manager-squad decisions were generated by this experiment.

The control here is a deliberately small prior-form component, **not** a matched refit of the production participation head. Before using these learned probabilities in production, compare against that stronger head with the same data cutoffs and features; isolate input effects, keep calibration chronological, specify conditional/full-points integration and test legal selection/point relevance. Unconditional point forecasts must not simply be multiplied by p_play again. No champion promotion, future points gain or original-Dastan superiority follows from the Brier result.

## Cost and integrity

All35prefix admissions/input preparation took **11.58seconds**, peak sampled RSS **1.665GiB**. The four fixed fits, reporting and a separate retained all-player completed-GW diagnostic took **2.47seconds**, peak **0.349GiB**, two threads. Time includes orchestration and diagnostics, not just fitting. No GPU/cloud/PC/paid feed was needed. Resource and disk limits were monitored continuously during these jobs, with no breaches. No raw archive, fitted binary, private manager data or individual predictions are committed.

Sources checked15OctoberUTC/16OctoberSingapore: [pinned AIrsenal exporter](https://github.com/alan-turing-institute/AIrsenal/blob/212a0aa478fe885808355dc5f08f81f8f9822893/src/airsenal/export/attributes.py), [pinned Dastan README and ablations](https://github.com/qazybekb/smartplayfpl-dastan/blob/758db9247e8b3a9a870c991064f74d8339d61cd0/README.md), and [calibration guidance](https://scikit-learn.org/stable/modules/calibration.html). Existing provenance limits and promotion gates remain in effect.
