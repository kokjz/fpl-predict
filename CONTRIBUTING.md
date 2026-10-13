# Development workflow

1. Create a purpose-specific branch from current `main` before changing engine code or configuration.
2. Make coherent commits as changes are completed. Run tests and `python tools/check_repository.py` after staging, before each push. Push regularly to the corresponding branch.
3. Open a pull request for each significant set of changes. Describe the problem, final behavior, validation and material limitations.
4. Review the full diff, source/data boundaries, staged contents and test results. Resolve findings before merging. Required checks must pass; no automatic merges.
5. Prefer squash merges. After the last PR depending on a branch has merged into `main`, verify no open PR uses it as head or base, then delete both its remote and local branch. Keep branches while dependent work remains open. Switch to `main` and check for unmerged work before local deletion. Keep the original approved model available for rollback.

Merging code does not approve a trained model. Model changes require predeclared development/audit/points/integrity gates, chronological evaluation and later independent evidence. No guaranteed monotonically improving real-world performance is claimed. Preserve failed experiments locally, not in ordinary Git history.

Tests run offline using synthetic fixtures. Optional integration tests require `FPL_PREDICT_RUN_INTEGRATION=1` and an explicitly prepared private runtime; skipped local-data checks must be disclosed. Run them before promoting a model. No real manager data or API credentials may be added as fixtures.

Python and numerical dependencies are intentionally pinned for artifact compatibility. Dependency PRs must test both package behavior and compatibility with trusted artifacts. Do not accept an automated version bump merely because unit tests pass.

Use the repository privacy audit as a check, not a proof that no possible secret exists. Review `git diff --cached` yourself. Avoid absolute personal paths, author email disclosure, private squad files, screenshots, notebooks with outputs, executable model binaries and downloaded player datasets. Use a GitHub no-reply commit email.
