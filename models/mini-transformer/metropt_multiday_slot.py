"""One bounded M1 slot; final slot also scores within the SAME 870s child budget.

Run under tools/public-data/macos_industrial_run_v2.py, one parent per seed.
Three ordered slots maximum. Never auto-starts the next slot or retries a root.
"""
import json
from pathlib import Path
import signal
import sys

from metropt_multiday import CONFIG_SHA, ROOT, contract, digest, verify_closed
from metropt_multiday_run import authorize, run
sys.path.insert(0,str(ROOT/'tools'))
from macos_demand_runtime import MacCheckpoint


def main(dataset,campaign,seed,permit,score_permit):
    authorize(permit,'M1-train-predict');authorize(score_permit,'M1-score')
    c=contract();index=c['training']['init_seeds'].index(seed)
    check=MacCheckpoint(seconds=870)
    def terminate(signum,frame):raise RuntimeError('parent requested bounded termination; preserve partial state')
    signal.signal(signal.SIGTERM,terminate)
    campaign=Path(campaign)
    declaration={'plan_id':c['plan_id'],'config_sha256':CONFIG_SHA,'dataset_closure_sha256':digest(Path(dataset)/'root-closed.json'),
                 'seeds':c['training']['init_seeds'],'training_permit_sha256':digest(permit),'score_permit_sha256':digest(score_permit),
                 'source_pins':{n:digest(Path(__file__).with_name(n)) for n in ('metropt_multiday.py','metropt_multiday_run.py','metropt_multiday_score.py','metropt_multiday_slot.py','small_model.py')},
                 'parent_units':3,'child_seconds_each_including_final_scoring':870}
    if index==0:
        campaign.mkdir(parents=True,exist_ok=False)
        with (campaign/'campaign.json').open('x') as f:json.dump(declaration,f,indent=2);f.write('\n')
    elif json.loads((campaign/'campaign.json').read_bytes())!=declaration:
        raise ValueError('campaign/source/input/permit differs')
    roots=[campaign/('unit-'+str(s)) for s in c['training']['init_seeds']]
    for earlier in roots[:index]:verify_closed(earlier)
    check.check();run(dataset,roots[index],seed,permit);check.check()
    if index==2:
        from metropt_multiday_score import main as score
        score(dataset,roots,campaign/'scores',score_permit);check.check()
    # No further slot is launched here. Operator/caller checks this exit and closure first.


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--campaign',required=True)
    p.add_argument('--seed',type=int,choices=(20261016,20261017,20261018),required=True)
    p.add_argument('--permit',required=True);p.add_argument('--score-permit',required=True)
    a=p.parse_args();main(a.dataset,a.campaign,a.seed,a.permit,a.score_permit)
