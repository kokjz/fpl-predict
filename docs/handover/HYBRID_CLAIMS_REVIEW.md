# Assessing common claims about the hybrid workflow

Checked **27 October 2026**. This supplements HYBRID_WORKFLOW.md; it does not
authorise a new FPL experiment, feature, hyperparameter sweep or paid API system.

| Claim | Assessment for this project |
|---|---|
| Architect/programmer separation can help | Reasonable workflow hypothesis. It can separate scientific scrutiny from implementation loops, but coordination overhead and mistakes can erase the benefit. Measure actual work rather than promise an optimum. |
| Sonnet3.5 is the intended architect | Version mismatch. The intended choices are Sonnet5.5 or Opus5.5. Claims about a different model do not establish these models' relative strengths. |
| Claude is the superior ML/visual/planning manager | Not demonstrated for this project. Both families can reason over code, metrics and images. Role specialisation is useful without treating either as categorically better, immune to tunnel vision or an oracle. |
| Sol's high DeepSWE ranking proves the allocation | The benchmark is real, but the inspected official board does not establish a GPT-6.1 Sol ranking or this ML-role comparison. Version, harness, effort and task evidence are needed; general code benchmarks do not measure FPL research judgment or season points. |
| Sol's $0.10/M cached input makes repeated coding nearly free | A real eligible cache-read rate, not the price of every request. Cache writes, uncached/new input, generated output and applicable mode/length premiums remain chargeable. It is not a subscription token entitlement or a discount on local training CPU. |
| Cached inputs uniquely favour Sol over Sonnet5.5 | Incorrect at the checked standard API rates: both list $2/M input, $10/M output and $0.10/M cache reads. Actual token counts, cache eligibility, work/rework and product allowances still differ. |
| Passing code/plans between vendors reuses the cache | Not a shared cross-vendor cache. Prompt-prefix cache reuse depends on the provider/model/request boundaries and lifetime; forwarding a plan does not transfer cache state. |
| Handoff overhead and stale state are real concerns | Applicable. Use one private package brief/revision/hash, exact source/artifact/data hashes, a current owner, results packet and decision log. One code writer; review at logical boundaries rather than copy whole codebases each turn. |
| A structured orchestration framework is necessary | A small file-based contract is sufficient now. No automatic inter-chat communication, router, API integration, agents or paid orchestration is needed. |

The inspected primary DeepSWE source describes a long-horizon engineering
benchmark with113tasks and controlled agents/verifiers. The board rendered for
this review is dated22September2026 and contains older model configurations;
it is not a verified6.1Sol result. This is a limit of the retrieved evidence,
not evidence that Sol performs poorly. [Official benchmark](https://deepswe.datacurve.ai/),
[method and harness](https://github.com/datacurve-ai/deep-swe).

OpenAI's model page supports complex coding capability and publishes Sol's
standard prices, including cache writes and higher long-input/fast-mode rates.
Anthropic independently publishes matching standard Sonnet5.5 input/output and
cache-hit prices. These facts cannot establish relative subscription value or
which model completes a particular task with fewer tokens.
[Sol model/pricing](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
[Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing).

Prompt caching reuses available matching request prefixes under model-specific
eligibility, boundaries and lifetimes; it does not cache an edited filesystem
merely because the same filename is read again. New/changed prompt material and
outputs still have costs. Keep useful reference context stable and inspect real
usage when available, but do not feed unnecessary large files to manufacture
cache hits or assume a perpetual cache. Compaction may change reuse while still
reducing total context cost. [Official cache mechanics](https://developers.openai.com/api/docs/guides/prompt-caching).

For this FPL project, the architect's most useful review is about deadline-safe
data, chronological validation, point means versus appearance calibration,
decision-policy value, historical reuse and uncertainty. The latest Brier gain
coexisted with a full-season loss; a generic overfitting narrative or a favourable
plot does not overturn the measured qualification failure. Neither a switch to
feature engineering nor a hyperparameter search is automatically justified.

Target encoding is only an illustrative example in the outside assessment,
not an approved implementation task. Any future use must justify the feature,
respect existing identity exclusions and estimate encodings solely from allowed
past training data within chronological folds. No future validation/test target
or same-row outcome may leak into features. Do not introduce it in the current
PR42 repair/release scope.

Recommendation: try the optional split on the already-authorised package,
preserve single-chat fallback, and record actual time/rework/defects/handoff and
available usage. Keep Sonnet/Opus scientific review at package boundaries and Sol
implementation autonomous within the accepted scope. No model supremacy, cost
guarantee, endless search or automated pipeline is implied.
