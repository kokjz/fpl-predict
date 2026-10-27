import hashlib,importlib.util,json,zipfile,stat,subprocess,sys
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


def test_sibling_checkout_resolves_source_and_private_paths_without_rewriting_evidence(tmp_path):
    parent=tmp_path/'fpl prediction model research';parent.mkdir()
    z,h=bundle(parent);original=z.read_bytes();target=parent/'private-workspace';source=parent/'fpl-predict'
    paths=m.restore(z,h,target,source_checkout=source)
    assert not source.exists()  # Restoration does not clone/create a second checkout.
    assert json.loads((target/'PORTABLE_PATHS.json').read_text())==paths
    assert m.resolve('/old/work/fpl-predict',paths)==str(source)
    assert m.resolve('/old/work/fpl-predict/tools/helper.py',paths)==str(source/'tools/helper.py')
    assert m.resolve('/old/work/model/value.json',paths)==str(target/'payload/model/value.json')
    assert m.resolve('/old/work/fpl-predict-private/value.json',paths)==str(target/'payload/fpl-predict-private/value.json')
    assert m.resolve('/old/work',paths)==str(target/'payload')
    assert (target/'payload/model/value.json').read_bytes()==b'{"safe":true}' and z.read_bytes()==original
    with pytest.raises(ValueError):m.resolve('/old/work/fpl-predict/../model/value.json',paths)
    with pytest.raises(ValueError,match='outside'):m.resolve('/old/work-other/fpl-predict/helper.py',paths)


def test_existing_sibling_checkout_and_legacy_path_maps_remain_usable(tmp_path):
    z,h=bundle(tmp_path);source=tmp_path/'fpl-predict';source.mkdir();marker=source/'existing.txt';marker.write_text('preserve')
    paths=m.restore(z,h,tmp_path/'private-workspace',source_checkout=source)
    assert marker.read_text()=='preserve'
    assert m.resolve('/old/work/fpl-predict/existing.txt',paths)==str(marker)
    default=m.restore(z,h,tmp_path/'default')
    assert m.resolve('/old/work/fpl-predict/src/main.py',default)==str(tmp_path/'default/payload/fpl-predict/src/main.py')
    del default['source_checkout']
    assert m.resolve('/old/work/fpl-predict/src/main.py',default)==str(tmp_path/'default/payload/fpl-predict/src/main.py')


def test_private_restore_cannot_be_placed_inside_selected_public_checkout(tmp_path):
    z,h=bundle(tmp_path);source=tmp_path/'future-public-checkout';target=source/'private-workspace'
    with pytest.raises(ValueError,match='outside checkout'):m.restore(z,h,target,source_checkout=source)
    assert not source.exists()


def test_source_checkout_rejects_existing_file(tmp_path):
    z,h=bundle(tmp_path);source=tmp_path/'file';source.write_text('preserve')
    with pytest.raises(ValueError,match='Source checkout'):m.restore(z,h,tmp_path/'private-workspace',source_checkout=source)
    assert source.read_text()=='preserve' and not (tmp_path/'private-workspace').exists()


def test_cli_restores_sibling_layout_with_spaces_and_resolves_actual_source(tmp_path):
    parent=tmp_path/'fpl prediction model research';parent.mkdir();z,h=bundle(parent)
    source=parent/'fpl-predict';target=parent/'private-workspace';tool=Path(m.__file__)
    result=subprocess.run([sys.executable,str(tool),'restore','--archive',str(z),'--sha256',h,
                           '--destination',str(target),'--source-checkout',str(source)],check=True,capture_output=True,text=True)
    assert json.loads(result.stdout)['status']=='restored'
    result=subprocess.run([sys.executable,str(tool),'resolve','--map',str(target/'PORTABLE_PATHS.json'),
                           '--path','/old/work/fpl-predict/tools/example.py'],check=True,capture_output=True,text=True)
    assert result.stdout.strip()==str(source/'tools/example.py')


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
