"""CARE Farm B/C holdout: freeze every fold, then open the event information and score once.

    python3 tools/care_holdout_score.py freeze   # verify all 31 folds and close the freeze root (no truth)
    python3 tools/care_holdout_score.py derived --scratch DIR   # rebuild input/preparation with the frozen sources, compare bytes
    python3 tools/care_holdout_score.py pin-scorer   # bind the committed scorer and its dependencies to the freeze
    python3 tools/care_holdout_score.py score    # first truth access; writes the one-shot result

The decision follows examples/configs/care-holdout-bc-20261018.json: own model on common support,
Farm B + C pooled, assets keyed by (farm, asset_id). Floor breaks make the result "not established".
"""
import argparse
import csv
import hashlib
from datetime import datetime
import io
import json
import math
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path=[p for p in sys.path if Path(p or '.').resolve()!=Path(__file__).resolve().parent]
sys.path[:0]=[str(ROOT/'models/mini-transformer')]
import care_holdout as H  # noqa: E402
from care_alarm import (COMMON,METHODS,NATIVE,NEURAL_ISSUED,BASELINE_ISSUED,PREDICTION,active_seconds,  # noqa: E402
                        eligible_seconds,episodes,event_result)
from care_training_preparation import baseline_predict  # noqa: E402
from metropt_multiday import Files,digest,verify_closed  # noqa: E402

FREEZE=H.WORK/'freeze'
SCORES=ROOT/'artifacts/care-holdout-scores-20261018'
LEADS=(0,24,72,168)
MONTH_HOURS=720
DEFAULT_INTERVAL_HOURS=(167.5,168.5)


def threshold_for(thresholds,method):
    return thresholds['neural' if method=='neural-common' else 'baseline']['threshold']


def verify_unit(farm,fold):
    """Recompute flags, lineage, scores and episodes of every test row from the input (no truth)."""
    root=H.unit_root(farm,fold)
    if not H.unit_complete(farm,fold):raise ValueError(f'{farm} fold {fold} incomplete')
    s=json.loads((root/'summary.json').read_bytes())
    if s['resources']['elapsed_seconds']>870 or s['resources']['peak_rss_bytes']>2*1024**3:raise ValueError(f'{farm} fold {fold} over a limit')
    rows=list(PREDICTION.iter_unpack((root/'test.bin').read_bytes()));reader=H.HoldoutConsumer(farm,fold,'test')
    profile=json.loads((root/'input.json').read_bytes())['profile'];eps=json.loads((root/'episodes.json').read_bytes())
    thresholds=json.loads((root/'thresholds.json').read_bytes())['methods'];checked=[]
    for event in reader.fold['test_events']:
        d=reader.event(event);part=[r for r in rows if r[0]==event];nt=d.meta['split_row_counts']['train']
        if [r[1] for r in part]!=list(range(nt,d.meta['rows'])):raise ValueError('prediction row coverage')
        for r in part:
            n=r[1];raw=d._rows[n];issued=d.past_ok(n);common=d.common_ok(n);native=d.native_ok(n);base=bool(d._rows[n-1][2]&4)
            if r[5]!=NEURAL_ISSUED*issued+COMMON*common+NATIVE*native+BASELINE_ISSUED*base or r[2]!=raw[1] or r[3]!=d._rows[n-1][0]+600 or r[4]!=raw[0]+600:
                raise ValueError('record support/lineage/timing')
            if raw[2]&3==3 and tuple(r[6:8])!=tuple(raw[3:5]):raise ValueError('observation differs')
            if issued and (tuple(r[8:10])!=(r[15],r[18]) or not all(math.isfinite(x) for x in r[14:23])):raise ValueError('neural p50/quantile record')
            if base and tuple(r[10:12])!=baseline_predict(profile['baseline'],d._rows[n-1][5]):raise ValueError('baseline differs')
            for eligible,index,pred in ((common,12,8),(native,13,10)):
                if eligible and r[index]!=max(abs(r[6+v]-r[pred+v])/profile['alarm_scales'][v]['R64'] for v in range(2)):raise ValueError('score differs')
        for method in METHODS:
            if episodes(part,method,threshold_for(thresholds,method))!=eps[str(event)][method]:raise ValueError('frozen episode differs')
        checked.append({'event_id':event,'rows':len(part)});reader._cache.clear()
    return {'farm':farm,'fold':fold,'closure_sha256':digest(root/'root-closed.json'),'test_sha256':digest(root/'test.bin'),
            'episodes_sha256':digest(root/'episodes.json'),'thresholds_sha256':digest(root/'thresholds.json'),'events':checked}


