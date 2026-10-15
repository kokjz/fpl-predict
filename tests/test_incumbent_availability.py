import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fpl_model import CORE_FEATURES
from incumbent_availability import (POLICY,SIGNALS,augment,block_difference,equal_coverage,
                                    fit_head,gate,source_observations)


def inputs():
    d=pd.DataFrame([dict(season=s,GW=g,element=i+1,fixture=g,pos=3,
        cutoff=pd.Timestamp('2026-01-01T10:00Z')+pd.Timedelta(days=g*7),
        ts=pd.Timestamp('2026-01-01T12:00Z')+pd.Timedelta(days=g*7),
        minutes=90 if i%3 else 0,played=float(i%3!=0))
        for s in ['2024-25','2025-26'] for g in range(1,39) for i in range(20)])
    x=pd.DataFrame(1.,index=d.index,columns=CORE_FEATURES);x['n_history']=5.;x['last5_minutes']=70.
    b=pd.DataFrame(dict(id=range(1,21),code=range(101,121)))
    o=pd.DataFrame([dict(gameweek=g,fpl_code=i+101,source_position=3,
        published_at=(pd.Timestamp('2026-01-01T09:00Z')+pd.Timedelta(days=g*7)).isoformat(),
        source_deadline=(pd.Timestamp('2026-01-01T10:00Z')+pd.Timedelta(days=g*7)).isoformat(),
        chance_label=100 if i%3 else 0) for g in range(4,39) for i in range(20)])
    return d,x,b,o


def test_augmentation_retains_all_rows_and_explicit_unknowns():
    d,x,b,o=inputs();z,coverage=augment(d,x,b,o)
    assert len(z)==len(d) and z.index.equals(x.index) and z[CORE_FEATURES].equals(x)
    assert z.loc[d.season.eq('2024-25'),SIGNALS].eq([0.,1.]).all().all()
    assert z.loc[d.season.eq('2025-26')&d.GW.ge(4),'availability_missing'].eq(0).all()
    assert sum(r['rows'] for r in coverage)==len(d)
    assert (z.availability_chance.eq(0)&z.availability_missing.eq(0)).any()
    assert (z.availability_chance.eq(0)&z.availability_missing.eq(1)).any()


@pytest.mark.parametrize('kind',['late','position','duplicate','chance','bridge','index'])
def test_join_rejects_integrity_failures(kind):
    d,x,b,o=inputs()
    if kind=='late':o.loc[0,'published_at']=o.loc[0,'source_deadline']
    if kind=='position':o.loc[0,'source_position']=2
    if kind=='duplicate':o=pd.concat([o,o.iloc[:1]])
    if kind=='chance':o.loc[0,'chance_label']=101
    if kind=='bridge':b=b.iloc[1:]
    if kind=='index':x=x.iloc[::-1]
    with pytest.raises(ValueError):augment(d,x,b,o)


def test_fixed_head_is_outcome_safe_and_never_promotes():
    d,x,b,o=inputs();z,_=augment(d,x,b,o);report,p=fit_head(d,z)
    assert not report['model_promotion'] and not report['points_gain_measured']
    assert report['training_rows']==1140
    changed=d.copy();changed.loc[changed.season.eq('2025-26')&changed.GW.ge(20),'played']=1.
    _,q=fit_head(changed,z)
    assert np.array_equal(p[['control','structured']].values,q[['control','structured']].values)
    assert report['evaluation']['validation']['metrics']['structured']['candidates']['brier']<.01


def test_source_requires_complete_scope_before_reading_archive(tmp_path):
    proof=tmp_path/'proof.json';proof.write_text(json.dumps({'records':[{'gameweek':4}]}))
    with pytest.raises(ValueError,match='exactly one'):source_observations(tmp_path/'absent',proof)


def test_equal_coverage_is_exact():
    f=pd.DataFrame(dict(GW=[28]*4,element=[4,2,3,1],fixture=[1]*4,candidate=[True]*4,
                        control=[.9,.9,.7,.6],structured=[.5,.5,.8,.9],played=[1,0,1,1]))
    r=equal_coverage(f)
    assert r['n']==2 and r['control_misses']==1 and r['structured_misses']==0


def test_gate_requires_all_guards():
    m={'control':{'candidates':{'brier':.1},'all':{'brier':.1}},
       'structured':{'candidates':{'brier':.09},'all':{'brier':.09}}}
    assert gate(m,{'block4_interval':[-.02,-.001]})['passed']
    assert not gate(m,{'block4_interval':[-.02,.001]})['passed']
    m['structured']['all']['brier']=.11
    assert not gate(m,{'block4_interval':[-.02,-.001]})['passed']


def test_blocks_reject_missing_candidate_weeks():
    f=pd.DataFrame(dict(GW=[28,29,31,32],candidate=[True]*4,played=[1.]*4,control=[.8]*4,structured=[.9]*4))
    with pytest.raises(ValueError,match='contiguous'):block_difference(f)


def test_bundled_protocol_matches_implementation():
    p=Path(__file__).parents[1]/'src/fpl_predict_resources/incumbent_availability_protocol.json'
    assert json.loads(p.read_text())==POLICY
