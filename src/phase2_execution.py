"""Offline execution of the frozen prospective test; never fits or retrieves.

Seasonal replicas below preserve the released label and squad algorithms.
Every future-season entry point requires explicit phase2_authorised=True.
This module does not grant that authority to its caller.
"""
from pathlib import Path
import csv
import hashlib
import io
import json
import re
import copy
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from availability_evidence import utc
from conditional_forecaster import SIGNALS
from fpl_model import CORE_FEATURES, DC_FEATURES, FeatureStore, normalise, candidate_mask
from market_stage_c import canonical_hash
from fplcache_availability import integer_codes, player_payload, PRIVATE_EXTRAS
from availability_history import optional_integer, MAX_BYTES, REQUIRED
from external_benchmark import _timestamp
from deadline_provenance import read_snapshot, extract_bootstrap
from availability_prospective import phase2_gates
from benchmark_metrics import evaluate
from benchmark_evaluation import paired_block_errors

KEYS = ['season', 'fixture', 'fpl_code']
HISTORICAL = {f'{y}-{str(y+1)[-2:]}' for y in range(2020, 2026)}


def scope(seasons, *, phase2_authorised=False):
    allowed = HISTORICAL | ({'2026-27'} if phase2_authorised is True else set())
    if not set(seasons) <= allowed:
        raise ValueError('Season refused; explicit phase2 authorisation required')


def checked_path(path, season, *, phase2_authorised=False):
    scope([season], phase2_authorised=phase2_authorised)
    text = str(path).replace('\\', '/')
    if not phase2_authorised and re.search(r'2026[-_/]27|2627|cache/(2026/(?:[7-9]|1[0-2])/|2027/)', text):
        raise ValueError('Future-season path refused')
    return Path(path)


def path_time(path, *, phase2_authorised=False):
    match = re.fullmatch(r'cache/(\d{4})/(\d{1,2})/(\d{1,2})/(\d{2})(\d{2})\.json\.xz', path)
    if not match:
        raise ValueError('Snapshot path refused')
    year, month, day, hour, minute = map(int, match.groups())
    stamp = pd.Timestamp(year=year, month=month, day=day, hour=hour, minute=minute, tz='UTC')
    if stamp > utc('2026-05-24T13:30:00+00:00') and phase2_authorised is not True:
        raise ValueError('Snapshot after final permitted deadline')
    return stamp


def select_snapshot(entries, deadline, *, phase2_authorised=False):
    """Entries carry the listing blob and independently looked-up adding clock."""
    deadline = utc(deadline)
    if deadline > utc('2026-05-24T13:30:00+00:00') and phase2_authorised is not True:
        raise ValueError('Deadline refused')
    eligible = []
    for entry in entries:
        stamp = path_time(entry['path'], phase2_authorised=phase2_authorised)
        commit = utc(entry['commit_time'])
        if stamp - commit > pd.Timedelta(minutes=5):
            raise ValueError('Adding commit precedes path clock')
        if stamp < deadline and commit < deadline and deadline-stamp <= pd.Timedelta(hours=24):
            eligible.append((stamp, entry))
    if not eligible:
        return None
    return dict(max(eligible, key=lambda pair: pair[0])[1])


