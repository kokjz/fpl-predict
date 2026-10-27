"""Frozen, no-fit appearance/return diagnostics; no policy or model promotion.

Use freeze() before evaluate(). All source paths/output belong to an explicit
private manifest. API separation is not a security boundary for untrusted code.
"""
from collections import defaultdict
from itertools import combinations
from pathlib import Path
import argparse
import gzip
import json
import math
from availability_evidence import utc
from experiment_runner import file_hash
from horizon_forecast import Horizon
from rolling_planner import _market
from season_engine import State, Market, Action, prepare

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT/'docs/coherence_protocol_2026-10-26.json'
ROLES = ('proposed_squad', 'starters', 'bench', 'captain_or_vice')


def read(path):
    with (gzip.open if str(path).endswith('.gz') else open)(path, 'rt') as stream:
        return json.load(stream)


def checked(entry):
    path = Path(entry['path'])
    if file_hash(path) != entry['sha256']:
        raise ValueError('Input checksum differs')
    return path


def private_new(path):
    path = Path(path).resolve()
    if path.exists() or path.is_relative_to(ROOT):
        raise ValueError('Require a new private output')
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def action(raw):
    return Action(**{k: tuple(v) if k in ('buys', 'sells', 'starters', 'bench') else v
                     for k, v in raw.items()})


def freeze(manifest, expected, output):
    if file_hash(manifest) != expected:
        raise ValueError('Manifest differs')
    m = read(manifest)
    protocol = read(PROTOCOL)
    if m['protocol_sha256'] != file_hash(PROTOCOL):
        raise ValueError('Protocol differs')
    required = {(s, n, p) for s in protocol['seasons'] for n in protocol['paths']['opening_seeds']
                for p in protocol['paths']['policies']}
    cases = m['paths']
    if len(cases) != len(required) or {(c['season'], c['seed'], c['policy']) for c in cases} != required:
        raise ValueError('Missing/duplicate declared case')
    if len({c['name'] for c in cases}) != len(cases):
        raise ValueError('Duplicate case identity')
    if any(c['repetition'] != 1 for c in cases):
        raise ValueError('Only the first declared identical repetition is admitted')
    origins = {}
    sources = {}
    for season in protocol['seasons']:
        source = m['references'][season]
        d = read(checked(source['decisions']))['weeks']
        a = read(checked(source['appearance']))['weeks']
        if len(d) != 38 or len(a) != 38:
            raise ValueError('Require complete origins')
        sources[season] = dict(decisions=source['decisions'], appearance=source['appearance'], outcomes=source['outcomes'])
        origins[season] = (d, a)
        previous = None
        for g, (spec, sidecar) in enumerate(zip(d, a), 1):
            market = Market.create(**spec['market'])
            horizon = Horizon.create(market, **spec['forecast'])
            if previous is not None and utc(market.as_of) <= previous:
                raise ValueError('Nonchronological origin inventory')
            previous = utc(market.deadline)
            if market.season != season or (market.gameweek, sidecar['gameweek']) != (g, g):
                raise ValueError('Origin inventory differs')
            if sidecar['as_of'] != market.as_of or utc(sidecar['trained_through']) >= utc(market.as_of):
                raise ValueError('Appearance clock differs/late')
            if sidecar['decision_sha256'] != source['decisions']['sha256']:
                raise ValueError('Appearance and mean lineage differ')
            keys = [(r['gameweek'], r['id']) for r in sidecar['rows']]
            if len(keys) != len(set(keys)) or set(keys) != set(horizon.values()):
                raise ValueError('Appearance coverage differs')
            xp = horizon.values()
            for row in sidecar['rows']:
                p, raw_p = row['p_play'], row['raw_p_play']
                if not all(math.isfinite(v) and 0 <= v <= 1 for v in (p,raw_p)) or p == 0 and xp[row['gameweek'],row['id']] != 0:
                    raise ValueError('Invalid or incoherent appearance marginal')
                if type(row['fixture_count']) is not int or row['fixture_count'] < 0 or type(row['official_zero']) is not bool:
                    raise ValueError('Invalid fixture/official-zero stratum')
    panels = []
    raw_hashes = {}
    for case in cases:
        d, _ = origins[case['season']]
        for g, spec in enumerate(d, 1):
            record_path = Path(case['directory'])/f'GW{g:02d}_decision.json'
            raw = read(checked(dict(path=str(record_path), sha256=case['decision_sha256'][str(g)])))
            raw_hashes[str(record_path)] = file_hash(record_path)
            market = Market.create(**spec['market'])
            horizon = Horizon.create(market, **spec['forecast'])
            if (raw['gameweek'], raw['inputs_as_of']) != (g, market.as_of) or raw['forecast_provenance'] != dict(horizon.provenance):
                raise ValueError('Saved decision source/origin differs')
            before = dict(raw['state_before'], total_points=0.)
            for field in ('holdings', 'used_chips'):
                before[field] = tuple(map(tuple, before[field]))
            state = State(**before)
            held = [i for i, _ in state.holdings]
            proposed = raw['provisional_actions']
            if len(proposed) != len(horizon.gameweeks) or proposed[0] != raw['action']:
                raise ValueError('Incomplete/changed provisional actions')
            for target, value in zip(horizon.gameweeks, proposed):
                proposal = action(value)
                prepared = prepare(state, _market(market, target, horizon.values()), proposal)
                panels.append(dict(case=case['name'], season=case['season'], seed=case['seed'],
                    policy=case['policy'], origin=g, target=target, held_before=held if target == g else [],
                    proposed_squad=sorted(p['id'] for p in prepared.squad), starters=list(proposal.starters),
                    bench=list(proposal.bench), captain_or_vice=[proposal.captain, proposal.vice]))
                state = prepared.state
    out = private_new(output)
    with gzip.open(out, 'xt') as stream:
        json.dump(dict(complete=True, evaluator_parsed=False, manifest_sha256=expected,
            protocol_sha256=file_hash(PROTOCOL), sources=sources, panels=panels,
            decision_sha256=raw_hashes, actual_cumulative_points_retained=False), stream,
            separators=(',', ':'), allow_nan=False)
    return dict(complete=True, sha256=file_hash(out), panels=len(panels), cases=len(cases), evaluator_parsed=False)


