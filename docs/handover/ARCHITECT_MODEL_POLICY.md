# Selected architect model and effort

**User decision, 27 October 2026:** use **Claude Opus5.5 / Medium** for most
architect tasks, **including initial setup/intake**. Use **High** as needed for
a specific harder question within the same architect conversation. This replaces
the earlier Sonnet-first architect recommendation. GPT-6.1 Sol remains the
programmer; the weekly planning chat's model and workflow are unchanged.

| Work | Effort |
|---|---|
| Initial handover, reviewing the existing brief, ordinary package planning and result interpretation | Medium |
| A difficult experiment design, leakage/validation problem, or unresolved conflict between component metrics and season-level decisions | High when needed; state the question and reason |
| After the difficult question is resolved | Return to Medium for routine work |

Verify the actual selected model/effort and tool access. Record an effort change
and its purpose in the private decision/resume notes; do not pretend a UI setting
changed if it was not verified. The user has authorised this Medium/High policy;
it adds no per-commit approval gate. No automatic extra chat, agent, API router,
paid overage, Xhigh/Max setting or switch to another model is authorised.

Opus is not required to perform the programmer's repeated execution loops. Keep
architecture exchanges at package boundaries, with staged source/evidence
retrieval and concise briefs/results. Check actual available Pro usage; context
compaction does not reset consumed allowance. If a limit is reached, preserve
the resume state rather than enabling paid continuation or substituting a model
without the user's direction.

The selection is a workflow choice, not a measured FPL accuracy/points gain or
proof that Opus outperforms Sonnet on this project. Research protocols, promotion
gates, source/weights, negative findings and one-writer ownership remain intact.
Initial intake does not authorise a new fit or rerunning completed studies.

## Grounding checked 27 October 2026

Anthropic positions Opus for complex sustained judgment and Sonnet for faster
scoped work. It recommends starting Opus5.5 at Medium and evaluating effort on
the actual workload. These vendor claims support the choice but are not an
independent FPL-project evaluation. Pro usage is shared across chat and Code;
API token prices are not a subscription entitlement.

- [Opus effort guidance](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)
- [Sonnet/Opus positioning](https://www.anthropic.com/claude-sonnet-5-5)
- [Claude Code with Pro](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan)