def admit_snapshot(entry, bridge, history, *, phase2_authorised=False):
    scope([entry['season']], phase2_authorised=phase2_authorised)
    path_time(entry['path'], phase2_authorised=phase2_authorised)  # refuse forbidden paths before opening any bytes
    selected = select_snapshot([entry], entry['deadline'], phase2_authorised=phase2_authorised)
    if selected is None:
        raise ValueError('Snapshot not eligible')
    local = checked_path(entry['local_path'], entry['season'], phase2_authorised=phase2_authorised)
    if not local.is_file():
        raise ValueError('Snapshot absent')
    raw = local.read_bytes()
    if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() != entry['blob']:
        raise ValueError('Git blob mismatch')
    payload, excluded = player_payload(read_snapshot(local, entry['sha256']))
    published = max(path_time(entry['path'], phase2_authorised=phase2_authorised), utc(entry['commit_time']))
    report, identities = extract_bootstrap(payload, entry['season'], int(entry['gameweek']), published.isoformat())
    if utc(report['deadline']) != utc(entry['deadline']):
        raise ValueError('Snapshot deadline differs from planning calendar')
    if bridge.id.duplicated().any() or bridge.code.duplicated().any():
        raise ValueError('Ambiguous season bridge')
    h = history.loc[history.season.eq(entry['season']) & history.GW.eq(entry['gameweek'])]
    codes = h.element.map(bridge.set_index('id').code)
    if codes.isna().any():
        raise ValueError('Missing history bridge')
    codes = pd.Series(integer_codes(codes), index=h.index)
    identities = identities.copy()
    identities['fpl_code'] = integer_codes(identities.fpl_code)
    if identities.fpl_code.duplicated().any():
        raise ValueError('Duplicate normalized snapshot code')
    roster = identities.set_index('fpl_code')
    matched = codes.isin(roster.index)
    used = roster.loc[codes.loc[matched].to_numpy()]
    if not np.array_equal(used.position.to_numpy(), h.loc[matched, 'pos'].to_numpy()):
        raise ValueError('Snapshot position mismatch')
    id_drift = int(np.count_nonzero(used.element.to_numpy() != h.loc[matched, 'element'].to_numpy()))
    observations = []
    for p in payload['elements']:
        row = dict(season=entry['season'], gameweek=int(entry['gameweek']), element=p['id'],
                   fpl_code=p['code'], source_position=p['element_type'], team=p['team'],
                   published_at=published.isoformat(), source_deadline=report['deadline'],
                   chance_label=p.get('chance_of_playing_next_round'), news_present=bool(p.get('news')))
        row.update({name: p.get(name) for name in PRIVATE_EXTRAS})
        observations.append(row)
    obs = pd.DataFrame(observations)
    chance = pd.to_numeric(obs.chance_label, errors='raise').to_numpy(float)
    if np.isinf(chance).any() or ((chance[np.isfinite(chance)] < 0) | (chance[np.isfinite(chance)] > 100)).any():
        raise ValueError('Invalid chance label')
    report.update(status='admitted', assistant_managers_excluded=excluded,
                  known_labels=int(np.isfinite(chance).sum()), commit_time=entry['commit_time'],
                  path_time=path_time(entry['path'], phase2_authorised=phase2_authorised).isoformat(), published_at=published.isoformat(),
                  unmatched_history_rows=int((~matched).sum()), id_drift_rows=id_drift,
                  identity_key='season/gameweek/fpl_code')
    return report, obs


def augment(rows, features, bridges, observations, *, phase2_authorised=False):
    """Same SIGNALS bytes as incumbent augment, generalized by seasonal keys."""
    scope(rows.season, phase2_authorised=phase2_authorised)
    if not rows.index.equals(features.index):
        raise ValueError('Unaligned features')
    scope(observations.season, phase2_authorised=phase2_authorised)
    if observations.duplicated(['season', 'gameweek', 'fpl_code']).any():
        raise ValueError('Duplicate observations')
    z = rows[['season', 'GW', 'element', 'fixture', 'pos', 'cutoff']].copy()
    z['row'] = np.arange(len(z))
    z['fpl_code'] = np.nan
    for season, bridge in bridges.items():
        scope([season], phase2_authorised=phase2_authorised)
        if bridge.id.duplicated().any() or bridge.code.duplicated().any():
            raise ValueError('Ambiguous bridge')
        ix = z.season.eq(season)
        z.loc[ix, 'fpl_code'] = z.loc[ix, 'element'].map(bridge.set_index('id').code)
    if z.fpl_code.isna().any():
        raise ValueError('Missing stable bridge')
    if 'fpl_code' in rows and not np.array_equal(z.fpl_code.to_numpy(), rows.fpl_code.to_numpy()):
        raise ValueError('Row stable code mismatch')
    obs = observations.loc[observations.season.ne('2020-21')].copy()
    z = z.merge(obs, left_on=['season', 'GW', 'fpl_code'], right_on=['season', 'gameweek', 'fpl_code'],
                how='left', validate='many_to_one', suffixes=('', '_source')).sort_values('row')
    matched = z.published_at.notna()
    if (z.loc[matched, 'pos'].to_numpy() != z.loc[matched, 'source_position'].to_numpy()).any():
        raise ValueError('Source position differs')
    publication = z.loc[matched, 'published_at'].map(utc)
    deadline = z.loc[matched, 'source_deadline'].map(utc)
    cutoff = z.loc[matched, 'cutoff'].map(utc)
    if publication.ge(deadline).any() or publication.ge(cutoff).any():
        raise ValueError('Source is not before both cutoffs')
    chance = pd.to_numeric(z.chance_label, errors='raise').to_numpy(float)
    if np.isinf(chance).any() or ((chance[np.isfinite(chance)] < 0) | (chance[np.isfinite(chance)] > 100)).any():
        raise ValueError('Invalid chance covariate')
    result = features.copy()
    result[SIGNALS[0]] = np.where(np.isnan(chance), 0., chance/100.)
    result[SIGNALS[1]] = np.isnan(chance).astype(float)
    coverage = z.assign(matched=matched.to_numpy(), known=np.isfinite(chance)).groupby(['season', 'GW']).agg(
        rows=('row', 'size'), matched=('matched', 'sum'), known=('known', 'sum')).reset_index()
    return result, coverage.to_dict('records')