def probability_bin(p):
    for lo, hi in zip((0, .2, .5, .8, .95), (.2, .5, .8, .95, 1)):
        if p < hi or hi == 1:
            return f'{lo:g}:{hi:g}'
    raise ValueError('Invalid probability')


def return_bin(q):
    if q is None: return 'undefined_p0'
    if q < 0: return 'negative'
    for lo, hi in zip((0, 2, 4, 8, 12), (2, 4, 8, 12, 20)):
        if q < hi or hi == 20 and q == hi: return f'{lo}:{hi}'
    return 'above20'


def observation(mu, p, raw_p, hidden):
    actual, minutes, cards = (hidden[k] for k in ('actual', 'minutes', 'cards'))
    if not all(math.isfinite(v) for v in (mu, p, raw_p, actual, minutes, cards)) or not 0 <= p <= 1 or not 0 <= raw_p <= 1 or minutes < 0:
        raise ValueError('Invalid numeric observation')
    if p == 0 and mu != 0:
        raise ValueError('Nonzero unconditional mean with zero appearance')
    q = mu/p if p else None
    if q is not None and not math.isfinite(q): raise ValueError('Nonfinite conditional return')
    y = float(minutes > 0)
    residual = mu-actual
    conditional = y == 1 and q is not None
    qr = q-actual if conditional else 0.
    return [1., mu, actual, abs(residual), residual**2, p, y, (p-y)**2,
        raw_p, (raw_p-y)**2, float(q is not None), q if q is not None else 0.,
        float(conditional), abs(qr), qr**2, qr, float(y == 1 and p == 0),
        float(y == 0 and cards > 0), float(y == 0 and actual != 0)], q


