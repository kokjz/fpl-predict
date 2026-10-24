import copy
import hashlib
import pytest
from approved_decision import project_decision_approved
from approved_horizon import project_approved
from test_approved_horizon import setup, review


def test_opt_in_mean_identity_and_saved_artifact_unchanged(tmp_path,monkeypatch):
    root,history,m,f,k=setup(tmp_path,monkeypatch)
    artifact=root/'artifact.joblib';before=hashlib.sha256(artifact.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match='opt-in'):project_decision_approved(root,history,m,f,**k)
    h,a,r=project_decision_approved(root,history,m,f,**k,allow_research_policy=True)
    old,_=project_approved(root,history,m,f,**k)
    assert h.values()==old.values() and r['appearance']['mean_reproduction_max_abs_error']==0
    assert hashlib.sha256(artifact.read_bytes()).hexdigest()==before==a['model_sha256']
    assert r['forecaster_weights_unchanged'] and not r['production_policy_approved']
    assert len(a['decision_sha256'])==len(a['calendar_sha256'])==64


def test_manual_absence_stays_zero_only_in_current_gameweek(tmp_path,monkeypatch):
    root,history,m,f,k=setup(tmp_path,monkeypatch);extra=review(m)
    extra['review']['players'][0]['minutes']=0
    h,a,r=project_decision_approved(root,history,m,f,**k,**extra,allow_research_policy=True)
    probabilities={(v['gameweek'],v['id']):v['p_play'] for v in a['rows']}
    assert h.values()[30,1]==probabilities[30,1]==0
    assert h.values()[32,1]==6.4 and probabilities[32,1]>0
    assert probabilities[31,1]==0


def test_fractional_manual_sensitivity_matches_original_bridge(tmp_path,monkeypatch):
    root,history,m,f,k=setup(tmp_path,monkeypatch);extra=review(m)
    h,a,r=project_decision_approved(root,history,m,f,**k,**extra,allow_research_policy=True)
    old,_=project_approved(root,history,m,f,**k,**extra)
    assert h.values()==old.values() and h.values()[30,1]==pytest.approx(.8)


def test_invalid_receipt_fails_before_appearance_loading(tmp_path,monkeypatch):
    root,history,m,f,k=setup(tmp_path,monkeypatch);k['receipt_sha256']='0'*64
    with pytest.raises(ValueError,match='receipt hash'):
        project_decision_approved(root,history,m,f,**k,allow_research_policy=True)