def fixed_squad(rows, features, predictions, season, opening_gw=10, count=20, *, phase2_authorised=False):
    """Parameterized replica of the fixed GW20 retrospective squad selector."""
    if count != 20:
        raise ValueError('Require exactly 20 squads')
    from forecast import legal_squad, select_xi
    from points_replay import realised_points
    scope(rows.season, phase2_authorised=phase2_authorised)
    scope([season], phase2_authorised=phase2_authorised)
    if not rows.index.equals(features.index):
        raise ValueError('Squad feature alignment')
    year = rows[rows.season.eq(season)]
    opening = year[year.GW.eq(opening_gw)]
    cutoff = opening.cutoff.iloc[0]
    opening = opening.loc[(features.loc[opening.index, 'n_history'] >= 3) &
                          (features.loc[opening.index, 'last5_minutes'] >= 45)].drop_duplicates('element')
    history = year[year.ts < cutoff-pd.Timedelta(hours=3)].sort_values('ts').groupby('element').tail(1).set_index('element')
    pool = []
    for r in opening.itertuples():
        if r.element not in history.index:
            continue
        price = float(history.loc[r.element, 'value'])
        if not np.isfinite(price) or price <= 0:
            continue
        pool.append(dict(id=int(r.element), position=int(r.pos), team=int(r.team_id), price_tenths=price,
                         weight=max(float(features.loc[r.Index, 'ew4_points_core']), .1)))
    rng = np.random.default_rng(20260921)
    squads, seen = [], set()
    for _ in range(10000):
        selected = []
        for pos, n in [(1, 2), (2, 5), (3, 5), (4, 3)]:
            candidates = [p for p in pool if p['position'] == pos]
            weights = np.array([p['weight'] for p in candidates])
            ids = rng.choice(len(candidates), size=n, replace=False, p=weights/weights.sum())
            selected.extend(candidates[i] for i in ids)
        key = tuple(sorted(p['id'] for p in selected))
        if key not in seen and legal_squad(selected) and sum(p['price_tenths'] for p in selected) <= 1000:
            squads.append(selected)
            seen.add(key)
            if len(squads) == count:
                break
    if len(squads) != count:
        raise ValueError('Fixed squad count')
    test = rows.season.eq(season) & rows.GW.between(opening_gw, 38)
    z = rows.loc[test, ['GW', 'element', 'minutes', 'total_points']].copy()
    for method, values in predictions.items():
        z[method] = values
    grouped = z.groupby(['GW', 'element']).agg({m: 'sum' for m in predictions} | {'minutes': 'sum', 'total_points': 'sum'})
    totals = {m: [] for m in predictions}
    for squad in squads:
        players = {p['id']: p for p in squad}
        one = {m: 0. for m in predictions}
        for gw in range(opening_gw, 39):
            sub = grouped.loc[gw] if gw in grouped.index.get_level_values(0) else pd.DataFrame()
            actual = {i: float(sub.loc[i, 'total_points']) if i in sub.index else 0. for i in players}
            played = {i: bool(sub.loc[i, 'minutes'] > 0) if i in sub.index else False for i in players}
            for method in predictions:
                choices = [dict(p, expected_points=float(sub.loc[p['id'], method]) if p['id'] in sub.index else 0.) for p in squad]
                one[method] += realised_points(select_xi(choices), players, actual, played)
        for method in predictions:
            totals[method].append(one[method])
    deltas = {m: (np.array(v)-totals['control']).tolist() for m, v in totals.items() if m != 'control'}
    return dict(totals=totals, deltas=deltas, squad_sha256=canonical_hash(squads), count=count, first_gw=opening_gw, season=season)


