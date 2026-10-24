"""Explicit research-policy bridge from verified approved forecast weights.

No registry/default writes. Synthetic compatibility does not establish current
season accuracy or approve an experimental management policy for production.
"""
import hashlib
import io
import json
import joblib
import pandas as pd
from approved_horizon import project_approved
from decision_availability import project_probabilities
from forecast_sensitivity import apply_sensitivity
from model_registry import resolve_champion


def project_decision_approved(root, history, market, fixtures, *, through,
        receipt_path, receipt_sha256, source_as_of, source_hashes=None, review=None,
        bootstrap=None, bootstrap_as_of=None, allow_research_policy=False):
    if not allow_research_policy:
        raise ValueError('Explicit research-policy opt-in required')
    horizon, report = project_approved(root, history, market, fixtures, through=through,
        receipt_path=receipt_path, receipt_sha256=receipt_sha256, source_as_of=source_as_of,
        source_hashes=source_hashes, review=review, bootstrap=bootstrap, bootstrap_as_of=bootstrap_as_of)
    artifact, version, record = resolve_champion(root)
    raw = artifact.read_bytes()
    if hashlib.sha256(raw).hexdigest() != report['artifact_sha256'] or record['sha256'] != report['artifact_sha256']:
        raise ValueError('Approved model changed between mean and appearance views')
    model = joblib.load(io.BytesIO(raw))
    if model.metadata.get('version') != version or getattr(model, 'requires_availability', False):
        raise ValueError('Unadmitted approved appearance-head interface')
    targets = []
    for player in market.players:
        team = int(player['team'])
        for f in fixtures.itertuples():
            if pd.isna(f.event) or f.event not in horizon.gameweeks or team not in (f.team_h, f.team_a):
                continue
            targets.append((player['id'], int(f.event)))
    overrides = report['applied_overrides']

    class View:
        # This is a conservative verified-existence upper bound, not a fabricated
        # original fit timestamp or a change to the saved artifact metadata.
        metadata = dict(trained_through=report['model_observed_by'],
                        approval='Research appearance view of verified approved weights')

        def predict(self, x, pos):
            values = model.predict(x, pos).copy()
            if len(values) != len(targets):
                raise ValueError('Approved mean/appearance target order differs')
            for index, (i, g) in zip(values.index, targets):
                if g == market.gameweek and i in overrides:
                    adjusted = apply_sensitivity(values.loc[index].to_dict(), overrides[i])
                    for key, value in adjusted.items():
                        values.loc[index, key] = value
            return values

    hard_zero = {i for i, override in overrides.items()
                 if override.get('minutes') == 0 or override.get('availability') == 0}
    rows, appearance_report = project_probabilities(View(), history, market, fixtures,
        horizon, official_zero_ids=hard_zero)
    provenance = dict(horizon.provenance)
    provenance['source_hashes'] = dict(provenance['source_hashes'])
    payload = dict(rows=[dict(r) for r in horizon.forecasts], provenance=provenance)
    mean_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()
    calendar_hash = hashlib.sha256(fixtures[['id', 'event', 'team_h', 'team_a', 'kickoff_time']].to_json(orient='records', date_format='iso').encode()).hexdigest()
    availability = dict(gameweek=market.gameweek, as_of=market.as_of,
        trained_through=report['model_observed_by'], model_sha256=record['sha256'],
        decision_sha256=mean_hash, calendar_sha256=calendar_hash, rows=rows,
        source_hashes=provenance['source_hashes'], report=appearance_report,
        identity_scope='decision hash is canonical approved mean horizon; calendar hash is canonical admitted five-field view, not original source bytes')
    return horizon, availability, dict(report, appearance=appearance_report,
        research_policy_opt_in=True, forecaster_weights_unchanged=True,
        production_policy_approved=False,
        scope='Mechanical optional-policy compatibility only; manual current-GW sensitivities retained; no new calibration/accuracy or automatic default approval')
