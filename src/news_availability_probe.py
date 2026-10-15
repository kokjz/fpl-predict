"""Fixed chronological appearance probe; no production model or account changes."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix,hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from availability_evidence import utc
from experiment_runner import file_hash

FORM=['last_minutes','last5_minutes','last5_appearance','history_count','days_since_last',
      'pos_1','pos_2','pos_3','pos_4']
ARMS=('form','form_chance','form_text','form_chance_text')


def prepare_frame(players, observations):
    """Join admitted observations to prior form; never guess missing GW outcomes.

    Call availability_history.admit_prefix and verify source/bootstrap hashes
    before this adapter. The supplied roster/fixture-history intersection is
    conditional coverage; audit counts separately from model fitting.
    """
    p=players[players.season.eq('2025-26')].copy();p['ts']=pd.to_datetime(p.ts,utc=True)
    if p.duplicated(['fixture','fpl_code']).any():raise ValueError('Duplicate fixture targets')
    if observations.duplicated(['gameweek','fpl_code']).any():raise ValueError('Duplicate observations')
    result=[];coverage=[]
    for gw,obs in observations.groupby('gameweek',sort=True):
        if obs.available_by.nunique()!=1 or obs.deadline.nunique()!=1:raise ValueError('Ambiguous publication')
        cutoff=utc(obs.available_by.iloc[0]);deadline=utc(obs.deadline.iloc[0])
        if cutoff>=deadline:raise ValueError('Late publication')
        past=p[p.ts.lt(cutoff-pd.Timedelta(hours=3)) & p.gameweek.ne(gw)].sort_values('ts')
        histories={int(code):g for code,g in past.groupby('fpl_code')}
        target=p[p.gameweek.eq(gw)].groupby('fpl_code').agg(actual_minutes=('minutes','sum'),position=('position','first'))
        omitted=0
        for r in obs.itertuples():
            if r.fpl_code not in target.index:omitted+=1;continue
            if int(target.loc[r.fpl_code,'position'])!=int(r.position):raise ValueError('Source/target position conflict')
            h=histories.get(int(r.fpl_code));last=h.tail(5) if h is not None else None
            n=len(h) if h is not None else 0
            mean_minutes=float(last.minutes.mean()) if n else 0.
            values=dict(last_minutes=float(h.minutes.iloc[-1]) if n else 0.,last5_minutes=mean_minutes,
                last5_appearance=float(last.minutes.gt(0).mean()) if n else 0.,history_count=min(n,12),
                days_since_last=min(60.,(cutoff-h.ts.iloc[-1]).total_seconds()/86400) if n else 60.)
            values.update({f'pos_{pos}':int(int(r.position)==pos) for pos in range(1,5)})
            result.append(dict(season='2025-26',gameweek=int(gw),fpl_code=int(r.fpl_code),deadline=deadline.isoformat(),
                published_at=cutoff.isoformat(),candidate=bool(n>=3 and mean_minutes>=45),
                actual_minutes=float(target.loc[r.fpl_code,'actual_minutes']),news=r.news,chance_label=r.chance_label,**values))
        coverage.append(dict(gameweek=int(gw),source_rows=len(obs),not_in_fixture_history=omitted,admitted=len(obs)-omitted))
    return pd.DataFrame(result),coverage


def validate(frame):
    needed=['season','gameweek','fpl_code','deadline','published_at','candidate','actual_minutes','news','chance_label',*FORM]
    if set(needed)-set(frame):raise ValueError('Missing probe columns')
    d=frame.copy()
    if d.empty or set(d.season) != {'2025-26'} or d.duplicated(['gameweek','fpl_code']).any():raise ValueError('Wrong/duplicate probe scope')
    for k in ('gameweek','fpl_code'):
        a=d[k].to_numpy(float)
        if not np.isfinite(a).all() or (a<1).any() or not (a==a.astype(int)).all():raise ValueError('Invalid identity')
    if not d.gameweek.between(4,38).all() or not d.candidate.isin([True,False]).all():raise ValueError('Invalid window/cohort')
    for k in FORM+['actual_minutes']:
        a=d[k].to_numpy(float)
        if not np.isfinite(a).all() or (a<0).any():raise ValueError('Invalid numeric probe input')
    chance=pd.to_numeric(d.chance_label,errors='raise')
    if ((chance.dropna()<0)|(chance.dropna()>100)).any() or not np.isfinite(chance.dropna()).all():raise ValueError('Invalid chance label')
    for deadline,published in zip(d.deadline,d.published_at):
        if utc(published)>=utc(deadline):raise ValueError('Source publication is not predeadline')
    if not d.news.map(lambda s:pd.isna(s) or isinstance(s,str)).all():raise ValueError('News must be text or unknown')
    d['news']=d.news.fillna('');return d.sort_values(['gameweek','fpl_code']).reset_index(drop=True)


def train_features(training, frames):
    """Vocabulary/scaling learn from training only; no test-time fitting."""
    scaler=StandardScaler().fit(training[FORM])
    text=TfidfVectorizer(max_features=256,min_df=2,ngram_range=(1,2),sublinear_tf=True)
    text.fit(training.news.map(lambda s:s if str(s).strip() else 'unknown_news'))
    output=[]
    for d in frames:
        form=csr_matrix(scaler.transform(d[FORM]))
        chance=d.chance_label.to_numpy(float);missing=np.isnan(chance)
        signals=csr_matrix(np.column_stack([np.where(missing,0,chance/100),missing.astype(float)]))
        news=text.transform(d.news.map(lambda s:s if str(s).strip() else 'unknown_news'))
        output.append(dict(form=form,form_chance=hstack([form,signals],format='csr'),
            form_text=hstack([form,news],format='csr'),form_chance_text=hstack([form,signals,news],format='csr')))
    return output,dict(vocabulary_size=len(text.vocabulary_),max_features=256,training_only_transforms=True)


def metrics(frame, probabilities):
    result={}; y=frame.actual_minutes.gt(0).to_numpy(float)
    for name,mask in [('all',np.ones(len(frame),bool)),('candidates',frame.candidate.to_numpy(bool))]:
        target=y[mask];p=np.asarray(probabilities)[mask];high=p>=.8
        bins=[]
        for lo,hi in [(0,.5),(.5,.8),(.8,.95),(.95,1.0000001)]:
            ix=(p>=lo)&(p<hi)
            bins.append(dict(lower=lo,upper=min(hi,1),n=int(ix.sum()),
                mean_probability=float(p[ix].mean()) if ix.any() else None,
                actual_rate=float(target[ix].mean()) if ix.any() else None))
        result[name]=dict(n=len(target),brier=float(np.mean((p-target)**2)) if len(target) else None,
            high_probability_n=int(high.sum()),high_probability_nonappearances=int((target[high]==0).sum()),reliability=bins)
    return result


def run(frame):
    d=validate(frame); train=d[d.gameweek.le(19)];validation=d[d.gameweek.between(20,27)];test=d[d.gameweek.ge(28)]
    if any(g.empty for g in (train,validation,test)) or train.actual_minutes.gt(0).nunique()!=2:raise ValueError('Insufficient chronological/class coverage')
    features,transform=train_features(train,[train,validation,test]);predictions=test[['season','gameweek','fpl_code','candidate','actual_minutes']].copy()
    summary={}; y=train.actual_minutes.gt(0).astype(int)
    with threadpool_limits(limits=2):
        for arm in ARMS:
            model=LogisticRegression(C=1,solver='liblinear',max_iter=300,random_state=20261016)
            model.fit(features[0][arm],y)
            if int(model.n_iter_.max())>=300:raise ValueError('Probe did not converge; do not silently report partial fit')
            v=model.predict_proba(features[1][arm])[:,1];p=model.predict_proba(features[2][arm])[:,1]
            summary[arm]=dict(validation=metrics(validation,v),test=metrics(test,p));predictions[arm]=p
    # Paired whole-GW resampling for the one declared source-rich versus form contrast.
    candidates=predictions[predictions.candidate]; yy=candidates.actual_minutes.gt(0).astype(float)
    gap=(candidates.form_chance_text-yy)**2-(candidates.form-yy)**2
    weekly=pd.DataFrame({'gw':candidates.gameweek,'gap':gap}).groupby('gw').gap.mean()
    rng=np.random.default_rng(20261016);n=len(weekly);length=min(4,n)
    starts=rng.integers(0,n,size=(4000,int(np.ceil(n/length))));ii=((starts[:,:,None]+np.arange(length))%n).reshape(4000,-1)[:,:n]
    interval=np.quantile(weekly.to_numpy()[ii].mean(axis=1),[.025,.975]).tolist()
    report=dict(schema_version=1,scope='Retrospective fixed news/availability appearance probe, not incumbent/Dastan reproduction',
        training_rows=len(train),validation_rows=len(validation),test_rows=len(test),arms=summary,transforms=transform,
        declared_primary=dict(contrast='form_chance_text minus form',metric='candidate mean per-GW Brier difference',
          difference=float(weekly.mean()),block4_interval=interval,gameweeks=n,interpretation='Inspected historical window; descriptive, not an untouched test'),
        model_promotion=False,points_or_squad_gain_measured=False,
        limits=['News/chance are official FPL observations syndicated by AIrsenal, not independent club-news text',
          'Chance labels are learned covariates, never assigned as start probabilities',
          'Rows require common published roster/fixture-history coverage; missing target rows are not imputed',
          'News vocabulary and all numeric transforms fit training only; no parameter/seed search',
          'A participation improvement alone does not validate unconditional points/selection changes'])
    return report,predictions


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--sha256',required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():p.error('Output exists; preserve experiments')
    if file_hash(args.input)!=args.sha256:p.error('Input checksum mismatch')
    args.output.mkdir(parents=True)
    spec=dict(input_sha256=args.sha256,engine_sha256=file_hash(Path(__file__)),
      protocol_sha256=file_hash(Path(__file__).parent/'fpl_predict_resources/news_probe_protocol.json'))
    (args.output/'manifest.json').write_text(json.dumps(spec,indent=2))
    report,predictions=run(pd.read_csv(args.input));predictions.to_csv(args.output/'predictions.csv',index=False)
    (args.output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False))


if __name__=='__main__':main()
