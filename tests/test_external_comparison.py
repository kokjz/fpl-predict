import importlib.util
from pathlib import Path
import pandas as pd
import pytest

path = Path(__file__).resolve().parents[1] / "tools/compare_dastan.py"
spec = importlib.util.spec_from_file_location("comparison", path)
comparison = importlib.util.module_from_spec(spec); spec.loader.exec_module(comparison)


def frames():
    ours = pd.DataFrame({"season": ["2024-25"] * 2, "GW": [20, 20],
        "element": [1, 1], "fixture": [10, 11], "total_points": [1, 3],
        "points_core": [1, 3], "model": [2., 2.], "last5": [1., 1.],
        "ewm": [2., 2.], "candidate": [True, True]})
    external = pd.DataFrame({"season": ["2024-25"], "gameweek": [20],
        "fpl_code": [99], "actual": [4], "minutes": [180], "dastan": [3.],
        "dastan_without_ep_next": [3.]})
    return ours, external, pd.DataFrame({"id": [1], "code": [99]})


def test_matches_football_ids_and_aggregates_double_without_favourable_filter():
    ours, external, mapping = frames()
    result = comparison.report(ours, external, mapping)
    assert result["matched_rows"] == 1
    assert result["cohorts"]["predeadline_candidates"]["models"]["v1"]["rmse"] == 0
    assert result["cohorts"]["predeadline_candidates"]["models"]["dastan"]["rmse"] == 1


@pytest.mark.parametrize("failure", ["duplicate", "outcome", "mapping", "scoring", "candidate"])
def test_invalid_comparisons_fail_instead_of_silently_selecting_good_rows(failure):
    ours, external, mapping = frames()
    if failure == "duplicate": external = pd.concat([external, external])
    elif failure == "outcome": external["actual"] = 5
    elif failure == "mapping": mapping["id"] = 2
    elif failure == "scoring": ours.loc[0, "points_core"] = 0
    else: ours.loc[0, "candidate"] = False
    with pytest.raises(ValueError): comparison.align(ours, external, mapping)
