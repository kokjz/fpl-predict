import copy
import json
import numpy as np
import pytest
from appearance_calibration import fit,transform,apply


def rows():
    return [dict(season='2022-23',gameweek=g,id=i,as_of=f'2023-01-{g:02d}T00:00Z',available_at=f'2023-01-{g+1:02d}T00:00Z',p_play=p,label=y) for g in range(1,4) for i,(p,y) in enumerate([(.1,0),(.2,0),(.3,1),(.6,1),(.8,1),(.9,1)],1)]


def calibration():return fit(rows(),'2023-08-01T00:00Z',source_hashes={'cohort':'a'*64})


def test_save_reload_chronology_monotonicity_and_nontrivial_mapping():
    c=calibration();p=np.array([.1,.4,.8]);q=transform(p,json.loads(json.dumps(c)),'2023-08-01T00:00Z')
    assert np.all(np.diff(q)>0) and not np.allclose(q,p) and c['training_cells']==18
    assert np.allclose(q,1/(1+np.exp(-(c['slope']*np.log(p/(1-p))+c['intercept']))))
    assert np.array_equal(q,transform(p,c,'2023-08-01T00:00Z'))
    with pytest.raises(ValueError,match='cutoff'):transform(p,c,'2023-01-02T00:00Z')


def test_late_labels_duplicate_sources_and_unidentified_class_fail_before_fit():
    for mutation in ('late','duplicate','class','source'):
        rs=rows();source={'cohort':'a'*64}
        if mutation=='late':rs[0]['available_at']='2023-08-01T00:00Z'
        if mutation=='duplicate':rs.append(rs[0])
        if mutation=='class':
            for r in rs:r['label']=1
        if mutation=='source':source={}
        with pytest.raises(ValueError):fit(rs,'2023-08-01T00:00Z',source_hashes=source)


def test_probability_only_copy_keeps_flags_raw_values_and_input_immutable():
    s=dict(as_of='2023-08-01T00:00Z',trained_through='2022-06-01T00:00Z',rows=[dict(gameweek=1,id=1,p_play=.4,raw_p_play=.39,fixture_count=1,official_zero=False),dict(gameweek=1,id=2,p_play=0.,raw_p_play=0.,fixture_count=1,official_zero=True),dict(gameweek=1,id=3,p_play=0.,raw_p_play=0.,fixture_count=0,official_zero=False)])
    original=copy.deepcopy(s);r=apply(s,calibration());assert s==original and r['rows'][0]['p_play']!=.4
    assert r['rows'][1:]==s['rows'][1:] and r['rows'][0]['raw_p_play']==.39 and r['rows'][0]['uncalibrated_p_play']==.4
    bad=copy.deepcopy(s);bad['rows'][1]['p_play']=.1
    with pytest.raises(ValueError,match='Conflicting'):apply(bad,calibration())
