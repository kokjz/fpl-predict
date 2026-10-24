"""Origin-only appearance sidecars for the fixed decision-value experiment.

No training or registry selection takes place. The supplied trusted prior model,
history, calendar and original means must have separately verified source hashes.
"""
import numpy as np
import pandas as pd
from availability_evidence import utc
from fpl_model import FeatureStore


def project_probabilities(model, history, market, fixtures, horizon, *, official_zero_ids=()):
    if (horizon.season, horizon.origin, horizon.as_of) != (market.season, market.gameweek, market.as_of):
        raise ValueError('Probability/mean origins differ')
    trained = model.metadata['trained_through']
    if utc(trained) >= utc(market.as_of):
        raise ValueError('Appearance model fit is after the origin')
    if str(model.metadata['approval']).lower().find('research') < 0:
        raise ValueError('Require the declared prior-only research reference')
    known = {r['id'] for r in market.players}
    zeros = set(official_zero_ids)
    if not zeros <= known:
        raise ValueError('Unknown official-zero identity')
    if set(['id', 'event', 'team_h', 'team_a', 'kickoff_time']) - set(fixtures) or fixtures.id.duplicated().any():
        raise ValueError('Invalid admitted calendar')
    targets = []
    for player in market.players:
        team = int(player['team'])
        for f in fixtures.itertuples():
            if pd.isna(f.event) or f.event not in horizon.gameweeks or team not in (f.team_h, f.team_a):
                continue
            targets.append(dict(element=player['id'], season=market.season, fixture=int(f.id),
                GW=int(f.event), pos=player['position'], team_id=team,
                opponent_team=int(f.team_a if team == f.team_h else f.team_h),
                was_home=team == f.team_h, cutoff=utc(market.as_of), kickoff_time=f.kickoff_time))
    cells = {(g, i): [] for g in horizon.gameweeks for i in known}
    means = {key: 0. for key in cells}
    source_max = None
    if targets:
        target = pd.DataFrame(targets)
        features = FeatureStore(history).transform(target)
        ts = pd.to_datetime(features.source_max_ts, utc=True)
        if (ts.notna() & ts.ge(pd.Timestamp(market.as_of)-pd.Timedelta(hours=3))).any():
            raise ValueError('Post-origin appearance features')
        source_max = ts.max().isoformat() if ts.notna().any() else None
        prediction = model.predict(features, target.pos)
        if not prediction.index.equals(features.index) or not np.isfinite(prediction[['p_play', 'expected_points']]).all().all():
            raise ValueError('Invalid appearance predictions')
        if not prediction.p_play.between(0, 1).all():
            raise ValueError('Invalid appearance marginal')
        for r, p, xp in zip(target.itertuples(), prediction.p_play, prediction.expected_points):
            key = (int(r.GW), int(r.element))
            cells[key].append(float(p))
            means[key] += float(xp)
    original_means = horizon.values()
    output = []
    max_error = 0.
    for (g, i), raw in sorted(cells.items()):
        official_zero = g == market.gameweek and i in zeros
        original = original_means[g, i]
        reproduced = 0. if official_zero else means[g, i]
        max_error = max(max_error, abs(reproduced-original))
        if abs(reproduced-original) > 1e-8:
            raise ValueError('Replayed mean differs; do not mix model/source vintages')
        p = 0. if official_zero else 1-float(np.prod([1-(.98*v+.01) for v in raw]))
        raw_p = 0. if official_zero else 1-float(np.prod([1-v for v in raw]))
        if p == 0 and original != 0:
            raise ValueError('Nonzero mean without admitted appearance support')
        output.append(dict(gameweek=g, id=i, p_play=p, raw_p_play=raw_p,
                           fixture_count=len(raw), official_zero=official_zero))
    return output, dict(source_max_ts=source_max, trained_through=trained,
        mean_reproduction_max_abs_error=max_error, fixture_rows=len(targets),
        probability_assumption='Fixed 1% symmetric mixture per fixture, independent fixtures/players; not calibrated news probabilities',
        scope='Historical prior-only appearance sidecar; unchanged original unconditional means; card-only event probability omitted')
