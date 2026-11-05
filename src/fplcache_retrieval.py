"""Ledger-preserving continuation of bounded historical snapshot retrieval."""
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlencode
import argparse
import copy
import hashlib
import json
import subprocess
import urllib.error
import urllib.request

from deadline_provenance import MAX_COMPRESSED, read_snapshot
from fplcache_availability import path_time, select_snapshot, SOURCE_SEASONS, LAST_DEADLINE
from availability_evidence import utc
from research_receipts import receipt_path, write_json
import pandas as pd

COUNTERS = ('metadata_requests', 'downloads', 'total_bytes', 'retries', 're_selections')
LIMITS = dict(metadata_requests=600, downloads=210, total_bytes=250_000_000,
              retries=10, re_selections=10)


def read_json(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError('Required ledger file absent')
    return json.loads(path.read_text(encoding='utf-8'))


def key(row):
    return row['season'], int(row['gameweek'])


def retained_preflight(ledger, receipts, calendar):
    """No transport can run until retained bytes, identities and clocks verify."""
    for row in calendar:
        if row['season'] not in SOURCE_SEASONS or not 1 <= int(row['gameweek']) <= 38:
            raise ValueError('Calendar season refused before transport')
        if row['status'] == 'no_fixtures':
            if key(row) != ('2022-23', 7) or row['deadline'] is not None:
                raise ValueError('Invalid no-fixtures calendar')
        elif row['status'] != 'planned' or utc(row['deadline']) > utc(LAST_DEADLINE):
            raise ValueError('Calendar deadline refused before transport')
    if not ledger.get('listing_revision') or len(ledger['listing_revision']) != 40:
        raise ValueError('Missing listing revision')
    for name, limit in LIMITS.items():
        if type(ledger[name]) is not int or not 0 <= ledger[name] <= limit:
            raise ValueError('Invalid cumulative counter')
    selected = ledger['selected']
    keys = [key(row) for row in selected]
    if len(set(keys)) != len(keys) or keys != [key(row) for row in calendar[:len(keys)]]:
        raise ValueError('Ledger is not a unique calendar prefix')
    snapshots = [r for r in receipts if r['kind'] == 'snapshot']
    if len(snapshots) != len({(r['path'], r['adding_commit']) for r in snapshots}):
        raise ValueError('Duplicate retained download receipt')
    by_file = {(r['path'], r['adding_commit']): r for r in snapshots}
    verified = []
    for row in selected:
        if row['status'] == 'no_fixtures':
            if key(row) != ('2022-23', 7) or row['deadline'] is not None:
                raise ValueError('Invalid no-fixtures entry')
            continue
        if row['status'] == 'no_source':
            continue
        if row['status'] != 'selected':
            raise ValueError('Invalid selection status')
        path_time(row['path'])  # scope refusal before file access
        receipt = by_file.get((row['path'], row['adding_commit']))
        if receipt is None:
            raise ValueError('Missing retained file receipt')
        for name in ['blob', 'sha256', 'bytes', 'commit_time', 'path_time', 'local_path']:
            if row[name] != receipt[name]:
                raise ValueError('Retained receipt differs')
        p = Path(row['local_path'])
        if not p.is_file() or p.stat().st_size != row['bytes'] or p.stat().st_size > MAX_COMPRESSED:
            raise ValueError('Retained snapshot size')
        raw = p.read_bytes()
        if hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Retained SHA256 mismatch')
        if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() != row['blob']:
            raise ValueError('Retained Git blob mismatch')
        if select_snapshot([row], row['deadline']) is None:
            raise ValueError('Retained selection clock')
        verified.append(dict(path=row['path'], sha256=row['sha256'], blob=row['blob'], bytes=len(raw)))
    if sum(r['bytes'] for r in snapshots) != ledger['total_bytes']:
        raise ValueError('Retained byte counter differs')
    if len(snapshots) > ledger['downloads']:
        raise ValueError('Retained download counter differs')
    return copy.deepcopy(calendar[len(keys):]), verified


def save_state(output_directory, value):
    target = receipt_path(output_directory, 'retrieval.json')
    if not target.is_file():
        raise ValueError('Pre-created state destination required')
    target.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def append_event(output_directory, value):
    target = receipt_path(output_directory, 'network.jsonl')
    if not target.is_file():
        raise ValueError('Pre-created log required')
    with target.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(dict(value, utc=datetime.now(timezone.utc).isoformat()), allow_nan=False)+'\n')


