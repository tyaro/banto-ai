"""CARE Farm B/C one-shot holdout runner (examples/configs/care-holdout-bc-20261018.json).

    python3 tools/care_holdout.py source            # the ZIP against the contract pins
    python3 tools/care_holdout.py check-a           # generalized code reproduces the Farm A input and preparation bytes
    python3 tools/care_holdout.py input --farm B    # one child per file (870 s each), then the manifest root
    python3 tools/care_holdout.py prep --farm B     # train-only profiles, schedules and origins
    python3 tools/care_holdout.py campaign --hours 1.9   # every fold in order, one child each; resumes

Folds run B 0..8 then C 0..21. A floor break, an over-limit or a failed fold stops the campaign
(recorded in campaign-log.jsonl); nothing is substituted or retried. Scoring is tools/care_holdout_score.py.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path=[p for p in sys.path if Path(p or '.').resolve()!=Path(__file__).resolve().parent]
sys.path[:0]=[str(ROOT/'models/mini-transformer')]
import care_holdout as H  # noqa: E402
from metropt_multiday import digest, verify_closed  # noqa: E402

PARENT_SECONDS=900


def forbid_truth():
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)) and any(s in str(args[0]) for s in H.TRUTH_PATHS):
            raise PermissionError('event truth is unavailable before the freeze')
    sys.addaudithook(audit)


def log(entry):
    H.WORK.mkdir(parents=True,exist_ok=True)
    with open(H.WORK/'campaign-log.jsonl','a') as f:f.write(json.dumps({'time':time.time(),**entry})+'\n')


def source():
    c=H.contract()['source'];h=hashlib.sha256();m=hashlib.md5();n=0
    with open(H.ARCHIVE,'rb') as f:
        for block in iter(lambda:f.read(1<<24),b''):h.update(block);m.update(block);n+=len(block)
    found={'bytes':n,'md5':m.hexdigest(),'sha256':h.hexdigest()}
    if found!={'bytes':c['bytes'],'md5':c['md5'],'sha256':c['sha256']}:raise SystemExit('source differs from the contract: '+json.dumps(found))
    print(json.dumps({'source':'matches the contract',**found}))


def child(args,seconds=PARENT_SECONDS):
    began=time.monotonic()
    try:result=subprocess.run([sys.executable,'-I',__file__,*args],timeout=seconds)
    except subprocess.TimeoutExpired:return {'exit':None,'reason':'parent timeout','seconds':time.monotonic()-began}
    return {'exit':result.returncode,'seconds':time.monotonic()-began}


def input_farm(farm):
    H.check_farm(farm)
    for item in H.manifest(farm)['files']:
        root=H.event_root(farm,item['event_id'])
        if root.exists():
            verify_closed(root);continue  # a closed complete root is reused; anything else stops here
        r=child(['input-event','--farm',farm,'--event',str(item['event_id'])]);log({'stage':'input','farm':farm,'event':item['event_id'],**r})
        if r['exit']!=0:raise SystemExit(f'input stopped at {farm} event {item["event_id"]}: {r}')
    H.assemble(farm);print(json.dumps({'input':farm,'closure':digest(H.manifest_root(farm)/'root-closed.json')}))


def units():
    return [(farm,f['fold']) for farm in H.FARMS for f in H.folds(farm)]


def campaign(hours):
    deadline=time.monotonic()+hours*3600
    for farm,fold in units():
        root=H.unit_root(farm,fold)
        if root.exists():
            if H.unit_complete(farm,fold):
                s=json.loads((root/'summary.json').read_bytes())
                if s['resources']['elapsed_seconds']>870 or s['resources']['peak_rss_bytes']>2*1024**3:raise SystemExit(f'{farm} fold {fold} over a limit')
                continue
            log({'stage':'campaign','event':'stop','reason':'fold root exists but is not complete','farm':farm,'fold':fold})
            raise SystemExit(f'campaign not established: {farm} fold {fold} failed or is incomplete')
        if time.monotonic()+PARENT_SECONDS>deadline:
            log({'stage':'campaign','event':'segment end','next':[farm,fold]});print(json.dumps({'segment_end_before':[farm,fold]}));return
        r=child(['fold','--farm',farm,'--fold',str(fold)]);log({'stage':'campaign','farm':farm,'fold':fold,**r})
        if r['exit']!=0 or not H.unit_complete(farm,fold):
            log({'stage':'campaign','event':'stop','reason':'fold failed','farm':farm,'fold':fold})
            raise SystemExit(f'campaign not established: {farm} fold {fold} failed ({r})')
        print(json.dumps({'fold_complete':[farm,fold],**r}),flush=True)
    log({'stage':'campaign','event':'all folds complete'});print(json.dumps({'campaign':'all folds complete'}))


def check_a(output):
    """The generalized converter and preparation must reproduce the saved Farm A bytes (no training)."""
    import zipfile
    sys.path.insert(0,str(ROOT/'tools/public-data'))
    from care_input import pinned_input
    from care_numeric_prepare import convert
    import care_training_prepare
    m=pinned_input();saved=ROOT/'artifacts/care-numeric-input-20261016';verify_closed(saved)
    meta={f['event_id']:f for f in json.loads((saved/'dataset-manifest.json').read_bytes())['files']};check=H.Checkpoint(seconds=3600);result={}
    with zipfile.ZipFile(H.ARCHIVE) as z:
        for item in m['files']:
            out,first,bits,counts,n=convert(z,item,m['model_feature_order'],check,[])
            same=bytes(out)==(saved/f"event-{item['event_id']}.bin").read_bytes() and first.isoformat()==meta[item['event_id']]['first_timestamp']
            if bits is not None:
                import base64
                same=same and base64.b64encode(bits).decode()==meta[item['event_id']]['offline_prefix_status0_bits_base64']
            result[item['event_id']]=same
    if not all(result.values()):raise SystemExit('Farm A input differs: '+json.dumps(result))
    care_training_prepare.MacCheckpoint=lambda seconds:H.Checkpoint(seconds=seconds)
    care_training_prepare.main(str(saved),str(output))
    reference=ROOT/'artifacts/care-train-profile-schedule-20261016';names=[p.name for p in sorted(reference.iterdir()) if p.name.startswith(('fold-','anchor-'))]
    differ=[n for n in names if digest(reference/n)!=digest(Path(output)/n)]
    if differ:raise SystemExit('Farm A preparation differs: '+json.dumps(differ))
    print(json.dumps({'farm_a_input_files_identical':len(result),'farm_a_preparation_files_identical':len(names)}))


def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('source')
    a=sub.add_parser('check-a');a.add_argument('--output',required=True)
    for name in ('input','prep'):
        a=sub.add_parser(name);a.add_argument('--farm',choices=H.FARMS,required=True)
    a=sub.add_parser('input-event');a.add_argument('--farm',choices=H.FARMS,required=True);a.add_argument('--event',type=int,required=True)
    a=sub.add_parser('fold');a.add_argument('--farm',choices=H.FARMS,required=True);a.add_argument('--fold',type=int,required=True)
    a=sub.add_parser('campaign');a.add_argument('--hours',type=float,default=1.9)
    args=p.parse_args()
    if args.command=='source':source()
    elif args.command=='check-a':check_a(args.output)
    elif args.command=='input':forbid_truth();input_farm(args.farm)
    elif args.command=='input-event':forbid_truth();H.prepare_event(args.farm,args.event,H.Checkpoint())
    elif args.command=='prep':forbid_truth();H.prepare_profiles(args.farm,H.Checkpoint())
    elif args.command=='fold':
        forbid_truth()
        if (args.farm,args.fold) not in units():raise SystemExit('unregistered fold')
        H.run_fold(args.farm,args.fold,H.Checkpoint())
    elif args.command=='campaign':forbid_truth();campaign(args.hours)


if __name__=='__main__':
    main()
