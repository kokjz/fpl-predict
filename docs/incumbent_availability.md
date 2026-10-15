# Incumbent availability ablation

Optional research tests published structured availability against the **full
incumbent participation method**, rather than a small form-only control. It never
loads the saved champion, replaces the registry or makes live forecasts.

The fixed [protocol](../src/fpl_predict_resources/incumbent_availability_protocol.json)
uses two otherwise identical HGB7 regressors, original 49 performance features,
identical recency weights, and five earlier seasons plus 2025/26 GW1–19.
The augmented arm adds chance label and explicit missingness: zero differs from
unknown. Official percentages are learned covariates, never assigned probabilities.
No text or return-gameweek fields, tuning, or validation refit are used.

## Source and temporal boundary

Supply trusted locally generated caches, stable ID bridge, historical availability
CSV archive and reviewed exact-prefix proof. The command rechecks all 35 GW4–38
prefixes and bootstrap hashes, identities, positions, recorded deadlines and
publication before both source and cache cutoffs. All original fixture rows remain;
unmatched sources and older seasons stay unknown. Input, protocol, code and actual
environment hashes, split audits and coverage enter a frozen manifest. Git times
remain publisher evidence, not independent time certification.

```sh
fpl-predict incumbent-availability prepare \
  --history /path/to/trusted/history.pkl --features /path/to/trusted/features.pkl \
  --players /path/to/players_raw.csv --archive /path/to/attributes.csv.gz \
  --proof /path/to/reviewed-prefix-proof.json --output /path/to/new-manifest.json \
  --trust-local-cache
fpl-predict incumbent-availability run \
  --manifest /path/to/new-manifest.json --sha256 MANIFEST_SHA256 \
  --output /path/to/new-results --trust-local-cache
```

Pickles can execute code: hashes cannot make untrusted caches safe. Use the resource
supervisor for bounded runs. No automatic downloads, runtime initialisation or
fitted-binary saves occur.

## Scores and stopping

Validation GW20–27 and reused audit GW28–38 share fitted heads. Primary: candidate
**fixture-level** mean per-GW Brier difference, augmented minus control, with a
four-GW descriptive block interval. No independence assumption combines DGW fixture
probabilities. Report pooled all/candidate Brier, reliability, >=0.8 misses and
per-GW exactly matched-coverage misses. Minutes models stay unchanged. Brier
improvement alone does not establish improved calibration.

Both windows must improve candidate pooled Brier at least 0.5%, avoid worse
all-player Brier, and have interval upper bound below zero to proceed. This is an
experiment progression gate, **not** model promotion. Failure stops this fixed
hypothesis without more settings on the same outcomes. Success permits a separately
frozen unconditional points-feature augmentation and decision evaluation. Never
multiply unconditional point forecasts by appearance probability again.

This refits the incumbent method, not the saved champion already trained on
2025/26. Outcomes are inspected/reused, upstream statistics mutable and cache
schedule cutoffs reconstructed. One season of news cannot satisfy existing
multi-season promotion gates. Future frozen shadow validation is maintenance,
not a calendar blocker for this implementation.

Grounding checked 16 October 2026: [probability calibration](https://scikit-learn.org/stable/modules/calibration.html)
distinguishes reliability from discrimination and requires disjoint calibration
data; [temporal cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split)
supports chronological boundaries. No random calibration CV is used.
