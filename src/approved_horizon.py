"""Registry-approved artifact to origin-frozen research horizon integration."""
import datetime as dt
import hashlib
import json
import io
from pathlib import Path
import joblib
from availability_evidence import utc,scoped_overrides
from horizon_forecast import project
from model_registry import resolve_champion,digest
from native_solver_worker import read_json


def now_utc():return dt.datetime.now(dt.timezone.utc)


def observe_approved(root,destination):
    """Record current verified artifact existence; never invent its fit time."""
    artifact,version,record=resolve_champion(root)
    receipt=dict(schema_version=1,observed_at_utc=now_utc().isoformat(),champion=version,
        status=record['status'],artifact_sha256=record['sha256'],
        registry_sha256=digest(Path(root)/'model_registry.json'),
        interpretation='Existence observation is a conservative training-time upper bound, not an original fit timestamp or historical forecasting evidence.')
    with Path(destination).open('x') as stream:json.dump(receipt,stream,indent=2,allow_nan=False)
    return receipt


def project_approved(root,history,market,fixtures,*,through,receipt_path,receipt_sha256,
        source_as_of,source_hashes=None,review=None,bootstrap=None,bootstrap_as_of=None):
    """Load only verified approved bytes after origin/receipt admission.

    Source history/calendar admission belongs to their timestamped input adapter.
    A receipt proves only observed existence by a time. It cannot make a final
    deployment fit suitable for backtesting a season included in its training.
    Manual review uses the existing evidence schema and applies only to this GW.
    """
    receipt_path=Path(receipt_path)
    receipt_raw=receipt_path.read_bytes()
    if hashlib.sha256(receipt_raw).hexdigest()!=receipt_sha256:raise ValueError('Model observation receipt hash mismatch')
    receipt=read_json(receipt_raw)
    artifact,version,record=resolve_champion(root)
    if (receipt.get('schema_version'),receipt.get('status'),receipt.get('champion'),receipt.get('artifact_sha256'))!=(1,'approved',version,record['sha256']):raise ValueError('Model observation differs from approved champion')
    origin=utc(market.as_of);observed=utc(receipt['observed_at_utc'])
    if observed>=origin or utc(source_as_of)>origin:raise ValueError('Late model observation or source')
    overrides={};review_gw=None;hashes=dict(source_hashes or {});latest=utc(source_as_of)
    if review is not None:
        if bootstrap is None or bootstrap_as_of is None or utc(bootstrap_as_of)>origin:raise ValueError('Require origin-safe review bootstrap')
        events=[e for e in bootstrap['events'] if e['id']==review.get('GW')]
        if type(review.get('GW')) is not int or review['GW']!=market.gameweek or len(events)!=1 or utc(events[0]['deadline_time'])!=utc(market.deadline):raise ValueError('Availability review origin differs')
        review_gw,recorded,overrides=scoped_overrides(review,bootstrap,origin)
        event=next(e for e in bootstrap['events'] if e['id']==review_gw)
        if review_gw!=market.gameweek or utc(event['deadline_time'])!=utc(market.deadline):raise ValueError('Availability review origin differs')
        if not set(overrides)<={p['id'] for p in market.players}:raise ValueError('Review player missing from admitted market')
        latest=max(latest,recorded,utc(bootstrap_as_of))
        hashes['availability_review_canonical_json']=hashlib.sha256(json.dumps(review,sort_keys=True,allow_nan=False).encode()).hexdigest()
        hashes['availability_bootstrap_canonical_json']=hashlib.sha256(json.dumps(bootstrap,sort_keys=True,allow_nan=False).encode()).hexdigest()
    hashes.update(model_observation=receipt_sha256,approved_artifact=record['sha256'])
    artifact_raw=artifact.read_bytes()
    if hashlib.sha256(artifact_raw).hexdigest()!=record['sha256']:raise ValueError('Model bytes changed before loading')
    model=joblib.load(io.BytesIO(artifact_raw))
    if model.metadata.get('version')!=version:raise ValueError('Registry/model version mismatch')
    horizon,report=project(model,history,market,fixtures,through=through,
        trained_through=observed.isoformat(),source_as_of=latest.isoformat(),model_id='approved-'+version,
        source_hashes=hashes,availability_overrides=overrides,override_gameweek=review_gw)
    return horizon,dict(report,champion=version,artifact_sha256=record['sha256'],
        model_observed_by=observed.isoformat(),training_clock_scope='Conservative observation upper bound; not original fit time',
        review_gameweek=review_gw,applied_overrides=overrides,
        scope='Approved artifact mechanical integration; no new forecast or policy qualification from this interface')
