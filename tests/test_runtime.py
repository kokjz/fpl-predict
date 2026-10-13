import hashlib
import json
import pytest
from runtime import workspace_root, initialise, install_approved_model

def test_workspace_can_live_outside_checkout(tmp_path, monkeypatch):
    root = tmp_path / "runtime"
    monkeypatch.setenv("FPL_PREDICT_HOME", str(root))
    assert workspace_root() == root
    assert not root.exists()
    initialise()
    assert (root / "model_registry.json").exists()
    (root / "model_registry.json").write_text("custom")
    initialise()
    assert (root / "model_registry.json").read_text() == "custom"

def test_untrusted_artifact_is_rejected_without_loading(tmp_path):
    root = initialise(tmp_path / "workspace")
    source = tmp_path / "untrusted.joblib"
    source.write_bytes(b"not a model")
    with pytest.raises(ValueError, match="hash-verified"):
        install_approved_model(source, root)
    assert not any((root / "artifacts/models").iterdir())

def test_install_preserves_hash_and_rejects_path_escape(tmp_path):
    root = initialise(tmp_path / "runtime")
    source = tmp_path / "trusted"; source.write_bytes(b"approved synthetic bytes")
    registry = {"champion": "test", "versions": {"test": {"status": "approved",
                "artifact": "artifacts/models/test.joblib", "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}}}
    (root / "model_registry.json").write_text(json.dumps(registry))
    assert install_approved_model(source, root).read_bytes() == source.read_bytes()
    registry["versions"]["test"]["artifact"] = "../escape"
    (root / "model_registry.json").write_text(json.dumps(registry))
    with pytest.raises(ValueError, match="inside"):
        install_approved_model(source, root)
