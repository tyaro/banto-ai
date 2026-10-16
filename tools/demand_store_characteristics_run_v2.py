"""Pre-origin profiles and fixed Q1 attribution only; no model path."""
import argparse,csv,hashlib,json,math,os,sys,time,traceback
from pathlib import Path
from demand_store_characteristics import FIT,select_2013,snapshot_packet,profile
from demand_q1_attribution_v2 import diagnose
from demand_bounded_metrics import Arithmetic,P
from demand_input_boundary_v2 import load_inputs,load_transforms
from verify_demand_transfer import verify,pin
from macos_demand_runtime import MacCheckpoint
REPO=Path(__file__).resolve().parents[1]
BASE='macos-demand-store-characteristics-20261015'
CONTRACT='docs/research/demand-store-characteristics-contract-2026-10-15.md'
FILES=[CONTRACT,'docs/research/demand-store-characteristics-astra-review-2026-10-15.md','tools/demand_store_characteristics.py','tools/demand_q1_attribution_v2.py','tools/demand_store_characteristics_run_v2.py','tests/test_demand_store_characteristics.py','tests/test_demand_q1_attribution_v2.py']
def packet_pin(obj):
    raw=json.dumps(obj,sort_keys=True,allow_nan=False,separators=(',',':')).encode();return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
class Output:
    """Same reviewed artifact limits without importing the unrelated torch trainer."""
    def __init__(self,root):self.root=root;root.mkdir();self.pins={}
    def write(self,name,raw,failure=False):
        files=list(self.root.iterdir());maxfiles,maxbytes=(32,1024**3) if failure else (24,768*1024**2)
        if Path(name).name!=name or name in self.pins or (self.root/'root-closed.json').exists():raise ValueError('fresh entry required')
        if any(not p.is_file() or p.is_symlink() for p in files):raise ValueError('regular output files required')
        if len(files)+1>maxfiles or len(raw)>32*1024**2 or sum(p.stat().st_size for p in files)+len(raw)>maxbytes:raise RuntimeError('artifact_limit')
        with (self.root/name).open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        self.pins[name]=pin(self.root/name)
    def json(self,name,value,failure=False):self.write(name,json.dumps(value,allow_nan=False,sort_keys=True).encode(),failure)


