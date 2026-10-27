"""Verify/restore a user-transferred private checkpoint without executing it.

Archives and extracted contents stay outside this public source checkout. A
trusted separately supplied archive SHA256 is required. Never uploads anything.
Original evidence bytes are preserved; path maps are separate derived metadata.
"""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import re
import shutil
import stat
import tempfile
import zipfile

MAX_ARCHIVE=350*1024**2
MAX_EXPANDED=1536*1024**2
MAX_MEMBERS=50000
MAX_MANIFEST=12*1024**2
ROOT=Path(__file__).resolve().parents[1]


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def name(value):
    p=PurePosixPath(value)
    if not value or '\\' in value or p.is_absolute() or '..' in p.parts or str(p)!=value or any(re.search(r'[<>:"|?*\x00-\x1f]',x) or x.endswith((' ','.')) or re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?',x) for x in p.parts):raise ValueError('Unsafe/nonportable archive path')
    return value


def read_manifest(z):
    infos=z.infolist()
    if not infos or len(infos)>MAX_MEMBERS or sum(i.file_size for i in infos)>MAX_EXPANDED:raise ValueError('Archive size/member limit')
    names=set();folded=set()
    for i in infos:
        n=name(i.filename)
        if n in names or n.casefold() in folded or i.is_dir() or stat.S_ISLNK(i.external_attr>>16):raise ValueError('Duplicate/case-colliding/directory/symlink member')
        names.add(n);folded.add(n.casefold())
    info=z.getinfo('TRANSFER_MANIFEST.json')
    if info.file_size>MAX_MANIFEST:raise ValueError('Oversized transfer manifest')
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:raise ValueError('Duplicate manifest key')
            d[k]=v
        return d
    m=json.loads(z.read(info),object_pairs_hook=pairs)
    if m['schema_version']!=1 or not isinstance(m['original_workspace'],str):raise ValueError('Unknown transfer schema')
    members={}
    for r in m['members']:
        p=name(r['path'])
        if not p.startswith('payload/') or p in members or type(r['bytes']) is not int or r['bytes']<0 or not re.fullmatch('[0-9a-f]{64}',r['sha256']):raise ValueError('Invalid manifest member')
        members[p]=r
    if names!={'TRANSFER_MANIFEST.json',*members}:raise ValueError('Manifest/archive member mismatch')
    if any(z.getinfo(p).file_size!=r['bytes'] for p,r in members.items()):raise ValueError('Manifest member size mismatch')
    return m,members


def verify(archive,expected):
    archive=Path(archive)
    if not re.fullmatch('[0-9a-f]{64}',expected) or archive.stat().st_size>MAX_ARCHIVE or digest(archive)!=expected:raise ValueError('Archive checksum/size mismatch')
    with zipfile.ZipFile(archive) as z:
        m,members=read_manifest(z)
        for p,r in members.items():
            h=hashlib.sha256()
            with z.open(p) as f:
                for block in iter(lambda:f.read(1024**2),b''):h.update(block)
            if h.hexdigest()!=r['sha256']:raise ValueError('Member checksum mismatch: '+p)
        approved=m.get('approved_model')
        if approved:
            p=name(approved['path'])
            if members[p]['sha256']!=approved['sha256']:raise ValueError('Approved artifact differs')
    return m


def restore(archive,expected,destination,source_checkout=None):
    m=verify(archive,expected);target=Path(destination).resolve()
    source=Path(source_checkout).expanduser().resolve() if source_checkout is not None else target/'payload/fpl-predict'
    if target.exists() or target.is_relative_to(ROOT) or target.is_relative_to(source):raise ValueError('Require a new destination outside checkout')
    if source.exists() and not source.is_dir():raise ValueError('Source checkout must be a directory or a future clone location')
    target.parent.mkdir(parents=True,exist_ok=True);tmp=Path(tempfile.mkdtemp(prefix='.'+target.name+'-restore-',dir=target.parent))
    try:
        with zipfile.ZipFile(archive) as z:
            second,members=read_manifest(z)
            if second!=m:raise ValueError('Archive changed after verification')
            for info in z.infolist():
                p=tmp.joinpath(*PurePosixPath(info.filename).parts);p.parent.mkdir(parents=True,exist_ok=True)
                with z.open(info) as src,p.open('xb') as dst:shutil.copyfileobj(src,dst,1024**2)
                if info.filename!='TRANSFER_MANIFEST.json' and digest(p)!=members[info.filename]['sha256']:raise ValueError('Archive changed during extraction')
        if digest(archive)!=expected:raise ValueError('Archive changed during restoration')
        paths=dict(schema_version=1,original_workspace=m['original_workspace'],workspace=str(target/'payload'),source_checkout=str(source),scope='Original payload bytes unchanged; source paths resolve to source_checkout, other workspace paths to workspace; never rewrite frozen records')
        (tmp/'PORTABLE_PATHS.json').write_text(json.dumps(paths,indent=2)+'\n');tmp.rename(target)
    except BaseException:
        shutil.rmtree(tmp);raise
    return paths


def resolve(original,paths):
    root=paths['original_workspace'].rstrip('/');prefix=root+'/'
    if original==root:return str(Path(paths['workspace']))
    if not original.startswith(prefix):raise ValueError('Path is outside captured workspace; supply an explicit new runtime location')
    suffix=original[len(prefix):];name(suffix)
    if suffix=='fpl-predict' or suffix.startswith('fpl-predict/'):
        source=Path(paths.get('source_checkout',Path(paths['workspace'])/'fpl-predict'))
        return str(source.joinpath(*PurePosixPath(suffix).parts[1:]))
    return str(Path(paths['workspace']).joinpath(*PurePosixPath(suffix).parts))


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for command in ['verify','restore']:
        q=sub.add_parser(command);q.add_argument('--archive',type=Path,required=True);q.add_argument('--sha256',required=True)
        if command=='restore':
            q.add_argument('--destination',type=Path,required=True)
            q.add_argument('--source-checkout',type=Path,help='Actual public checkout or future clone path; default: DESTINATION/payload/fpl-predict')
    q=sub.add_parser('resolve');q.add_argument('--map',type=Path,required=True);q.add_argument('--path',required=True);a=p.parse_args()
    if a.command=='resolve':print(resolve(a.path,json.loads(a.map.read_text())));return
    m=verify(a.archive,a.sha256) if a.command=='verify' else restore(a.archive,a.sha256,a.destination,a.source_checkout)
    print(json.dumps(dict(status='verified' if a.command=='verify' else 'restored',members=len(m['members']) if a.command=='verify' else None,untrusted_code_executed=False)))


if __name__=='__main__':main()
