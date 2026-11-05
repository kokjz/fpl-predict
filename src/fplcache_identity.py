"""Identity-only historical diagnostic; never decodes availability values."""
from pathlib import Path
import hashlib
import json
import lzma
import math
import numbers
import re

import numpy as np
import pandas as pd
from deadline_provenance import MAX_COMPRESSED, MAX_EXPANDED
from fplcache_availability import path_time
from research_receipts import write_json

FIELDS = ('id', 'code', 'element_type')
IDENTITY_COLUMNS = ['season', 'GW', 'element', 'pos']


class IdentityJSON:
    """Skip unwanted values lexically, including strings and nested objects."""
    def __init__(self, raw):
        self.raw, self.i = raw, 0

    def white(self):
        while self.i < len(self.raw) and self.raw[self.i] in b' \r\n\t':
            self.i += 1
        if self.i >= len(self.raw):
            raise ValueError('Unexpected JSON end')
        return self.raw[self.i]

    def take(self, expected):
        if self.white() != expected:
            raise ValueError('Unexpected JSON delimiter')
        self.i += 1

    def string(self, keep):
        self.take(34)
        start = self.i-1
        escape = False
        while self.i < len(self.raw):
            c = self.raw[self.i]
            self.i += 1
            if escape:
                escape = False
            elif c == 92:
                escape = True
            elif c == 34:
                return json.loads(self.raw[start:self.i]) if keep else None
        raise ValueError('Unterminated JSON string')

    def skip(self):
        c = self.white()
        if c == 34:
            self.string(False)
        elif c in (123, 91):
            stack = [125 if c == 123 else 93]
            self.i += 1
            while stack:
                c = self.white()
                if c == 34:
                    self.string(False)
                    continue
                self.i += 1
                if c in (123, 91):
                    stack.append(125 if c == 123 else 93)
                    if len(stack) > 64:
                        raise ValueError('JSON nesting budget')
                elif c in (125, 93) and stack.pop() != c:
                    raise ValueError('JSON balance')
        else:
            while self.i < len(self.raw) and self.raw[self.i] not in b',}] \r\n\t':
                self.i += 1

    def value(self):
        if self.white() in (123, 91):
            self.skip()
            return None  # malformed identity, without decoding nested values
        start = self.i
        self.skip()
        return json.loads(self.raw[start:self.i])

    def elements(self):
        self.take(123)
        while self.white() != 125:
            name = self.string(True)
            self.take(58)
            if name == 'elements':
                self.take(91)
                rows = []
                while self.white() != 93:
                    self.take(123)
                    row = {}
                    while self.white() != 125:
                        name = self.string(True)
                        self.take(58)
                        if name in FIELDS:
                            if name in row:
                                raise ValueError('Duplicate identity field')
                            row[name] = self.value()
                        else:
                            self.skip()
                        if self.white() == 44:
                            self.i += 1
                        elif self.white() != 125:
                            raise ValueError('Element delimiter')
                    self.take(125)
                    rows.append({name: row.get(name) for name in FIELDS})
                    if self.white() == 44:
                        self.i += 1
                    elif self.white() != 93:
                        raise ValueError('Elements delimiter')
                self.take(93)
                return rows
            self.skip()
            if self.white() == 44:
                self.i += 1
            elif self.white() != 125:
                raise ValueError('Top-level delimiter')
        raise ValueError('Elements absent')


def read_identities(entry):
    path_time(entry['path'])  # scope refusal before any file access
    p = Path(entry['local_path'])
    if not p.is_file() or p.stat().st_size > MAX_COMPRESSED:
        raise ValueError('Snapshot size/absence')
    raw = p.read_bytes()
    if hashlib.sha256(raw).hexdigest() != entry['sha256']:
        raise ValueError('Snapshot SHA256 mismatch')
    if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() != entry['blob']:
        raise ValueError('Snapshot Git blob mismatch')
    decoder = lzma.LZMADecompressor(memlimit=64*1024**2)
    expanded = decoder.decompress(raw, max_length=MAX_EXPANDED+1)
    if len(expanded) > MAX_EXPANDED or not decoder.eof or decoder.unused_data:
        raise ValueError('Snapshot expansion budget/trailing bytes')
    return pd.DataFrame(IdentityJSON(expanded).elements(), columns=FIELDS)


