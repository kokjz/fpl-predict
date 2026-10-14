import copy
import numpy as np
import pandas as pd
import pytest
from availability_evidence import observations, scoped_overrides, official_baselines
from score_forecast import official_comparison, playing_time_diagnostics


def bootstrap():
    return {"events":[{"id":7,"is_next":True,"deadline_time":"2026-10-20T10:00:00Z"}],
            "elements":[{"id":1,"element_type":3,"status":"d","news":"Test news",
                         "chance_of_playing_next_round":75,"ep_next":"4.5"},
                        {"id":2,"element_type":4,"status":"a","ep_next":""}]}


def review():
    return {"schema_version":1,"GW":7,"recorded_at_utc":"2026-10-19T12:00:00Z",
        "players":[{"id":1,"minutes":65,"reason":"Illustrative reported rotation scenario",
        "source_url":"https://example.org/news","published_at_utc":"2026-10-19T10:00:00Z",
        "checked_at_utc":"2026-10-19T11:00:00Z"}]}


def test_chance_is_evidence_not_probability_and_unknowns_stay_unknown():
    b=bootstrap();source={"retrieved_utc":"2026-10-19T09:00:00Z","sha256":"synthetic","url":"https://example.org/api"}
    doc=observations(b,source)
    assert doc["players"][0]["official_chance_label"]==75
    assert "p_play" not in doc["players"][0]
    assert doc["players"][0]["expected_minutes_override"] is None
    assert doc["players"][1]["official_ep_next"] is None
    assert official_baselines(b)=={(1,7):4.5}
    b["events"][0]["is_next"]=False
    assert observations(b,source)["GW"] is None
    assert official_baselines(b)=={}


def test_review_keeps_provenance_and_gameweek_scope():
    gw,recorded,entries=scoped_overrides(review(),bootstrap(),"2026-10-19T13:00:00Z")
    assert gw==7 and entries[1]["minutes"]==65
    assert entries[1]["published_at_utc"]=="2026-10-19T10:00:00+00:00"


@pytest.mark.parametrize("failure",["post_deadline","future","missing_reason","source_order","naive","nonfinite","duplicate","unknown"])
def test_unusable_evidence_rejected(failure):
    d=review();entry=d["players"][0]
    if failure=="post_deadline":d["recorded_at_utc"]="2026-10-20T10:00:00Z"
    elif failure=="future":d["recorded_at_utc"]="2026-10-19T14:00:00Z"
    elif failure=="missing_reason":entry["reason"]=""
    elif failure=="source_order":entry["published_at_utc"]="2026-10-19T12:00:00Z"
    elif failure=="naive":entry["published_at_utc"]="2026-10-19 10:00:00"
    elif failure=="nonfinite":entry["minutes"]=float("nan")
    elif failure=="duplicate":d["players"].append(copy.deepcopy(entry))
    else:entry["id"]=999
    with pytest.raises(ValueError):scoped_overrides(d,bootstrap(),"2026-10-19T13:00:00Z")


def frame():
    return pd.DataFrame({"candidate_pool":[True,True,False],"actual":[10,0,2],
        "expected_points":[5,1,2],"last5_xp":[4,2,1],"ewm_xp":[4,1,2],
        "official_ep_next":[None,0.,2.],"expected_minutes":[120,45,90],
        "actual_minutes":[60,0,90],"p_play":[.6,.4,1.],"actual_appearance":[True,False,True]})


def test_official_baseline_missingness_never_flattens_error_with_zero_imputation():
    result=official_comparison(frame())["candidates"]
    assert result["eligible_rows"]==2 and result["matched_rows"]==1
    assert result["metrics"]["model"]["rmse"]==1
    assert result["metrics"]["official_ep_next"]["rmse"]==0
    assert result["metrics"]["model"]["n"]==result["metrics"]["official_ep_next"]["n"]
    assert official_comparison(frame().drop(columns="official_ep_next"))["all"]["matched_rows"]==0


def test_double_minutes_sum_is_distinct_from_any_appearance_and_bins_cover_boundaries():
    result=playing_time_diagnostics(frame())["candidates"]
    assert result["minutes"]["mae"]==52.5
    assert result["appearance_brier"]==pytest.approx(.16)
    assert sum(b["n"] for b in result["appearance_calibration_bins"])==2
    empty=frame();empty["candidate_pool"]=False
    assert playing_time_diagnostics(empty)["candidates"]["appearance_brier"] is None
    assert official_comparison(empty)["candidates"]["metrics"]["model"]["n"]==0