def unit_sources(root):
    """Content digests of the sources a fold recorded in its sources.zip."""
    import hashlib
    with zipfile.ZipFile(root/'sources.zip') as z:
        return {name:hashlib.sha256(z.read(name)).hexdigest() for name in sorted(z.namelist())}


def same_sources(roots):
    """Every fold must have been built by the same runner and model code."""
    sources=[unit_sources(root) for root in roots]
    if not sources or any(s!=sources[0] for s in sources):raise ValueError('folds were built by different sources')
    return sources[0]


def freeze():
    units=[verify_unit(farm,f['fold']) for farm in H.FARMS for f in H.folds(farm)]
    sources=same_sources([H.unit_root(u['farm'],u['fold']) for u in units])
    out=Files(FREEZE);state='failed'
    try:
        out.json('freeze-before-truth.json',{'contract_sha256':H.CONTRACT_SHA,'units':units,'folds':len(units),
            'input_closures':{farm:digest(H.manifest_root(farm)/'root-closed.json') for farm in H.FARMS},
            'preparation_closures':{farm:digest(H.prep_root(farm)/'root-closed.json') for farm in H.FARMS},'unit_sources':sources,
            'all_predictions_thresholds_alarms_closed':True,'event_truth_opened_yet':False});state='complete'
    finally:out.close(state)
    print(json.dumps({'freeze_closure':digest(FREEZE/'root-closed.json'),'folds':len(units)}))


def clopper_pearson(k,n,alpha=.05):
    """Exact two-sided interval by bisection on the binomial tails."""
    if n==0:return None
    def upper_tail(p):return math.fsum(math.comb(n,i)*p**i*(1-p)**(n-i) for i in range(k,n+1))
    def lower_tail(p):return math.fsum(math.comb(n,i)*p**i*(1-p)**(n-i) for i in range(0,k+1))
    def solve(f,target,increasing):
        lo,hi=0.,1.
        for _ in range(200):
            mid=(lo+hi)/2
            if (f(mid)<target)==increasing:lo=mid
            else:hi=mid
        return (lo+hi)/2
    low=0. if k==0 else solve(upper_tail,alpha/2,True)
    high=1. if k==n else solve(lower_tail,alpha/2,False)
    return [low,high]


def verify_archive():
    """The ZIP must still match the contract pins at the moment the truth is opened."""
    c=H.contract()['source'];h=hashlib.sha256();m=hashlib.md5();n=0
    with open(H.ARCHIVE,'rb') as f:
        for block in iter(lambda:f.read(1<<24),b''):h.update(block);m.update(block);n+=len(block)
    found={'bytes':n,'md5':m.hexdigest(),'sha256':h.hexdigest()}
    if found!={'bytes':c['bytes'],'md5':c['md5'],'sha256':c['sha256']}:raise ValueError('archive differs from the contract pins')
    return found


def read_truth(z,farm):
    member=f'CARE_To_Compare/Wind Farm {farm}/event_info.csv'
    text=z.read(member).decode('utf-8-sig')
    return list(csv.DictReader(io.StringIO(text),delimiter=';' if ';' in text.splitlines()[0] else ','))


