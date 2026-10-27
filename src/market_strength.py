"""Past-match market ratings; research only, never an approved model/default.

Raw target-match odds are deliberately absent from the projection API.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math

import numpy as np
from scipy.optimize import least_squares
from scipy.stats import poisson, skellam

LAMBDA_BOUNDS = (.05, 6.)
WINDOW_DAYS = 730
HALF_LIFE_DAYS = 120
RIDGE = 2.
COLUMN_GROUPS = {
    'one_x_two': (('AvgCH', 'AvgCD', 'AvgCA'), ('AvgH', 'AvgD', 'AvgA')),
    'over_under': (('AvgC>2.5', 'AvgC<2.5'), ('Avg>2.5', 'Avg<2.5')),
}
NAME_MAP = {name:name for name in (
    'Arsenal', 'Aston Villa', 'Bournemouth', 'Brentford', 'Brighton', 'Burnley',
    'Chelsea', 'Crystal Palace', 'Everton', 'Fulham', 'Leeds', 'Leicester',
    'Liverpool', 'Luton', 'Man City', 'Newcastle', 'Norwich', "Nott'm Forest",
    'Southampton', 'Watford', 'West Brom', 'West Ham', 'Wolves')}
NAME_MAP.update({'Man United':'Man Utd', 'Sheffield United':'Sheffield Utd', 'Tottenham':'Spurs'})


def timestamp(value):
    t = datetime.fromisoformat(value.replace('Z','+00:00')) if isinstance(value,str) else value
    if not isinstance(t,datetime) or t.tzinfo is None:
        raise ValueError('Timezone-aware timestamp required')
    return t.astimezone(timezone.utc)


def proportional(odds):
    a = np.asarray(odds,dtype=float)
    if a.ndim != 1 or len(a) < 2 or not np.isfinite(a).all() or (a<=1).any():
        raise ValueError('Complete finite decimal odds greater than one required')
    inv = 1/a
    return inv/inv.sum()


def market_probabilities(row):
    """Prefer a complete closing group; never splice bookmakers or missing cells."""
    result = {}; columns = {}
    for label, groups in COLUMN_GROUPS.items():
        for group in groups:
            try:
                values = proportional([float(row.get(k,'')) for k in group])
            except (ValueError,TypeError):
                continue
            result[label] = values; columns[label] = list(group)
            break
        else:
            raise ValueError('No admitted '+label+' odds')
    return np.array([result['one_x_two'][0],result['one_x_two'][2],result['over_under'][0]]), columns


def probabilities(home,away):
    if not all(math.isfinite(x) and x>0 for x in (home,away)):
        raise ValueError('Positive finite Poisson means required')
    return np.array([skellam.sf(0,home,away),skellam.cdf(-1,home,away),poisson.sf(2,home+away)])


def solve_lambdas(target):
    target = np.asarray(target,dtype=float)
    if target.shape != (3,) or not np.isfinite(target).all() or ((target<0)|(target>1)).any() or target[0]+target[1]>1:
        raise ValueError('Invalid home/away/over probability triple')
    fit = least_squares(lambda a:probabilities(*a)-target, np.array([1.35,1.35]),
                        bounds=LAMBDA_BOUNDS,ftol=1e-12,xtol=1e-12,gtol=1e-12,
                        max_nfev=200,method='trf')
    if not fit.success or not np.isfinite(fit.x).all():
        raise ValueError('Bounded lambda solver did not converge')
    residual = probabilities(*fit.x)-target
    return dict(lambda_home=float(fit.x[0]),lambda_away=float(fit.x[1]),
                squared_error=float(residual@residual),max_absolute_residual=float(abs(residual).max()),
                residual=residual.tolist(),nfev=int(fit.nfev),solver_status=int(fit.status))


def canonical_name(name):
    try: return NAME_MAP[name]
    except KeyError as e: raise ValueError('Unmapped market team: '+str(name)) from e


def match_fixture(season,date,home,away,fixtures):
    key = (season,date,canonical_name(home),canonical_name(away))
    if key not in fixtures:
        raise ValueError('No exact date/teams FPL fixture: '+str(key))
    return fixtures[key]


@dataclass(frozen=True)
class Rating:
    cutoff: datetime
    mu: float
    home_advantage: float
    attack: dict
    defence: dict
    source_max: datetime
    matches: int


def fit_ratings(matches,cutoff,*,target_match=None):
    """Reject unsafe input, then use only its 730-day strictly prior window."""
    cutoff=timestamp(cutoff);rows=[];seen=set()
    for row in matches:
        when=timestamp(row['kickoff'])
        if when>=cutoff: raise ValueError('Match kickoff must be strictly before cutoff')
        key=(row['season'],row['fixture'])
        if key==target_match: raise ValueError('Target-match odds are prohibited')
        if key in seen: raise ValueError('Duplicate market match identity')
        seen.add(key)
        if when < cutoff-timedelta(days=WINDOW_DAYS): continue
        if row['home']==row['away']: raise ValueError('Same-team fixture')
        if not all(math.isfinite(row[k]) and LAMBDA_BOUNDS[0]<=row[k]<=LAMBDA_BOUNDS[1]
                   for k in ('lambda_home','lambda_away')): raise ValueError('Invalid source lambda')
        rows.append((row,when))
    if not rows: raise ValueError('No market history; do not invent league parameters')
    clubs=sorted({row[k] for row,_ in rows for k in ('home','away')});index={n:i for i,n in enumerate(clubs)}
    n=len(clubs);x=[];y=[];weights=[]
    for row,when in rows:
        for home,team,opp,mean in [(1,row['home'],row['away'],row['lambda_home']),
                                  (0,row['away'],row['home'],row['lambda_away'])]:
            design=np.zeros(2+2*n);design[:2]=[1,home];design[2+index[team]]=1;design[2+n+index[opp]]=-1
            x.append(design);y.append(math.log(mean));weights.append(.5**((cutoff-when).total_seconds()/86400/HALF_LIFE_DAYS))
    x=np.asarray(x);w=np.sqrt(weights);penalty=np.zeros((2*n,2+2*n));penalty[:,2:]=math.sqrt(RIDGE)*np.eye(2*n)
    coef=np.linalg.lstsq(np.vstack([x*w[:,None],penalty]),np.r_[np.asarray(y)*w,np.zeros(2*n)],rcond=None)[0]
    return Rating(cutoff,float(coef[0]),float(coef[1]),dict(zip(clubs,coef[2:2+n])),
                  dict(zip(clubs,coef[2+n:])),max(when for _,when in rows),len(rows))


def project(rating,team,opponent,home):
    if type(home) is not bool or not team or not opponent or team==opponent:
        raise ValueError('Invalid target fixture metadata')
    if rating.source_max>=rating.cutoff: raise ValueError('Future rating source')
    attack=rating.attack;defence=rating.defence
    own=math.exp(rating.mu+rating.home_advantage*home+attack.get(team,0)-defence.get(opponent,0))
    other=math.exp(rating.mu+rating.home_advantage*(not home)+attack.get(opponent,0)-defence.get(team,0))
    return dict(mkt_lambda_for=own,mkt_lambda_against=other,mkt_cs_prob=math.exp(-other),
                cold_start_team=team not in attack,cold_start_opponent=opponent not in attack)
