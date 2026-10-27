# FPL improvement-chat handover

This is the entry point for a fresh Codex or Claude chat taking over prediction-
engine research on Windows. Read it before running models or modifying source.
Weekly squad planning remains a separate responsibility. Claude Desktop/Code
with Sonnet5.5 on Pro is the primary intended receiving setup. Start with the
[short bootstrap prompt](docs/handover/QUICK_START_PROMPT.md); the full prompt and
all evidence remain available without loading them all at once.

## Start here

1. Read the [staged bootstrap](docs/handover/BOOTSTRAP.md) and
   [Claude Pro workflow](docs/handover/CLAUDE_PRO_WORKFLOW.md), then
   [project context](docs/handover/PROJECT_CONTEXT.md),
   [operating rules](docs/handover/OPERATING_RULES.md) and the machine-readable
   [checkpoint](docs/handover/CHECKPOINT.json). The checkpoint distinguishes
   reviewed `main`, unmerged research and unchanged approved weights.
2. Read [Windows setup and restoration](docs/handover/WINDOWS_SETUP.md).
   Obtain the separately supplied **private** transfer archive and its trusted
   SHA256 from the user. It contains the exact model, original research evidence
   and private context; none of that archive belongs in this public repository.
3. Use the [fresh-chat prompt](docs/handover/NEXT_CHAT_PROMPT.md). Verify source,
   archive, model and runtime before resuming the exact listed unfinished work.
4. The weekly chat has a separate [update prompt](docs/handover/WEEKLY_CHAT_UPDATE.md)
   and [mandatory source-sync procedure](docs/handover/WEEKLY_SOURCE_SYNC.md).

Repository: https://github.com/kokjz/fpl-predict

The public repository supplies source, protocols, results and handover context.
The private archive supplies exact private artifacts and larger original
checkpoints. A clone alone does **not** contain the approved model binary.
Without the private transfer, public data and source can rebuild research
references, but a new fit must not impersonate the original approved artifact.

Do not treat research tags, benchmark winners, newer files or code merges as
model promotions. Do not upload private archives, personal context/team history,
credentials, model binaries or platform environments. The checkpoint and its
explicit remaining-work list take precedence over old progress statements.
