import hashlib,importlib.util,json,zipfile,stat
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('portable',Path(__file__).parents[1]/'tools/portable_handover.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def bundle(tmp_path,*,path='payload/model/value.json',body=b'{"safe":true}',bad_member_hash=False,extra=None):
    z=tmp_path/'private.zip';h=hashlib.sha256(body).hexdigest();manifest=dict(schema_version=1,original_workspace='/old/work',members=[dict(path=path,bytes=len(body),sha256='0'*64 if bad_member_hash else h)],approved_model=dict(path=path,sha256=h))
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as f:
        f.writestr('TRANSFER_MANIFEST.json',json.dumps(manifest));f.writestr(path,body)
        if extra:f.writestr(extra,b'x')
    return z,m.digest(z)


def test_verify_restore_preserves_bytes_and_creates_separate_path_map(tmp_path):
    z,h=bundle(tmp_path);assert len(m.verify(z,h)['members'])==1
    target=tmp_path/'new';paths=m.restore(z,h,target)
    assert (target/'payload/model/value.json').read_bytes()==b'{"safe":true}'
    assert m.resolve('/old/work/model/value.json',paths)==str(target/'payload/model/value.json')
    with pytest.raises(ValueError,match='outside'):m.resolve('/unknown/python',paths)
    with pytest.raises(ValueError,match='new destination'):m.restore(z,h,target)


@pytest.mark.parametrize('path',['../escape','/absolute','payload/CON','payload/a:bad','payload/a\\b','payload/../bad','payload/a*bad','payload/a?bad','payload/a|bad'])
def test_unsafe_paths_rejected_without_extraction(tmp_path,path):
    z,h=bundle(tmp_path,path=path)
    with pytest.raises(ValueError):m.restore(z,h,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_tampered_archive_member_and_unlisted_payload_rejected(tmp_path):
    z,h=bundle(tmp_path,bad_member_hash=True)
    with pytest.raises(ValueError,match='Member checksum'):m.verify(z,h)
    z,h=bundle(tmp_path,extra='payload/unlisted')
    with pytest.raises(ValueError,match='member mismatch'):m.verify(z,h)
    with pytest.raises(ValueError,match='Archive checksum'):m.verify(z,'0'*64)


def test_symlinks_and_case_collisions_rejected(tmp_path):
    z,h=bundle(tmp_path)
    with zipfile.ZipFile(z,'a') as f:
        i=zipfile.ZipInfo('payload/link');i.create_system=3;i.external_attr=(stat.S_IFLNK|0o777)<<16;f.writestr(i,'../../escape')
    with pytest.raises(ValueError,match='symlink'):m.verify(z,m.digest(z))
    z,h=bundle(tmp_path,extra='PAYLOAD/MODEL/VALUE.JSON')
    with pytest.raises(ValueError,match='case-colliding'):m.verify(z,h)