def score_events(truth,meta,rows,alarms):
    """truth: label rows with farm; meta/rows/alarms keyed by (farm, event). Returns per-asset stats and per-event rows."""
    stats={m:{} for m in METHODS};per_event=[];floors=[]
    for t in truth:
        farm=t['farm'];event=int(t['event_id']);m=meta[(farm,event)];key=H.asset_key(farm,m['asset_id']);part=rows[(farm,event)]
        base=datetime.fromisoformat(m['first_timestamp'])
        start=int((datetime.fromisoformat(t['event_start'])-base).total_seconds())+600
        end=int((datetime.fromisoformat(t['event_end'])-base).total_seconds())+600
        interval=[r for r in part if int(t['event_start_id'])<=r[2]<=int(t['event_end_id'])]
        if not interval or interval[0][4]!=start or interval[-1][4]!=end:raise ValueError(f'label timestamp/ID alignment: {farm} event {event}')
        common_fraction=sum(bool(r[5]&COMMON) for r in interval)/len(interval);hours=(end-start)/3600
        if t['event_label']=='anomaly' and common_fraction<.7:floors.append({'floor':'anomaly interval common support','farm':farm,'event_id':event,'fraction':common_fraction})
        out={'farm':farm,'event_id':event,'asset_key':key,'event_label':t['event_label'],'start':start,'end':end,'interval_hours':hours,
             'default_168h_interval':DEFAULT_INTERVAL_HOURS[0]<=hours<=DEFAULT_INTERVAL_HOURS[1],'interval_common_fraction':common_fraction,
             'attainable':{str(w):end-start>=w*3600 for w in LEADS},'methods':{}}
        for method in METHODS:
            s=stats[method].setdefault(key,{'farm':farm,'anomaly_events':0,'hits_at':{str(w):0 for w in LEADS},'attainable_at':{str(w):0 for w in LEADS},
                'earliness_sum':0.,'off_window_episodes':0,'normal_files':0,'normal_seconds':0,'normal_active_seconds':0,'false_episodes':0,'mae_sum':[0.,0.],'mae_n':0})
            eps=alarms[(farm,event)][method];seconds=eligible_seconds(part,method);d={'episodes':len(eps),'eligible_seconds':seconds}
            if t['event_label']=='anomaly':
                er=event_result(eps,start,end);s['anomaly_events']+=1;s['earliness_sum']+=er['earliness'];s['off_window_episodes']+=len(er['off_window_episodes'])
                for w in LEADS:
                    hit=er['hit'] and er['first_open']<=end-w*3600;s['hits_at'][str(w)]+=hit;s['attainable_at'][str(w)]+=end-start>=w*3600;d[f'hit_{w}h']=hit
                d.update(first_open=er['first_open'],lead_proxy_hours=None if er['lead_proxy_seconds'] is None else er['lead_proxy_seconds']/3600,
                         earliness=er['earliness'],active_before_start=len(er['already_active_before_start']),off_window=len(er['off_window_episodes']))
            elif t['event_label']=='normal':
                s['normal_files']+=1;s['normal_seconds']+=seconds;s['normal_active_seconds']+=active_seconds(part,method,eps);s['false_episodes']+=len(eps);d['false_episodes']=len(eps)
            else:raise ValueError('unknown event label')
            pred=8 if method=='neural-common' else 10;common=[r for r in part if r[5]&COMMON]
            for v in range(2):s['mae_sum'][v]+=math.fsum(abs(r[6+v]-r[pred+v]) for r in common)
            s['mae_n']+=len(common);out['methods'][method]=d
        per_event.append(out)
    for key,s in stats['neural-common'].items():
        if s['normal_files'] and s['normal_seconds']<24*3600:floors.append({'floor':'normal asset eligible hours','asset_key':key,'hours':s['normal_seconds']/3600})
    return stats,per_event,floors


