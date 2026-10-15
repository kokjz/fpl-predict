import numpy as np
import pandas as pd
import pytest

from native_sources import FIELDS,join_player_statistics,join_team_statistics,corrected_assignments,snapshot_features,match_roster_observations
from test_deadline_provenance import bootstrap


def player():
    return dict(season="2025-26",fixture=1,fpl_code=11,understat_id=100,
                team_name="Man City",opponent_name="Arsenal",home=True,
                ts=pd.Timestamp("2026-01-01T15:00:00Z"),minutes=90.)


def match():
    return dict(date="2026-01-01",h_team="Manchester City",a_team="Arsenal",**{f:"1.5" for f in FIELDS.values()})


def test_player_join_keeps_unknown_rows_and_counts_exact_duplicates():
    row=player();unmapped={**row,"fpl_code":22,"understat_id":np.nan}
    absent={**row,"fpl_code":33,"understat_id":200,"minutes":0.}
    m=match();p,proof=join_player_statistics(pd.DataFrame([row,unmapped,absent]),[(100,{"matches":[m,m]})])
    assert len(p)==3 and proof["mapped_appearance_missing"]==0
    assert p.us_xG.iloc[0]==1.5 and pd.isna(p.us_xG.iloc[1]) and p.us_xG.iloc[2]==0
    assert proof["unmapped_appearance_rows"]==1 and proof["exact_provider_duplicates_removed"]==1


def test_missing_or_conflicting_mapped_appearance_cannot_be_hidden():
    p,proof=join_player_statistics(pd.DataFrame([player()]),[])
    assert len(p)==1 and proof["mapped_appearance_missing"]==1
    m=match();changed={**m,"xG":"2.5"}
    with pytest.raises(ValueError,match="Conflicting"):
        join_player_statistics(pd.DataFrame([player()]),[(100,{"matches":[m,changed]})])


def test_team_join_uses_fpl_time_and_reports_provider_clock_offset():
    row={**player(),"team_h_score":2.,"team_a_score":1.}
    m=dict(date="2026-01-01 16:00:00",scored=2,missed=1,h_a="h",xG=1.5,xGA=.4,
           deep=3,deep_allowed=2,ppda={"att":10,"def":2},ppda_allowed={"att":8,"def":1})
    payload={"teams":{"1":{"title":"Manchester City","history":[m]}}}
    p,proof=join_team_statistics(pd.DataFrame([row]),[(2025,payload)])
    assert p.ts.iloc[0]==row["ts"] and proof["provider_team_time_offsets_seconds"]=={"3600":1}
    assert not proof["team_conflicts"]
    m["scored"]=99
    with pytest.raises(ValueError,match="venue/score"):
        join_team_statistics(pd.DataFrame([row]),[(2025,payload)])


def test_snapshot_selection_uses_capture_and_preserves_zero_vs_missing():
    payload=bootstrap();payload["total_players"]=1000
    payload["elements"][0].update(now_cost=50,selected_by_percent="10",transfers_in_event=5,
                                   transfers_out_event=2,ep_next="0",status="d",chance_of_playing_next_round=None,news=" ")
    p=snapshot_features(payload,"2025-26",28,"2025-08-28T09:00:00Z")
    assert p.selected.iloc[0]==100 and p.ar_ep_next.iloc[0]==0
    assert p.sig_chance_playing.iloc[0]==-1 and p.transfers_balance.iloc[0]==3
    with pytest.raises(ValueError):snapshot_features(payload,"2025-26",28,"2025-08-28T10:00:00Z")


def test_reviewed_identity_corrections_do_not_mutate_release_assignments():
    original=pd.DataFrame({"fpl_code":[437688,515501],"understat_id":[9082,5191]})
    result=corrected_assignments(original)
    assert result.understat_id.tolist()==[9216,10576]
    assert original.understat_id.tolist()==[9082,5191]


def test_match_roster_evidence_never_synthesises_absent_players():
    meta=dict(date="2026-01-01",h_team="Manchester City",a_team="Arsenal",h_team_id=1,a_team_id=2,h_goals=2,a_goals=0)
    a={**match(),"player_id":100,"team_id":1,"h_a":"h","goals":2,"own_goals":0}
    b={**match(),"player_id":200,"team_id":2,"h_a":"a","goals":0,"own_goals":0}
    payload={"rosters":{"h":{"1":a},"a":{"2":b}}}
    result=match_roster_observations(meta,payload)
    assert [i for i,r in result]==[100,200]
    a["team_id"]=999
    with pytest.raises(ValueError,match="identity"):match_roster_observations(meta,payload)
