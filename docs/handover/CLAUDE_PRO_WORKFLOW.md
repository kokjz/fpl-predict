# Claude Desktop/Code on Pro: bounded-context workflow

Guidance checked **27October2026** against Anthropic's official documentation.
The Claude architect uses user-selected Opus5.5 / Medium, including initial
setup, with High as needed in that conversation; read ARCHITECT_MODEL_POLICY.md.
This supersedes earlier Sonnet-first advice. GPT-6.1 Sol handles programming
separately. Actual receiving settings still require verification.
See HYBRID_WORKFLOW.md; this guide applies to the Claude side, not Codex quotas.
Verify the actual model, effort, plan and local execution environment in the
receiving app. An announced feature is not proof it is enabled for that account.

## Platform facts and limits

Claude and Claude Code draw from shared Pro five-hour and weekly allowances.
Conversation length, work and model choice affect consumption; there is no
reliable fixed number of project prompts or tokens to promise. Compaction frees
context, not consumed plan allowance. Do not convert API prices or the session's
API-style cost estimate into a Pro token entitlement. Check live account usage
and reset information. [Official Pro/Code guidance](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan),
[usage versus length](https://support.claude.com/en/articles/11647753-how-do-usage-and-length-limits-work),
[cost/usage tools](https://code.claude.com/docs/en/costs).

Anthropic recommends starting Opus5.5 at Medium. The user selected Medium for
most architect work and High as needed for a named difficult design/interpretation
question within that conversation. Record why and the actual setting; return to
Medium for routine work. Do not assume a UI setting changed, choose Xhigh/Max,
create agents or change models automatically. Vendor benchmarks do not establish
this project's correctness. [Opus effort guidance](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5).

Desktop's Code tab can run inside WSL2: select an installed distribution and a
Linux project folder. Its toolchain/Git then run in Linux. WSL1 is unsupported.
Some Desktop features, including integrated terminal/connectors, have rollout
limitations; plugins are unavailable in WSL sessions in the checked guidance.
Verify the actual agent's command/file abilities, not just whether a terminal
pane is visible. If connectors are unavailable, use separately authorised Git/
GitHub CLI authentication inside WSL; a connector is not mandatory. Missing
execution/authentication may require user setup. Do not enable paid cloud work
or disable resource/permission guards as a workaround.
[Desktop WSL guidance](https://code.claude.com/docs/en/desktop-wsl).

The small root CLAUDE.md explicitly imports the repository's AGENTS.md. This
avoids relying on version-dependent AGENTS discovery or Windows symlinks. Check
loaded instruction files in the installed version; do not import the entire
private master/history via CLAUDE.md. Auto-memory and compacted summaries are
convenience context, not immutable evidence or approval records.
[Instruction loading](https://code.claude.com/docs/en/memory).

## This project's loading and output budgets

These are **project working targets**, not Anthropic limits or guaranteed safe
context sizes. Correctness takes precedence when more evidence is necessary.

- Start from BOOTSTRAP.md, CHECKPOINT.json, compact PROJECT_CONTEXT.md and
  OPERATING_RULES.md. Read the private resume note/current master summary next.
  Aim for a few thousand tokens of essential context, rather than the entire
  approximately550KB historical master or23,000-plus research files. Byte counts
  are inventory facts, not exact token estimates. Preserve everything on disk.
- Retrieve only relevant protocol sections, findings, code and tests for the
  current step. Use headings/ranges/search and machine-produced summaries of
  JSON arrays. Typical tool output target: about2,000tokens per call; save long
  logs to private files and print paths/counts/assertions plus failing excerpts.
  Never truncate away a failure or treat a partial read as a complete review.
- Keep one coherent step active: inspect R1's invariants, patch and test them;
  then R2/R3 as part of the same existing research PR. Do not launch broad repo
  exploration, speculative candidates, parallel sessions or subagents by default.
  Programmatic numeric/file-hash verification uses local CPU, without sending
  every row through the LLM. One agent does not imply skipping independent
  arithmetic verifiers, meaningful tests or PR review.
- Review scoped diffs and run affected tests first. Run the full required suite
  at the appropriate integration checkpoint; rerun when changes/failures justify
  it. Capture all results, inspect every failure and preserve original evidence.
  Do not repeatedly run a full study/suite only to obtain more reassuring output.
- Keep progress reports short. Update authoritative on-disk context/receipts and
  Git commits at coherent milestones, then cite the files. Do not restate the
  full history or paste giant GitHub diff responses on every turn.

This design follows Anthropic's emphasis on focused work and verifiable results,
but the concrete budgets and no-default-agent policy are project choices.
[Official best practices](https://code.claude.com/docs/en/best-practices).

## Compaction, limits and resume safety

Inspect actual context with /context or the available Desktop context indicator,
and plan usage with /usage or account usage UI. Commands/UI vary by installed
version. Before a large next step or when context becomes crowded, write the
private RESUME_CURRENT.md and use /compact with a focus on the active package,
source/model hashes, untouched inputs, pending findings and next commands.
Afterward re-read the small checkpoint/resume note and relevant protocol.
For a different task, save the same state before starting a fresh session or
/clear. Do not assume every historical file will survive compaction intact.
[Context lifecycle](https://code.claude.com/docs/en/context-window),
[Desktop context controls](https://code.claude.com/docs/en/desktop).

At an actual usage limit, preserve work and a resume note. Wait for reset or ask
the user about an alternative; never enable usage credits, API billing, another
plan or a model switch automatically. Long local commands must have the declared
watchdog/resource bounds and durable logs; record their actual handles. After
compaction/restart, check process state before any retry. A stopped chat or
expired observation handle does not by itself prove a job stopped.

Do not send the private archive, full personal context or credentials to public
services to save local context. Keep personal evidence outside source. Context
economy changes how evidence is retrieved, never the scientific/Git/privacy
requirements or approved model/defaults.