class Continuation:
    def __init__(self, ledger, receipts, calendar, output_directory, evidence_directory):
        self.remaining, self.verified = retained_preflight(ledger, receipts, calendar)
        self.state = copy.deepcopy(ledger)
        self.before = {name: ledger[name] for name in COUNTERS}
        self.state['before_resume'] = dict(self.before)
        self.state['resume_started_at'] = datetime.now(timezone.utc).isoformat()
        self.output = Path(output_directory).resolve(strict=True)
        self.evidence = Path(evidence_directory).resolve(strict=True)
        for name in ['retrieval.json', 'network.jsonl']:
            p = receipt_path(self.output, name)
            if not p.is_file() or p.stat().st_size:
                raise ValueError('Fresh pre-created continuation output required')
        self.listings, self.additions = {}, {}

    def record(self, value):
        append_event(self.output, value)

    def save(self):
        save_state(self.output, self.state)

    def api(self, path, missing=False):
        if self.state['metadata_requests'] >= LIMITS['metadata_requests']:
            raise ValueError('Metadata budget exhausted')
        self.state['metadata_requests'] += 1
        self.save()
        self.record(dict(kind='api_request', ordinal=self.state['metadata_requests'], path=path))
        result = subprocess.run(['gh', 'api', path], capture_output=True)
        self.record(dict(kind='github_api', path=path, exit_code=result.returncode,
                         sha256=hashlib.sha256(result.stdout).hexdigest(), bytes=len(result.stdout),
                         error=result.stderr.decode(errors='replace') if result.returncode else None))
        if result.returncode:
            if missing and b'HTTP 404' in result.stderr:
                return None
            raise RuntimeError('GitHub metadata failure')
        return json.loads(result.stdout)

    def adding(self, candidate):
        path = candidate['path']
        if path not in self.additions:
            query = urlencode(dict(path=path, sha=self.state['listing_revision'], per_page=100))
            rows = self.api('repos/Randdalf/fplcache/commits?'+query)
            if not rows or len(rows) >= 100:
                raise ValueError('Adding history ambiguous')
            first = rows[-1]
            commit = self.api('repos/Randdalf/fplcache/commits/'+first['sha'])
            files = [f for f in commit['files'] if f['filename'] == path]
            if len(files) != 1 or files[0]['status'] != 'added':
                raise ValueError('First addition unproven')
            self.additions[path] = dict(candidate, adding_commit=first['sha'], blob=files[0]['sha'],
                                        commit_time=commit['commit']['committer']['date'])
        return self.additions[path]

    def choose(self, planned):
        deadline = utc(planned['deadline'])
        days = dict.fromkeys([deadline.normalize(), (deadline-pd.Timedelta(hours=24)).normalize()])
        for day in days:
            directory = f'cache/{day.year}/{day.month}/{day.day}'
            if directory not in self.listings:
                self.listings[directory] = self.api('repos/Randdalf/fplcache/contents/'+directory+'?ref='+self.state['listing_revision'], missing=True)
            candidates = []
            for file in self.listings[directory] or []:
                if file['type'] != 'file' or not file['name'].endswith('.json.xz'):
                    continue
                if day == deadline.normalize() and file['name'][:4] >= deadline.strftime('%H%M'):
                    continue
                stamp = path_time(file['path'])
                if stamp < deadline and deadline-stamp <= pd.Timedelta(hours=24):
                    candidates.append(dict(path=file['path'], listing_blob=file['sha']))
            for candidate in sorted(candidates, key=lambda r: path_time(r['path']), reverse=True):
                entry = self.adding(candidate)
                if select_snapshot([entry], deadline) is not None:
                    return dict(entry, **{name: planned[name] for name in ['season', 'gameweek', 'deadline']})
        return None

    def download(self, entry):
        path_time(entry['path'])
        url = 'https://raw.githubusercontent.com/Randdalf/fplcache/'+entry['adding_commit']+'/'+entry['path']
        for attempt in range(2):
            if self.state['downloads'] >= LIMITS['downloads']:
                raise ValueError('Download budget exhausted')
            local = receipt_path(self.output, f"snapshots/{self.state['downloads']:03d}.json.xz")
            if not local.is_file() or local.stat().st_size:
                raise ValueError('Fresh pre-created download slot required')
            self.state['downloads'] += 1
            self.save()
            self.record(dict(kind='download_request', url=url, ordinal=self.state['downloads']))
            try:
                with urllib.request.urlopen(url, timeout=60) as response:
                    raw = response.read(MAX_COMPRESSED+1)
                if len(raw) > MAX_COMPRESSED or self.state['total_bytes']+len(raw) > LIMITS['total_bytes']:
                    raise ValueError('Snapshot byte budget')
                if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() != entry['blob']:
                    raise ValueError('Snapshot Git blob mismatch')
                local.write_bytes(raw)
                self.state['total_bytes'] += len(raw)
                row = dict(entry, status='selected', url=url, local_path=str(local), bytes=len(raw),
                           sha256=hashlib.sha256(raw).hexdigest(), path_time=path_time(entry['path']).isoformat(),
                           published_at=max(path_time(entry['path']), utc(entry['commit_time'])).isoformat())
                self.record(dict(row, kind='snapshot', attempt=attempt))
                self.save()
                return row
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                self.record(dict(kind='transport_error', url=url, attempt=attempt, error=repr(exc)))
                if isinstance(exc, urllib.error.HTTPError) or attempt or self.state['retries'] >= LIMITS['retries']:
                    raise
                self.state['retries'] += 1
                self.save()
        raise AssertionError('Unreachable')

    def select_one(self, planned):
        entry = self.choose(planned)
        if entry is None:
            return dict(planned, status='no_source')
        row = self.download(entry)
        payload = read_snapshot(row['local_path'], row['sha256'])
        events = [r for r in payload['events'] if r['id'] == planned['gameweek']]
        if len(events) != 1:
            raise ValueError('Event clock ambiguous')
        own = utc(events[0]['deadline_time'])
        if own != utc(planned['deadline']):
            if self.state['re_selections'] >= LIMITS['re_selections']:
                raise ValueError('Reselection budget exhausted')
            self.state['re_selections'] += 1
            self.save()
            replacement = self.choose(dict(planned, deadline=own.isoformat()))
            if replacement is None:
                raise ValueError('No source on reselection')
            if (replacement['path'], replacement['adding_commit']) == (row['path'], row['adding_commit']):
                row = dict(row, deadline=own.isoformat())
            else:
                original = row
                row = self.download(replacement)
                row['replaces_path'] = original['path']
            row['original_planning_deadline'] = planned['deadline']
            payload = read_snapshot(row['local_path'], row['sha256'])
            events = [r for r in payload['events'] if r['id'] == planned['gameweek']]
            if len(events) != 1 or utc(events[0]['deadline_time']) != own:
                raise ValueError('Second deadline mismatch')
        return row

    def run(self):
        write_json(self.evidence, 'resume-retained-verification.json',
                   dict(listing_revision=self.state['listing_revision'], counters_before=self.before,
                        retained=self.verified, remaining_deadlines=len(self.remaining)))
        self.state['status'] = 'running'
        self.save()
        try:
            for planned in self.remaining:
                row = planned if planned['status'] == 'no_fixtures' else self.select_one(planned)
                self.state['selected'].append(row)
                self.save()
                print(json.dumps(dict(season=row['season'], gameweek=row['gameweek'], status=row['status'],
                                      counters={name: self.state[name] for name in COUNTERS})), flush=True)
            self.state.update(status='completed', finished_at=datetime.now(timezone.utc).isoformat(),
                              after_resume={name: self.state[name]-self.before[name] for name in COUNTERS})
            self.save()
        except BaseException as exc:
            self.state.update(status='blocked', error=repr(exc))
            self.save()
            raise


def main():
    parser = argparse.ArgumentParser()
    for name in ['ledger', 'receipts', 'calendar', 'output-dir', 'evidence-dir']:
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if not args.receipts.is_file():
        raise ValueError('Receipt file absent')
    receipts = [json.loads(line) for line in args.receipts.read_text(encoding='utf-8').splitlines()]
    Continuation(read_json(args.ledger), receipts, read_json(args.calendar), args.output_dir, args.evidence_dir).run()


if __name__ == '__main__':
    main()
