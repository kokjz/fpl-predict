# Windows setup and private checkpoint restoration

The transferred archive preserves exact evidence bytes and approved weights;
it does not contain credentials, a source `.git`directory, or reusable Mac
virtual environments/native libraries. Recreate environments on the receiving
machine. A private archive must never be uploaded to this public repository.

The receiving chat needs access to the private workspace, a terminal/Python/Git,
and authorised GitHub writes for implementation/PR work. A tool-less chat can
read context but cannot execute the handover; identify missing access explicitly
rather than claiming runs or uploads. This requirement is vendor-independent.

Read [WORKSPACE_LAYOUT.md](WORKSPACE_LAYOUT.md) for the supported parent folder
with sibling private-handover/, fpl-predict/ and private-workspace/. Its placement
and source mapping supersede older nested-clone-only examples.

For this receiving workflow the outer folder is named
`fpl prediction model research`, and the remote must be cloned only into its
`fpl-predict/` child. Keep related files under the parent where possible; record
necessary third-party storage/mount exceptions. Both roles follow this rule.
The old nested clone remains a tool compatibility default, not this workspace's
chosen destination.

## Runtime choice

Use Python3.12 for the engine. Match the measured private runtime versions in
`MIGRATION_RUNTIME.json`/the transfer manifest before loading trusted model
pickles. The old private `requirements.txt` can be older than the later measured
runtime; the measured transfer receipt and artifact smoke test resolve that.

At transfer preparation, the original artifact/replay environment uses NumPy2.3.5
and pandas2.2.3, while the published package metadata pins NumPy2.5.3 and
pandas3.0.6. Other measured pins are in the private runtime receipt. Keep these
roles separate: reproduce original replay/artifact checks in a clean environment
from the measured pins with source selected through PYTHONPATH, and run the
released package/tests in its own environment. Do not silently upgrade the
legacy environment with an editable install or claim exact reproduction across
a dependency change. Validate the artifact smoke oracle in the intended runtime.

