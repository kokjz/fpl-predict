# Windows setup and private checkpoint restoration

The transferred archive preserves exact evidence bytes and approved weights;
it does not contain credentials, a source `.git`directory, or reusable Mac
virtual environments/native libraries. Recreate environments on the receiving
machine. A private archive must never be uploaded to this public repository.

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
`Get-FileHash -Algorithm SHA256` can independently check the file first. Then use
these source-checkout commands with the actual archive/destination:

```sh
python tools/portable_handover.py verify --archive PRIVATE.zip --sha256 TRUSTED_SHA256
python tools/portable_handover.py restore --archive PRIVATE.zip --sha256 TRUSTED_SHA256 --destination NEW_PRIVATE_WORKSPACE
```

The tool refuses mismatched bytes, unsafe/colliding paths, symlinks and existing
output destinations. It verifies every member and leaves original payload bytes
unchanged. Inspect `TRANSFER_MANIFEST.json` and the generated `PORTABLE_PATHS.json`.
This verification does not itself execute/unpickle transferred models or scripts.

Clone the repository as `NEW_PRIVATE_WORKSPACE/payload/fpl-predict`. Keep that
source checkout on reviewed main for normal work; use a separate checkout or the
explicit pinned research branch for unfinishedPR42. Never change a checkout
owned by an active other task. The private registry belongs under the payload's
`model/`directory, selected through explicit `FPL_PREDICT_HOME`.

## Relocate paths honestly

Original manifests/logs may contain the old absolute workspace/interpreter paths.
They are immutable historical evidence. Resolve workspace paths with:

```sh
python tools/portable_handover.py resolve --map NEW_PRIVATE_WORKSPACE/PORTABLE_PATHS.json --path ORIGINAL_WORKSPACE_PATH
```

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