def finite_int64(values):
    integers, valid = [], []
    bounds = np.iinfo(np.int64)
    for value in values:
        ok = False
        if isinstance(value, (bool, np.bool_)):
            number = 0
        elif isinstance(value, numbers.Integral):
            number, ok = int(value), True
        elif isinstance(value, numbers.Real) and math.isfinite(value) and float(value).is_integer():
            number, ok = int(value), True
        elif isinstance(value, str) and re.fullmatch(r'[+-]?\d+', value):
            number, ok = int(value), True
        else:
            number = 0
        ok = ok and bounds.min <= number <= bounds.max
        integers.append(number if ok else 0)
        valid.append(ok)
    return np.array(integers, dtype='int64'), np.array(valid, dtype=bool)


def same(left, right):
    try:
        result = left == right
        return bool(result) if pd.notna(result) else False
    except (TypeError, ValueError):
        return False


def diagnostic(history, bridge, snapshot):
    """Counts every mismatch; malformed identities are a case-3 finding."""
    h = history[IDENTITY_COLUMNS].copy()
    hid, hv = finite_int64(h.element)
    bid, biv = finite_int64(bridge.id)
    bc, bcv = finite_int64(bridge.code)
    sid, siv = finite_int64(snapshot.id)
    sc, scv = finite_int64(snapshot.code)
    sp, spv = finite_int64(snapshot.element_type)
    hp, hpv = finite_int64(h.pos)
    bmap, cmap, rawmap = {}, {}, {}
    for i in range(len(bridge)):
        if biv[i]:
            rawmap.setdefault(bid[i], bridge.code.iloc[i])
            if bcv[i]:
                bmap.setdefault(bid[i], bc[i])
    for i in range(len(snapshot)):
        if scv[i]:
            cmap.setdefault(sc[i], i)
    imap = {}
    for i in range(len(snapshot)):
        if siv[i]:
            imap.setdefault(sid[i], i)
    rawcodes = pd.Series([rawmap.get(v, np.nan) if ok else np.nan for v, ok in zip(hid, hv)])
    hc = np.array([bmap.get(v, 0) for v in hid], dtype='int64')
    hcv = np.array([bool(ok and v in bmap) for v, ok in zip(hid, hv)])
    id_rows = [i for i in range(len(h)) if hv[i] and hid[i] in imap]
    code_rows = [i for i in range(len(h)) if hcv[i] and hc[i] in cmap]
    mismatch, after_cast, id_position, code_position, drift = [], [], [], [], []
    for i in id_rows:
        j = imap[hid[i]]
        if not same(snapshot.code.iloc[j], rawcodes.iloc[i]):
            mismatch.append(i)
        if not (scv[j] and hcv[i] and sc[j] == hc[i]):
            after_cast.append(i)
        if not same(snapshot.element_type.iloc[j], h.pos.iloc[i]):
            id_position.append(i)
    for i in code_rows:
        j = cmap[hc[i]]
        if not same(snapshot.element_type.iloc[j], h.pos.iloc[i]):
            code_position.append(i)
        if not (siv[j] and sid[j] == hid[i]):
            drift.append(i)
    def scalar(value):
        if isinstance(value, np.generic):
            return value.item()
        return None if pd.isna(value) else value
    examples = []
    indexes = list(dict.fromkeys(mismatch+after_cast+id_position+code_position+drift+list(range(len(h)))))[:5]
    for i in indexes:
        j = imap.get(hid[i]) if i in mismatch+after_cast+id_position else cmap.get(hc[i])
        examples.append([scalar(h.element.iloc[i]), scalar(rawcodes.iloc[i]),
                         scalar(snapshot.id.iloc[j]) if j is not None else None,
                         scalar(snapshot.code.iloc[j]) if j is not None else None,
                         [scalar(h.pos.iloc[i]), scalar(snapshot.element_type.iloc[j]) if j is not None else None]])
    return dict(history_rows=len(h), id_matched_rows=len(id_rows), id_unmatched_rows=len(h)-len(id_rows),
                id_code_mismatch_rows=len(mismatch), int64_code_mismatch_rows=len(after_cast), id_position_mismatch_rows=len(id_position),
                snapshot_code_dtype=str(snapshot.code.dtype), bridge_code_dtype=str(rawcodes.dtype),
                code_matched_rows=len(code_rows), code_unmatched_rows=len(h)-len(code_rows), code_position_mismatch_rows=len(code_position),
                duplicate_codes=int(pd.Series(sc[scv]).duplicated().sum()), duplicate_ids=int(pd.Series(sid[siv]).duplicated().sum()),
                id_drift_rows=len(drift), bridge_missing_history_rows=int((~hcv).sum()),
                invalid_snapshot_codes=int((~scv).sum()), invalid_bridge_codes=int((~bcv).sum()),
                invalid_snapshot_ids=int((~siv).sum()), invalid_bridge_ids=int((~biv).sum()), invalid_history_ids=int((~hv).sum()),
                invalid_positions=int((~spv | ~np.isin(sp, [1, 2, 3, 4, 5])).sum()+
                                      (~hpv | ~np.isin(hp, [1, 2, 3, 4])).sum()),
                duplicate_bridge_ids=int(pd.Series(bid[biv]).duplicated().sum()),
                duplicate_bridge_codes=int(pd.Series(bc[bcv]).duplicated().sum()), examples=examples)


