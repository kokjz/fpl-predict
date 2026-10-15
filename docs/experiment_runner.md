# Bounded local experiments

`fpl-predict run-experiment` supervises one explicitly requested trusted command.
It never selects a trainer, starts on import, downloads data or promotes a model.
The initial backend supports macOS/Linux POSIX process groups and `ps`; Windows
fails before launch. That is an implementation limitation, not evidence that an
experiment needs another machine. No new Python dependency is required.

Before using it, complete the [benchmark readiness checks](benchmark_workflow.md)
and lock the training/data protocol. Running a command is a separate deliberate
step; installing this package does not authorise expensive training.

## Specification

Keep the spec, inputs, logs and outputs in a private runtime. Example structure:

```json
{
  "argv": ["/path/to/python", "/path/to/reviewed/worker.py"],
  "inputs": {"worker.py": "<verified SHA256>", "features.csv": "<verified SHA256>"},
  "outputs": ["predictions.jsonl", "metrics.json"],
  "limits": {
    "threads": 2,
    "seconds": 1800,
    "memory_mib": 4096,
    "max_project_mib": 2048,
    "max_growth_mib": 512,
    "min_free_mib": 5120,
    "storage_poll_seconds": 5
  }
}
```

Input paths resolve relative to the spec file. Output paths resolve inside the
new run directory. Use absolute executable/source paths in argv or explicitly
arrange worker access to inputs; the runner does not copy inputs or change argv.
Declare every code/data/config input needed for reproducibility. Inputs and
outputs are checksummed; identities not explicitly declared cannot be verified.

```sh
fpl-predict run-experiment --spec /path/to/private/fold1.json \
  --directory /path/to/private/project/runs/fold1 \
  --storage-root /path/to/private/project
```

The destination must be new and inside the existing monitored project root.
A completed fold can be reused with `--reuse-completed` only if its specification,
runner code, Python version, declared inputs and output hashes still match. Failed
or interrupted directories are evidence, never resumable success; choose a new
attempt directory. One immutable directory per fold/method supports explicit
sequential resumption without rerunning completed work. There is no parallel
batch scheduler or automatic retraining.

## Limits and observations

- One process group runs at a time per invocation. Set OpenMP/BLAS/NumExpr thread
  variables before launch; well-behaved workers must honour these and their own
  `n_jobs`. These are not OS-enforced CPU quotas.
- Sample the process-group sum of RSS every0.25seconds by default. Kill the group
  on observed memory breach, timeout, monitoring failure or interruption. A
  worker leaving live descendants behind is incomplete, not successful.
- Check free disk and logical project size before launch, every5seconds, and on
  normal exit. Stop on maximum project size, per-run growth or minimum-free-space
  breach. The defaults above are initial budgets, not evidence of hardware limits.
  Set them before a job, considering available memory/storage and expected outputs.
- Storage scans do not follow symlinks, and shared/sparse files may differ from
  physical disk allocation. Monitor the actual project root, not just one output
  directory. Concurrent project activity counts against the same storage budget.
- Watchdogs sample: very short spikes, allocation between scans, shared-memory
  accounting and fork/session escapes cannot be bounded exactly. This is neither
  a security sandbox nor a hard memory/disk quota. Use only audited trusted jobs,
  retain free-space headroom and do not disable monitoring to make a fit pass.
- Outputs must be declared relative files and cannot resolve outside the run.
  Missing/changed/escaping artifacts or inputs modified by the worker invalidate
  completion. Logs and incomplete evidence are retained, never automatically deleted.

`run.json` contains status, exit code, start/end times, observed peak memory,
storage observations, limits, input/command/runner signatures and successful
output hashes. It avoids raw command arguments and local paths; stdout/stderr may
still contain private data and must remain outside Git. Status distinguishes
completion, worker failure, timeout, memory/storage limit, monitor/launch error,
interruption, leftover descendants and invalid artifacts.

## Storage hygiene and remote archives

Check project/free space at package, download and build checkpoints too; do not
start background monitoring outside active work. Remove regenerable build/test
caches after validation, preserve the operational champion and unique frozen
evidence, and avoid duplicate downloads. GitHub draft-release archival is optional
only when space measurements justify it and the content is independently audited
for privacy and redistribution rights. Never upload private team/history/secrets
or unaudited data/model binaries to a public repository. Verify uploaded hashes
and retrieval before removing any expendable local copy. This command uploads
nothing and never deletes artifacts to free space automatically.
