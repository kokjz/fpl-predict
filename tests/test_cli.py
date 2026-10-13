import sys
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
