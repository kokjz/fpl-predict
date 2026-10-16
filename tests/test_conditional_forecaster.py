import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest
from conditional_forecaster import fit,missing_availability,current_availability,predict_current
from test_conditional_integration import frames


def data():
    d,x,_=frames();d['sixty']=(d.minutes>=60).astype(float)
    return d,missing_availability(x)


def test_reload_and_future_outcome_mutation(tmp_path):
    d,x=data();train=~(d.season.eq('2025-26')&d.GW.ge(20));a=fit(d,x,train);future=~train;p=a.predict(x[future],d.loc[future,'pos'])
    d.loc[future,['points_core','total_points','minutes','played','sixty','dc_hit']]=[99,101,90,1,1,1]
    b=fit(d,x,train);pd.testing.assert_frame_equal(p,b.predict(x[future],d.loc[future,'pos']))
    f=tmp_path/'candidate.joblib';joblib.dump(a,f);pd.testing.assert_frame_equal(p,joblib.load(f).predict(x[future],d.loc[future,'pos']))
    assert np.allclose(p.expected_points,p.core_xp+p.dc_xp)
    assert (p.dc_xp<=2*p.p_play).all() and (p.p60<=p.p_play).all() and (p.expected_minutes<=90*p.p_play+1e-9).all()


def bootstrap():
    return dict(events=[dict(id=7,is_next=True,deadline_time='2026-10-20T10:00Z')],elements=[dict(id=5,element_type=3,chance_of_playing_next_round=25)])


def rows():
    t=pd.DataFrame(dict(element=[5,5],pos=[3,3],GW=[7,8],cutoff=['2026-10-19T10:00Z']*2),index=[10,20])
    return pd.DataFrame(index=t.index),t


def test_current_labels_scope_missingness_and_identity():
    x,t=rows();a,r=current_availability(x,t,bootstrap(),'2026-10-19T10:00Z')
    assert a.availability_chance.tolist()==[.25,0.] and a.availability_missing.tolist()==[0.,1.]
    assert r['known_label_fixture_rows']==1
    b=bootstrap();b['elements'][0]['chance_of_playing_next_round']=None
    assert current_availability(x,t,b,'2026-10-19T10:00Z')[0].availability_missing.eq(1).all()


@pytest.mark.parametrize('mutation,error',[('late','predeadline'),('duplicate','Duplicate'),('identity','Unknown'),('position','position'),('chance','chance'),('clock','clocks')])
def test_source_errors_fail_closed(mutation,error):
    x,t=rows();b=bootstrap();stamp='2026-10-19T10:00Z'
    if mutation=='late':stamp='2026-10-20T10:00Z'
    if mutation=='duplicate':b['elements']*=2
    if mutation=='identity':t.loc[10,'element']=9
    if mutation=='position':t.loc[10,'pos']=4
    if mutation=='chance':b['elements'][0]['chance_of_playing_next_round']=float('inf')
    if mutation=='clock':t.loc[10,'cutoff']='2026-10-18T10:00Z'
    with pytest.raises(ValueError,match=error):current_availability(x,t,b,stamp)


def test_legacy_predictor_unchanged():
    class Legacy:
        def predict(self,x,pos):return x.copy()
    x,t=rows();got,report=predict_current(Legacy(),x,t.pos,t,{},'invalid')
    pd.testing.assert_frame_equal(x,got);assert report is None


def test_bad_encoding_or_missing_columns_fail():
    d,x=data();m=fit(d,x,pd.Series(True,index=d.index))
    with pytest.raises(ValueError,match='features'):m.predict(x.drop(columns='availability_chance'),d.pos)
    x.loc[x.index[0],'availability_chance']=.5
    with pytest.raises(ValueError,match='encoding'):m.predict(x,d.pos)


def test_policy_keeps_gates_and_single_candidate():
    p=Path(__file__).parents[1]/'src/fpl_predict_resources/forecaster_qualification_protocol.json';s=json.loads(p.read_text())
    assert s['development']['test_seasons']==['2022-23','2023-24'] and 'REQUIRED_GATES' in s['promotion']