def classify(reports):
    invalid = ['invalid_snapshot_codes', 'invalid_bridge_codes', 'invalid_snapshot_ids', 'invalid_bridge_ids',
               'invalid_history_ids', 'invalid_positions', 'duplicate_ids', 'duplicate_bridge_ids', 'duplicate_bridge_codes',
               'bridge_missing_history_rows', 'duplicate_codes']
    if not reports or any(r[n] for r in reports for n in invalid):
        return 3
    if all(r['int64_code_mismatch_rows'] == 0 and r['id_position_mismatch_rows'] == 0 for r in reports):
        return 1
    if all(r['code_position_mismatch_rows'] == 0 for r in reports):
        return 2
    return 3


def snapshot_progress(evidence_directory, phase, ordinal, entry):
    if phase not in ('identity-diagnostic', 'admission'):
        raise ValueError('Progress phase refused')
    folder = 'diagnostic-progress' if phase == 'identity-diagnostic' else 'admission-progress'
    return write_json(evidence_directory, f'{folder}/{ordinal:03d}.json',
                      dict(season=entry['season'], gameweek=entry['gameweek'], path=entry.get('path'), phase=phase))


def diagnostic_loop(entries, history, bridges, evidence_directory):
    reports = []
    for ordinal, entry in enumerate(entries):
        if entry['status'] != 'selected':
            continue
        snapshot_progress(evidence_directory, 'identity-diagnostic', ordinal, entry)
        snapshot = read_identities(entry)
        h = history.loc[history.season.eq(entry['season']) & history.GW.eq(entry['gameweek']), IDENTITY_COLUMNS]
        report = diagnostic(h, bridges[entry['season']], snapshot)
        reports.append(dict(report, season=entry['season'], gameweek=entry['gameweek'], path=entry['path']))
    fields = [name for name, value in reports[0].items() if type(value) is int and name != 'gameweek'] if reports else []
    totals = {name: sum(r[name] for r in reports) for name in fields}
    seasons = {s: {name: sum(r[name] for r in reports if r['season'] == s) for name in fields}
               for s in sorted({r['season'] for r in reports})}
    return dict(case=classify(reports), snapshots=len(reports), snapshots_detail=reports,
                overall=totals, per_season=seasons, identity_fields=list(FIELDS),
                history_columns=IDENTITY_COLUMNS, availability_values_decoded=False,
                target_columns_selected=False, features_or_predictions_read=False, network_requests=0)