def admit_prefix(raw, record, bootstrap, season, *, phase2_authorised=False):
    scope([season], phase2_authorised=phase2_authorised)
    """Return aggregate audit and selected raw observations without assumed UTC.

    Use publication of the exact byte prefix as the conservative availability
    time, retaining naive source clocks as opaque capture identifiers. The final
    append group is selected without using player outcomes or a name fallback.
    """
    if len(raw) > MAX_BYTES: raise ValueError("Archive size budget")
    deadline = _timestamp(record["deadline"]); published = _timestamp(record["published_at"])
    if published >= deadline: raise ValueError("Publication is not before deadline")
    if not re.fullmatch(r"[0-9a-f]{40}", record["commit"]): raise ValueError("Invalid commit identity")
    size = record["size"]
    if type(size) is not int or not 0 < size <= len(raw): raise ValueError("Invalid prefix extent")
    prefix = raw[:size]
    blob = hashlib.sha1(b"blob "+str(size).encode()+b"\0"+prefix).hexdigest()
    if blob != record["git_blob_sha1"]: raise ValueError("Published prefix checksum mismatch")
    if not prefix.endswith(b"\n"): raise ValueError("Incomplete CSV record")
    reader = csv.DictReader(io.StringIO(prefix.decode("utf-8"), newline=""))
    if not REQUIRED <= set(reader.fieldnames or []): raise ValueError("Missing source schema")
    if len(reader.fieldnames) != len(set(reader.fieldnames)): raise ValueError("Duplicate source columns")
    # Keep only the last contiguous capture group, not all historical rows.
    capture = None; selected = []; completed = set()
    for row in reader:
        if None in row or any(v is None for v in row.values()): raise ValueError("Malformed CSV row")
        stamp = row["timestamp"]
        if not stamp: raise ValueError("Missing capture identifier")
        if capture != stamp:
            if stamp in completed: raise ValueError("Noncontiguous capture groups")
            if capture is not None: completed.add(capture)
            capture = stamp; selected = []
        selected.append(row)
    if not selected: raise ValueError("Empty published prefix")
    gw = optional_integer(record["gameweek"], 1, 38)
    events = [e for e in bootstrap["events"] if e["id"] == gw]
    if len(events) != 1 or _timestamp(events[0]["deadline_time"]) != deadline:
        raise ValueError("Independent bootstrap deadline differs")
    by_code = {}; by_id = {}
    for player in bootstrap["elements"]:
        if player["code"] in by_code or player["id"] in by_id: raise ValueError("Ambiguous bootstrap identity")
        by_code[player["code"]] = player; by_id[player["id"]] = player
    seen_codes = set(); seen_ids = set(); known = 0; missing = 0; news = 0; chance = 0; return_gw = 0
    observations = []
    for row in selected:
        if row["season"] != season[2:4]+season[-2:] or optional_integer(row["gameweek"], 1, 38) != gw:
            raise ValueError("Capture season/gameweek differs")
        if not re.fullmatch(r"p\d+", row["opta_code"]): raise ValueError("Missing stable source identity")
        code = int(row["opta_code"][1:]); element = optional_integer(row["player_id"], 1, 100000)
        if code <= 0 or code in seen_codes or element in seen_ids: raise ValueError("Duplicate source identity")
        seen_codes.add(code); seen_ids.add(element)
        official = by_code.get(code)
        if official is None:
            if element in by_id: raise ValueError("Source ID maps to another bootstrap code")
            missing += 1
        else:
            if official["id"] != element: raise ValueError("Source code/element conflict")
            position = {"GK": 1, "DEF": 2, "MID": 3, "FWD": 4}.get(row["position"])
            if official["element_type"] != position: raise ValueError("Source position conflict")
            known += 1
        value = optional_integer(row["chance_of_playing_next_round"], 0, 100)
        back = optional_integer(row["return_gameweek"], 1, 38)
        text = row["news"].strip(); news += bool(text); chance += value is not None; return_gw += back is not None
        observations.append(dict(fpl_code=code, element=element, news=text,
                                 chance_label=value, return_gameweek=back,
                                 available_by=published.isoformat(), source_clock=capture))
    report = dict(gameweek=gw, published_at=published.isoformat(), deadline=deadline.isoformat(),
                  publication_lead_hours=(deadline-published).total_seconds()/3600,
                  commit=record["commit"], git_blob_sha1=blob, prefix_bytes=size,
                  prefix_sha256=hashlib.sha256(prefix).hexdigest(), rows=len(selected),
                  bootstrap_known=known, absent_at_other_capture=missing,
                  news_nonempty=news, chance_known=chance, return_gameweek_known=return_gw,
                  source_clock_has_timezone=(bool(re.search(r"(?:Z|[+-]\d\d:\d\d)$", capture))),
                  time_basis="exact-prefix Git publication, not assumed source-clock timezone",
                  model_admitted=False, benchmark_admitted=False)
    return report, observations


