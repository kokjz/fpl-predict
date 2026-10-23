"""Declared expected-net-season-points criteria, not a significance test.

Every case is retained. Openings are nested within seasons, not independent
football seasons; this small historical study produces no confidence interval.
"""
import argparse
import json
import math
from pathlib import Path
from statistics import mean,median


def evaluate(rows,protocol,*,integrity_verified):
    if type(integrity_verified) is not bool:raise ValueError('Explicit integrity verdict required')
    seasons=protocol['seasons'];seeds=protocol['opening_seeds'];policies=protocol['policies']
    expected={(s,n,p) for s in seasons for n in seeds for p in policies};by={}
    for row in rows:
        key=(row['season'],row['seed'],row['policy'])
        if key in by or key not in expected:raise ValueError('Duplicate/undeclared case')
        if row['status']!='completed' or type(row['net_points']) not in (int,float) or not math.isfinite(row['net_points']):
            raise ValueError('Incomplete/nonfinite case; never omit losing/failing arms')
        by[key]=float(row['net_points'])
    if set(by)!=expected or len(by)!=protocol['paths']:raise ValueError('Missing declared cases')
    criteria=protocol['decision_framework'];season_limit=criteria['material_season_loss_limit'];case_limit=criteria['material_single_opening_loss_limit']
    if (type(season_limit) not in (int,float) or type(case_limit) not in (int,float)
            or not math.isfinite(season_limit) or not math.isfinite(case_limit) or season_limit<0 or case_limit<0):raise ValueError('Invalid downside allowances')
    result={}
    for control in (policies[0],policies[2]):
        pairs=[dict(season=s,seed=n,difference=by[s,n,policies[1]]-by[s,n,control]) for s in seasons for n in seeds]
        means={s:mean(r['difference'] for r in pairs if r['season']==s) for s in seasons}
        values=[r['difference'] for r in pairs];overall=mean(means.values())
        result[control]=dict(pairs=pairs,season_means=means,equal_season_mean=overall,median_opening_gain=median(values),
            worst_opening_gain=min(values),wins=sum(v>0 for v in values),ties=sum(v==0 for v in values),losses=sum(v<0 for v in values),
            material_losses=sum(v< -season_limit for v in values),material_loss_definition=f'opening loss exceeding {season_limit}points',
            material_loss_frequency=sum(v< -season_limit for v in values)/len(values),
            research_support=integrity_verified and overall>0 and min(means.values())>=-season_limit and min(values)>=-case_limit,
            interpretation='Declared descriptive historical support only; no confidence/significance or automatic policy/model promotion')
    return dict(schema_version=1,integrity_verified=integrity_verified,comparisons=result,seasons=len(seasons),openings_per_season=len(seeds),
        old_zero_negative_gate_unchanged=True,policy_promotion=False,model_promotion=False,
        uncertainty='Two previously inspected outcome seasons; starting cases within each season are dependent. No IID-week or opening-as-season inference.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for field in ('rows','protocol','output'):p.add_argument('--'+field,type=Path,required=True)
    p.add_argument('--integrity-verified',action='store_true');a=p.parse_args()
    if a.output.exists():p.error('Output exists; preserve previous assessments')
    result=evaluate(json.loads(a.rows.read_text()),json.loads(a.protocol.read_text()),integrity_verified=a.integrity_verified)
    with a.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)


if __name__=='__main__':main()
