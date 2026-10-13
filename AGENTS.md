# Engine repository instructions

- This repository is public-ready source only. Never copy parent-project context, squad/team files, screenshots, credentials or personal decision/history into Git.
- Create a purpose-specific branch for each change. Test coherent changes before pushing; commit and push regularly. Significant changes require a PR, diff/review/check validation, resolved findings and merge only after checks pass.
- A code merge does not promote a trained model. Preserve the approved registry and chronological evaluation/promotion gates. Do not tune on inspected holdouts and call them untouched.
- Keep all mutable runtime artifacts under the ignored workspace selected by FPL_PREDICT_HOME. Test with synthetic data, not a real team.
- Run pytest and tools/check_repository.py, inspect staged diff, and verify privacy before every commit/push.
- Never rewrite published substantive history, delete validation evidence, or execute model training/account actions as part of routine repository maintenance.
- Report skipped integration checks and unmeasured performance honestly. Do not introduce CI data downloads or automatic retraining/model promotion.
- Clean up both remote and local branches after their last dependent PR has merged into main. Check open PR head/base dependencies first; never delete a branch still needed by dependent work.
