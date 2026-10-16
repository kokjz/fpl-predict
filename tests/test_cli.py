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


@pytest.mark.parametrize("command,module", [("reference-pilot", "reference_pilot"), ("audit-deadlines", "deadline_provenance"), ("native-reference", "native_reference"), ("native-development", "native_development"), ("audit-availability", "availability_history"), ("conditional-reference", "conditional_reference"), ("historical-references", "historical_references"), ("archived-reference", "archived_reference"), ("selection-benchmark", "selection_benchmark"), ("participation-audit", "participation_audit"), ("news-probe", "news_availability_probe")])
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


def test_trial_review_never_initialises_runtime(tmp_path,monkeypatch):
    root=tmp_path/'unused';monkeypatch.setenv('FPL_PREDICT_HOME',str(root))
    monkeypatch.setattr(sys,'argv',['fpl-predict','decision-trial','review','--root',str(root),'--output',str(tmp_path/'review.json')])
    monkeypatch.setattr('fpl_predict_cli.initialise',lambda:(_ for _ in ()).throw(AssertionError('runtime write')))
    seen=[];monkeypatch.setattr('fpl_predict_cli.runpy.run_module',lambda module,run_name:seen.append(module))
    main()
    assert seen==['decision_trial'] and not root.exists()


def test_qualification_dispatch_does_not_initialise_runtime(tmp_path,monkeypatch):
    root=tmp_path/'unused';monkeypatch.setenv('FPL_PREDICT_HOME',str(root))
    monkeypatch.setattr(sys,'argv',['fpl-predict','qualify-season','arms'])
    monkeypatch.setattr('fpl_predict_cli.initialise',lambda:pytest.fail('Unexpected operational runtime write'))
    seen=[];monkeypatch.setattr('fpl_predict_cli.runpy.run_module',lambda module,run_name:seen.append(module))
    main();assert seen==['season_qualification'] and not root.exists()
