import numpy as np
import pandas as pd
import pytest
from news_availability_probe import FORM,prepare_frame,run,train_features,validate


def data():
    rows=[]
    for gw in (4,5,19,20,27,28,29,38):
        for i in range(12):
            row={k:float(i%3) for k in FORM}
            row.update(season='2025-26',gameweek=gw,fpl_code=i+1,deadline='2026-05-01T10:00Z',
                published_at='2026-05-01T09:00Z',candidate=True,actual_minutes=90. if i%3 else 0.,
                news='available for selection' if i%3 else 'injury doubt',chance_label=100 if i%3 else 25)
            rows.append(row)
    return pd.DataFrame(rows)


def test_chronological_probe_keeps_all_arms_and_never_promotes():
    report,pred=run(data())
    assert set(report['arms'])=={'form','form_chance','form_text','form_chance_text'}
    assert report['test_rows']==36 and report['declared_primary']['gameweeks']==3
    assert not report['model_promotion'] and not report['points_or_squad_gain_measured']
    assert np.isfinite(pred[list(report['arms'])]).all().all()


def test_vocab_and_scaling_never_fit_test_values():
    d=data();train=d[d.gameweek.le(19)];test=d[d.gameweek.ge(28)].copy()
    test['news']='unseenfuturetoken';test[FORM]=999
    (a,b),meta=train_features(train,[train,test])
    (aa,_),other=train_features(train,[train,data()[data().gameweek.ge(28)]])
    assert meta==other and (a['form_text']!=aa['form_text']).nnz==0
    assert b['form_text'].shape[1]==a['form_text'].shape[1]


@pytest.mark.parametrize('kind',['late','duplicate','nan','chance','scope'])
def test_probe_rejects_bad_source_or_rows(kind):
    d=data()
    if kind=='late':d.loc[0,'published_at']=d.loc[0,'deadline']
    if kind=='duplicate':d=pd.concat([d,d.iloc[:1]])
    if kind=='nan':d.loc[0,'last_minutes']=np.nan
    if kind=='chance':d.loc[0,'chance_label']=101
    if kind=='scope':d.loc[0,'season']='2024-25'
    with pytest.raises(ValueError):validate(d)


def test_prepare_excludes_future_and_same_gw_outcomes_from_features():
    rows=[dict(season='2025-26',gameweek=gw,fixture=gw,fpl_code=1,position=3,minutes=mins,ts=stamp)
          for gw,mins,stamp in [(1,90,'2025-08-01T12:00Z'),(4,0,'2025-09-13T12:00Z'),(5,90,'2025-09-20T12:00Z')]]
    p=pd.DataFrame(rows);obs=pd.DataFrame([dict(gameweek=4,fpl_code=1,position=3,available_by='2025-09-13T09:00Z',
        deadline='2025-09-13T10:00Z',news='injury doubt',chance_label=25)])
    a,coverage=prepare_frame(p,obs);p.loc[p.gameweek.ge(4),'minutes']=777
    b,_=prepare_frame(p,obs)
    assert a[FORM].equals(b[FORM]) and a.last_minutes.iloc[0]==90
    assert not a.candidate.iloc[0] and coverage[0]['admitted']==1
