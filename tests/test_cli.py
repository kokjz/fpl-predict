import sys
import pytest
from fpl_predict_cli import main

def test_subcommand_help_is_forwarded_without_workspace_writes(tmp_path, monkeypatch):
    root = tmp_path / "unused"
    monkeypatch.setenv("FPL_PREDICT_HOME", str(root))
    monkeypatch.setattr(sys, "argv", ["fpl-predict", "forecast", "--help"])
    seen = []
    monkeypatch.setattr("fpl_predict_cli.runpy.run_module", lambda module, run_name: seen.append((module, sys.argv[1:])))
    main()
    assert seen == [("forecast", ["--help"])]
    assert not root.exists()


@pytest.mark.parametrize("command,module", [("reference-pilot", "reference_pilot"), ("audit-deadlines", "deadline_provenance"), ("native-reference", "native_reference"), ("native-development", "native_development")])
def test_research_dispatch_does_not_initialise_operational_runtime(tmp_path, monkeypatch, command, module):
    root = tmp_path / "unused"
    monkeypatch.setenv("FPL_PREDICT_HOME", str(root))
    monkeypatch.setattr(sys, "argv", ["fpl-predict", command, "example-argument"])
    seen = []
    monkeypatch.setattr("fpl_predict_cli.initialise", lambda: (_ for _ in ()).throw(AssertionError("runtime write")))
    monkeypatch.setattr("fpl_predict_cli.runpy.run_module", lambda module, run_name: seen.append((module, sys.argv[1:])))
    main()
    assert seen == [(module, ["example-argument"])]
    assert not root.exists()
