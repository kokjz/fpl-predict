# Receiving research workspace layout

The supported sibling layout keeps the source checkout separate from the private
handover and restored runtime. The outer folder may be named
`fpl prediction model research`; quote paths containing spaces in commands.

## Required receiving location for both roles

The user-selected outer folder **must be named `fpl prediction model research`**.
Record its actual absolute path once in the canonical private resume note. Both
the Sonnet architect and Sol programmer must use that same physical project root.
Clone the remote repository **only into `<OUTER>/fpl-predict/`**, never a default
Documents, Downloads, application checkout or unrelated workspace directory.
Inspect an existing clone instead of creating another. Any genuinely needed
additional research worktree/source view must also stay under the outer root,
with its role and owner recorded; it must not become another untracked active
clone or change the canonical source/coordination locations.

Keep project-specific notes, coordination, restored evidence, models, logs,
environments, outputs, downloaded inputs and temporary files under this root
where possible. Use private sibling directories, not the public checkout, for
private material. Do not change tool permissions, resource guards or immutable
evidence merely to enforce placement.

Third-party application-managed locations may be outside the root when necessary,
for example WSL/Docker storage or application caches/configuration. Record those
exceptions, their purpose, actual paths/mounts and relationship to the canonical
workspace. For WSL, choose one authoritative outer project folder with the same
name in the selected filesystem and expose/access it from both applications;
do not maintain independent Windows and Linux copies. Platform-managed caches
and authentication stores do not belong in public Git. If an app silently
creates a checkout elsewhere, correct its destination before continuing; do not
accept that alternate clone as the active source.

```text
fpl prediction model research/          Local parent; do not initialise Git here
  CLAUDE.md                            Optional small local pointer file
  private-handover/                     Extracted outer delivery ZIP
    README_FIRST.md
    roles/
    coordination/                      ONE canonical active packet
    PRIVATE_TRANSFER/                  Original inner archive and companions
    source/                            Current guides and offline Git bundle
    tools/                             Current standalone restore/smoke tools
  fpl-predict/                          Public clone; only this folder is Git
  private-workspace/                    New destination for inner-core restore
    PORTABLE_PATHS.json                 Derived local source/runtime mappings
    TRANSFER_MANIFEST.json
    payload/
      model/                           Private registry and approved artifact
      work/                            Original research evidence
      planning/                        Private operational context
      ...
```

The restore destination must not exist beforehand. Preserve the archive's
original bytes; newer hashed addenda describe current state. Keep the delivery ZIP under the outer project root where possible, for example
in an archives/ sibling directory, and avoid redundant downloaded/extracted
copies. Account for archives/runtime growth in storage checks; do not move files
elsewhere merely to bypass a guard. Never put private files inside the public
checkout.
The user may skip manual verification of the outer delivery ZIP after their
private device-to-device transfer. The programmer performs routine automated
archive/member and approved-artifact checks during setup/restoration; preserve
the supplied checksums and provenance. This is not a request to bypass the
restore tool's verification or load an unchecked model.

## Sessions, instructions and ownership

Start the architect's local Claude Code session at the outer parent. Explicitly
read `private-handover/README_FIRST.md`, its `CLAUDE.md` and referenced `AGENTS.md`,
the architect role prompt, current context and this guide. When the repository
exists, also read `fpl-predict/CLAUDE.md` and its referenced `AGENTS.md` before
repository work. Do not assume sibling/child instructions have all loaded at
launch or that bare paths in older prompts are relative to the outer parent.

An optional short outer `CLAUDE.md` can use the
[local pointer template](templates/WORKSPACE_CLAUDE_TEMPLATE.md). Do not copy a
child instruction file to the parent without correcting its relative references,
or automatically import the complete private history. The architect reads and
interprets evidence and writes only its owned private notes; the programmer is
the sole implementation writer.

The programmer may start in `fpl-predict/`, with explicit access to the sibling
handover/runtime folders. Both roles use the **same**
`private-handover/coordination/`, recording its actual absolute location and
ownership in RESUME_CURRENT.md. Do not create another active packet in the
repository or restored snapshot. Paths such as `coordination/...` in generic
prompts mean that canonical directory, not a new folder under the current shell.

Use one physical workspace accessible to the relevant Windows/WSL sessions;
verify actual access instead of maintaining divergent copies. Selecting the
outer folder is a navigation choice, not a new cloud project or permission to
write source. Pure architect intake can precede repository/runtime setup.
Generate/use the path map in the runtime that executes it: Windows drive paths
and WSL mount paths are different spellings, not interchangeable native paths.
If changing runtime, retain the earlier map and record a new derived map with
that runtime's actual locations; keep both pointed at the same physical files.

## Restore with the actual source location

The current `portable_handover.py restore` accepts `--source-checkout`, pointing
to the real sibling clone or its future location. It records this in the new
private `PORTABLE_PATHS.json` without cloning or modifying the checkout.

From the outer parent, using a compatible installed Python (commands work in
PowerShell or a POSIX shell; substitute the actual inner archive/checksum):

```sh
python "private-handover/tools/portable_handover.py" verify --archive "PRIVATE_INNER.zip" --sha256 TRUSTED_INNER_SHA256
python "private-handover/tools/portable_handover.py" restore --archive "PRIVATE_INNER.zip" --sha256 TRUSTED_INNER_SHA256 --destination "private-workspace" --source-checkout "fpl-predict"
git clone https://github.com/kokjz/fpl-predict.git "fpl-predict"
```

If the sibling checkout already exists, inspect/verify it instead of cloning
over it. An offline alternative is the supplied source bundle; set its clone's
origin to the public repository URL before network sync and PR work. See
[WINDOWS_SETUP.md](WINDOWS_SETUP.md) for runtime qualification and source locks.

The original workspace root maps to `private-workspace/payload/`. Its exact
`fpl-predict` subtree maps to the selected sibling checkout; other private paths
stay beneath the restored payload. Prefix lookalikes are not treated as source.
For example, resolving `ORIGINAL_WORKSPACE/fpl-predict/tools/example.py` uses the
sibling clone, while `ORIGINAL_WORKSPACE/model/model_registry.json` uses the
private payload. Use `resolve --map ... --path ...` with the actual original
absolute path from the manifest, not a guessed old location.

Existing legacy maps without `source_checkout` retain the nested source default.
Restore without `--source-checkout` also keeps the old
`DESTINATION/payload/fpl-predict` location; that is a supported alternative, not
the approved clone location for this receiving workspace. Do not use that
fallback here: pass `<OUTER>/fpl-predict/` explicitly. If a map was already generated
for a different location, preserve it and create a separately named derived map
recording the corrected `source_checkout` and provenance. Use the current tool:
older copied resolvers ignored that field. Validate both source/private paths.

Set `FPL_PREDICT_HOME` to the absolute `private-workspace/payload/model` path in
the appropriate receiving shell/runtime. Keep runtime paths out of Git. This
variable chooses the engine home; it does not automatically relocate every
historical launcher. Use explicit roots/maps and separately recorded adapters
for legacy launchers and interpreters. Do not rewrite original evidence or
rerun finished scientific studies merely to obtain new file paths.

This layout changes neither the weekly planner's model nor its source-sync SOP.
It needs no new weekly-chat prompt. Code, weights and policy approvals remain
separate; verify receiving compatibility before research execution.
