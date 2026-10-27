# Windows handover: user checklist

This checklist applies to the latest private package and the user's selected
Opus5.5 Medium architect / GPT-6.1 Sol programmer workflow. It is not a request
to start weekly squad planning or new model training.

1. **Create the outer folder.** Choose a private location on Windows and create
   `fpl prediction model research`. This is the one active project root. Do not
   initialise Git here. Keep the delivery ZIP under it where possible, for
   example in `archives/`.
2. **Transfer and extract.** Privately transfer the latest complete handover ZIP
   and extract its contents into `OUTER/private-handover/`. Check that
   `README_FIRST.md`, `roles/`, `coordination/`, `PRIVATE_TRANSFER/` and `tools/`
   sit directly inside that folder, not beneath an accidental second wrapper.
   Manual outer-ZIP SHA256 checking is optional for the user; the programmer
   retains automated archive/member and approved-model verification.
3. **Start the architect.** In Claude Desktop's Code tab, select a local session
   and the outer folder. Select Opus5.5 / Medium, including initial setup. Give
   the session read access to the handover and use
   `private-handover/roles/architect/START_PROMPT.md`. Read-only/Plan intake is
   appropriate initially. Permit scoped private-note writes when recording the
   brief, without making the architect a second engine-code writer.
4. **Confirm the intake packet.** The architect reads current instructions,
   checkpoint and brief, records the real outer/coordination paths and missing
   prerequisites, and prepares the existing PR42 handoff. The one active packet
   is `OUTER/private-handover/coordination/`. No new experiment or redesign is
   needed. Use High within that architect conversation for a specific harder
   question when needed, recording the actual setting/reason.
5. **Start the programmer.** Open the intended GPT-6.1 Sol coding session with
   access to the same outer root and packet; use
   `private-handover/roles/programmer/START_PROMPT.md`. It must clone the public
   repository only at `OUTER/fpl-predict/`, or inspect an existing clone there.
   Once created, that checkout is its coding working directory, with explicit
   access to the private sibling folders. Authenticate GitHub through the normal
   account flow; no credentials are included in the archive.
6. **Let the programmer restore and qualify.** It uses the current standalone
   tool on the inner archive, restores into the NEW `OUTER/private-workspace/`,
   and passes `--source-checkout` for `OUTER/fpl-predict/`. It verifies source and
   private path mappings, approved registry/model bytes, compatible runtimes,
   smoke checks and repository tests before claiming readiness. The inner tool
   does not take the outer delivery ZIP. Preserve original snapshots and record
   derived path/runtime adapters separately.
7. **Resolve actual machine prerequisites.** The programmer handles ordinary
   setup it can perform. WSL installation, administrator actions or interactive
   authentication may need the user. Keep one physical workspace, record any
   necessary WSL/Docker/app-managed paths/mounts and verify both apps' access.
   Do not create another clone at an application's default location, copy old
   platform environments, disable guards or silently enable paid compute/APIs.
8. **Resume the existing research package.** All44historical paths are complete.
   The programmer finishes PR42's existing R1/R2/R3 repairs, valid-state checks,
   tests and final negative-result release. The architect reviews evidence at a
   logical checkpoint. Follow the normal Git/review/check/merge/cleanup SOP;
   do not rerun completed paths merely for migration or promote failed research.
9. **Confirm operational handover.** Require a compact record of actual source,
   artifact/hash, runtime checks, paths, owner and next action. Preserve the
   original device's files until receiving checks pass. No receiving Windows
   qualification or transfer is claimed by the package's origin-machine proof.
10. **Continue the separate weekly workflow.** No additional weekly-chat prompt
    is needed for this workspace/model-assistance change. Its approved model,
    source-sync and planning SOP remain unchanged; source releases and private
    model/policy promotions remain separate.

For technical commands and placement details, see
[WORKSPACE_LAYOUT.md](WORKSPACE_LAYOUT.md), [WINDOWS_SETUP.md](WINDOWS_SETUP.md)
and [ARCHITECT_MODEL_POLICY.md](ARCHITECT_MODEL_POLICY.md). Both comprehensive
role prompts are included in the private package; read current addenda before
older snapshot instructions. Never upload the private archive to public Git.
