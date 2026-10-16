"""One candidate-only comparison against closed PP and RP linear outputs."""
import json
import math
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_compare import floats
from rust_r1_moments_audit import metrics,packed

def main():
    out=Files(ROOT/'artifacts/rust-r1-fused-linear-local-comparison-20261016');status='failed';check=MacCheckpoint(seconds=870);passed=False
    try:
        names=['rust-r1-layer-fixture2-20261016','rust-r1-layer-kernel-20261016','rust-r1-fused-linear-local-kernel-20261016','rust-r1-fused-linear-probe-20261016','rust-r1-fused-linear-dependencies-20261016']
        roots=[ROOT/'artifacts'/n for n in names]
        for p in roots:verify_closed(p)
        probe=json.loads((roots[3]/'summary.json').read_bytes());assert probe['artificial_cases']==8 and probe['paths']==2 and probe['exact_elements']==74 and probe['boundary_rejections']==13 and probe['parent_only_graph_routes']==3 and probe['high_rank_wrapper'] and probe['backward_calls']==0
        # No post-probe changes to the candidate, metadata guard or dependency.
        for pin in json.loads((roots[4]/'source-pins-before-kernels.json').read_bytes()):assert digest(ROOT/pin['path'])==pin['sha256']
        ms=[json.loads((p/'manifest.json').read_bytes()) for p in roots[:3]];raw=[(p/'tensors.bin').read_bytes() for p in roots[:3]]
        for p,m in zip(roots,ms,strict=False):assert digest(p/'tensors.bin')==m['payload_sha256']
        assert ms[1]['fixture_manifest_sha256']==ms[2]['fixture_manifest_sha256']==digest(roots[0]/'manifest.json')
        config=ROOT/'examples/configs/rust-r1-fused-linear-admission-20261016.json'
        out.sources([Path(__file__),config,ROOT/'crates/banto-ai/src/fused_linear.rs',ROOT/'crates/banto-ai/examples/diagnose_fused_linear.rs',ROOT/'tools/public-data/rust_r1_moments_audit.py',ROOT/'tools/public-data/rust_r1_compare.py']);out.json('phase.json',{'contract_sha256':digest(config),'candidate_count':1,'old_baseline_kernels':0,'full_forward':0,'training':False})
        def values(i,key):return floats(raw[i],ms[i]['tensors'][key])
        records=[];cases=[]
        for c in ms[0]['cases']:
            cid=c['id'];keys=sorted(k for k in ms[2]['tensors'] if k.startswith(cid+'/candidate/'));assert len(keys)==22
            for key in keys:
                node=key.split('/candidate/',1)[1];pp=values(0,cid+'/pp/'+node);rp=values(1,cid+'/rp/'+node);candidate=values(2,key)
                assert ms[0]['tensors'][cid+'/pp/'+node]['shape']==ms[2]['tensors'][key]['shape']
                records.append({'case':cid,'node':node,'baseline':metrics(pp,rp,True),'candidate':metrics(pp,candidate,True),'candidate_equals_baseline_bytes':packed(candidate)==packed(rp)})
            selected=[r for r in records if r['case']==cid];a=math.fsum(r['baseline']['SSE'] for r in selected);b=math.fsum(r['candidate']['SSE'] for r in selected);cases.append({'case':cid,'baseline_SSE':a,'candidate_SSE':b,'nonincrease':b<=a,'failing_elements':sum(r['candidate']['failing_elements'] for r in selected)});check.check()
        assert len(records)==154 and sum(r['candidate']['elements'] for r in records)==465696
        a=math.fsum(r['baseline']['SSE'] for r in records);b=math.fsum(r['candidate']['SSE'] for r in records);bad=sum(r['candidate']['failing_elements'] for r in records)
        gates={'finite_within_original_tolerance':bad==0,'aggregate_SSE_strictly_lower':b<a,'every_case_SSE_nonincreasing':all(r['nonincrease'] for r in cases)};passed=all(gates.values())
        summary={'local_gate_pass':passed,'gates':gates,'comparisons':154,'elements':465696,'baseline_SSE':a,'candidate_SSE':b,'candidate_failing_elements':bad,'case_nonincrease_count':sum(r['nonincrease'] for r in cases),'candidate_equals_baseline_bytes':sum(r['candidate_equals_baseline_bytes'] for r in records),'candidate_count':1,'full_forward':0,'model_changed':False,'training':False,'R1_complete':False,'resources':check.check()}
        out.json('comparisons.json',records);out.json('case-comparisons.json',cases);out.json('summary.json',summary);print(json.dumps(summary));status='complete'
    finally:out.close(status)
    return 0 if passed else 1

if __name__=='__main__':sys.exit(main())