def run(output):
    guard=MacCheckpoint(seconds=870);a=Arithmetic(guard.check);files=Output(output);status='failed';stage='sources';done=[]
    try:
        if sys.version_info[:3]!=(3,14,8) or sys.platform!='darwin':raise ValueError('fixed Mac3.14.8')
        scoring=REPO/'artifacts/macos-demand-bounded-scoring-2014-20261015';protected=json.loads((scoring/'protected.json').read_bytes())
        for suffix in ('','-execution-records','-preparation-records','-preparation-v2-records','-readback-records','-doc-records'):
            p=Path(str(scoring)+suffix);protected['closures'][str(p)]=verify(p)
        protected['source_pins'].update({p:pin(REPO/p) for p in FILES})
        files.json('protected.json',protected);files.write('contract.md',(REPO/CONTRACT).read_bytes());files.json('sources.json',{p:(REPO/p).read_text() for p in FILES})
        rawroot=REPO/'artifacts/macos-demand-rebuild-20261015';csvpath=rawroot/'selected-internal.csv'
        assert pin(csvpath)==json.loads((rawroot/'root-closed.json').read_bytes())['files']['selected-internal.csv']
        boundary=REPO/'artifacts/macos-demand-input-boundary-20261015-v2';binding=json.loads((boundary/'binding.json').read_bytes())
        inputs=load_inputs(boundary/'inputs.json',binding['file_pins']['inputs.json']);transforms=load_transforms(boundary/'transforms.json',binding['file_pins']['transforms.json'])
        stage='pre-origin-profiles'
        with csvpath.open(newline='') as stream:history=select_2013(csv.DictReader(stream))
        profiles={str(s):profile(history[s],'2014-01-01') for s in FIT}
        assert all(profiles[str(s)]['raw_observed_mean']==transforms['scales'][str(s)] for s in FIT)
        selected=[r for r in inputs if '2014-01-01'<=r['origin']<'2014-04-01'];assert len(selected)==70 and len({r['origin'] for r in selected})==7
        packets=[];snapshots=[]
        for r in selected:
            packet=snapshot_packet(r);p=profile(packet,r['origin']);base=profiles[str(r['store'])]['open_mean']
            packets.append({'key':r['key'],'store':r['store'],'origin':r['origin'],'records':packet})
            snapshots.append({'key':r['key'],'store':r['store'],'origin':r['origin'],'packet_pin':packet_pin(packet),'profile':p,
                'level_relative_to_2013_open_mean':p['open_mean']/base if base and p['open_mean'] is not None else None})
            guard.check()
        files.json('history-2013.json',history);files.json('profiles-2014-01-01.json',profiles);files.json('Q1-past-only-packets.json',packets);files.json('Q1-pre-origin-snapshots.json',snapshots)
        freeze={n:files.pins[n] for n in ('history-2013.json','profiles-2014-01-01.json','Q1-past-only-packets.json','Q1-pre-origin-snapshots.json')}
        files.json('freeze-before-diagnosis-labels.json',{'pins':freeze,'profiles_saved_before_current_label_read':True,'not_blind_to_previously_seen_2014':True,
            'input_pin':binding['file_pins']['inputs.json'],'raw_source_pin':pin(csvpath),'source_transform_pin':binding['file_pins']['transforms.json']})
        print(json.dumps({'stage':'profiles-and-70-snapshots-frozen-before-diagnosis-labels','stores':10}),flush=True)
        stage='saved-Q1-diagnosis'
        source=REPO/'artifacts/macos-demand-seasonal-shared-2014-20261015';predictions=json.loads((source/'predictions-before-scoring.json').read_bytes())
        forecasts=[f for f in predictions if '2014-01-01'<=f['origin']<'2014-04-01'];assert {f['key'] for f in forecasts}=={r['key'] for r in selected}
        labels={r['key']:r for r in json.loads((source/'scoring-labels.json').read_bytes()) if r['key'] in {f['key'] for f in forecasts}}
        for f in forecasts:
            l=labels[f['key']];assert l['observed']==l['raw_actual']
            assert l['assumed_missing_zero']==[0. if v is None and not opened else v for v,opened in zip(l['observed'],f['assumed_open_mask'])]
        summaries={}
        for group in ('Q1_all','Q1_normal'):
            saved=json.loads((scoring/('evaluation-'+group+'.json')).read_bytes())
            for mode in ('observed','assumed_missing_zero'):
                stage=group+'-'+mode;d=diagnose(forecasts,labels,group,mode,saved[mode],a)
                files.json('diagnosis-'+stage+'.json',d);done.append(stage)
                summaries[stage]={m:{'decision':d['metrics'][m]['total']['net']['decision'],
                    'net_positive_stores':[s for s,v in d['metrics'][m]['stores'].items() if int(v['net']['lower_numerator'])>0],
                    'store_concentration':d['metrics'][m]['store_concentration'],'origin_concentration':d['metrics'][m]['origin_concentration']} for m in ('total_MSE','over')}
                print(json.dumps({'stage':stage,'complete':True}),flush=True)
        stage='immutability-check'
        assert all(pin(output/n)==v for n,v in freeze.items())
        assert {p:verify(Path(p)) for p in protected['closures']}==protected['closures'] and all(pin(REPO/p)==v for p,v in protected['source_pins'].items())
        summary={'status':'complete','profiles':10,'snapshots':70,'Q1_diagnostic_views':4,'summaries':summaries,'max_arithmetic_bits':a.max_bits,
            'profile_label_feedback':False,'fixed_classification':False,'new_fit':False,'new_predictions':False,'new2015':False,'deletion_fits':0,
            'four_season_acceptance_unchanged':'mandatory_false_Q1_MSE_over_increase','adopted':False,'formal_permission':False}
        files.json('summary.json',summary);status='complete';print(json.dumps({k:v for k,v in summary.items() if k!='summaries'}),flush=True)
    except BaseException as exc:
        files.json('failure.json',{'stage':stage,'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc(),'completed_views':done},True)
        raise
    finally:
        resource_error=None
        try:resources=guard.check()
        except BaseException as exc:
            resource_error=exc;status='failed';files.json('resource-failure.json',{'type':type(exc).__name__,'message':str(exc),'root_failure_overrides_any_summary':True},True)
            resources={'snapshot_error':str(exc),'sampled_peak_footprint_bytes':guard.max_footprint,'peak_rss_bytes':guard.max_rss,'elapsed_seconds':time.monotonic()-guard.started}
        files.json('resources.json',resources,True);files.json('root-closed.json',{'status':status,'files':files.pins.copy(),'immutable':True,'formal_permission':False},True)
        if resource_error is not None:raise resource_error
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);arg=p.parse_args()
    if arg.output.parent.resolve()!=REPO/'artifacts' or arg.output.exists():raise ValueError('fresh artifact root')
    run(arg.output.absolute())
