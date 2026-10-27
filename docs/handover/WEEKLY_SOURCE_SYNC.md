# Mandatory source sync before weekly model analysis

Added 27 October 2026 at the user's request. Model improvement may run on a
different device from weekly squad planning. A local checkout is not evidence
that it contains the latest reviewed release.

Before **any model analysis**—including a forecast, horizon/chip plan,
sensitivity run, model comparison or finalised-gameweek review:

1. Inspect the intended engine checkout, its branch, local changes and remote.
   Fetch the remote and its branch updates. Record the fetch time and remote
   `main` commit. A previous cycle's fetch is insufficient.
2. Use a clean checkout of reviewed, merged `main`, safely fast-forwarded to
   `origin/main`; verify their exact commit IDs match. Never analyse with an
   unmerged research branch, stale private script copy or uncommitted engine
   changes. Do not merge research PRs as a weekly-planning shortcut.
3. Preserve local work. If the checkout is dirty/diverged/in use by another chat,
   do not reset, force, switch branches or pull over it. Resolve safely, or use
   a separate clean checkout of the fetched reviewed release. If the remote
   cannot be checked, disclose the limitation and resolve it before claiming
   analysis with the latest release.
4. Read the current release and operational handoff, registry and model report.
   Resolve the **approved** champion and verify its artifact hash and runtime/
   schema compatibility. Source sync does not transfer private weights or
   promote newer experiments. Obtain a newly approved artifact through the
   authorised private handoff if required; never substitute a research model.
5. Record the engine commit, remote-main commit/fetch time, champion version/
   hash and input/generation timestamps. Refresh current rules, news, fixtures,
   prices and confirmed manager state for the authorised cycle.
6. Recheck remote main and the registry before final advice. If they changed,
   preserve the old frozen run, read the release, and refresh with a compatible
   approved release when feasible. Disclose the version actually used.

This is an on-demand prerequisite for each analysis invocation, not a background
monitor. Model training, tuning, promotion and engine changes remain the remit
of the improvement chat; weekly analysis does not authorise those actions.
Unfinished improvement PRs may remain open while weekly analysis uses current
reviewed main. Declaring the improvement repository fully synchronised at the
end of its own package still requires its existing PR-resolution/cleanup SOP.