OBSERVATION_COLUMNS = ['season', 'gameweek', 'fpl_code', 'source_position',
                       'published_at', 'source_deadline', 'chance_label']


def choose_sources(calendar, airsenal, snapshots, bridges, history, *, phase2_authorised=False):
    """Admit one source for a whole GW; primary inputs are raw/proof/bootstrap tuples.

    All inputs are offline and explicitly supplied. Missing primary coverage
    permits fallback; an invalid supplied proof is an error, never a fallback.
    """
    scope(history.season, phase2_authorised=phase2_authorised)
    scope([r['season'] for r in calendar], phase2_authorised=phase2_authorised)
    scope([r['season'] for r in snapshots], phase2_authorised=phase2_authorised)
    keys = [(r['season'], int(r['gameweek'])) for r in calendar]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate calendar key')
    observations, reports = [], []
    for week in calendar:
        season, gw = week['season'], int(week['gameweek'])
        h = history.loc[history.season.eq(season) & history.GW.eq(gw)]
        if week.get('status') == 'no_fixtures':
            if len(h):
                raise ValueError('No-fixture calendar conflicts with rows')
            reports.append(dict(season=season, gameweek=gw, source='no_fixtures', observations=0, known_labels=0))
            continue
        deadline = utc(week['deadline'])
        primary = []
        for raw, record, bootstrap in airsenal.get((season, gw), []):
            if int(record['gameweek']) != gw or utc(record['deadline']) != deadline:
                raise ValueError('Primary proof calendar conflict')
            if utc(record['published_at']) >= deadline:
                continue
            primary.append((utc(record['published_at']), raw, record, bootstrap))
        block = pd.DataFrame(columns=OBSERVATION_COLUMNS)
        source = 'none'
        if primary:
            latest = max(v[0] for v in primary)
            selected = [v for v in primary if v[0] == latest]
            if len(selected) != 1:
                raise ValueError('Ambiguous primary publication')
            _, raw, record, bootstrap = selected[0]
            _, admitted = admit_prefix(raw, record, bootstrap, season, phase2_authorised=phase2_authorised)
            official = {p['code']: p for p in bootstrap['elements']}
            block = pd.DataFrame([dict(season=season, gameweek=gw, fpl_code=p['fpl_code'],
                source_position=official[p['fpl_code']]['element_type'], published_at=p['available_by'],
                source_deadline=record['deadline'], chance_label=p['chance_label'])
                for p in admitted if p['fpl_code'] in official], columns=OBSERVATION_COLUMNS)
            if len(block):
                source = 'AIrsenal'
        if block.empty:
            entries = [p for p in snapshots if p['season'] == season and int(p['gameweek']) == gw]
            selected = select_snapshot(entries, deadline, phase2_authorised=phase2_authorised)
            if selected is not None:
                if utc(selected['deadline']) != deadline:
                    raise ValueError('Fallback calendar conflict')
                _, block = admit_snapshot(selected, bridges[season], history, phase2_authorised=phase2_authorised)
                source = 'fplcache fallback'
        if len(block):
            observations.append(block[OBSERVATION_COLUMNS])
        reports.append(dict(season=season, gameweek=gw, source=source, observations=len(block),
                            known_labels=int(pd.to_numeric(block.chance_label).notna().sum())))
    result = pd.concat(observations, ignore_index=True) if observations else pd.DataFrame(columns=OBSERVATION_COLUMNS)
    # Validate code-keyed source positions even if the caller needs labels only.
    empty_features = pd.DataFrame(index=history.index)
    _, coverage = augment(history, empty_features, bridges, result, phase2_authorised=phase2_authorised)
    by_key = {(r['season'], int(r['GW'])): r for r in coverage}
    for report in reports:
        c = by_key.get((report['season'], report['gameweek']), {})
        report.update(history_rows=int(c.get('rows', 0)), matched_rows=int(c.get('matched', 0)),
                      known_rows=int(c.get('known', 0)), unmatched_rows=int(c.get('rows', 0)-c.get('matched', 0)))
    return result, reports


