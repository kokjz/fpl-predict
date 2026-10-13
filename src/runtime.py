"""Explicit, ignored runtime workspace; importing modules never writes files."""
import os
from pathlib import Path
import shutil
import json
import hashlib

RESOURCES = Path(__file__).resolve().parent / "fpl_predict_resources"

def workspace_root():
    return Path(os.environ.get("FPL_PREDICT_HOME", Path.cwd() / "var")).expanduser().resolve()

def initialise(root=None):
    root = Path(root).resolve() if root is not None else workspace_root()
    root.mkdir(parents=True, exist_ok=True)
    for directory in ("data", "artifacts/models", "forecasts", "experiments", "decision_trials"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    sources = [(RESOURCES / "model_registry.json", root / "model_registry.json")]
    sources += [(RESOURCES / name, root / name) for name in
                ("EXPERIMENT_PROTOCOL.md", "IMPROVEMENT_PROTOCOL.md", "I2_PROTOCOL.md")]
    for source, destination in sources:
        if not destination.exists():
            shutil.copyfile(source, destination)
    return root

def install_approved_model(source, root=None):
    """Copy only the expected immutable artifact, without unpickling input."""
    root = initialise(root)
    registry = json.loads((root / "model_registry.json").read_text())
    record = registry["versions"][registry["champion"]]
    raw = Path(source).read_bytes()
    if record["status"] != "approved" or hashlib.sha256(raw).hexdigest() != record["sha256"]:
        raise ValueError("Artifact is not the approved, hash-verified model")
    destination = (root / record["artifact"]).resolve()
    if not destination.is_relative_to(root):
        raise ValueError("Model artifact must remain inside the workspace")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.read_bytes() != raw:
        raise FileExistsError("Refusing to replace a different model")
    destination.write_bytes(raw)
    return destination
