# Isolating appearance probabilities and bench-aware selection

Research-only historical package; the approved model and production selector
remain unchanged. The [fixed protocol](../src/fpl_predict_resources/conditional_selection_protocol.json)
separates the source of appearance estimates from how decisions exploit them.

One shared HGB7 core-return model learns only from earlier appearing players.
A shared conditional DC model and conditional minutes diagnostic use the same
chronological boundary. No availability labels enter these return models. Each
arm then uses its frozen appearance probability times the same conditional return;
this is a genuine conditional fit, not scaling already unconditional core points.
A shared pooled, recency-weighted training-only prior estimates zero-minute
card-only probability and its conditional return. Nonappearance without a card
has zero points; unexplained zero-minute returns fail closed. Negative returns
remain in targets, including card-only penalties. No fitted artifact is
saved or promoted. All transforms/weights fit earlier training rows only.

Training: five earlier seasons plus 2025/26 GW1–19. Development: GW20–27.
Reused descriptive audit: GW28–38. Old/new appearance heads and their admitted
source proof are reused from the prior fixed study; no retraining/tuning of them.
Four fixed arms cross old/new probabilities with current mean-XI versus expected
legal autosub/vice-aware selection. An unchanged incumbent-method anchor measures
whether the new conditional architecture itself helps or hurts. No best-arm pick.

The expected selector enumerates all legal XIs, outfield bench orders and keeper
choices for an owned 15. Captain/vice are optimised analytically. Independent
three-state events (minutes played, card-only, complete absence) yield exact
missing-count distributions by position;
legal bench replacements are averaged over those counts and bench appearances.
It maximises expected team points under this explicit distribution, not realised
future appearances. Every conditional return can include a cameo; minutes or a card
block an autosub, while captain fallback depends on minutes. Realised scoring remains the established rule-aware scorer.

The primary player-GW probability uses independent fixture appearances, while
points/minutes means sum fixture expectations. Persistent fixture availability
uses p_any=max(p_fixture) as a separate predeclared sensitivity; means stay fixed,
and conditional-on-any return is derived from the declared fixture joint model.
This is not dividing a legacy unconditional forecast to pretend it was fitted
conditionally. The joint fixture model also preserves card-only probability and return moments,
separating any minutes from card-only eligibility. Player-to-player independence
is not learned. A fixed .25 mixture
with a shared-uniform appearance shock stress-tests primary chosen plans while
preserving marginals; it is deliberately not an estimated football correlation.
Do not select a coupling or stress weight based on results.

Primary practical comparison: new probabilities + expected selector versus old
probabilities + mean selector, averaging twelve identical neutral squads within
GW before block intervals. Also report the factorial contrasts and incumbent
anchor. Existing source/roster/price/schedule limitations and previously inspected
outcome bias apply. Prototype progression requires development RMSE improvement
at least 0.5%, MAE within 0.5%, no lower NDCG, nonnegative owned points versus both
anchor and old-mean. Only new-expected is a prespecified possible finalist.
Existing full promotion gates remain separate and unchanged. Always publish all
completed-window results, even when progression fails.

Run `fpl-predict conditional-integration --help` for trusted cache/manifest and
frozen-head CSV inputs with SHA256 checks. Python caches are executable; never
load untrusted pickle data. Use the resource supervisor with two threads, 4GiB,
15-minute job budgets and storage monitoring. Before broader studies, use a
bounded mechanical selector pilot with no outcome scoring. No GPU or download
is implied. Future frozen weekly review is ongoing maintenance, not a package
completion prerequisite.

Rules checked 16 October 2026: [official team management](https://www.premierleague.com/en/news/2174899/fpl-basics-managing-your-team).
Temporal methodology: [scikit-learn cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split).


Development opening squads are frozen from GW20 metadata; audit squads separately
from GW28. No later roster is used to select development squads. Owned evaluation
requires every held player forecast and never zero-fills an unknown nonblank.
Audit verified blanks reuse the earlier admitted calendar/roster proof. Development
fixture forecasts inherit the historical cache's reconstructed schedule limitation.

The mechanical pilot evaluates selectors on one opening squad per window without
scoring outcomes. The fixed full study evaluates all twelve squads and all GWs,
plus persistent-fixture reoptimisation for squads0/4/8 (one per original stratum).
Positive-dependence stress evaluates the already chosen primary plans only; it
is not a reoptimisation or measured correlation model. Exactness of primary
selection does not imply the assumed independence distribution is accurate.


A first fit attempt stopped during admission, before fitting or scoring, because
one development row has zero minutes and a yellow-card penalty. The original
zero-return assumption was too narrow. This case was preserved; the fixed
training-only pooled card prior and three-state selector were added before the
replacement run. No row was dropped or outcome corrected. Captain fallback and
autosub eligibility are tested separately for this case. This is a data/rule
correction, not tuning against forecast scores; the failed attempt remains stored.


The initial owned replay's reference check found one rotation opening panel
differed from the previously frozen audit benchmark. The cause was reconstructing
neutral prior minutes from this season only instead of reusing the admitted
last-four history across seasons. Audit metadata and anchor values now come
exactly from the retained market; development panels keep their original inputs.
CSV numeric reads use round-trip precision. All arms are rerun on the restored
predeclared panels without changing fitted forecasts, probabilities, seeds or
selection rules. The superseded replay is retained, not selected by performance.
