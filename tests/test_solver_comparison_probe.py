"""No-outcome controller, frozen-state identity, failure retention and paired pool."""
import importlib.util,json
from pathlib import Path
import pytest
from test_season_solver_probe import fixture as old_fixture,fake


def module():
    spec=importlib.util.spec_from_file_location('comparison',Path(__file__).parents[1]/'tools/probe_solver_comparison.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def inputs(tmp_path):
    old=old_fixture(tmp_path);m=module();reference=old['reference'];root=tmp_path/'reference'
    import shutil
    for seed in [20261024,20261025]:shutil.copytree(reference,root/f'{seed}_standingH6_adaptive/result/season')
    lock=json.loads(old['lock'].read_text());lock['inputs_sha256']=dict(decisions=m.digest(old['decisions']))
    lock['source_sha256']={str(Path('src')/n):sha for n,sha in lock['source_sha256'].items()}
    ids=json.loads(old['opening'].read_text());lock['openings']={str(seed):dict(ids=ids) for seed in [20261024,20261025]}
    old['lock'].write_text(json.dumps(lock))
    p=Path(__file__).parents[1]/'docs/solver_comparison_protocol_2026-10-24.json'
    return dict(decisions=old['decisions'],reference=root,lock=old['lock'],lock_sha256=m.digest(old['lock']),protocol=p,protocol_sha256=m.digest(p),output=tmp_path/'probe')


def test_twenty_paired_cases_need_no_outcomes_and_keep_same_pool(tmp_path,monkeypatch):
    m=module();a=inputs(tmp_path);calls=[];original=m.read_bundle
    def read(path):
        assert not any(s in Path(path).name for s in ['outcomes','settled'])
        return original(path)
    monkeypatch.setattr(m,'read_bundle',read)
    def solve(*args,**kwargs):calls.append(args[0].gameweek);return fake(*args,**kwargs)
    out=m.run(**a,solvers=dict(standing=solve,solio_adapted=solve))
    assert out['complete'] and len(out['cases'])==20 and len(calls)==20 and out['identity'].startswith('Injected')
    for first,second in zip(out['cases'][::2],out['cases'][1::2]):
        assert first['pool_sha256']==second['pool_sha256'] and first['objective']==second['objective']
    assert not out['policy_promotion'] and not out['model_promotion']


@pytest.mark.parametrize('kind',['lock','source','forecast'])
def test_changed_frozen_inputs_stop_before_solvers(tmp_path,kind):
    m=module();a=inputs(tmp_path)
    if kind=='lock':a['lock_sha256']='0'*64
    elif kind=='forecast':a['decisions'].write_text(a['decisions'].read_text()+' ')
    else:
        z=json.loads(a['lock'].read_text());z['source_sha256']['src/rolling_planner.py']='0'*64;a['lock'].write_text(json.dumps(z));a['lock_sha256']=m.digest(a['lock'])
    with pytest.raises(ValueError):m.run(**a,solvers=dict(standing=fake,solio_adapted=fake))
    assert not a['output'].exists()


@pytest.mark.parametrize('kind',['nan','bound'])
def test_invalid_solver_reply_is_fatal_and_retained(tmp_path,kind):
    m=module();a=inputs(tmp_path)
    def bad(*args,**kwargs):
        actions,report=fake(*args,**kwargs)
        if kind=='nan':report['objective']=float('nan')
        else:report['selected_plan_bound']['upper_objective']=-999.
        return actions,report
    with pytest.raises(ValueError):m.run(**a,solvers=dict(standing=bad,solio_adapted=fake))
    failure=json.loads((a['output']/'failure.json').read_text());assert failure['failed_attempt']['actions']
    if kind=='nan':assert failure['failed_attempt']['report']['objective']=={'nonfinite':'nan'}
    assert not (a['output']/'summary.json').exists()
