"""One already-read 2014 chronological replay. Never reads or evaluates 2015."""
import time
STARTED=time.monotonic()
import argparse,json,math,sys,traceback
from pathlib import Path
from demand_common_residual import train,forecast,quarter
from demand_input_boundary_v2 import _pinned_json,load_inputs,load_transforms,LabelReader,label_scenarios,CUTS
from demand_shortfall_quantity import measure
from verify_demand_transfer import verify,pin
from macos_demand_runtime import MacCheckpoint
REPO=Path(__file__).resolve().parents[1]
CONTRACT='docs/research/demand-common-residual-design-2026-10-15.md'

def run(output):
 from demand_calendar_train import Files
 guard=MacCheckpoint(seconds=870)
 if output.parent!=REPO/'artifacts' or output.exists():raise ValueError('fresh root required')
 files=Files(output);status='failed';stage='sources';states=[]
 try:
  if sys.version_info[:3]!=(3,14,8) or sys.platform!='darwin':raise ValueError('Mac Python3.14.8 required')
  prefix=REPO/'artifacts/macos-demand-prefix-adapter-20261015';source=REPO/'artifacts/macos-demand-input-boundary-20261015-v2';previous=json.loads((prefix/'summary.json').read_bytes())
  closures={str(prefix):verify(prefix),**previous['closures']}
  for suffix in ('execution-records','readback-records'):
   p=Path(str(prefix)+'-'+suffix);closures[str(p)]=verify(p)
   if closures[str(p)]['recorded_status']!='complete':raise ValueError('prefix verification must complete first')
  names=[CONTRACT,'tools/demand_common_residual.py','tools/demand_common_residual_check.py','tests/test_demand_common_residual.py',*previous['source_pins']];pins={p:pin(REPO/p) for p in dict.fromkeys(names)}
  if any(pins[p]!=v for p,v in previous['source_pins'].items()):raise ValueError('protected source changed')
  files.write('contract.md',(REPO/CONTRACT).read_bytes());files.json('sources.json',{p:(REPO/p).read_text() for p in pins});files.write('source-final-state.json',(source/'source-final-state.json').read_bytes())
  binding=json.loads((source/'binding.json').read_bytes());inputs=load_inputs(source/'inputs.json',binding['file_pins']['inputs.json']);t=load_transforms(source/'transforms.json',binding['file_pins']['transforms.json']);forecasts=[]
  # The estimator receives each materialized historical batch, never full inputs or label paths.
  for cutoff in CUTS:
   stage='fixed-quarter-'+cutoff;path=prefix/('prefix-'+cutoff+'.json');batch=_pinned_json(path,pin(path));state=train(batch);state['source_prefix_pin']=pin(path);states.append(state)
   current=[r for r in inputs if r['origin'].startswith('2014-') and quarter(r['origin'])==str(CUTS.index(cutoff)+1)]
   forecasts.extend(forecast(r,t,state) for r in current);guard.check()
  if len(forecasts)!=260 or len({r['key'] for r in forecasts})!=260:raise ValueError('fixed 2014 issue population required')
  files.json('frozen-quarter-states.json',states);files.json('predictions-before-scoring.json',forecasts)
  files.json('input-binding.json',{'prefix_source':str(prefix),'source_binding_pin':pin(source/'binding.json'),'source_input_pin':binding['file_pins']['inputs.json'],'source_transform_pin':binding['file_pins']['transforms.json'],
      'source_label_index_pin':binding['file_pins']['label-index.json'],'source_label_payload_pin':binding['file_pins']['labels.jsonl'],'same_origin_target_used_before_prediction':False,'earlier_quarter_labels_in_later_fixed_fit':True})
  print(json.dumps({'stage':'all_2014_predictions_frozen_before_scoring','beta':[s['beta'] for s in states],'current_alpha':[s['calibration'][str(k+1)]['alpha'] for k,s in enumerate(states)]}),flush=True)
  stage='separate-2014-label-scoring'
  index=_pinned_json(source/'label-index.json',binding['file_pins']['label-index.json']);reader=LabelReader(source/'labels.jsonl',index,inputs,binding['file_pins']['labels.jsonl']);by_key={r['key']:r for r in inputs};modes={'observed':[],'assumed_missing_zero':[]}
  support={'raw_nulls':0,'imputed_closure_positions':0,'newyear_true_zeros':0}
  for f in forecasts:
   inp=by_key[f['key']];label=reader.read_available(inp,'2014-12-31');scenarios=label_scenarios(inp,label)
   for mode in modes:
    v=scenarios[mode];modes[mode].append({**f,'actual':v['actual'],'raw_actual':v['raw_actual'],'complete_label':v['complete']})
   support['raw_nulls']+=sum(v is None for v in label['raw_actual']);support['imputed_closure_positions']+=len(scenarios['imputed_positions'])
   if f['origin']=='2014-01-01' and label['raw_actual'][0]==0.:support['newyear_true_zeros']+=1
  files.json('observed-labels.json',modes['observed']);files.json('assumed-labels.json',modes['assumed_missing_zero']);files.json('assumption-support.json',support)
  evaluation={};eligibility={}
  for mode,rr in modes.items():
   groups={'all260':rr,'normal250':[r for r in rr if r['origin']!='2014-01-01'],'newyear10':[r for r in rr if r['origin']=='2014-01-01'],'yearend':[r for r in rr if r['origin'].startswith('2014-12-')]}
   groups.update({f'Q{q}_all':[r for r in rr if quarter(r['origin'])==str(q)] for q in range(1,5)})
   groups.update({f'Q{q}_normal':[r for r in rr if quarter(r['origin'])==str(q) and r['origin']!='2014-01-01'] for q in range(1,5)})
   for name,rows in groups.items():
    B=measure(rows,lambda r:r['baseline_proxy']);v=measure(rows,lambda r:r['candidate']);evaluation.setdefault(name,{})[mode]={'matched_mean28':B,'fixed_candidate':v}
    delta={'total_MSE':v['macro']['total']-B['macro']['total'],'under':v['shortfall']['macro']['under']-B['shortfall']['macro']['under'],'over':v['shortfall']['macro']['over']-B['shortfall']['macro']['over']}
    failed=[k for k,d in delta.items() if d>(1e-12 if k=='total_MSE' else 1e-8)]
    eligibility.setdefault(name,{})[mode]={'paired_differences':delta,'eligible':not failed,'violations':failed}
   guard.check()
  files.json('evaluation.json',evaluation);files.json('quarter-risk-checks.json',eligibility)
  if {p:verify(Path(p)) for p in closures}!=closures or any(pin(REPO/p)!=v for p,v in pins.items()):raise ValueError('protected evidence changed')
  summary={'status':'complete','closures':closures,'source_pins':pins,'models':4,'lambda':1.,'prefix_complete_counts':previous['prefix_complete_counts'],'prefix_feature_counts':previous['prefix_feature_eligible_counts'],
    'current_quarter_alpha':[s['calibration'][str(k+1)]['alpha'] for k,s in enumerate(states)],'supported_models':sum(s['supported'] for s in states),
    'feature_fallback_2014':sum(r['features'] is None for r in forecasts),'changed_windows_2014':sum(abs(r['correction_total'])>1e-8 for r in forecasts),'all_predictions_retained_without_outer_replacement':True,
    'new_2015_content_fit_predictions_evaluation':False,'adjustment_last_year':2014,'independent_validation':False,'training_internal_constraints_not_holdout':True,'one_predeclared_pass_finished':True,
    'adopted':False,'formal_permission':False,'resources':guard.check(),'seconds':time.monotonic()-STARTED}
  files.json('summary.json',summary);status='complete';print(json.dumps({k:v for k,v in summary.items() if k not in ('closures','source_pins')}),flush=True)
 except BaseException as error:
  files.json('failure.json',{'stage':stage,'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()},True);files.json('failure-prefix.json',{'states':states},True);raise
 finally:files.json('root-closed.json',{'status':status,'files':files.pins.copy(),'immutable':True,'formal_permission':False},True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output.absolute())