class Metrics:
    def __init__(self):
        self.values = [0.]*19
        self.missing = 0
        self.minimum_q = None
        self.maximum_q = None

    def add(self, values, q):
        self.values = [a+b for a, b in zip(self.values, values)]
        if q is not None:
            self.minimum_q = q if self.minimum_q is None else min(q, self.minimum_q)
            self.maximum_q = q if self.maximum_q is None else max(q, self.maximum_q)

    def report(self):
        n, mu, actual, ae, se, p, y, brier, raw_p, raw_brier, nq, q, nc, qae, qse, qr, impossible, cards, nonzero = self.values
        div = lambda value, count: value/count if count else None
        return dict(n=int(n), missing_outcomes=self.missing, mean_points=div(mu,n), actual_mean=div(actual,n),
            point_bias=div(mu-actual,n), point_mae=div(ae,n), point_rmse=math.sqrt(se/n) if n else None,
            mean_probability=div(p,n), appearance_rate=div(y,n), probability_bias=div(p-y,n), brier=div(brier,n),
            raw_mean_probability=div(raw_p,n), raw_brier=div(raw_brier,n), implied_return_n=int(nq),
            mean_implied_return=div(q,nq), minimum_implied_return=self.minimum_q, maximum_implied_return=self.maximum_q,
            observed_played_n=int(y), conditional_scored_n=int(nc), conditional_bias=div(qr,nc),
            conditional_mae=div(qae,nc), conditional_rmse=math.sqrt(qse/nc) if nc else None,
            zero_probability_played=int(impossible), card_only_outcomes=int(cards), no_appearance_nonzero_points=int(nonzero))


def joint(rows):
    """Descriptive joint residuals; marginal miscalibration is not isolated."""
    expected = sum(1-r['p'] for r in rows)
    observed = sum(1-r['y'] for r in rows)
    result = dict(panels=1, no_shows_expected=expected, no_shows_observed=observed,
        independent_variance=sum(r['p']*(1-r['p']) for r in rows), count_squared_residual=(observed-expected)**2)
    pairs = {}
    for label in ('same_club', 'different_club'):
        ps = [(a,b) for a,b in combinations(rows,2) if (a['team']==b['team']) == (label=='same_club')]
        pairs[label] = dict(n=len(ps), residual_product=sum((a['y']-a['p'])*(b['y']-b['p']) for a,b in ps),
            predicted_joint=sum(a['p']*b['p'] for a,b in ps), observed_joint=sum(a['y']*b['y'] for a,b in ps))
    return result, pairs


