import joblib
import numpy as np
import pandas as pd
import pytest
from threadpoolctl import threadpool_limits

from benchmark_metrics import evaluate
from fpl_model import CORE_FEATURES, fit_estimator, sample_weights
from lightweight_candidates import LightweightCore, positions
from search_lightweight import run, eligible


def synthetic():
    rng = np.random.default_rng(42)
    x = pd.DataFrame(rng.uniform(0, 1, (300, len(CORE_FEATURES))), columns=CORE_FEATURES)
    pos = np.tile(np.arange(1, 5), 75)
    for p in range(1, 5): x[f"pos_{p}"] = (pos == p).astype(float)
    x["n_history"] = 4; x["last5_minutes"] = 60
    r = pd.DataFrame({"season": "2022-23", "GW": np.repeat(np.arange(1, 76), 4),
        "element": np.arange(300), "pos": pos, "points_core": rng.integers(-2, 12, 300),
        "minutes": np.tile([0, 30, 90], 100),
        "ts": pd.date_range("2022-01-01", periods=300, tz="UTC")})
    return x, r


@pytest.mark.parametrize("kind", ["incumbent", "position", "minutes_mixture", "extra_trees"])
def test_candidates_ignore_future_labels_at_inference_and_reload(kind, tmp_path):
    x, r = synthetic()
    with threadpool_limits(limits=2):
        model = LightweightCore(kind).fit(x, r)
        expected = model.predict(x)
        altered = x.assign(minutes=90, total_points=999, name="unknown", element=999)
        # Parallel forest reduction can change the last floating-point bit.
        np.testing.assert_allclose(model.predict(altered), expected, rtol=0, atol=1e-12)
        path = tmp_path / "local.joblib"; joblib.dump(model, path)
        np.testing.assert_allclose(joblib.load(path).predict(x), expected, rtol=0, atol=1e-12)
        assert np.isfinite(expected).all() and ((0 <= expected) & (expected <= 20)).all()
        if kind == "incumbent":
            original = fit_estimator("hgb7", x[CORE_FEATURES], r.points_core, sample_weights(r))
            np.testing.assert_array_equal(expected, np.clip(original.predict(x[CORE_FEATURES]), 0, 20))


def test_minutes_mixture_handles_missing_playing_states():
    x, r = synthetic(); r["minutes"] = 0; r["points_core"] = 0
    with threadpool_limits(limits=2):
        assert (LightweightCore("minutes_mixture").fit(x, r).predict(x) == 0).all()


def test_invalid_position_and_misaligned_labels_rejected():
    x, r = synthetic(); x.loc[0, "pos_1"] = 2
    with pytest.raises(ValueError, match="valid position"): positions(x)
    with pytest.raises(ValueError, match="ordered indices"):
        LightweightCore("incumbent").fit(x, r.iloc[::-1])


def test_double_gameweek_error_is_aggregated_at_decision_grain():
    x, r = synthetic(); x = x.iloc[:2].copy(); r = r.iloc[:2].copy()
    r["element"] = 1; r["GW"] = 1; r["points_core"] = [1, 3]
    result = evaluate(r, x, [2., 2.])
    assert result["candidate_fixture"]["rmse"] == 1
    assert result["candidate_player_gw"]["n"] == 1
    assert result["candidate_player_gw"]["rmse"] == 0
    x.loc[1, "n_history"] = 0
    with pytest.raises(ValueError, match="membership differs"): evaluate(r, x, [2., 2.])


def test_search_is_write_once_and_cannot_promote_without_gates(tmp_path):
    with pytest.raises(FileExistsError): run(tmp_path, tmp_path)
    baseline = {"pooled": {"rmse": 3., "mae": 2.}, "folds": {f:
        {"candidate_fixture": {"rmse": 3.}} for f in ("2022-23", "2023-24")}}
    candidate = {**baseline, "pooled": {"rmse": 2.99, "mae": 2.}}
    assert not eligible(candidate, baseline)


def test_missing_input_reserves_output_path_without_promotion(tmp_path):
    out = tmp_path / "new"
    with pytest.raises(FileNotFoundError): run(tmp_path, out)
    # Input hashes fail before a run begins; a nonempty directory still prevents
    # rerunning under the same evidence path.
    assert out.exists()
    with pytest.raises(FileExistsError): run(tmp_path, out)
