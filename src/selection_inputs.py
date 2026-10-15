"""Offline adapters for selection research; inputs stay in the chosen workspace."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from deadline_provenance import extract_bootstrap, read_snapshot, replay_event_assignments
from experiment_runner import file_hash


def native_market(predictions, players, manifest, snapshot_root, calendar_audit, calendar_root, models):
    """Rebuild a listed market using checked bootstraps and as-of assignments.

    Only positively verified club blanks may be zero-filled. Snapshot captures
    and manually transcribed announcements are provenance claims, not an
    independent historical data-availability certificate.
    """
    if predictions.duplicated(['season','gameweek','fixture','fpl_code']).any(): raise ValueError('Duplicate forecast fixture')
    p = players.copy(); p['ts'] = pd.to_datetime(p.ts,utc=True)
    target = predictions.copy()
    if target.season.nunique() != 1: raise ValueError('One season required')
    if str(target.season.iloc[0]) != manifest['season']: raise ValueError('Season mismatch')
    output = []; evidence = []
    for gw, forecasts in target.groupby('gameweek',sort=True):
        entries = [s for s in manifest['snapshots'] if s['gameweek'] == gw]
        if len(entries) != 1: raise ValueError('Ambiguous/missing capture')
        entry = entries[0]; path = (Path(snapshot_root)/entry['file']).resolve()
        if not path.is_relative_to(Path(snapshot_root).resolve()): raise ValueError('Escaping snapshot path')
        boot = read_snapshot(path,entry['sha256'])
        info, _ = extract_bootstrap(boot,manifest['season'],int(gw),entry['captured_at'])
        cutoff = pd.Timestamp(entry['captured_at']); deadline = pd.Timestamp(info['deadline'])
        available = [b for b in calendar_audit['base_screens'] if pd.Timestamp(b['captured_at']) < cutoff]
        if not available: raise ValueError('No pre-capture fixture base')
        base = max(available,key=lambda b:pd.Timestamp(b['captured_at']))
        base_path = Path(calendar_root)/base['file']
        if not base_path.resolve().is_relative_to(Path(calendar_root).resolve()) or file_hash(base_path) != base['sha256']:
            raise ValueError('Fixture base checksum/path')
        fixtures = pd.read_csv(base_path)
        updates = [u for u in calendar_audit['updates'] if pd.Timestamp(u['available_at']) > pd.Timestamp(base['captured_at'])]
        assignments = replay_event_assignments(fixtures,base['captured_at'],updates,cutoff)
        fixture_ids = set(assignments.loc[assignments.event.eq(gw),'id'].astype(int))
        if fixture_ids != set(forecasts.fixture.astype(int)): raise ValueError('As-of membership differs from scored fixtures')
        current = fixtures[fixtures.id.isin(fixture_ids)]
        counts = pd.concat([current.team_h,current.team_a]).value_counts().to_dict()
        names = {t['id']:t['name'] for t in boot['teams']}
        raw = p[p.season.astype(str).eq(str(target.season.iloc[0])) & p.gameweek.eq(gw)]
        if set(raw.fixture.astype(int)) != fixture_ids: raise ValueError('Outcome fixture mismatch')
        if raw.duplicated(['fixture','fpl_code']).any(): raise ValueError('Duplicate raw outcome')
        paired = forecasts.merge(raw[['fixture','fpl_code','total_points','minutes','yellow_cards','red_cards','position','team_name']],
                                on=['fixture','fpl_code'],validate='one_to_one',suffixes=('','_raw'))
        if (len(paired) != len(forecasts) or not np.allclose(paired.actual,paired.total_points) or
                not np.allclose(paired.minutes,paired.minutes_raw) or not np.allclose(paired.position,paired.position_raw)):
            raise ValueError('Forecast/outcome conflict')
        paired['cards'] = paired.yellow_cards+paired.red_cards
        aggregate = paired.groupby('fpl_code').agg({**{m:'sum' for m in models},'actual':'sum','minutes':'sum','cards':'sum'})
        prior = p[p.ts < cutoff-pd.Timedelta(hours=3)].sort_values('ts').groupby('fpl_code').tail(4).groupby('fpl_code').minutes.mean()
        blanks = 0
        for element in boot['elements']:
            if element['element_type'] not in (1,2,3,4): continue
            code = element['code']; club = names[element['team']]; count = int(counts.get(element['team'],0))
            if count == 0:
                values = {k:0. for k in [*models,'actual','minutes','cards']}; blanks += 1
                if code in aggregate.index and (aggregate.loc[code].abs()>1e-10).any(): raise ValueError('Blank has nonzero data')
            else:
                if code not in aggregate.index: raise ValueError('Unexplained missing played-club forecast')
                rows = paired[paired.fpl_code.eq(code)]
                if set(rows.fixture.astype(int)) != set(current.loc[current.team_h.eq(element['team']) | current.team_a.eq(element['team']),'id']):
                    raise ValueError('Incomplete club/player fixture coverage')
                if not rows.team_name.eq(club).all() or not rows.position.eq(element['element_type']).all(): raise ValueError('Roster conflict')
                values = aggregate.loc[code].to_dict()
            output.append(dict(season=manifest['season'],gameweek=int(gw),deadline=deadline.isoformat(),inputs_as_of=cutoff.isoformat(),
                fpl_code=int(code),position=element['element_type'],team=club,price_tenths=element['now_cost'],
                can_buy=int(element['can_select']),prior_minutes=float(prior.get(code,0)),ownership=float(element['selected_by_percent']),
                fixture_count=count,blank_verified=int(count == 0),**values))
        evidence.append(dict(gameweek=int(gw),snapshot_sha256=entry['sha256'],base_sha256=base['sha256'],
                             fixtures=len(fixture_ids),listed=len(boot['elements']),verified_blank_players=blanks))
    return pd.DataFrame(output),dict(weeks=evidence,independent_availability_certified=False,
        caveats=['Snapshot-quote execution approximation','Publisher capture claims/manual schedule announcements',
                 'Forecast history availability is separately audited; mutable corrected source limitations retained'])


def dastan_market(archive, players, models, lagged_prices):
    """Original archived forecasts, conditional weekly panels on exported coverage.

    Prices/club/minutes are strictly earlier raw rows. No claim of a complete
    predeadline market or verified missing-player blanks; no rolling finances.
    """
    raw = players[players.season.astype(str).eq('2024-25')].copy()
    raw['ts'] = pd.to_datetime(raw.ts,utc=True)
    mapping = {'GKP':1,'DEF':2,'MID':3,'FWD':4}
    archive = archive.copy(); archive['position'] = archive.position.map(mapping)
    if archive.position.isna().any() or archive.duplicated(['gameweek','fpl_code']).any(): raise ValueError('Archive identity conflict')
    lagged_prices = lagged_prices.copy()
    lagged_prices['ts'] = pd.to_datetime(lagged_prices.ts,utc=True)
    if lagged_prices.duplicated(['fpl_code','fixture']).any(): raise ValueError('Duplicate price source')
    result = []; audit = []
    for gw, week in archive.groupby('gameweek',sort=True):
        outcomes = raw[raw.gameweek.eq(gw)]
        # Historical canonical deadline is a reconstruction; expose that limit.
        deadline = pd.to_datetime(outcomes.deadline,utc=True).min()
        prior = raw[raw.ts < deadline-pd.Timedelta(hours=3)].sort_values('ts')
        last = prior.groupby('fpl_code').tail(1).set_index('fpl_code')
        means = prior.groupby('fpl_code').tail(4).groupby('fpl_code').minutes.mean()
        actuals = outcomes.groupby('fpl_code').agg(total_points=('total_points','sum'),minutes=('minutes','sum'),
            cards=('yellow_cards','sum'),reds=('red_cards','sum'),position=('position','first'))
        price_rows = lagged_prices[lagged_prices.ts < deadline-pd.Timedelta(hours=3)].sort_values('ts').groupby('fpl_code').tail(1).set_index('fpl_code')
        excluded = []
        for r in week.itertuples():
            if r.fpl_code not in actuals.index: raise ValueError('Unmatched archive outcome')
            if r.fpl_code not in last.index or r.fpl_code not in price_rows.index:
                excluded.append(int(r.fpl_code)); continue
            a = actuals.loc[r.fpl_code]; h = last.loc[r.fpl_code]
            if a.position != r.position or not np.isclose(a.total_points,r.actual) or not np.isclose(a.minutes,r.minutes):
                raise ValueError('Archived outcome conflict')
            result.append(dict(season='2024-25',gameweek=int(gw),deadline=deadline.isoformat(),
                inputs_as_of=(deadline-pd.Timedelta(seconds=1)).isoformat(),fpl_code=int(r.fpl_code),position=int(r.position),
                team=h.team_name,price_tenths=int(price_rows.loc[r.fpl_code,'value']),can_buy=1,prior_minutes=float(means.get(r.fpl_code,0)),
                ownership=0.,actual=float(a.total_points),minutes=float(a.minutes),cards=float(a.cards+a.reds),
                **{m:float(getattr(r,m)) for m in models}))
        audit.append(dict(gameweek=int(gw),exported_players=len(week),excluded_no_prior_metadata=excluded))
    return pd.DataFrame(result),dict(weeks=audit,scope='weekly owned panels conditional on original archive coverage',
        caveats=['Reconstructed cutoff, unequal original training/information history',
                 'Earlier fixture prices used only to sample panels, not historical execution quotes',
                 'Lagged club/appearance data; omitted players/blanks not zero-filled; no complete market claim'])
