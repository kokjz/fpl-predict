import copy
import hashlib
from dataclasses import asdict
import pytest
from native_solver_worker import read_json,verified_sources,patched_tree,validate_request,RESOURCES
from test_rolling_planner import setup


def request(gw=18,H=4):
    s,m,h=setup(gw=gw,H=H);state=asdict(s);state.pop('total_points')
    q=dict(schema_version=1,market=dict(season=m.season,gameweek=m.gameweek,deadline=m.deadline,as_of=m.as_of,rows=[dict(p) for p in m.players]),state=state,xp=[[g,i,v] for (g,i),v in h.values().items()],through=gw+H-1,chip_schedule={},opening_ids=None,seconds=.5)
    return q


def test_source_hashes_and_path_boundary_checked_before_any_execution(tmp_path):
    root=tmp_path/'source';root.mkdir();p=root/'code.py';p.write_text("raise AssertionError('must never execute')")
    expected={'code.py':hashlib.sha256(p.read_bytes()).hexdigest()}
    assert verified_sources(root,expected)['code.py'].startswith('raise')
    p.write_text('changed')
    with pytest.raises(ValueError,match='checksum'):verified_sources(root,expected)
    outside=tmp_path/'outside.py';outside.write_text('other');(root/'link.py').symlink_to(outside)
    with pytest.raises(ValueError,match='escapes'):verified_sources(root,{'link.py':hashlib.sha256(outside.read_bytes()).hexdigest()})


def test_ast_patch_inserts_reset_and_fh_callback_without_replacing_other_constraints():
    source='''
def solve(data, fts, transfer_count, use_wc, use_fh, m):
    players=[];gws=[14,15];buy_price={};sell_price={};price_modified_players=[]
    squad={};squad_fh={};in_the_bank={};transfer_out_first={};fh_sell_price={}
    raw_gw_ft={w:fts[w]-transfer_count[w]+1-use_wc[w]-use_fh[w] for w in gws}
    m.addConstrs([fh_sell_price[p]*squad[p,w-1]+in_the_bank[w-1]>=fh_sell_price[p]*squad_fh[p,w] for p in players for w in gws])
    m.addConstrs(['unchanged'])
    return raw_gw_ft
'''
    calls=[]
    class Model:
        def addConstrs(self,rows):calls.append(rows)
    tree,digest=patched_tree(source);namespace={'native_fh_budget':lambda *a:calls.append('correct-fh-budget')};exec(compile(tree,'synthetic','exec'),namespace)
    result=namespace['solve']({'free_transfer_resets':{16:5}},{14:2,15:1},{14:1,15:1},{14:0,15:0},{14:0,15:0},Model())
    assert result=={14:2,15:5} and calls==['correct-fh-budget',['unchanged']] and len(digest)==64
    with pytest.raises(ValueError,match='structure'):patched_tree('x=1')


def test_request_rejects_hidden_outcomes_future_clocks_and_missing_duplicate_forecasts():
    recipe=read_json((RESOURCES/'native_solver_recipe.json').read_bytes());q=request();validate_request(q,recipe)
    bad=copy.deepcopy(q);bad['market']['rows'][0]['actual']=10.
    with pytest.raises(ValueError,match='outcome'):validate_request(bad,recipe)
    bad=copy.deepcopy(q);bad['market']['as_of']=bad['market']['deadline']
    with pytest.raises(ValueError,match='precede'):validate_request(bad,recipe)
    bad=copy.deepcopy(q);bad['xp'].pop()
    with pytest.raises(ValueError,match='Incomplete'):validate_request(bad,recipe)
    bad=copy.deepcopy(q);bad['xp'].append(bad['xp'][0])
    with pytest.raises(ValueError,match='cells'):validate_request(bad,recipe)


def test_chip_profile_accepts_two_windows_but_rejects_consecutive_fh_or_used_token():
    recipe=read_json((RESOURCES/'native_solver_recipe.json').read_bytes());q=request();q['chip_schedule']={'19':'3xc','20':'3xc'};validate_request(q,recipe)
    q['chip_schedule']={'19':'freehit','20':'freehit'}
    with pytest.raises(ValueError,match='Consecutive'):validate_request(q,recipe)
    q['chip_schedule']={'19':'3xc'};q['state']['used_chips']=[['3xc',1]]
    with pytest.raises(ValueError,match='Illegal'):validate_request(q,recipe)
    with pytest.raises(ValueError,match='Duplicate'):read_json('{"a":1,"a":2}')
    with pytest.raises(ValueError,match='Nonfinite'):read_json('{"a":NaN}')
