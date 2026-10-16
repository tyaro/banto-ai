"""Compare frozen R1 named tensors under unchanged R0 tolerances."""
import json,math,struct,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'models/mini-transformer'),str(ROOT/'tools')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
def floats(raw,e):
    assert e['offset_bytes']%4==0 and e['length_bytes']%4==0
    b=raw[e['offset_bytes']:e['offset_bytes']+e['length_bytes']]
    assert len(b)==e['length_bytes'] and math.prod(e['shape'])*4==len(b)
    return [v[0] for v in struct.iter_unpack('<f',b)]
def main(reference,rust,output):
    out=Files(output);status='failed';check=MacCheckpoint(seconds=870);passed=False
    try:
        config=ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json';cfg=json.loads(config.read_bytes())
        out.json('phase.json',{'scope':'R1 saved named-tensor numerical comparison only','R0_tolerances_unchanged':True,'contract_sha256':digest(config),'training_test_evaluation':False})
        out.sources([Path(__file__),config,ROOT/'tools/macos_demand_runtime.py',ROOT/'models/mini-transformer/metropt_multiday.py'])
        ref=Path(reference);rs=Path(rust);verify_closed(ref);verify_closed(rs)
        fixture=json.loads((ref/'fixtures.json').read_bytes());manifest=json.loads((rs/'traces-layout.json').read_bytes())
        raw_ref=(ref/'python-traces.bin').read_bytes();raw_rs=(rs/'rust-traces.bin').read_bytes()
        assert digest(rs/'rust-traces.bin')==manifest['payload_sha256']
        assert [c['id'] for c in fixture['cases']]==[c['id'] for c in manifest['cases']]
        results=[];total=bad=0;max_abs=0.
        for left,right in zip(fixture['cases'],manifest['cases'],strict=True):
            lt={v['name']:v for v in left['traces']};rt={v['name']:v for v in right['traces']}
            assert set(lt)==set(rt) and left['batch']==right['batch']
            centers=floats(raw_ref,lt['context_center'])
            for name,entry in rt.items():
                e=lt[name];assert e['shape']==entry['shape']
                xs=floats(raw_ref,e);ys=floats(raw_rs,entry);assert len(xs)==len(ys)
                failures=[];largest=ratio=0.;nonfinite=0;bad_count=0
                for i,(x,y) in enumerate(zip(xs,ys,strict=True)):
                    if not math.isfinite(x) or not math.isfinite(y):nonfinite+=1;bad_count+=1;continue
                    if name=='quantiles':
                        v=(i//(32*3))%3;b=i//(3*32*3)
                        limit=1e-4*fixture['train_scale32'][v]+2e-5*abs(x-centers[b*3+v])
                    else:
                        tol=cfg['tolerance']['normalized_activation'];limit=tol['atol']+tol['rtol']*abs(x)
                    error=abs(x-y);largest=max(largest,error);ratio=max(ratio,error/limit)
                    if error>limit:
                        bad_count+=1
                        if len(failures)<5:failures.append({'index':i,'reference':x,'rust':y,'absolute_error':error,'limit':limit})
                total+=len(xs);bad+=bad_count;max_abs=max(max_abs,largest)
                results.append({'case':left['id'],'tensor':name,'shape':e['shape'],'elements':len(xs),'max_absolute_error':largest,'max_tolerance_ratio':ratio,'failing_elements':bad_count,'nonfinite':nonfinite,'failure_examples':failures})
            q=floats(raw_rs,rt['quantiles'])
            assert all(a<=b<=c for a,b,c in zip(q[0::3],q[1::3],q[2::3],strict=True))
            check.check()
        passed=bad==0
        out.json('tensor-comparisons.json',results)
        out.json('summary.json',{'status':'complete','parity_pass':passed,'cases':len(fixture['cases']),'named_tensor_comparisons':len(results),'elements_compared':total,'failing_elements':bad,'max_absolute_error':max_abs,'reference_closure_sha256':digest(ref/'root-closed.json'),'rust_closure_sha256':digest(rs/'root-closed.json'),'training_or_test_evaluation':False,'resources':check.check()})
        print(json.dumps({'parity_pass':passed,'elements':total,'failing_elements':bad,'max_absolute_error':max_abs}));status='complete'
    except BaseException:
        out.json('failure.json',{'traceback':traceback.format_exc()},True);raise
    finally:out.close(status)
    return 0 if passed else 1
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--reference',required=True);p.add_argument('--rust',required=True);p.add_argument('--output',required=True);a=p.parse_args();sys.exit(main(a.reference,a.rust,a.output))
