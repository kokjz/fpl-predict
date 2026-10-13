# Security and privacy

Do not post credentials or private team data in issues, pull requests, commits or logs. For a suspected credential leak, revoke/rotate the credential first and contact the maintainer through GitHub's private vulnerability-reporting channel if available. Do not open a public issue containing the sensitive material.

Only trusted, hash-verified locally generated model artifacts may be deserialized. Pickle/joblib can execute code. The installer checks the approved SHA256 without loading the supplied artifact.

Runtime data, personal teams, downloaded histories, generated forecasts, screenshots, caches and model binaries are excluded from Git. CI runs offline tests with read-only repository permission and no project secrets. Workflow actions are pinned to immutable commits. Dependency updates are reviewed PRs, never automatic promotions.

Before making the repository public, verify current indexed contents and all reachable history, commit author privacy, dependency/data licenses and repository settings. The content audit catches common token formats/private paths and forbidden file types; it is not an exhaustive secret detector. This repository does not redistribute third-party football datasets.
