import json
import pytest
from research_receipts import write_json


def test_active_directory_and_previous_directory_refusal(tmp_path):
    old = tmp_path/'handover-previous'
    active = tmp_path/'handover-active'
    old.mkdir()
    active.mkdir()
    original = old/'receipt.json'
    original.write_bytes(b'preserved')
    written = write_json(active, 'receipt.json', dict(ok=True))
    assert written == active/'receipt.json'
    assert json.loads(written.read_text()) == dict(ok=True)
    with pytest.raises(ValueError, match='active evidence'):
        write_json(active, original, dict(ok=False))
    with pytest.raises(ValueError):
        write_json(active, '../handover-previous/new.json', {})
    assert original.read_bytes() == b'preserved'
    assert not (old/'new.json').exists()
    with pytest.raises(FileExistsError):
        write_json(active, 'receipt.json', {})
