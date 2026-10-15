"""Synthetic adversarial benchmark admission and reporting tests; never train."""
import hashlib
import json
import sys

import numpy as np
import pandas as pd
import pytest

import external_benchmark as benchmark


def outcomes():
    # One double, one single and one explicit blank. All are known predeadline.
    return pd.DataFrame([
        dict(season="2025-26", gameweek=20, fpl_code=11, fixture=190,
             actual=2, candidate=True, deadline="2026-01-01T10:00:00Z"),
        dict(season="2025-26", gameweek=20, fpl_code=11, fixture=191,
             actual=6, candidate=True, deadline="2026-01-01T10:00:00Z"),
        dict(season="2025-26", gameweek=20, fpl_code=22, fixture=192,
             actual=-1, candidate=True, deadline="2026-01-01T10:00:00Z"),
        dict(season="2025-26", gameweek=20, fpl_code=33, fixture=0,
             actual=0, candidate=False, deadline="2026-01-01T10:00:00Z"),
    ])


def manifest(name="first", grain="player_gameweek", kind="archived_predeadline"):
    return dict(schema_version=1, model_id=name, grain=grain, prediction_kind=kind,
                target_by_season={"2025-26": "fpl-total-2025-26"},
                source_url="https://example.org/reference", source_revision="a" * 40,
                code_sha256="b" * 64, data_sha256="c" * 64, input_sha256="d" * 64,
                timing=dict(train_cutoff="2025-05-01T12:00:00Z",
                            selection_cutoff="2025-06-01T12:00:00Z",
                            features_cutoff="2026-01-01T09:00:00Z",
                            created_at="2026-01-01T09:30:00Z",
                            captured_at="2026-01-01T09:35:00Z"))


def forecast(codes=(11, 22, 33), values=(7., 0., 0.)):
    return pd.DataFrame(dict(season=["2025-26"] * len(codes), gameweek=[20] * len(codes),
                             fpl_code=list(codes), prediction=list(values)))


def test_shared_rows_coverage_and_double_sum_do_not_select_best_model_rows():
    truth = outcomes()
    fixtures = truth.drop(columns=["actual", "candidate", "deadline"]).assign(prediction=[3., 4., 0., 0.])
    report = benchmark.compare(truth, [(fixtures, manifest("first", "fixture")),
                                      (forecast(), manifest("second")),
                                      (forecast((11,), (8.,)), manifest("third"))])
    assert report["all_model_intersection"]["rows"] == 1
    pair = report["pairwise_intersections"][0]
    assert pair["rows"] == 3
    assert pair["cohorts"]["predeadline_candidates"]["rows"] == 2
    assert pair["cohorts"]["all_matched"]["models"]["first"]["rmse"] == pytest.approx(np.sqrt(2 / 3))
    assert report["coverage_by_model"]["third"]["candidate_coverage"] == .5
    assert report["promotion"] is False
    assert "11" not in report["sources"]  # no per-player export
    assert len(report["protocol_sha256"]) == 64


@pytest.mark.parametrize("mode", ["duplicate", "unmapped", "nonfinite", "score_conflict",
                                   "different_target", "fractional_id", "bool_id", "unknown_season"])
def test_bad_rows_are_rejected_even_if_outside_eventual_intersection(mode):
    f, m = forecast(), manifest()
    if mode == "duplicate": f = pd.concat([f, f.iloc[[2]]])
    elif mode == "unmapped": f.loc[2, "fpl_code"] = 999
    elif mode == "nonfinite": f.loc[2, "prediction"] = np.nan
    elif mode == "score_conflict": f["actual"] = [8, -1, 99]
    elif mode == "different_target": m["target_by_season"]["2025-26"] = "core"
    elif mode == "fractional_id": f["fpl_code"] = [11, 22, 33.5]
    elif mode == "bool_id": f["fpl_code"] = [11, 22, True]
    else: f.loc[2, "season"] = "2099-00"
    with pytest.raises(ValueError):
        benchmark.compare(outcomes(), [(f, m), (forecast((11,), (8,)), manifest("second"))])


@pytest.mark.parametrize("mode", ["partial_double", "candidate_conflict", "deadline_conflict",
                                   "blank_points", "blank_and_fixture", "duplicate_outcome"])
def test_schedule_and_candidate_integrity(mode):
    truth = outcomes()
    f = truth.drop(columns=["actual", "candidate", "deadline"]).assign(prediction=1.)
    if mode == "partial_double": f = f.drop(index=1)
    elif mode == "candidate_conflict": truth.loc[1, "candidate"] = False
    elif mode == "deadline_conflict": truth.loc[2, "deadline"] = "2026-01-01T11:00:00Z"
    elif mode == "blank_points": truth.loc[3, "actual"] = 1
    elif mode == "blank_and_fixture": truth.loc[1, "fixture"] = 0
    else: truth = pd.concat([truth, truth.iloc[[0]]])
    with pytest.raises(ValueError):
        benchmark.compare(truth, [(f, manifest(grain="fixture")), (forecast(), manifest("second"))])