def evaluate(frozen, expected, output):
    if file_hash(frozen) != expected: raise ValueError('Frozen memberships differ')
    frozen_data = read(frozen)
    if not frozen_data['complete'] or frozen_data['evaluator_parsed'] or frozen_data['protocol_sha256'] != file_hash(PROTOCOL):
        raise ValueError('Incomplete or changed frozen evidence')
    for name, sha in frozen_data['decision_sha256'].items(): checked(dict(path=name,sha256=sha))
    sources = frozen_data['sources']
    decisions = {s:read(checked(v['decisions']))['weeks'] for s,v in sources.items()}
    appearance = {s:read(checked(v['appearance']))['weeks'] for s,v in sources.items()}
    # First evaluator parsing: all membership panels above were already frozen.
    outcomes = {s:{int(g):{int(i):r for i,r in rows.items()} for g,rows in read(checked(v['outcomes']))['weeks'].items()} for s,v in sources.items()}
    panels = defaultdict(list)
    for panel in frozen_data['panels']: panels[panel['season'],panel['origin'],panel['target']].append(panel)
    metrics = defaultdict(Metrics)
    for season in sources:
        for lead in range(6):
            for dimension, categories in [('position',range(1,5)),('p_bin',['0:0.2','0.2:0.5','0.5:0.8','0.8:0.95','0.95:1']),
                ('q_bin',['negative','0:2','2:4','4:8','8:12','12:20','above20','undefined_p0']),('fixtures',[0,1,2,'3plus']),('official_zero',[False,True])]:
                for category in categories: metrics[f'{season}/lead{lead}/{dimension}/{category}']
    cell_count = 0
    joint_totals = {}
    joint_pairs = {}
    for season in sources:
        for spec, ap in zip(decisions[season], appearance[season]):
            origin = spec['market']['gameweek']
            by = {r['id']:r for r in spec['market']['rows']}
            probability = {(r['gameweek'],r['id']):r for r in ap['rows']}
            for forecast in spec['forecast']['rows']:
                target, i, mu = forecast['gameweek'], forecast['id'], forecast['expected_points']
                lead = target-origin
                if not 0 <= lead <= 5: raise ValueError('Undeclared forecast lead')
                p = probability[target,i]
                relevant = panels[season,origin,target]
                if len(relevant) != 6: raise ValueError('Incomplete case roles')
                roles = set()
                case_roles = []
                for panel in relevant:
                    if lead == 0 and i in panel['held_before']:
                        roles.add('held_before_any_current');case_roles.append((panel['case'],'held_before_current'))
                    for role in ROLES:
                        if i in panel[role]: roles.add(role+'_any');case_roles.append((panel['case'],role))
                q = mu/p['p_play'] if p['p_play'] else None
                prefix = f'{season}/lead{lead}'
                keys = [prefix+'/all_market',prefix+f'/position/{by[i]["position"]}',prefix+'/p_bin/'+probability_bin(p['p_play']),
                    prefix+'/q_bin/'+return_bin(q),prefix+'/fixtures/'+str(p['fixture_count'] if p['fixture_count']<3 else '3plus'),
                    prefix+'/status/'+str(by[i].get('status') or 'unknown'),prefix+'/official_zero/'+str(p['official_zero'])]
                keys += [prefix+'/role/'+role for role in roles]
                keys += [f'case/{name}/lead{lead}/{role}' for name,role in case_roles]
                hidden = outcomes[season].get(target,{}).get(i)
                cell_count += 1
                if hidden is None:
                    for key in keys: metrics[key].missing += 1
                    continue
                values, q = observation(mu,p['p_play'],p['raw_p_play'],hidden)
                for key in keys: metrics[key].add(values,q)
            for panel in panels[season,origin,origin]:
                rows = []
                for i in panel['proposed_squad']:
                    hidden = outcomes[season][origin].get(i)
                    if hidden is None: raise ValueError('Missing proposed-squad current result')
                    rows.append(dict(p=probability[origin,i]['p_play'],y=float(hidden['minutes']>0),team=by[i]['team']))
                values, pairs = joint(rows)
                key = panel['case']
                for k,v in values.items(): joint_totals.setdefault(key,defaultdict(float))[k] += v
                for label, pair in pairs.items():
                    for k,v in pair.items(): joint_pairs.setdefault(key+'/'+label,defaultdict(float))[k] += v
    out = private_new(output)
    result = dict(complete=True,protocol_sha256=file_hash(PROTOCOL),frozen_sha256=expected,
        forecast_cells=cell_count,cases=12,current_squad_panels=sum(int(v['panels']) for v in joint_totals.values()),
        metrics={k:v.report() for k,v in sorted(metrics.items())},joint_count_totals=joint_totals,joint_pair_totals=joint_pairs,
        new_fit=False,forecaster_weights_changed=False,production_approved=False,
        limits=['Two reused seasons; repeated paths and overlapping origins/players/role cohorts are dependent',
            'No significance/generalisation interval, no causal attribution; marginal miscalibration may mimic dependence',
            'Observed-player conditional errors are diagnostic, not ex-ante eligibility or an unconditional forecast comparison'])
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return dict(complete=True,forecast_cells=cell_count,current_squad_panels=result['current_squad_panels'],groups=len(metrics),sha256=file_hash(out))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['freeze','evaluate'])
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--sha256',required=True)
    parser.add_argument('--output',required=True,type=Path)
    a=parser.parse_args()
    print(json.dumps((freeze if a.phase=='freeze' else evaluate)(a.input,a.sha256,a.output)))


if __name__=='__main__': main()
