"""One bounded CARE fold. Fold4 also freezes/scores in the SAME870s child unit."""
import json
from pathlib import Path
import signal
import sys
from care_learning import authorize,run
from metropt_multiday import ROOT,verify_closed
sys.path.insert(0,str(ROOT/'tools'))
from macos_demand_runtime import MacCheckpoint


def main(dataset,prepared,campaign,fold):
    if type(fold) is not int or not 0<=fold<5:raise ValueError('unregistered fold')
    check=MacCheckpoint(seconds=870);declaration=authorize(campaign,dataset,prepared);allow_labels=False
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            p=str(args[0])
            if any(s in p for s in ('care-evaluator-contract-','care-label-metadata-','event-info-','label-manifest.json')) and not allow_labels:
                raise PermissionError('event truth is unavailable to training/inference roles')
    sys.addaudithook(audit)
    def terminate(signum,frame):raise RuntimeError('bounded parent termination; preserve partial state')
    signal.signal(signal.SIGTERM,terminate)
    for root in declaration['unit_roots'][:fold]:verify_closed(root)
    run(dataset,prepared,campaign,fold,declaration['unit_roots'][fold],check);check.check()
    if fold==4:
        from care_score import main as score
        for root in declaration['unit_roots']:verify_closed(root)
        allow_labels=True
        score(dataset,prepared,campaign,declaration['score_root'],check);check.check()

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--prepared',required=True);p.add_argument('--campaign',required=True);p.add_argument('--fold',type=int,choices=range(5),required=True);a=p.parse_args();main(a.dataset,a.prepared,a.campaign,a.fold)