def summarize(stats):
    """Rates for one set of per-asset stats (an asset, a farm or the pool)."""
    keys=('anomaly_events','earliness_sum','off_window_episodes','normal_files','normal_seconds','normal_active_seconds','false_episodes','mae_n')
    s={k:sum(x[k] for x in stats) for k in keys}
    s['hits_at']={str(w):sum(x['hits_at'][str(w)] for x in stats) for w in LEADS};s['attainable_at']={str(w):sum(x['attainable_at'][str(w)] for x in stats) for w in LEADS}
    s['detection_at']={w:(s['hits_at'][w]/s['attainable_at'][w] if s['attainable_at'][w] else None) for w in s['hits_at']}
    s['detection_ci95_at']={w:clopper_pearson(s['hits_at'][w],s['attainable_at'][w]) for w in s['hits_at']}
    s['earliness']=s['earliness_sum']/s['anomaly_events'] if s['anomaly_events'] else None
    rate=s['false_episodes']*3600*1000/s['normal_seconds'] if s['normal_seconds'] else None
    s['false_episodes_per_1000_record_hours']=rate;s['false_episodes_per_asset_30_days']=None if rate is None else rate*MONTH_HOURS/1000
    s['normal_alarm_fraction']=s['normal_active_seconds']/s['normal_seconds'] if s['normal_seconds'] else None
    s['lead1_mae_common_thermal']=[math.fsum(x['mae_sum'][v] for x in stats)/s['mae_n'] for v in range(2)] if s['mae_n'] else None
    return s


def decide(results,floors):
    rule=H.contract()['decision'];own=results['neural-common'];pooled=own['pooled']
    checks={'detection_72h_at_least_0.50':pooled['detection_at']['72'] is not None and pooled['detection_at']['72']>=.5,
            'detection_24h_at_least_0.60':pooled['detection_at']['24'] is not None and pooled['detection_at']['24']>=.6,
            'pooled_false_alarms_at_most_1.0_per_asset_30_days':pooled['false_episodes_per_asset_30_days'] is not None and pooled['false_episodes_per_asset_30_days']<=1.,
            'every_asset_false_alarms_at_most_1.0_per_asset_30_days':all(a['false_episodes_per_asset_30_days'] is not None and a['false_episodes_per_asset_30_days']<=1. for a in own['per_asset'].values() if a['normal_files'])}
    established=not floors
    return {'method':rule['method'],'pooled_over':rule['pooled_over'],'established':established,'floor_breaks':floors,'checks':checks,
            'outcome':('pass' if all(checks.values()) else 'fail') if established else 'not established',
            'reported_not_decisive':rule['reported_not_decisive']}


def verify_frozen(frozen):
    """Every fold, input and preparation root must still hold exactly the frozen bytes."""
    if same_sources([H.unit_root(u['farm'],u['fold']) for u in frozen['units']])!=frozen['unit_sources']:raise ValueError('fold sources changed after the freeze')
    for u in frozen['units']:
        root=H.unit_root(u['farm'],u['fold']);verify_closed(root)
        found=[digest(root/n) for n in ('root-closed.json','test.bin','episodes.json','thresholds.json')]
        if found!=[u['closure_sha256'],u['test_sha256'],u['episodes_sha256'],u['thresholds_sha256']]:raise ValueError('fold changed after the freeze')
    for farm in H.FARMS:
        root=H.manifest_root(farm);verify_closed(root)
        if digest(root/'root-closed.json')!=frozen['input_closures'][farm]:raise ValueError('input changed after the freeze')
        for f in json.loads((root/'dataset-manifest.json').read_bytes())['files']:
            event=H.event_root(farm,f['event_id']);verify_closed(event)
            if digest(event/'root-closed.json')!=f['event_root_closure_sha256']:raise ValueError('input event changed after the freeze')
        prep=H.prep_root(farm);verify_closed(prep)
        if digest(prep/'root-closed.json')!=frozen['preparation_closures'][farm]:raise ValueError('preparation changed after the freeze')


DERIVED=H.WORK/'derived-check'
PRODUCERS=('models/mini-transformer/care_holdout.py','models/mini-transformer/care_training_preparation.py','models/mini-transformer/care_input.py',
           'models/mini-transformer/metropt_multiday.py','tools/public-data/care_numeric_prepare.py')


