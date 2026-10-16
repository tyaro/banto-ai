"""Score the predeclared norm candidate and attention stages on same input bytes."""
import json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/public-data'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools')]
from metropt_multiday import Files,digest,verify_closed
from rust_r1_compare import floats
from macos_demand_runtime import MacCheckpoint
def compare(xs,ys):
    assert len(xs)==len(ys)
    errors=[];ratios=[];bad=mask=0
    for x,y in zip(xs,ys,strict=True):
        if not math.isfinite(x) or not math.isfinite(y):
            assert x==y==float('-inf');mask+=1;continue
        e=abs(x-y);limit=2e-6+2e-5*abs(x);errors.append(e);ratios.append(e/limit);bad+=e>limit
    return {'elements':len(xs),'exact_negative_infinity_mask_values':mask,'max_absolute_error':max(errors,default=0),'squared_error_sum':math.fsum(e*e for e in errors),'max_tolerance_ratio':max(ratios,default=0),'failing_elements':bad,'byte_exact':all(x==y for x,y in zip(xs,ys,strict=True))}
def main():
    out=Files(ROOT/'artifacts/rust-r1-upstream-comparison2-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        ref=ROOT/'artifacts/rust-r1-upstream-fixture-20261016';rs=ROOT/'artifacts/rust-r1-upstream-kernel-20261016'
        verify_closed(ref);verify_closed(rs)
        out.json('phase.json',{'scope':'same-input saved diagnostic outputs only','candidate_gate':'predeclared all six norm inputs within unchanged tolerance and lower aggregate squared error; no failing-index selection','training':False,'full_forward_calls':0,'prior_failure':'first Rust diagnostic did not compile: generic shape array serialization; comparator was started before successful compile and failed missing closure; preserve both; serialization changed to Vec, numerical code unchanged'})
        out.sources([Path(__file__),ROOT/'tools/public-data/rust_r1_compare.py'])
        l=json.loads((ref/'manifest.json').read_bytes());r=json.loads((rs/'manifest.json').read_bytes())
        assert r['fixture_manifest_sha256']==digest(ref/'manifest.json')
        lb=(ref/'tensors.bin').read_bytes();rb=(rs/'tensors.bin').read_bytes();assert digest(ref/'tensors.bin')==l['payload_sha256'] and digest(rs/'tensors.bin')==r['payload_sha256']
        a={n:floats(lb,e) for n,e in l['tensors'].items()};b={n:floats(rb,e) for n,e in r['tensors'].items()}
        results={};norms=[];attention=[]
        for side in ['python','rust']:
            for j in range(3):
                key=f'{side}.norm{j}'
                for suffix in ['division','reciprocal']:results[key+'.'+suffix]=compare(a[key+'.reference'],b[key+'.'+suffix])
                for suffix in ['mean','inverse_std']:results[key+'.'+suffix]=compare(a[key+'.native_'+suffix],b[key+'.'+suffix])
                norms.append(key)
            for kind in ['temporal','variate']:
                for suffix in ['q','k','v','logits','probs','mixed','reference']:
                    key=f'{side}.{kind}.{suffix}';assert l['tensors'][key]['shape']==r['tensors'][key]['shape'];results[key]=compare(a[key],b[key]);attention.append(key)
        # Recover original Rust normalized/attention stage outputs exactly.
        old=ROOT/'artifacts/rust-r1-burn-predictions2-20261016';verify_closed(old)
        om=json.loads((old/'traces-layout.json').read_bytes());ob=(old/'rust-traces.bin').read_bytes()
        os={e['name']:floats(ob,e) for e in om['cases'][0]['traces']}
        cert={}
        for j in range(3):cert[f'norm{j}']=os[f'blocks.1.norms.{j}']==b[f'rust.norm{j}.division']
        for k in ['temporal','variate']:cert[k]=os[f'blocks.1.{k}']==b[f'rust.{k}.reference']
        assert all(cert.values())
        old_sse=math.fsum(results[k+'.division']['squared_error_sum'] for k in norms);new_sse=math.fsum(results[k+'.reciprocal']['squared_error_sum'] for k in norms)
        candidate_pass=all(results[k+'.reciprocal']['failing_elements']==0 for k in norms) and new_sse<old_sse
        summary={'candidate_gate_pass':candidate_pass,'norm_inputs':6,'norm_elements':6*7680,'division_squared_error_sum':old_sse,'reciprocal_squared_error_sum':new_sse,
                 'attention_stage_comparisons':len(attention),'attention_failing_elements':sum(results[k]['failing_elements'] for k in attention),'original_Rust_stages_reconstructed_byte_exact':cert,
                 'R1_complete':False,'full_forward_calls':0,'training':False,'resources':check.check()}
        out.json('comparisons.json',results);out.json('summary.json',summary);print(json.dumps(summary));status='complete'
    finally:out.close(status)
if __name__=='__main__':main()