@pytest.mark.parametrize("field,value", [
    ("train_cutoff", "2026-01-01T10:00:00Z"),
    ("selection_cutoff", "2026-01-01T11:00:00Z"),
    ("features_cutoff", "2026-01-01T10:00:00Z"),
    ("features_cutoff", "2026-01-01T09:31:00Z"),
    ("captured_at", "2026-01-01T10:00:00Z"),
    ("captured_at", "2026-01-01T09:00:00Z"),
    ("created_at", "2026-01-02T09:00:00Z"),
    ("train_cutoff", "2025-01-01"),
    ("features_cutoff", "NaT"),
])
def test_lookahead_naive_or_invalid_origin_timing_rejected(field, value):
    m = manifest(); m["timing"][field] = value
    with pytest.raises(ValueError):
        benchmark.compare(outcomes(), [(forecast(), m), (forecast(), manifest("second"))])


def test_retrospective_generation_date_is_preserved_not_backdated():
    m = manifest(kind="retrospective")
    m["timing"]["created_at"] = "2026-10-15T09:00:00Z"
    del m["timing"]["captured_at"]
    report = benchmark.compare(outcomes(), [(forecast(), m), (forecast(), manifest("second"))])
    assert report["sources"]["first"]["prediction_kind"] == "retrospective"
    assert report["sources"]["first"]["declared_timing_ranges"]["created_at"]["min"].startswith("2026-10-15")


def test_per_row_timing_and_column_adapter_accept_noncanonical_exports():
    m = manifest(); m["columns"] = {"gameweek": "gw", "prediction": "xpts"}
    f = forecast().rename(columns={"gameweek": "gw", "prediction": "xpts"})
    f["train_cutoff"] = "2025-04-01T12:00:00+08:00"
    normal, timing = benchmark.normalise_forecast(f, m, benchmark.prepare_outcomes(outcomes()))
    assert len(normal) == 3
    assert timing["train_cutoff"]["min"] == "2025-04-01T04:00:00+00:00"


@pytest.mark.parametrize("mode", ["duplicate_mapping", "implicit_alias", "missing_mapping", "missing_timing", "bad_hash", "duplicate_name"])
def test_manifest_errors_rejected(mode):
    m = manifest(); f = forecast()
    if mode == "duplicate_mapping": m["columns"] = {"prediction": "x", "actual": "x"}
    elif mode == "implicit_alias": m["columns"] = {"prediction": "fpl_code"}
    elif mode == "missing_mapping": m["columns"] = {"prediction": "missing"}
    elif mode == "missing_timing": del m["timing"]["selection_cutoff"]
    elif mode == "bad_hash": m["code_sha256"] = "unverified"
    else: m["model_id"] = "second"
    with pytest.raises(ValueError):
        benchmark.compare(outcomes(), [(f, m), (forecast(), manifest("second"))])


def test_empty_intersection_and_no_candidate_rows_are_explicit_not_nan():
    first = forecast((11,), (8.,)); second = forecast((22,), (-1.,))
    report = benchmark.compare(outcomes(), [(first, manifest()), (second, manifest("second"))])
    assert report["all_model_intersection"]["rows"] == 0
    assert report["all_model_intersection"]["cohorts"]["predeadline_candidates"]["models"]["first"]["rmse"] is None
    truth = outcomes().assign(candidate=False)
    report = benchmark.compare(truth, [(forecast(), manifest()), (forecast(), manifest("second"))])
    assert report["coverage_by_model"]["first"]["candidate_coverage"] is None
    json.dumps(report, allow_nan=False)


def test_ordinary_absence_reduces_coverage_but_timing_diff_in_double_fails():
    truth = outcomes()
    f = truth.drop(columns=["actual", "candidate", "deadline"]).assign(prediction=1.)
    f["features_cutoff"] = ["2026-01-01T08:00:00Z", "2026-01-01T09:00:00Z"] + ["2026-01-01T08:00:00Z"] * 2
    with pytest.raises(ValueError, match="differing timing"):
        benchmark.normalise_forecast(f, manifest(grain="fixture"), benchmark.prepare_outcomes(truth))


