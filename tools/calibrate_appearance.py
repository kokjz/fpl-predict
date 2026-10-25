"""Fit the predeclared prior-season appearance correction from archived counters.

Training never reads target outcomes or later corrected match histories. API
cumulative-minute increments are a noisy historical appearance-label proxy, not
independent final per-match provenance. All exclusions are retained by reason.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
from appearance_calibration import fit,apply
from availability_evidence import utc
from deadline_provenance import read_snapshot
from experiment_runner import file_hash
from season_benchmark import read_bundle


def checked(entry):
    p=Path(entry['path'])
    if file_hash(p)!=entry['sha256']:raise ValueError('Calibration input checksum differs')
    return p


def counter_cohort(season,entries,sidecar,root):
    """Use only GW1..37 labels observed at the following predeadline origin."""
    if [e['gameweek'] for e in entries]!=list(range(1,39)) or [w['gameweek'] for w in sidecar['weeks']]!=list(range(1,39)):raise ValueError('Incomplete training origins')
    counts=Counter();rows=[];clocks=[]
    for e,nxt,w in zip(entries[:-1],entries[1:],sidecar['weeks'][:-1]):
        if (w['gameweek'],w['as_of'])!=(e['gameweek'],e['captured_at']) or not utc(e['captured_at'])<utc(nxt['captured_at']):raise ValueError('Training origin differs')
        b=read_snapshot(Path(root)/e['file'],e['compressed_sha256']);after=read_snapshot(Path(root)/nxt['file'],nxt['compressed_sha256']);event=next(z for z in after['events'] if z['id']==e['gameweek'])
        cells=[r for r in w['rows'] if r['gameweek']==e['gameweek']]
        if not (event.get('finished') is True and event.get('data_checked') is True):counts['unconfirmed_origin_cells']+=len(cells);continue
        before={p['id']:p for p in b['elements']};later={p['id']:p for p in after['elements']}
        if len(before)!=len(b['elements']) or len(later)!=len(after['elements']):raise ValueError('Ambiguous training identity')
        for r in cells:
            counts['considered']+=1;i=r['id']
            if r['official_zero']:counts['official_zero']+=1;continue
            if not r['fixture_count'] or r['p_play']==0:counts['zero_support']+=1;continue
            if i not in before or i not in later or before[i]['code']!=later[i]['code']:counts['unmatched_identity']+=1;continue
            values=[p.get('minutes') for p in (before[i],later[i])]
            if any(type(v) is not int or v<0 for v in values):counts['invalid_counter']+=1;continue
            delta=values[1]-values[0]
            if delta<0:counts['negative_revision']+=1;continue
            rows.append(dict(season=season,gameweek=e['gameweek'],id=i,as_of=e['captured_at'],available_at=nxt['captured_at'],p_play=r['p_play'],label=int(delta>0),minute_increment=delta,label_source_sha256=nxt['compressed_sha256']))
            counts['included']+=1
        clocks.append(dict(gameweek=e['gameweek'],label_available_at=nxt['captured_at'],label_source_sha256=nxt['compressed_sha256']))
    return rows,dict(counts=counts,clocks=clocks,label='Nonnegative API cumulative-minute increment before next deadline; prior revisions can add label noise; no later final histories used')


def prepare(manifest,expected,output):
    if file_hash(manifest)!=expected:raise ValueError('Calibration manifest checksum differs')
    spec=read_bundle(manifest);out=Path(output).resolve()
    if out.exists() or out.is_relative_to(Path(__file__).resolve().parents[1]):raise ValueError('Require new private output directory')
    if spec['protocol_sha256']!=file_hash(spec['protocol']):raise ValueError('Calibration protocol differs')
    # Check every input before writing fitted outputs.
    for s in spec['training'].values():checked(s['markets']);checked(s['availability'])
    for s in spec['targets'].values():checked(s['availability'])
    out.mkdir(parents=True);summaries=[]
    for season,target in spec['targets'].items():
        year=target['training_season'];source=spec['training'][year];ap=read_bundle(checked(source['availability']));entries=read_bundle(checked(source['markets']))['market_origins']
        rows,audit=counter_cohort(year,entries,ap,source['source_root']);base=read_bundle(checked(target['availability']));first=base['weeks'][0]['as_of']
        with gzip.open(out/(year+'_training.json.gz'),'xt') as stream:json.dump(dict(rows=rows,audit=audit),stream,separators=(',',':'))
        hashes=dict(protocol=spec['protocol_sha256'],markets=source['markets']['sha256'],appearance=source['availability']['sha256'],cohort=file_hash(out/(year+'_training.json.gz')))
        c=fit(rows,first,source_hashes=hashes);(out/(season+'_calibration.json')).write_text(json.dumps(c,indent=2)+'\n')
        weeks=[apply(w,c) for w in base['weeks']]
        with gzip.open(out/(season+'.json.gz'),'xt') as stream:json.dump(dict(base,weeks=weeks),stream,separators=(',',':'),allow_nan=False)
        summaries.append(dict(target=season,training_season=year,calibration=c,cohort_audit=audit,source_sha256=target['availability']['sha256'],result_sha256=file_hash(out/(season+'.json.gz'))))
    result=dict(complete=True,targets=summaries,manifest_sha256=expected,point_means_modified=False,target_outcomes_read=False,model_promotion=False);(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--manifest-sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();prepare(a.manifest,a.manifest_sha256,a.output)


if __name__=='__main__':main()