def regenerate(scratch):
    """Rebuild every input event and preparation root with the code the folds recorded; compare the payload bytes."""
    import tempfile
    from unittest import mock
    verify_closed(FREEZE);frozen=json.loads((FREEZE/'freeze-before-truth.json').read_bytes());recorded=frozen['unit_sources']
    for name in PRODUCERS:
        if recorded.get(name)!=digest(ROOT/name):raise ValueError('producer source differs from the frozen folds: '+name)
    scratch=Path(tempfile.mkdtemp(dir=scratch));differ=[];compared=0
    for farm in H.FARMS:
        for item in H.manifest(farm)['files']:
            event=item['event_id'];old=H.event_root(farm,event);new=scratch/farm/f'event-{event}'
            with mock.patch.object(H,'event_root',lambda f,e,new=new:new):H.prepare_event(farm,event,H.Checkpoint(seconds=3600))
            q=lambda r:{k:v for k,v in json.loads((r/'quality.json').read_bytes()).items() if k!='resources'}
            same=(old/f'event-{event}.bin').read_bytes()==(new/f'event-{event}.bin').read_bytes() and (old/'meta.json').read_bytes()==(new/'meta.json').read_bytes() and q(old)==q(new)
            compared+=1;differ+=[] if same else [f'{farm} event {event}']
        new=scratch/farm/'prep'
        with mock.patch.object(H,'prep_root',lambda f,new=new:new):H.prepare_profiles(farm,H.Checkpoint(seconds=3600))
        old=H.prep_root(farm)
        for path in sorted(old.iterdir()):
            if path.name.startswith(('fold-','anchor-')):
                compared+=1
                if path.read_bytes()!=(new/path.name).read_bytes():differ.append(f'{farm} {path.name}')
        m=lambda r:{k:v for k,v in json.loads((r/'manifest.json').read_bytes()).items() if k!='resources'}
        compared+=1
        if m(old)!=m(new):differ.append(f'{farm} preparation manifest')
    out=Files(DERIVED);state='failed'
    try:
        out.json('derived-check.json',{'freeze_closure_sha256':digest(FREEZE/'root-closed.json'),'producer_sources':{n:recorded[n] for n in PRODUCERS},
            'compared':compared,'differ':differ,'identical':not differ});state='complete'
    finally:out.close(state)
    if differ:raise SystemExit('derived artifacts differ: '+json.dumps(differ))
    print(json.dumps({'derived_artifacts_identical':compared}))


def verify_derived():
    verify_closed(DERIVED);d=json.loads((DERIVED/'derived-check.json').read_bytes())
    if not d['identical'] or d['freeze_closure_sha256']!=digest(FREEZE/'root-closed.json'):raise ValueError('derived artifacts not verified against the frozen sources')


SCORER_PIN=H.WORK/'scorer-pin'
SCORER=('tools/care_holdout_score.py','models/mini-transformer/care_alarm.py','models/mini-transformer/care_holdout.py',
        'models/mini-transformer/care_training_preparation.py','models/mini-transformer/care_input.py','models/mini-transformer/metropt_multiday.py',
        'examples/configs/care-holdout-bc-20261018.json')


def scorer_sources():return {name:digest(ROOT/name) for name in SCORER}