def write_inputs(root):
    actual = root / "outcomes.jsonl"
    actual.write_text(outcomes().to_json(orient="records", lines=True))
    paths = []
    for name in ("first", "second"):
        path = root / (name + ".csv")
        forecast().to_csv(path, index=False)
        m = manifest(name)
        m["file"] = path.name
        m["input_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path = root / (name + ".json")
        manifest_path.write_text(json.dumps(m))
        paths.append(manifest_path)
    return actual, paths


def invoke(monkeypatch, actual, paths, output, outcome_sha=None):
    args = ["benchmark", "--outcomes", str(actual), "--outcomes-sha256",
            outcome_sha or hashlib.sha256(actual.read_bytes()).hexdigest(),
            "--output", str(output)]
    for path in paths: args += ["--manifest", str(path)]
    monkeypatch.setattr(sys, "argv", args)
    benchmark.main()


def test_local_cli_hashes_write_once_no_paths_or_individual_predictions(tmp_path, monkeypatch):
    actual, paths = write_inputs(tmp_path)
    output = tmp_path / "report.json"
    invoke(monkeypatch, actual, paths, output)
    raw = output.read_text(); report = json.loads(raw)
    assert report["all_model_intersection"]["rows"] == 3
    assert str(tmp_path) not in raw
    assert '"fpl_code"' not in raw
    assert '"prediction"' not in raw
    assert len(report["manifest_sha256"]) == 2
    saved = output.read_bytes()
    with pytest.raises(SystemExit): invoke(monkeypatch, actual, paths, output)
    assert output.read_bytes() == saved


@pytest.mark.parametrize("failure", ["outcome_hash", "export_hash", "duplicate_json", "duplicate_csv", "csv_bool"])
def test_cli_rejects_bad_files_without_creating_output(tmp_path, monkeypatch, failure):
    actual, paths = write_inputs(tmp_path)
    output = tmp_path / "nested/report.json"
    sha = None
    if failure == "outcome_hash": sha = "0" * 64
    elif failure == "export_hash": (tmp_path / "first.csv").write_text("changed")
    elif failure == "duplicate_json": paths[0].write_text('{"model_id":"one", "model_id":"two"}')
    elif failure == "duplicate_csv":
        (tmp_path / "first.csv").write_text("a,a\n1,2\n")
    else:
        actual.write_text("season,gameweek,fpl_code,fixture,actual,candidate,deadline\n2025-26,20,11,1,0,False,2026-01-01T10:00:00Z\n")
    with pytest.raises(SystemExit) as error:
        invoke(monkeypatch, actual, paths, output, sha)
    assert error.value.code == 2
    assert not output.parent.exists()


def test_input_bound_and_json_duplicate_checks(tmp_path, monkeypatch):
    path = tmp_path / "too_big.csv"; path.write_text("a\n" * 20)
    real = benchmark.protocol
    monkeypatch.setattr(benchmark, "protocol", lambda: {**real(), "max_file_bytes": 10})
    with pytest.raises(ValueError, match="size limit"): benchmark.load_table(path)
    with pytest.raises(ValueError, match="Duplicate JSON"): benchmark._json('{"a":1,"a":2}')


def test_csv_outcomes_roundtrip_is_explicit_and_hash_stable(tmp_path):
    path = tmp_path / "outcomes.csv"
    original = outcomes(); original["candidate"] = original.candidate.map({True:"true", False:"false"})
    original.to_csv(path, index=False)
    loaded, sha = benchmark.load_table(path)
    validated = benchmark.prepare_outcomes(loaded)
    assert validated.candidate.tolist() == [True, True, True, False]
    assert sha == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("field,value", [
    ("source_revision", "main"),
    ("source_url", "https://user:secret@example.org/reference"),
    ("source_url", "https://example.org/reference?token=secret"),
    ("source_url", "https://"),
])
def test_mutable_revision_or_sensitive_source_url_rejected(field, value):
    m = manifest(); m[field] = value
    with pytest.raises(ValueError):
        benchmark.compare(outcomes(), [(forecast(), m), (forecast(), manifest("second"))])


def test_nonintegral_realised_points_rejected():
    truth = outcomes(); truth["actual"] = [2, 6, -1, .5]
    with pytest.raises(ValueError):
        benchmark.prepare_outcomes(truth)


def test_actual_cli_dispatch_uses_benchmark_module_without_training(tmp_path, monkeypatch):
    from fpl_predict_cli import main
    monkeypatch.setenv("FPL_PREDICT_HOME", str(tmp_path / "unused"))
    monkeypatch.setattr(sys, "argv", ["fpl-predict", "benchmark", "--help"])
    seen = []
    monkeypatch.setattr("fpl_predict_cli.runpy.run_module", lambda module, run_name: seen.append(module))
    main()
    assert seen == ["external_benchmark"]
    assert not (tmp_path / "unused").exists()


def test_benchmark_dispatch_does_not_initialise_operational_workspace(tmp_path, monkeypatch):
    from fpl_predict_cli import main
    monkeypatch.setenv("FPL_PREDICT_HOME", str(tmp_path / "unused"))
    monkeypatch.setattr(sys, "argv", ["fpl-predict", "benchmark", "--outcomes", "explicit.jsonl"])
    seen = []
    monkeypatch.setattr("fpl_predict_cli.runpy.run_module", lambda module, run_name: seen.append(module))
    main()
    assert seen == ["external_benchmark"]
    assert not (tmp_path / "unused").exists()