def prediction_hashes(rows, features, control, conditional, *, phase2_authorised=False):
    """Hash only key/position/features and predictions; never inspect outcomes."""
    scope(rows.season, phase2_authorised=phase2_authorised)
    if not rows.index.equals(features.index) or rows.duplicated(KEYS).any():
        raise ValueError('Canary alignment/keys')
    names = list(getattr(control, 'feature_names_in_', CORE_FEATURES))
    with threadpool_limits(limits=2):
        core = np.clip(control.predict(features[names]), 0, 20)
        pred = conditional.predict(features, rows.pos)
    arrays = {'control': core, **{name: pred[name].to_numpy() for name in ('core_xp', 'expected_points', 'p_play')}}
    hashes = {}
    for name, values in arrays.items():
        values = np.asarray(values, dtype=np.float64)
        if values.shape != (len(rows),) or not np.isfinite(values).all():
            raise ValueError('Invalid canary prediction')
        hashes[name] = hashlib.sha256(values.tobytes(order='C')).hexdigest()
    return dict(key_sha256=canonical_hash(rows[KEYS].to_dict('records')), rows=len(rows), prediction_sha256=hashes)


def verify_canary(rows, features, control, conditional, expected, *, phase2_authorised=False):
    got = prediction_hashes(rows, features, control, conditional, phase2_authorised=phase2_authorised)
    if got != expected:
        raise ValueError('Canary mismatch; scoring refused')
    return got


def forecasts(control, conditional):
    """Core forecasts and a3 full forecasts, never infer a missing full head."""
    if not {'core_xp', 'expected_points'} <= set(conditional):
        raise ValueError('Conditional expected_points required for gate 7')
    control = np.asarray(control, dtype=float)
    candidate = conditional.core_xp.to_numpy(float)
    full = conditional.expected_points.to_numpy(float)
    if any(v.shape != control.shape or not np.isfinite(v).all() for v in (candidate, full, control)):
        raise ValueError('Forecast shape or finiteness')
    return (dict(control=control, conditional=candidate, blend_equal=.5*control+.5*candidate),
            dict(control=control, conditional=full, blend_equal=.5*control+.5*full))


def decision(gates):
    if gates['conditional']['passed']:
        return 'conditional'
    if gates['blend_equal']['passed']:
        return 'blend_equal'
    return None