def pin_scorer():
    """Bind the reviewed scorer and its dependencies to this freeze, before the truth is opened."""
    import subprocess
    verify_closed(FREEZE);verify_derived()
    head=subprocess.run(['git','-C',str(ROOT),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
    dirty=subprocess.run(['git','-C',str(ROOT),'status','--porcelain','--',*SCORER],capture_output=True,text=True,check=True).stdout
    if dirty:raise SystemExit('scorer files differ from the commit: '+dirty)
    out=Files(SCORER_PIN);state='failed'
    try:
        out.json('scorer-pin.json',{'freeze_closure_sha256':digest(FREEZE/'root-closed.json'),'commit':head,'sources':scorer_sources()});state='complete'
    finally:out.close(state)
    print(json.dumps({'scorer_pinned_at':head}))


def verify_scorer():
    verify_closed(SCORER_PIN);pin=json.loads((SCORER_PIN/'scorer-pin.json').read_bytes())
    if pin['freeze_closure_sha256']!=digest(FREEZE/'root-closed.json') or pin['sources']!=scorer_sources():raise ValueError('scorer differs from the pinned sources')
    return pin


def score():
    verify_closed(FREEZE);frozen=json.loads((FREEZE/'freeze-before-truth.json').read_bytes())
    if frozen['contract_sha256']!=H.CONTRACT_SHA or frozen['folds']!=31 or frozen['event_truth_opened_yet']:raise ValueError('freeze record')
    verify_frozen(frozen);verify_derived();pin=verify_scorer()
    out=Files(SCORES);state='failed'
    try:
        out.json('before-truth.json',{'freeze_closure_sha256':digest(FREEZE/'root-closed.json'),'archive':verify_archive(),'scorer_commit':pin['commit'],
                                      'scorer_sources':pin['sources'],'truth_opened_yet':False})
        meta={};rows={};alarms={}
        for u in frozen['units']:
            farm=u['farm'];root=H.unit_root(farm,u['fold']);part=list(PREDICTION.iter_unpack((root/'test.bin').read_bytes()));eps=json.loads((root/'episodes.json').read_bytes())
            files={f['event_id']:f for f in json.loads((H.manifest_root(farm)/'dataset-manifest.json').read_bytes())['files']}
            for e in u['events']:
                event=e['event_id'];meta[(farm,event)]=files[event];rows[(farm,event)]=[r for r in part if r[0]==event];alarms[(farm,event)]=eps[str(event)]
        # First truth access, after the freeze record above; the frozen roots and the archive are checked again right before it.
        verify_frozen(frozen);verify_derived();verify_scorer();verify_archive()
        with zipfile.ZipFile(H.ARCHIVE) as z:
            truth=[{**t,'farm':farm} for farm in H.FARMS for t in read_truth(z,farm)]
        if {(t['farm'],int(t['event_id'])) for t in truth}!=set(meta) or len(truth)!=len(meta):raise ValueError('truth cohort differs from the fixed files')
        for t in truth:
            asset=t.get('asset') or t.get('asset_id')
            if asset is not None and str(asset)!=meta[(t['farm'],int(t['event_id']))]['asset_id']:raise ValueError('label asset differs')
        out.json('truth-rows.json',[{k:t[k] for k in ('farm','event_id','event_label','event_start','event_end','event_start_id','event_end_id')} for t in truth])
        stats,per_event,floors=score_events(truth,meta,rows,alarms);results={}
        for method in METHODS:
            per=stats[method]
            results[method]={'pooled':summarize(list(per.values())),'per_farm':{farm:summarize([s for s in per.values() if s['farm']==farm]) for farm in H.FARMS},
                             'per_asset':{k:summarize([s]) for k,s in sorted(per.items())}}
        decision=decide(results,floors)
        out.json('metrics.json',results);out.json('per-event.json',per_event);out.json('decision.json',decision)
        own=results['neural-common']['pooled']
        out.json('summary.json',{'outcome':decision['outcome'],'checks':decision['checks'],'floor_breaks':len(floors),
            'events':{'anomaly':sum(t['event_label']=='anomaly' for t in truth),'normal':sum(t['event_label']=='normal' for t in truth)},
            'pooled':{m:{k:results[m]['pooled'][k] for k in ('hits_at','attainable_at','detection_at','detection_ci95_at','false_episodes','false_episodes_per_asset_30_days','normal_alarm_fraction','earliness','lead1_mae_common_thermal')} for m in METHODS},
            'own_model_per_farm':{f:{k:results['neural-common']['per_farm'][f][k] for k in ('hits_at','attainable_at','detection_at','false_episodes_per_asset_30_days')} for f in H.FARMS},
            'own_model_max_asset_false_rate':max((a['false_episodes_per_asset_30_days'] for a in results['neural-common']['per_asset'].values() if a['normal_files']),default=None),
            'default_168h_intervals':sum(e['default_168h_interval'] for e in per_event if e['event_label']=='anomaly'),'pooled_detection_72h':own['detection_at']['72']})
        state='complete'
    except BaseException:
        import traceback
        out.json('failure.json',{'traceback':traceback.format_exc()},True);raise
    finally:out.close(state)
    print(json.dumps(json.loads((SCORES/'summary.json').read_bytes()),indent=1))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=('freeze','derived','pin-scorer','score'));p.add_argument('--scratch',default=str(H.WORK));a=p.parse_args()
    {'freeze':freeze,'derived':lambda:regenerate(a.scratch),'pin-scorer':pin_scorer,'score':score}[a.command]()
