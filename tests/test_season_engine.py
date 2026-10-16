from dataclasses import replace
import copy
import datetime as dt
import pytest
from season_engine import State,Market,Action,prepare,settle,replay,rules_for


def roster():
    pos=[1]*2+[2]*5+[3]*5+[4]*3
    return [dict(id=i+1,position=p,team=f'T{i//3}',price_tenths=50,can_buy=True,expected_points=2.) for i,p in enumerate(pos)]


def market(gw,rows=None,season='2025-26'):
    day=dt.datetime(2025,8,1,12,tzinfo=dt.timezone.utc)+dt.timedelta(days=7*(gw-1))
    return Market.create(season,gw,day.isoformat(),(day-dt.timedelta(hours=1)).isoformat(),roster() if rows is None else rows)


def action(buys=(),sells=(),chip=None):
    return Action(tuple(buys),tuple(sells),(1,3,4,5,8,9,10,11,13,14,15),(6,7,12,2),1,3,chip)


def state(gw=2,ft=1,season='2025-26'):
    return State(season,gw,tuple((p['id'],50) for p in roster()),250,ft)


def outcomes(points=2.):
    return {i:dict(actual=points,minutes=90.,cards=0.) for i in range(1,16)}


def test_initial_squad_budget_and_ordinary_ft_banking():
    pre=prepare(State('2025-26'),market(1),action(range(1,16)));s,row=settle(pre,outcomes())
    assert s.bank==250 and s.free_transfers==1 and row['net_points']==24 and row['hits']==0
    for gw in range(2,9):s,_=settle(prepare(s,market(gw),action()),outcomes())
    assert s.free_transfers==5 and s.total_points==8*24


def test_freehit_reverts_original_ledger_and_cash_and_retains_ft():
    r=roster();r.append(dict(r[0],id=16,price_tenths=80));r[0]['price_tenths']=55
    a=replace(action((16,),(1,),'freehit'),starters=(16,*action().starters[1:]),captain=16)
    original=state(ft=3);p=prepare(original,market(2,r),a);o=outcomes();o[16]=dict(actual=10.,minutes=90.,cards=0.)
    s,row=settle(p,o)
    assert p.playing_bank==222 and row['net_points']==40 and s.bank==250 and s.holdings==original.holdings and s.free_transfers==3
    with pytest.raises(ValueError,match='already used'):prepare(replace(s,gameweek=3),market(3),action(chip='freehit'))
    with pytest.raises(ValueError,match='Consecutive'):prepare(replace(s,gameweek=20),market(20),action(chip='freehit'))


def test_wildcard_permanent_and_no_hits_ft_retained():
    r=roster();r.extend([dict(r[0],id=16,price_tenths=60),dict(r[2],id=17,price_tenths=70)])
    a=replace(action((16,17),(1,3),'wildcard'),starters=(16,17,*action().starters[2:]),captain=16,vice=17)
    s=prepare(state(ft=2),market(2,r),a).state
    assert dict(s.holdings)[16]==60 and dict(s.holdings)[17]==70 and 1 not in dict(s.holdings)
    assert s.bank==220 and s.free_transfers==2


def test_purchase_sales_half_profit_and_hits():
    r=roster();r[0]['price_tenths']=57;r.append(dict(r[0],id=16,price_tenths=55));r.append(dict(r[2],id=17,price_tenths=45))
    a=replace(action((16,17),(1,3)),starters=(16,17,*action().starters[2:]),captain=16,vice=17)
    p=prepare(state(),market(2,r),a)
    assert p.received==103 and p.spent==100 and p.hits==4 and p.state.bank==253 and p.state.free_transfers==1


