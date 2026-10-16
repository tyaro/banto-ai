"""Bounded prefix materialization and input-only support audit. No estimator fit."""
import time
STARTED=time.monotonic()
import argparse,copy,json,subprocess,sys,traceback
from pathlib import Path
import demand_input_boundary_v2 as b
from demand_input_boundary_v2 import _pinned_json
import demand_prefix_adapter as a
from verify_demand_transfer import verify,pin
from macos_demand_runtime import MacCheckpoint
REPO=Path(__file__).resolve().parents[1]
CONTRACT='docs/research/demand-prefix-adapter-design-2026-10-15.md'

def run(output):
 sys.path.insert(0,str(REPO/'models/mini-transformer'));from demand_calendar_train import Files
 guard=MacCheckpoint(seconds=870);files=Files(output);status='failed';stage='source'
 try:
  if output.parent!=REPO/'artifacts' or sys.version_info[:3]!=(3,14,8) or sys.platform!='darwin':raise ValueError('fresh Mac Python3.14.8 root required')
  source=REPO/'artifacts/macos-demand-input-boundary-20261015-v2';old=json.loads((source/'summary.json').read_bytes());closures={str(source):verify(source),**old['closures']}
  for suffix in ('execution-records','readback-records','doc-records','doc-records-v2'):
   path=Path(str(source)+'-'+suffix);closures[str(path)]=verify(path)
  if closures[str(source)+'-doc-records']['recorded_status']!='failed' or closures[str(source)+'-doc-records-v2']['recorded_status']!='complete':raise ValueError('preserve OS failed/successful document checks')
  names=[CONTRACT,'tools/demand_prefix_adapter.py','tools/demand_prefix_adapter_check.py','tools/demand_prefix_consumer_check.py','tests/test_demand_prefix_adapter.py',*old['source_pins']];pins={p:pin(REPO/p) for p in dict.fromkeys(names)}
  if any(pins[p]!=v for p,v in old['source_pins'].items()):raise ValueError('prior source changed')
  files.write('contract.md',(REPO/CONTRACT).read_bytes());files.json('sources.json',{p:(REPO/p).read_text() for p in pins});files.write('source-final-state.json',(source/'source-final-state.json').read_bytes())
  binding=b.strict_json((source/'binding.json').read_bytes());inputs=b.load_inputs(source/'inputs.json',binding['file_pins']['inputs.json']);t=b.load_transforms(source/'transforms.json',binding['file_pins']['transforms.json']);index=_pinned_json(source/'label-index.json',binding['file_pins']['label-index.json'])
  prefixes={};ledgers={};support={};stdio=[];canaries=[]
  for cutoff in b.CUTS:
   stage='prefix-'+cutoff;reader=b.LabelReader(source/'labels.jsonl',index,inputs,binding['file_pins']['labels.jsonl']);batch,ledger=a.materialize(inputs,t,reader,cutoff)
   prefixes[cutoff]=batch;ledgers[cutoff]=ledger;support[cutoff]=a.feature_support(batch);name='prefix-'+cutoff+'.json';files.write(name,b.canonical(batch))
   # Change only non-permitted future input values while preserving their own contracts.
   altered=copy.deepcopy(inputs)
   for row in altered:
    if row['target_dates'][-1]>=cutoff:
     row['past_values']=[None if v is None else .5*v for v in row['past_values']];row['matched_mean28']=[.5*v for v in row['matched_mean28']]
   rr=b.LabelReader(source/'labels.jsonl',index,altered,binding['file_pins']['labels.jsonl']);variant,_=a.materialize(altered,t,rr,cutoff)
   if b.canonical(variant)!=b.canonical(batch):raise ValueError('non-permitted input affected delivered rows')
   canaries.append({'cutoff':cutoff,'nonpermitted_input_modified':True,'prefix_unchanged':True,'prefix_pin':files.pins[name]})
   command=[str(REPO/'environments/demand-macos/.venv/bin/python'),'-B',str(REPO/'tools/demand_prefix_consumer_check.py'),'--prefix',str(output/name),'--pin',json.dumps(files.pins[name])]
   process=subprocess.Popen(command,cwd=REPO,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
   try:stdout,stderr=process.communicate(timeout=max(.1,min(870.,870-(time.monotonic()-STARTED))))
   except subprocess.TimeoutExpired:process.kill();stdout,stderr=process.communicate()
   stdio.append({'command':command,'stdout':stdout.decode(),'stderr':stderr.decode(),'returncode':process.returncode})
   if process.returncode:raise RuntimeError('prefix consumer check failed')
   check=json.loads(stdout);assert check['support']==support[cutoff] and check['consumer_received_only_prefix'];guard.check()
  files.json('prefix-ledgers.json',ledgers);files.json('feature-support.json',support);files.json('consumer-stdio-exits.json',stdio);files.json('nonpermitted-canaries.json',canaries)
  issue_features=[]
  for r in inputs:
   if not r['origin'].startswith('2014-'):continue
   x,reasons=a.input_features(r,t);issue_features.append({'key':r['key'],'store':r['store'],'origin':r['origin'],'features':x,'reasons':reasons})
  files.json('input-only-2014-features.json',issue_features)
  if {p:verify(Path(p)) for p in closures}!=closures or any(pin(REPO/p)!=v for p,v in pins.items()):raise ValueError('protected evidence changed')
  summary={'status':'complete','closures':closures,'source_pins':pins,'source_binding_pin':pin(source/'binding.json'),'prefix_complete_counts':[support[c]['complete_rows'] for c in b.CUTS],
    'prefix_feature_eligible_counts':[support[c]['eligible_rows'] for c in b.CUTS],'issue2014_feature_eligible':sum(r['features'] is not None for r in issue_features),
    'feature_spec':a.FEATURE_SPEC,'new_fit':False,'new_predictions':False,'new_scores':False,'2015_new_content_use_or_evaluation':False,
    'support_not_independent_sample_size':True,'only_prefix_rows_delivered':True,'not_python_sandbox':True,'adopted':False,'formal_permission':False,'resources':guard.check(),'seconds':time.monotonic()-STARTED}
  files.json('summary.json',summary);status='complete';print(json.dumps({k:v for k,v in summary.items() if k not in ('closures','source_pins')}),flush=True)
 except BaseException as error:
  files.json('failure.json',{'stage':stage,'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()},True);raise
 finally:files.json('root-closed.json',{'status':status,'files':files.pins.copy(),'immutable':True,'formal_permission':False},True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output.absolute())
