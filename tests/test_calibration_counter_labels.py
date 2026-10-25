import hashlib
import importlib.util
import json
from datetime import datetime,timedelta,timezone
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('calibrate_tool',Path(__file__).parents[1]/'tools/calibrate_appearance.py');tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)


def test_counter_labels_use_confirmed_next_snapshot_and_retain_exclusions(tmp_path):
    entries=[];weeks=[];start=datetime(2023,8,1,tzinfo=timezone.utc)
    for g in range(1,39):
        players=[dict(id=i,code=i+100,minutes=(g-1)*90 if i==1 else 100-g if i==4 else 0) for i in range(1,5)]
        events=[dict(id=w,finished=w<g,data_checked=w<g) for w in range(1,39)]
        if g==4:events[2]['data_checked']=False
        p=tmp_path/f'{g}.json';p.write_text(json.dumps(dict(elements=players,events=events)))
        clock=(start+timedelta(days=7*g)).isoformat();entries.append(dict(gameweek=g,captured_at=clock,file=p.name,compressed_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
        weeks.append(dict(gameweek=g,as_of=clock,rows=[dict(gameweek=g,id=i,p_play=0. if i in (2,3) else .5,fixture_count=0 if i==3 else 1,official_zero=i==2) for i in range(1,5)]))
    rows,audit=tool.counter_cohort('2023-24',entries,dict(weeks=weeks),tmp_path)
    assert len(rows)==36 and all(r['id']==1 and r['label']==1 and r['minute_increment']==90 for r in rows)
    assert audit['counts']['unconfirmed_origin_cells']==4 and audit['counts']['negative_revision']==36 and audit['counts']['official_zero']==36 and audit['counts']['zero_support']==36
    assert all(r['available_at']>r['as_of'] and r['gameweek']!=38 for r in rows)
    (tmp_path/'1.json').write_text('{}')
    with pytest.raises(ValueError,match='checksum'):tool.counter_cohort('2023-24',entries,dict(weeks=weeks),tmp_path)
