import json
from pathlib import Path
import pytest
from incumbent_availability_points import POLICY,run
from experiment_runner import file_hash


def test_points_extension_rejects_unqualified_or_mismatched_heads(tmp_path):
    manifest=tmp_path/'manifest.json';manifest.write_text('{}')
    hp=tmp_path/'pred.csv';hp.write_text('control,structured\n.9,.8\n')
    head=tmp_path/'head.json';head.write_text(json.dumps(dict(integration_eligible=False)))
    with pytest.raises(ValueError,match='eligible'):
        run(manifest,file_hash(manifest),head,file_hash(head),hp,file_hash(hp),tmp_path/'new')
    assert not (tmp_path/'new').exists()
    with pytest.raises(ValueError,match='checksum'):
        run(manifest,'0'*64,head,file_hash(head),hp,file_hash(hp),tmp_path/'new')


def test_points_protocol_keeps_unconditional_semantics_and_no_promotion():
    p=Path(__file__).parents[1]/'src/fpl_predict_resources/incumbent_availability_points_protocol.json'
    assert json.loads(p.read_text())==POLICY
    assert not POLICY['promotion'] and 'never multiply' in POLICY['interpretation']
