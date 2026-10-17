"""Check one permitted batch in a child receiving only its path and pin; no fitting."""
import argparse,json,sys,time
from pathlib import Path
from unittest.mock import patch
from demand_input_boundary_v2 import _pinned_json
from demand_prefix_adapter import validate_batch,feature_support
from macos_demand_runtime import MacCheckpoint

def run(path,pin):
 guard=MacCheckpoint(seconds=870);allowed=path.resolve();original=Path.open
 def checked(p,*args,**kwargs):
  if p.resolve()!=allowed:raise AssertionError('consumer attempted non-prefix datafile read')
  return original(p,*args,**kwargs)
 with patch.object(Path,'open',checked):
  batch=validate_batch(_pinned_json(path,pin));support=feature_support(batch)
 return {'status':'passed','cutoff':batch['cutoff'],'support':support,'consumer_received_only_prefix':True,'no_model_fit_prediction_score':True,'not_python_sandbox':True,'resources':guard.check()}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prefix',type=Path,required=True);p.add_argument('--pin',required=True);args=p.parse_args()
 print(json.dumps(run(args.prefix,json.loads(args.pin))))