def test_bb_counts_all_once_tc_negative_and_vice_fallback():
    o=outcomes();o[1]=dict(actual=0.,minutes=0.,cards=0.)
    bb,row=settle(prepare(state(),market(2),action(chip='bboost')),o)
    assert row['net_points']==30 and row['autosub_delta']==0 and row['bench_boost_points']==8
    _,row=settle(prepare(state(),market(2),action(chip='3xc')),o);assert row['net_points']==26 and row['extra_captain_bonus']==2
    o[1]=dict(actual=-2.,minutes=90.,cards=0.)
    _,row=settle(prepare(state(),market(2),action(chip='3xc')),o);assert row['net_points']==14


def test_chips_windows_expiry_exclusivity_and_opening_rules():
    for chip in ['freehit','wildcard']:
        with pytest.raises(ValueError,match='unavailable'):prepare(State('2025-26'),market(1),action(range(1,16),chip=chip))
    p=prepare(state(19),market(19),action(chip='3xc'));s,_=settle(p,outcomes())
    assert prepare(s,market(20),action(chip='3xc')).state.used_chips==( ('3xc',1),('3xc',20) )
    with pytest.raises(ValueError):prepare(state(),market(2),action(chip='bboost+3xc'))


def test_afcon_topup_applies_before_policy_and_season_specific():
    seen=[]
    def policy(s,m):seen.append(s.free_transfers);return action()
    s,_,_=replay([market(16)],{16:outcomes()},policy,state(16,ft=1),require_full_season=False)
    assert seen==[5] and s.free_transfers==5
    assert prepare(state(16,season='2026-27'),market(16,season='2026-27'),action()).state.free_transfers==2


def test_missing_quotes_unknown_outcomes_and_invalid_actions_fail():
    with pytest.raises(ValueError,match='held-player'):prepare(state(),market(2,roster()[1:]),action())
    with pytest.raises(ValueError,match='Unknown outcome'):settle(prepare(state(),market(2),action()),{})
    r=roster();r.append(dict(r[0],id=16,price_tenths=999))
    with pytest.raises(ValueError,match='funds'):prepare(state(),market(2,r),replace(action((16,),(1,)),starters=(16,*action().starters[1:]),captain=16))
    with pytest.raises(ValueError,match='round trips'):prepare(state(),market(2),action((1,),(1,)))
    r=roster();r[0]['actual']=20
    with pytest.raises(ValueError,match='outcome'):market(2,r)


def test_club_transfer_overlimit_hold_allowed_next_transfer_repairs():
    r=roster();r[3]['team']='T0' # four current players from one club
    prepare(state(),market(2,r),action())
    r.append(dict(r[4],id=16))
    with pytest.raises(ValueError,match='Club limit'):prepare(state(),market(2,r),replace(action((16,),(5,)),starters=(1,3,4,16,*action().starters[4:])))
    r.append(dict(r[3],id=17,team='NEW'))
    prepare(state(),market(2,r),replace(action((17,),(4,)),starters=(1,3,17,*action().starters[3:])))


def test_full38knownanswer_replay_chips_and_hidden_future_mutation():
    markets=[market(gw) for gw in range(1,39)];hidden={gw:outcomes() for gw in range(1,39)};seen=[]
    chips={2:'wildcard',3:'bboost',4:'3xc',5:'freehit',20:'wildcard',21:'bboost',22:'3xc',23:'freehit'}
    def policy(s,m):seen.append((s.gameweek,s.holdings));return action(range(1,16) if s.gameweek==1 else (),chip=chips.get(s.gameweek))
    s,rows,actions=replay(markets,hidden,policy)
    assert len(rows)==38 and s.gameweek==39 and len(s.used_chips)==8 and s.total_points==38*24+2*8+2*2
    changed=copy.deepcopy(hidden);changed[38]=outcomes(100.)
    _,_,again=replay(markets,changed,policy)
    assert actions==again
    with pytest.raises(ValueError,match='exactly38'):replay(markets[:-1],hidden,policy)


