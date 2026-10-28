import copy
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

import market_stage_c as stage
import market_stage_c_amendment as amended
from panel_diagnostic import panel_hash
from test_panel_diagnostic import panels
from test_market_stage_c import bundle


def tool():
    path=Path(__file__).resolve().parents[1]/'tools/run_market_stage_c_amended.py'
    spec=importlib.util.spec_from_file_location('amended_stage_c_worker',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


def test_original_fixture_hash_is_checked_before_comparison(monkeypatch):
    p=panels()
    monkeypatch.setattr(amended,'compare_panels',lambda *a,**k:pytest.fail('Hash must fail first'))
    with pytest.raises(amended.FixtureGuardError,match='hash differs') as error:
        amended.original_fixture(p,copy.deepcopy(p),'0'*64)
    assert error.value.receipt['reason']=='original_fixture_hash'


def test_class_a_returns_original_object_not_regenerated():
    original=panels();regenerated=copy.deepcopy(original)
    regenerated['2022-23']['squads'][0][0]['weight']=np.nextafter(2.,3.)
    fixture,receipt=amended.original_fixture(original,regenerated,panel_hash(original))
    assert fixture is original and fixture is not regenerated
    assert receipt['comparison']['classification']=='A' and receipt['status']=='accepted'
    assert fixture['2022-23']['squads'][0][0]['weight']==2.


def test_class_b_blocks_before_market_or_fit_and_preserves_receipt(tmp_path,monkeypatch):
    m=tool();original=panels();regenerated=copy.deepcopy(original)
    regenerated['2022-23']['squads'][0][0]['price_tenths']=46.
    calls=[];cfg={'references':{'original_i4_panel_canonical_sha256':panel_hash(original)}}
    monkeypatch.setattr(m,'amendment',lambda:cfg);monkeypatch.setattr(m,'legacy_runtime',lambda:{})
    monkeypatch.setattr(m.strict,'protocol',lambda:{})
    monkeypatch.setattr(m,'load_original',lambda *a:({'panels':original},{},'synthetic',0,{}))
    monkeypatch.setattr(m.strict.i4,'load',lambda e:(None,None,object()))
    monkeypatch.setattr(m.strict.i4,'panels',lambda c:calls.append('panels') or regenerated)
    monkeypatch.setattr(m.strict,'market_rows',lambda *a:pytest.fail('No market rows after B'))
    monkeypatch.setattr(m.strict,'fit',lambda *a:pytest.fail('No fit after B'))
    with pytest.raises(amended.FixtureGuardError,match='not class A'):m.build({},tmp_path)
    assert calls==['panels'] and not (tmp_path/'bundle.npz').exists()
    receipt=json.loads((tmp_path/'panel-consistency.json').read_text())
    assert receipt['status']=='blocked' and receipt['comparison']['classification']=='B'


def test_both_methods_replay_same_original_squad_object(monkeypatch):
    original=panels();regenerated=copy.deepcopy(original)
    regenerated['2022-23']['squads'][0][0]['weight']=np.nextafter(2.,3.)
    fixture,_=amended.original_fixture(original,regenerated,panel_hash(original));seen=[]
    def replay(frame,panel,methods):
        assert methods==stage.METHODS
        squad=panel['squads'][0]
        assert any(squad is s for fold in original.values() for s in fold['squads'])
        assert not any(squad is s for fold in regenerated.values() for s in fold['squads'])
        seen.append(squad)
        return {method:dict(mean_total=100.) for method in methods}
    monkeypatch.setattr(stage.i4,'replay',replay)
    predictions={(f,m):np.arange(8,dtype=float)+.1 for f in stage.FOLDS for m in stage.METHODS}
    stage.analyse(bundle(),predictions,fixture)
    assert len(seen)==4  # Two original squads per fold, shared by both methods.


def test_pool_minmax_extension_keeps_exact_original_mean_and_report_bytes(tmp_path,monkeypatch):
    m=tool();fits=tmp_path/'fits';output=tmp_path/'output';output.mkdir()
    order=[dict(fold=f,method=a) for f in stage.FOLDS for a in stage.METHODS];ctx={'synthetic':'same fixture'}
    for job in order:
        p=fits/(job['fold']+'_'+job['method']);p.mkdir(parents=True);m.strict.write_json(p/'amendment-context.json',ctx)
    monkeypatch.setattr(m,'context',lambda p:ctx)
    monkeypatch.setattr(m.strict,'protocol',lambda:{'fit_order':order})
    original_report={'pooled_fixed_squad_delta':.15000000000000002,'points':{
        '2022-23':{'market_strength':{'deltas':[.1]*20}},'2023-24':{'market_strength':{'deltas':[.2]*20}}}}
    saved=[]
    def aggregate(*args):
        m.strict.write_json(output/'report.json',original_report);saved.append((output/'report.json').read_bytes())
    monkeypatch.setattr(m.strict,'aggregate',aggregate)
    m.aggregate(tmp_path/'build',fits,output)
    ext=json.loads((output/'summary-extension.json').read_text())
    assert (output/'report.json').read_bytes()==saved[0]
    assert ext['pooled_fixed_squad_delta']==dict(mean=.15000000000000002,minimum=.1,maximum=.2,panels=40,
        mean_definition='unchanged I4 mean of two20-panel fold means; min/max over40 panel deltas')


def test_amendment_checks_unchanged_strict_and_numeric_paths():
    m=tool();cfg=m.amendment()
    assert cfg['references']['strict_stage_c_tool_lf_sha256']=='f62fff4dff9f5b9cbd1715137385b4dcd2f8ebbd0dec5b5550af483afd62802b'