The engine's bounded experiment watchdog currently uses POSIX `ps`, process
sessions and group signals. Full supervised benchmark support on native Windows
is **not verified**. Prefer WSL2Linux for that workflow rather than silently
removing resource guards. Microsoft documents [WSL installation](https://learn.microsoft.com/en-us/windows/wsl/install)
and recommends keeping Linux-run projects in the [WSL filesystem](https://learn.microsoft.com/en-us/windows/wsl/filesystems)
for performance. Installing WSL may require administrator action/restart; ask the
user for that external setup if absent. Do not change system settings silently.
Native Windows can perform the standard-library archive verification/restoration;
that does not establish native-Windows benchmark/runtime qualification.

The optional adapted Solio worker has a **separate** Python3.14/HiGHS environment
and exact source recipe in `src/fpl_predict_resources/native_solver_recipe.json`.
Obtain the pinned external source or use the transferred verified source text;
reinstall platform-specific packages rather than copy Mac native libraries.
No GPU/CUDA/cloud installation is necessary for the current checkpoint.

## Restore without executing transferred code

Obtain the archive and SHA256 through the user's private transfer. On Windows,
manual `Get-FileHash -Algorithm SHA256` checking of the outer delivery is optional
for the user's private device-to-device transfer. The programmer performs
automated inner archive/member and approved-artifact checks using the supplied
checksums; those guards remain active. Then use
these source-checkout commands with the actual archive/destination:

```sh
python tools/portable_handover.py verify --archive PRIVATE.zip --sha256 TRUSTED_SHA256
python tools/portable_handover.py restore --archive "PRIVATE.zip" --sha256 TRUSTED_SHA256 --destination "NEW_PRIVATE_WORKSPACE" --source-checkout "ACTUAL_SOURCE_CHECKOUT"
```

The tool refuses mismatched bytes, unsafe/colliding paths, symlinks and existing
output destinations. It verifies every member and leaves original payload bytes
unchanged. Inspect `TRANSFER_MANIFEST.json` and the generated `PORTABLE_PATHS.json`.
This verification does not itself execute/unpickle transferred models or scripts.

For the sibling layout, clone the repository as `fpl-predict/` beside
`private-handover/` and `private-workspace/` under the chosen outer parent. Pass
that actual absolute or shell-relative source location to `--source-checkout`
when restoring; it can be the future clone location. Keep reviewed main for
normal work; use a separate checkout or the explicit pinned research branch for
unfinished PR42. Never change another task's checkout. The private registry lives
in `NEW_PRIVATE_WORKSPACE/payload/model/`, selected through explicit
`FPL_PREDICT_HOME`. Omitting `--source-checkout` retains the older nested default
`NEW_PRIVATE_WORKSPACE/payload/fpl-predict` for compatibility; do not create a
second clone merely to satisfy that default.

## Relocate paths honestly

Original manifests/logs may contain the old absolute workspace/interpreter paths.
They are immutable historical evidence. Resolve workspace paths with:

```sh
python tools/portable_handover.py resolve --map NEW_PRIVATE_WORKSPACE/PORTABLE_PATHS.json --path ORIGINAL_WORKSPACE_PATH
```

The current resolver honours `source_checkout` for the exact original
`fpl-predict` subtree, while other paths stay in the private payload. Older
standalone copies ignored this field: use the current tool and check source and
private mappings separately. Changing `FPL_PREDICT_HOME` alone is insufficient
for historical source/interpreter paths.

Do not rewrite frozen source/data/forecast files and retain their old hashes.
Create separately named derived manifests/wrappers when a filesystem/runtime
adaptation is necessary. Record old/new hashes and each path-only change;
recheck all original data/model/source hashes. External interpreter/site-package
paths need explicit new runtime locations. Legacy private launchers are evidence,
not turnkey Windows commands: their old Git/Python/native-runtime paths must be
adapted in copies, with scientific settings unchanged. Do not rerun completed
benchmarks merely to obtain new file paths.

## Validate before resuming

1. Verify the source revision/branch, full member manifest and approved-model
   hash. Read the private context master, current plans and unresolved findings.
2. Build a clean receiving-machine environment from the measured pins. Do not
   reuse `.venv`, executable/native modules or platform caches from the old machine.
3. Run the provided synthetic approved-artifact smoke oracle under the explicit
   trusted-model flag and compare the frozen tolerance. Then run repository tests
   and `tools/check_repository.py`. Document skipped optional integrations.
4. Follow CHECKPOINT.json's exact remaining-work list and original gates. All
   existing repeated results must remain attributed to their original source.
   Any newly run portability test gets its own provenance; do not relabel it as
   the historical source or treat compatibility as improved accuracy.
5. Before publishing, inspect staged contents and ensure that private payloads,
   path maps, archives, runtime receipts and personal context remain outside Git.

If the private artifact is unavailable, public data plus the ordinary documented
training commands can build a research reference. The resulting hash is a new
artifact; it is not automatically the approved1.0.0binary. No private key or
credential is required in the transfer, and authentication should be configured
separately without printing secrets.

Example after restoring and recreating the legacy environment (substitute actual
paths; do not change the trusted artifact hash):

```sh
PYTHONPATH=SOURCE_CHECKOUT/src LEGACY_PYTHON SOURCE_CHECKOUT/tools/handover_smoke.py \
  --model PRIVATE_PAYLOAD/model/artifacts/models/789e8849922116d989584ccfcb912082bb96201cb5af80ce9e70823e047fe233.joblib \
  --oracle PRIVATE_PAYLOAD/migration/PRIVATE_RUNTIME_SMOKE.json --trust-local-model
```

For the preserved research source, fetch tags and inspect the exact revision before
creating a separate working branch/checking out the existing PR branch:

```sh
git fetch origin --prune --tags
git show --no-patch research-handover-2026-10-27
git show --no-patch 9e26851a92371690848e3811c6e120026dd33011
```

The handover tag preserves the unmerged research head and the numerical source
in its ancestry. It is not a production release or approved model. The reviewed
handover source and tools are available on main; consult CHECKPOINT.json for the
exact open PR and next review step. Do not rerun the finished matrix merely
because it was produced in an unmerged research branch.


## Optional two-chat setup

Use HYBRID_WORKFLOW.md and the role-specific prompts. Claude may plan/interpret
without command access if the user supplies versioned evidence, while a local
GPT-6.1 Sol/Codex programmer performs execution. Prefer the same verified private
workspace/runtime accessible to the programmer; check each application's real
Windows/WSL file/command access before use. No model choice implies native-
Windows benchmark support or transfers credentials between apps. One research
worktree writer; no automatic cross-chat bridge or new API billing. Keep package
brief/results/ownership files outside Git. If separate filesystems are used,
transfer small hash-pinned packets through the user and revalidate them.