def test_market_timing_duplicate_roster_and_state_mutability_fail():
    with pytest.raises(ValueError,match='predeadline'):Market.create('2025-26',1,'2025-01-01T12:00Z','2025-01-01T12:00Z',roster())
    with pytest.raises(ValueError,match='roster'):market(1,roster()+[roster()[0]])
    with pytest.raises(ValueError):State('2025-26',2,())
    with pytest.raises(ValueError):State('2025-26',2,tuple([(1,50)]*15))
    with pytest.raises(TypeError):market(1).players[0]['price_tenths']=1


def test_bootstrap_active_vs_future_override_and_config_mismatch():
    from season_engine import audit_bootstrap
    r=rules_for('2025-26')
    b=dict(game_settings=dict(squad_squadplay=11,squad_squadsize=15,squad_team_limit=3,squad_total_spend=1000,transfers_cap=20,transfers_sell_on_fee=.5,max_extra_free_transfers=4),chips=[dict(name=w['name'],start_event=w['start'],stop_event=w['stop'],number=1,overrides={}) for w in r['chip_windows']])
    assert audit_bootstrap(b,'2025-26',1)['active_rules_compatible']
    chip=next(c for c in b['chips'] if c['name']=='freehit' and c['start_event']==20);chip['overrides']={'rules':{'squad_squadsize':16}}
    early=audit_bootstrap(b,'2025-26',1);assert early['active_rules_compatible'] and not early['full_future_chip_configuration_supported']
    assert not audit_bootstrap(b,'2025-26',20)['active_rules_compatible']
    b['game_settings']['max_extra_free_transfers']=1
    assert 'max_extra_free_transfers' in audit_bootstrap(b,'2025-26',1)['mismatches']


def test_initial_capital_cannot_be_forged():
    with pytest.raises(ValueError,match='initial capital'):prepare(State('2025-26',bank=1500),market(1),action(range(1,16)))


def test_card_only_player_blocks_autosub_but_not_vice_captain():
    o=outcomes();o[1]=dict(actual=-1.,minutes=0.,cards=1.)
    _,r=settle(prepare(state(),market(2),action(chip='3xc')),o)
    assert r['autosub_delta']==0 and r['net_points']==23 and r['scoring_captain']==3


def test_dgw_totals_and_blank_legality_are_preserved():
    o=outcomes();o[1]=dict(actual=10.,minutes=180.,cards=0.)
    _,r=settle(prepare(state(),market(2),action(chip='3xc')),o);assert r['net_points']==50
    o={i:dict(actual=0.,minutes=0.,cards=0.) for i in o}
    _,r=settle(prepare(state(),market(2),action()),o);assert r['net_points']==0


def test_full_replay_cli_hashes_and_write_once(tmp_path,monkeypatch):
    import hashlib,json,sys
    from dataclasses import asdict
    from season_engine import main
    inputs=dict(markets=dict(schema_version=1,weeks=[dict(season='2025-26',gameweek=gw,deadline=market(gw).deadline,as_of=market(gw).as_of,rows=roster()) for gw in range(1,39)]),
     actions=dict(schema_version=1,weeks=[dict(gameweek=gw,**asdict(action(range(1,16) if gw==1 else ()))) for gw in range(1,39)]),
     outcomes=dict(schema_version=1,weeks=[dict(gameweek=gw,players=[dict(id=i,**v) for i,v in outcomes().items()]) for gw in range(1,39)]))
    argv=['season-replay']
    for name,obj in inputs.items():
        p=tmp_path/(name+'.json');p.write_text(json.dumps(obj));argv.extend(['--'+name,str(p),'--'+name+'-sha256',hashlib.sha256(p.read_bytes()).hexdigest()])
    out=tmp_path/'new';argv.extend(['--output',str(out)]);monkeypatch.setattr(sys,'argv',argv);main()
    r=json.loads((out/'report.json').read_text());assert r['final_state']['total_points']==38*24 and len(r['rows'])==38
    with pytest.raises(SystemExit):main()
