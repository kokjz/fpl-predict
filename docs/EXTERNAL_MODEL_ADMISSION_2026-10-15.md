# External model admission and disposition — 15 October 2026

This bounded package applies one policy to seven inspected public project families:
first inspect/pin source and licence, then verify archived forecasts or released
weight training/selection cutoffs plus input compatibility, otherwise independently
refit a named method on chronological data when worthwhile. Published aggregate
errors are never pasted into a shared leaderboard. Missing original-system evidence
does not prevent explicitly labelled retrospective method comparisons.

| Family and source revision | Evidence/feasibility | Current disposition |
| --- | --- | --- |
| [Original OpenFPL](https://github.com/daniegr/OpenFPL/tree/ad055ba7270145ce8ecc1f19581423493b1357e7), MIT | Paper reports2020/21–2023/24development and2024/25GW32–38prospective test; published player schemas require contemporary availability. Retained older inputs lack it. Model/scaler training membership is not independently certified. | Original released-weight2024/25route explicitly not admitted in this package. Execute40member cv1 chronological refit on rebuilt common inputs, labelled reduced/modified whole method. No exhaustive search/full750MBbinary download. |
| [Dastan](https://github.com/qazybekb/smartplayfpl-dastan/tree/758db9247e8b3a9a870c991064f74d8339d61cd0), MIT | Existing matched2024/25archive and measured32-head chronological native-input adaptation; released2025opponent feature temporal counterexamples remain. | Reuse completed prediction bytes/metrics. No test-driven retraining or relabelling as original-system parity. |
| [AIrsenal](https://github.com/alan-turing-institute/AIrsenal/tree/212a0aa478fe885808355dc5f08f81f8f9822893), MIT | Closed-form minute-scaled Dirichlet update and recent-minutes model are cheap. Original team model imports bpl-next NumPyro Dixon–Coles; full operational source/database/scoring adapter is distinct work. | Execute explicitly AIrsenal-inspired conjugate/Poisson composition, with declared team/residual/time/history changes. Full original AIrsenal not scored; a weak reduced reference does not establish its performance or a Mac limitation. |
| [OpenFPL Scout AI](https://github.com/elcaiseri/OpenFPL-Scout-AI/tree/6f03815f392ce1714043a2e14b171fa264364d5c), MIT | Current weights/config include2026GW5; some archive paths freeze on first recall after deadline. Rich external features and Ridge/XGBoost/CatBoost/MLP ensemble require their own as-of adapter and earlier-only fit. | Do not backcast shipped weights or accept frozenflag alone. No new original forecast with verified matching cutoff admitted. Earlier I3 already tests cheap Ridge-style and conditional learners; no additional ensemble rewrite/search without a separately justified protocol. Not classified impossible on current hardware. |
| [fpl-forecast](https://github.com/daniel-mehta/fpl-forecast/tree/b59c56ef7f0f7ef768d29ea07da972b155100521), AGPL-3.0-only | Newly inspected public publication registry and immutable GW6 branch expose a562player export, source/run lineage and file hashes. Source snapshot dates differ materially from the saved comparison forecast. | Original published GW6CSVhash/stable IDs/positions/timing checked; execute one separate post-hoc archived comparison, with unequal information cutoffs and one-GW limitations. Do not copy its implementation into this MIT engine or redistribute raw exports. No model reimplementation or new heavy dependencies needed. |
| [Lionel](https://github.com/jotohow/lionel/tree/cc0b743fd70f16df414948fd88547a24de5ceb2b) | Hierarchical PyMC/NUTS fitting and optimisation; no compatible exact-row admitted archive in inspected files. A full data/rules/sampling adapter would be a new modelling package. | Scope closed for this first bounded comparison package: no measured advantage justifies adding a sampling-heavy rewrite now. Could be reconsidered as a distinct future hypothesis; no proof of hardware infeasibility and no external-compute task created. |
| [FPL decision engine](https://github.com/Linus-J/FPL-decision-engine) | Odds/Dixon–Coles and empirical shrinkage ideas; no code licence identified in prior source inspection and no matched forecast export admitted. | No code copied/executed. Defer original implementation reuse pending clear licence and historical inputs. Generic ideas alone are not an original-model accuracy comparison. |

Head metadata was refreshed15October for OpenFPL,AIrsenal,Scout,Lionel and
fpl-forecast; Dastan's previously pinned inspected revision is reused unchanged.
This is a bounded shortlist and source inspection, not exhaustive all-branch or
all-project certification. The relevant paper is https://arxiv.org/html/2508.09992v1 .
AIrsenal paths inspected include prediction/player_models/conjugate.py,
scaling.py,minutes_models/recent.py and team_models/dixon_coles.py.

## Source and safety boundaries

The OpenFPL public feature-definition pickle contains only dict/list/string
opcodes. It was inspected with pickletools and read through a data-only unpickler
that rejects all classes; no third-party fitted-model pickle or notebook code was
executed. Public search logs/model filenames yield the frozen40member recipe;
the implementation re-trains those settings. Small scalers were retained privately
for source audit but not deserialised. No provider model binaries are committed.

The fpl-forecast archive is pinned to
f76514676147dad7e6d7e247576c9d19ce90b330. Its public manifest checksums bind the
CSV, run manifest and freshness file. Git records22September11:07:20UTCbefore
10October10:00UTCdeadline; this is publisher/Git history evidence, not independent
cryptographic timestamp certification. Its run metadata declares training seasons
2022/23–2025/26and source availability before generation. Those declarations do
not independently audit every underlying training/source byte or model selection.
Results are explicitly conditional on these limits. The public CSV remains outside
this repository; only aggregate results/adapter code are published. No AGPL code
was copied or executed. No private team/manager information is used in the comparison.

Existing historical outcome windows remain inspected/reused. No method receives
untouched-test status by being imported into this tool. No current weights are
run backwards. All failures/gaps and incomplete fixed-squad coverage are retained.
Actual original-system parity is a narrower unanswered question; useful method
comparisons and this implementation package do not wait indefinitely for it.

See [measured results](HISTORICAL_EXTERNAL_RESULTS_2026-10-15.md). Future weekly
validation is separate maintenance; it is not a reason to keep this package open.
