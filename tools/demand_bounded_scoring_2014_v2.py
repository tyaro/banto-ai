"""Re-score immutable 2014 forecasts only; no training or prediction path."""
import argparse,json,os,sys,time,traceback
from pathlib import Path
from demand_bounded_metrics import Arithmetic,P,S,BITS,FIT,groups,score_group,summarize
from verify_demand_transfer import verify,pin
from macos_demand_runtime import MacCheckpoint
REPO=Path(__file__).resolve().parents[1]
BASE='macos-demand-bounded-scoring-2014-20261015'
CONTRACT='docs/research/demand-bounded-scoring-contract-2026-10-15.md'
SOURCE='macos-demand-seasonal-shared-2014-20261015'
FILES=[CONTRACT,'docs/research/demand-bounded-scoring-astra-review-2026-10-15.md','tools/demand_bounded_metrics.py','tools/demand_bounded_scoring_2014_v2.py','tests/test_demand_bounded_metrics.py']
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
    guard=MacCheckpoint(seconds=870);a=Arithmetic(guard.check);stage='source-pins';status='failed';done=[];evaluation={};files=Output(output)
    try:
        if sys.version_info[:3]!=(3,14,8) or sys.platform!='darwin':raise ValueError('fixed Mac3.14.8 runtime')
        source=REPO/'artifacts'/SOURCE;protected=json.loads((source/'protected.json').read_bytes())
        for suffix in ('','-execution-records','-preparation-records','-preparation-v2-records','-postrun-fixtures-records','-readback-records','-doc-records'):
            path=Path(str(source)+suffix);protected['closures'][str(path)]=verify(path)
        protected['source_pins'].update({p:pin(REPO/p) for p in FILES})
        files.json('protected.json',protected);files.write('contract.md',(REPO/CONTRACT).read_bytes())
        files.json('sources.json',{p:(REPO/p).read_text() for p in FILES})
        freeze=json.loads((source/'freeze-before-scoring.json').read_bytes())
        assert pin(source/'predictions-before-scoring.json')==freeze['predictions_pin']
        assert all(pin(source/n)==v for n,v in freeze['states'].items())
        assert all(pin(source/n)==v for n,v in freeze['quarter_predictions'].items())
        forecasts=json.loads((source/'predictions-before-scoring.json').read_bytes());labels=json.loads((source/'scoring-labels.json').read_bytes())
        assert len(forecasts)==len(labels)==260 and len({f['key'] for f in forecasts})==260
        bykey={l['key']:l for l in labels};assert set(bykey)=={f['key'] for f in forecasts}
        rows=[]
        for f in forecasts:
            if not f['origin'].startswith('2014-') or f['store'] not in FIT:raise ValueError('2014 FIT only')
            l=bykey[f['key']];raw=l['raw_actual'];assert l['observed']==raw
            assert l['assumed_missing_zero']==[0. if y is None and not opened else y for y,opened in zip(raw,f['assumed_open_mask'])]
            rows.append({'forecast':f,**{k:l[k] for k in ('observed','assumed_missing_zero')}})
        support={'raw_nulls':sum(y is None for l in labels for y in l['raw_actual']),
            'imputed_positions':sum(y is None and z==0 for l in labels for y,z in zip(l['observed'],l['assumed_missing_zero'])),
            'newyear_true_zeros':sum(bykey[f['key']]['raw_actual'][0]==0 for f in forecasts if f['origin']=='2014-01-01')}
        assert support=={'raw_nulls':10,'imputed_positions':10,'newyear_true_zeros':10}
        files.json('configuration.json',{'p':P,'S':str(S),'bits':BITS,'max_terms':8192,'group_names':list(groups(rows)),
            'source_prediction_pin':pin(source/'predictions-before-scoring.json'),'source_labels_pin':pin(source/'scoring-labels.json'),
            'freeze_pin':pin(source/'freeze-before-scoring.json'),'label_support':support,'fit_predict_2015':False,'deletion_fits':0})
        evaluation={}
        for name,selected in groups(rows).items():
            stage='score-'+name;evaluation[name]={}
            for mode in ('observed','assumed_missing_zero'):
                stage='score-'+name+'-'+mode;evaluation[name][mode]=score_group(selected,mode,a)
            files.json('evaluation-'+name+'.json',evaluation[name]);done.append(name)
            print(json.dumps({'group':name,'complete':True,'decisions':{m:evaluation[name][m]['decisions'] for m in evaluation[name]}}),flush=True)
        stage='verification'
        assert {p:verify(Path(p)) for p in protected['closures']}==protected['closures']
        assert all(pin(REPO/p)==v for p,v in protected['source_pins'].items())
        summary={'status':'complete','scoring_only':True,'source_recorded_status':'failed','source_unchanged':True,'windows':260,
            'groups':len(evaluation),'p':P,'max_arithmetic_bits_observed':a.max_bits,'retrained':False,'new_predictions':False,
            'new2015':False,'deletion_fits':0,'adopted':False,'formal_permission':False,**summarize(evaluation)}
        files.json('summary.json',summary);status='complete';print(json.dumps(summary),flush=True)
    except BaseException as exc:
        files.json('partial-evaluation.json',evaluation,True)
        files.json('failure.json',{'stage':stage,'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc(),'completed_groups':done,'max_arithmetic_bits_observed':a.max_bits},True)
        raise
    finally:
        resource_error=None
        try:resources=guard.check()
        except BaseException as exc:
            resource_error=exc;status='failed'
            files.json('resource-failure.json',{'stage':'final-resource','type':type(exc).__name__,'message':str(exc),'root_failure_overrides_any_summary':True},True)
            resources={'snapshot_error':type(exc).__name__,'message':str(exc),'sampled_peak_footprint_bytes':guard.max_footprint,'peak_rss_bytes':guard.max_rss,'elapsed_seconds':time.monotonic()-guard.started}
        files.json('resources.json',resources,True)
        files.json('root-closed.json',{'status':status,'files':files.pins.copy(),'immutable':True,'formal_permission':False},True)
        if resource_error is not None:raise resource_error

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.parent.resolve()!=REPO/'artifacts' or args.output.exists():raise ValueError('fresh artifact root required')
    run(args.output.absolute())
