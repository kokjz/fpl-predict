import importlib.util
from pathlib import Path
import sys
from dataclasses import replace
import pytest
from season_engine import State
from horizon_forecast import Horizon
from test_season_engine import state,market,action


def module():
    s=importlib.util.spec_from_file_location('calendar_probe',Path(__file__).parents[1]/'tools/probe_chip_calendars.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def test_different_state_used_token_is_skipped_never_repaired():
    m=module();s=State('2025-26',12,tuple((i,50) for i in range(1,16)),100,2,(('freehit',2),))
    calendar={14:'freehit'};original=dict(calendar)
    assert 'already used' in m.compatible_schedule(s,17,calendar,[]) and calendar==original
    assert m.compatible_schedule(s,17,{14:'bboost'},[]) is None
    assert 'outside' in m.compatible_schedule(s,17,{18:'bboost'},[])


def test_expiry_season_inventory_and_consecutive_freehit():
    m=module();base=State('2025-26',19,tuple((i,50) for i in range(1,16)),100,2)
    assert m.compatible_schedule(base,20,{19:'3xc',20:'3xc'},[]) is None
    assert m.compatible_schedule(replace(base,season='2024-25'),20,{19:'3xc',20:'3xc'},[]) is not None
    assert 'consecutive' in m.compatible_schedule(base,20,{19:'freehit',20:'freehit'},[])
    assert m.compatible_schedule(base,20,{19:'bboost'},[('bboost',1)]) is not None


def test_remaining_resource_reserve_counts_tokens_once_and_expires():
    m=module();s=state(38);mk=market(38)
    h=Horizon.create(mk,[dict(gameweek=38,id=p['id'],expected_points=2.) for p in mk.players],trained_through='2025-05-01T00:00Z',feature_cutoff=mk.as_of,source_as_of=mk.as_of,model_id='synthetic')
    reserve,info=m.remaining_reserve(s,mk,h,[action()],[['3xc',20]])
    assert reserve==0 and not info['remaining_tokens'] and not info['coarse_schedule']


def test_probe_rejects_wrong_supplied_hash_before_reading_inputs(tmp_path):
    m=module();lock=tmp_path/'lock.json';lock.write_text('{}')
    with pytest.raises(ValueError,match='checksum'):
        m.run(tmp_path/'never-read.json',tmp_path/'reference',lock,lock,lock,tmp_path/'out',native_python='unused',solio_source=tmp_path,solio_site_packages=tmp_path,opening_lock_sha256='0'*64,source_lock_sha256='0'*64,protocol_sha256='0'*64)
    assert not (tmp_path/'out').exists()
