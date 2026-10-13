import importlib.util
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "tools/check_repository.py"
spec = importlib.util.spec_from_file_location("audit", path)
audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)

def test_private_artifacts_and_credential_formats_are_rejected():
    assert audit.reasons("planning/TEAM_STATE.json", b"{}")
    assert audit.reasons("var/forecast.json", b"{}")
    assert audit.reasons("src/example.py", ("ghp_" + "A" * 36).encode())
    assert audit.reasons("src/example.py", ("/Users/" + "somebody/private").encode())
    assert audit.reasons("weights.joblib", b"binary")
    assert not audit.reasons("src/model_registry.py", b"def resolve(): pass")