def official_outcomes(events, fixture_rows, *, phase2_authorised=False):
    """Decode supplied event-live fixture explains against an explicit fixture universe.

    fixture_rows supplies official schedule/identity metadata. Per-fixture stats
    come from explain, never from the event aggregate (which would double DGWs).
    """
    scope(fixture_rows.season, phase2_authorised=phase2_authorised)
    records = []
    for (season, gw), payload in events.items():
        scope([season], phase2_authorised=phase2_authorised)
        seen = set()
        for player in payload['elements']:
            if player['id'] in seen:
                raise ValueError('Duplicate event-live identity')
            seen.add(player['id'])
            for fixture in player['explain']:
                stats = fixture['stats']
                if len({v['identifier'] for v in stats}) != len(stats):
                    raise ValueError('Duplicate event-live stat')
                values = {v['identifier']: v['value'] for v in stats}
                if 'minutes' not in values:
                    raise ValueError('Event-live fixture minutes missing')
                records.append(dict(season=season, GW=gw, element=player['id'], fixture=fixture['fixture'],
                                    **values, total_points=sum(v['points'] for v in stats)))
    truth = pd.DataFrame(records)
    keys = ['season', 'GW', 'element', 'fixture']
    if truth.empty or truth.duplicated(keys).any() or fixture_rows.duplicated(keys).any():
        raise ValueError('Incomplete/duplicate event-live universe')
    joined = fixture_rows.merge(truth, on=keys, how='outer', validate='one_to_one', indicator=True)
    if not joined._merge.eq('both').all():
        raise ValueError('Event-live coverage differs from fixture universe')
    return joined.drop(columns='_merge')


def admit_outcomes(frame, bridges, calendar, expected_keys, *, phase2_authorised=False):
    """Admit supplied vaastav rows with explicit deadlines and complete keyed coverage."""
    scope(frame.season, phase2_authorised=phase2_authorised)
    scope(expected_keys.season, phase2_authorised=phase2_authorised)
    if frame.duplicated(['season', 'element', 'fixture']).any():
        raise ValueError('Duplicate outcome fixture')
    d = frame.copy()
    d['fpl_code'] = 0
    for season in d.season.unique():
        bridge = bridges[season]
        if bridge.id.duplicated().any() or bridge.code.duplicated().any():
            raise ValueError('Ambiguous outcome bridge')
        ix = d.season.eq(season)
        d.loc[ix, 'fpl_code'] = integer_codes(d.loc[ix, 'element'].map(bridge.set_index('id').code))
    d['fpl_code'] = integer_codes(d.fpl_code)
    clocks = {(r['season'], int(r['gameweek'])): r for r in calendar}
    supplied_cutoff = 'cutoff' in d
    for key, group in d.groupby(['season', 'GW']):
        if key not in clocks or clocks[key].get('status') == 'no_fixtures':
            raise ValueError('Outcome calendar coverage')
    deadlines = pd.Series([utc(clocks[(s, int(g))]['deadline'])
                           for s, g in zip(d.season, d.GW)], index=d.index)
    if supplied_cutoff and not d.cutoff.map(utc).eq(deadlines).all():
        raise ValueError('Outcome deadline mismatch')
    d['cutoff'] = deadlines
    for name in ('minutes', 'total_points'):
        values = pd.to_numeric(d[name], errors='raise').to_numpy(float)
        if not np.isfinite(values).all() or not np.equal(values, np.floor(values)).all():
            raise ValueError('Invalid official outcome')
    if not d.minutes.between(0, 90).all():
        raise ValueError('Invalid fixture minutes')
    d = normalise(d)
    actual = pd.MultiIndex.from_frame(d[KEYS])
    expected = pd.MultiIndex.from_frame(expected_keys[KEYS])
    if actual.has_duplicates or expected.has_duplicates or set(actual) != set(expected):
        raise ValueError('Incomplete outcome keys')
    return d


def asof_features(history, targets, *, phase2_authorised=False):
    scope(history.season, phase2_authorised=phase2_authorised)
    scope(targets.season, phase2_authorised=phase2_authorised)
    # The released CORE correction applies only to 2022-23. Each FeatureStore
    # resets by season, so historical corrections cannot alter 2026-27 rows.
    masked = history.copy()
    if targets.season.eq('2022-23').any():
        from core_xg_mask import mask_history
        masked, _ = mask_history(history)
    features = FeatureStore(masked).transform(targets)
    has_source = features.source_max_ts.notna()
    if (features.loc[has_source, 'source_max_ts'] >= targets.loc[has_source, 'cutoff']-pd.Timedelta(hours=3)).any():
        raise ValueError('As-of history crosses completion buffer')
    return features[CORE_FEATURES+[n for n in DC_FEATURES if n not in CORE_FEATURES]]


