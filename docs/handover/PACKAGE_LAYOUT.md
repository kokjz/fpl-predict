# Private takeover package: workflow entry points

The separately transferred ZIP is private. This public file describes its layout;
it does not include the archive, approved weights or personal context.

```text
README_FIRST.md                    Extract/verify sequence and precedence
START_PROMPT.md                    Select role and enter the shared workflow
roles/
  architect/START_PROMPT.md         Sonnet5.5; user-selected Opus5.5 when useful
  programmer/START_PROMPT.md        GPT-6.1 Sol implementation and execution
  model_improvement/UPDATE_PROMPT.md  Update an existing improvement chat
  weekly_planner/UPDATE_PROMPT.md   Update the separate weekly-planning chat
coordination/
  ACTIVE_PACKAGE.json              One package/revision/hash/source/owner state
  PACKAGE_BRIEF.md                 Existing authorised PR42 completion scope
  RESULTS_PACKET.md                Historical evidence vs unrun receiving work
  DECISION_LOG.md                  Dated shared scientific/engineering decisions
  RESUME_CURRENT.md                Compact restart state and next commands
  USAGE_GUIDE.md                   Practical usage/rework/handoff measurement
PRIVATE_TRANSFER/                 Immutable core ZIP and final companion files
LATEST_WORKSPACE_UPDATES/          Hashed newer context; preserve original bytes
source/                           Public handover docs and offline Git bundle
tools/                            Core verification/restoration and model smoke
PACKAGE_MANIFEST.json              Outer members, sizes and hashes
LATEST_UPDATES_MANIFEST.json       Earlier/new mutable context hashes
```

Both roles use the **same** coordination directory, not separate copied active
briefs. Set its actual receiving location in the private resume note. The outer
package's coordination files are the canonical initial packet; when moving it
to a new working location, record the one current location and retire the old
location as a snapshot. The programmer claims implementation ownership before
writing source; the architect reads/updates its owned planning/review notes at
logical boundaries. No automatic messaging or model switching is configured.

The initial brief carries already-authorised PR42 R1/R2/R3 repairs and final
research release. Its results packet labels all completed historical paths and
the negative qualification separately from receiving runtime/tests not yet run.
It does not claim a Claude architect reviewed the new packet. Routine repairs
do not await a new architecture approval. See HYBRID_WORKFLOW.md for the cycle.

The inner core ZIP has its own trusted checksum/schema and immutable snapshots.
Do not pass the outer ZIP to tools/portable_handover.py; follow README_FIRST.md.
Newer context/addenda/coordination and the current source bundle supersede old
workflow assumptions without relabelling old scientific files or artifacts.

The programmer verifies source/private artifact/runtime and runs bounded checks;
the architect can read compact versioned evidence without execution access. After
normal review/check/merge/synchronisation, the weekly chat consumes reviewed main
and the approved private registry. New documentation or another LLM's opinion
does not approve a new forecast model or authorise squad/account operations.
