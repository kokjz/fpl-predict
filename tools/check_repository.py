"""Audit the Git index before commit; print paths only, never secret values."""
import re
import subprocess
import sys
from pathlib import Path

BLOCKED_COMPONENTS = {"var", "data", "artifacts", "forecasts", "experiments", "decision_trials",
                      "planning", "screenshots", "context", ".venv", "__pycache__", ".pytest_cache"}
BLOCKED_SUFFIXES = {".joblib", ".pkl", ".pickle", ".png", ".jpg", ".jpeg", ".pem", ".key", ".p12"}
PATTERNS = [re.compile(p) for p in (
    r"gh[pousr]_[A-Za-z0-9]{30,}", r"github_pat_[A-Za-z0-9_]{30,}",
    r"AKIA[A-Z0-9]{16}", r"sk-[A-Za-z0-9_-]{32,}",
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", r"/Users/[A-Za-z0-9._-]+/",
    r"(?i)(?:api_key|access_token|password)\s*=\s*['\"][^'\"]{12,}['\"]",
)]

def reasons(path, raw):
    errors = []
    parts = Path(path).parts
    if any(part in BLOCKED_COMPONENTS for part in parts): errors.append("runtime/private directory")
    if Path(path).suffix.lower() in BLOCKED_SUFFIXES: errors.append("binary/private artifact")
    if Path(path).name.startswith((".env", "TEAM_STATE", "CONTEXT_MASTER", "USER_PROMPT")):
        errors.append("private configuration/context file")
    try: text = raw.decode("utf-8")
    except UnicodeDecodeError: return errors + ["non-text content"]
    if any(pattern.search(text) for pattern in PATTERNS): errors.append("credential/private-path pattern")
    if len(raw) > 1_000_000: errors.append("oversized tracked file")
    return errors

def main():
    root = Path(__file__).resolve().parent.parent
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    errors = []
    for name in filter(None, names):
        raw = subprocess.check_output(["git", "show", ":" + name], cwd=root)
        errors.extend(f"{name}: {reason}" for reason in reasons(name, raw))
    if errors:
        print("Repository audit failed:\n" + "\n".join(errors)); return 1
    print(f"Repository audit passed for {len(list(filter(None, names)))} indexed text files.")
    return 0

if __name__ == "__main__": sys.exit(main())