def score(frame, bridges, calendar, expected_keys, airsenal, snapshots, control, conditional,
          canary_rows, canary_features, canary_record, *, evidence_root,
          season='2026-27', opening_gw=10, phase2_authorised=False):
    """Compose the one-shot scorer from explicit offline admitted inputs.

    frame is vaastav-format (or the output of official_outcomes), including
    pre-window history. All writes are aggregate receipts under evidence_root.
    The caller must supply the independent complete outcome-key universe.
    """
    scope([season], phase2_authorised=phase2_authorised)
    if season == '2026-27' and opening_gw != 10:
        raise ValueError('First prospective GW differs from registered GW10')
    scope(frame.season, phase2_authorised=phase2_authorised)
    root = checked_path(evidence_root, season, phase2_authorised=phase2_authorised).resolve()
    canary = verify_canary(canary_rows, canary_features, control, conditional, canary_record,
                           phase2_authorised=phase2_authorised)
    d = admit_outcomes(frame, bridges, calendar, expected_keys, phase2_authorised=phase2_authorised)
    declared = {int(r['gameweek']) for r in calendar if r['season'] == season}
    if not set(range(opening_gw, 39)) <= declared:
        raise ValueError('Incomplete phase2 calendar')
    features = asof_features(d, d, phase2_authorised=phase2_authorised)
    obs, sources = choose_sources(calendar, airsenal, snapshots, bridges, d, phase2_authorised=phase2_authorised)
    features, coverage = augment(d, features, bridges, obs, phase2_authorised=phase2_authorised)
    test = d.season.eq(season) & d.GW.between(opening_gw, 38)
    rows, x = d.loc[test], features.loc[test]
    with threadpool_limits(limits=2):
        core = np.clip(control.predict(x[list(getattr(control, 'feature_names_in_', CORE_FEATURES))]), 0, 20)
        pred = conditional.predict(x, rows.pos)
    core, full = forecasts(core, pred)
    reports = {name: evaluate(rows, x[CORE_FEATURES], values) for name, values in core.items()}
    squads = fixed_squad(d, features, core, season, opening_gw, phase2_authorised=phase2_authorised)
    totals = rows[['season', 'GW', 'element', 'total_points']].assign(**full).groupby(['season', 'GW', 'element']).sum()
    full_rmse = {a: float(np.sqrt(np.mean((totals[a]-totals.total_points)**2))) for a in full}
    pool = candidate_mask(x)
    paired = rows.loc[pool, ['season', 'GW', 'element', 'points_core']].assign(
        **{a: v[pool.to_numpy()] for a, v in core.items()}).groupby(['season', 'GW', 'element']).sum().reset_index().rename(
            columns={'GW': 'gameweek', 'points_core': 'actual'})
    gates, intervals = {}, {}
    for arm in ('conditional', 'blend_equal'):
        interval = paired_block_errors(paired, arm, 'control')
        if interval['status'] != 'descriptive_interval':
            raise ValueError('Insufficient contiguous weeks for descriptive interval')
        intervals[arm] = interval
        units = lambda a: {u: reports[a]['candidate_'+u] for u in ('player_gw', 'fixture')}
        gates[arm] = phase2_gates(units(arm), units('control'), float(np.mean(squads['deltas'][arm])),
            full_rmse[arm], full_rmse['control'], [interval['rmse']['lower'], interval['rmse']['upper']])
    report = dict(gates=gates, promotion_eligible=decision(gates), candidates_tested=2,
        automatic_promotion=False, metrics=reports, full_player_gw_rmse=full_rmse,
        fixed_squads=squads, block_intervals=intervals, sources=sources, coverage=coverage, canary=canary)
    root.mkdir(parents=True, exist_ok=True)
    target = root/'phase2-report.json'
    if not target.resolve().is_relative_to(root):
        raise ValueError('Evidence path escapes root')
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return report
