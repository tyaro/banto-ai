"""No-forward diagnosis of frozen R1 mismatches and reduction arithmetic."""
import json,math,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'models/mini-transformer'),str(ROOT/'tools'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_compare import floats
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def pair_sum(xs):
    while len(xs)>1:xs=[f32(xs[i]+xs[i+1]) for i in range(0,len(xs),2)]
    return xs[0]
def main():
    out=Files(ROOT/'artifacts/rust-r1-saved-diagnosis-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        phase={'scope':'saved-byte comparison only; no new forward or training','hypothesis':'sequential f32 population variance in Flex introduces rounding before transformer; compare to independent high precision moments and balanced f32 sum without changing model or tolerances','original_result':'114 elements beyond intermediate/normalized tolerance; all physical quantiles within fixed tolerance'}
        out.json('phase.json',phase)
        out.sources([Path(__file__),ROOT/'tools/public-data/rust_r1_compare.py',ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json'])
        folders=[ROOT/'artifacts'/n for n in ['rust-r1-python-reference-20261016','rust-r1-burn-predictions-20261016','rust-r1-compare-20261016']]
        for p in folders:verify_closed(p)
        ref,rs,cmp=folders;fixture=json.loads((ref/'fixtures.json').read_bytes());actual=json.loads((rs/'traces-layout.json').read_bytes())
        rb=(ref/'python-traces.bin').read_bytes();sb=(rs/'rust-traces.bin').read_bytes();inputs=(ref/'inputs.bin').read_bytes()
        rows=[]
        for case,rust in zip(fixture['cases'],actual['cases'],strict=True):
            lt={e['name']:e for e in case['traces']};rt={e['name']:e for e in rust['traces']}
            values=floats(inputs,{'offset_bytes':case['offset_bytes'],'length_bytes':case['length_bytes'],'shape':[case['batch'],3,128]})
            rc=floats(rb,lt['context_scale']);sc=floats(sb,rt['context_scale']);mu=floats(rb,lt['context_center']);sm=floats(sb,rt['context_center'])
            for i in range(case['batch']*3):
                xs=values[i*128:(i+1)*128];floor=fixture['floor_certificates']['floor-equal']['floors'][i%3]
                exact_mean=math.fsum(xs)/128;exact_std=math.sqrt(math.fsum((x-exact_mean)**2 for x in xs)/128)
                pm=f32(pair_sum(xs)/128)
                pv=f32(pair_sum([f32(f32(x-pm)**2) for x in xs])/128)
                ps=max(f32(math.sqrt(pv)),floor)
                truth=max(f32(exact_std),floor)
                rows.append({'case':case['id'],'channel_row':i,'reference_mean':mu[i],'rust_mean':sm[i],'high_precision_mean_f32':f32(exact_mean),'balanced_f32_mean':pm,'reference_scale':rc[i],'rust_scale':sc[i],'high_precision_scale_f32':truth,'balanced_f32_scale':ps,'reference_error_to_moment':abs(rc[i]-truth),'rust_error_to_moment':abs(sc[i]-truth),'balanced_error_to_moment':abs(ps-truth)})
        comparisons=json.loads((cmp/'tensor-comparisons.json').read_bytes())
        failed=[{k:e[k] for k in ['case','tensor','failing_elements','max_absolute_error','max_tolerance_ratio']} for e in comparisons if e['failing_elements']]
        q=[e for e in comparisons if e['tensor']=='quantiles'];assert all(e['failing_elements']==0 for e in q)
        sums={k:math.fsum(r[k] for r in rows) for k in ['reference_error_to_moment','rust_error_to_moment','balanced_error_to_moment']}
        out.json('context-moment-diagnosis.json',rows);out.json('failed-tensor-summary.json',failed)
        summary={'forward_calls':0,'training':False,'cases':len(fixture['cases']),'physical_quantile_cases_passed':len(q),'physical_quantile_elements':sum(e['elements'] for e in q),'physical_quantile_max_tolerance_ratio':max(e['max_tolerance_ratio'] for e in q),'first_failed_stage_per_case':{c['id']:next((e['tensor'] for e in failed if e['case']==c['id']),None) for c in fixture['cases']},'scale_absolute_errors_against_independent_moments':sums,'R1_complete':False,'input_closures':[{'path':str(p.relative_to(ROOT)),'sha256':digest(p/'root-closed.json')} for p in folders],'resources':check.check()}
        out.json('summary.json',summary);print(json.dumps(summary));status='complete'
    finally:out.close(status)
if __name__=='__main__':main()
