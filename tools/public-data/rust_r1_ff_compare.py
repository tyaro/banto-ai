"""Decompose the frozen remaining error without model execution."""
import json,sys,struct,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/public-data'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools')]
from metropt_multiday import Files,digest,verify_closed
from rust_r1_compare import floats
from macos_demand_runtime import MacCheckpoint
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def main():
    out=Files(ROOT/'artifacts/rust-r1-ff-diagnosis2-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        fixture=ROOT/'artifacts/rust-r1-ff-fixture-20261016';rs=ROOT/'artifacts/rust-r1-ff-kernel-20261016'
        verify_closed(fixture);verify_closed(rs)
        out.json('phase.json',{'scope':'saved ff.2 and residual error decomposition; no new forward or training','tolerances':'unchanged R0.1','repair':'Rust JSON f32 shortest decimals must be parsed back as f32 before byte equality; first diagnostic compared parsed float64 decimals directly and is retained as failed','new_kernel_calls':0})
        out.sources([Path(__file__),ROOT/'tools/public-data/rust_r1_compare.py'])
        m=json.loads((fixture/'manifest.json').read_bytes());raw=(fixture/'tensors.bin').read_bytes()
        t={k:floats(raw,e) for k,e in m['tensors'].items()};r={k:[f32(x) for x in v] for k,v in json.loads((rs/'outputs.json').read_bytes()).items()}
        def cmp(a,b):
            errors=[abs(x-y) for x,y in zip(a,b,strict=True)];ratios=[e/(2e-6+2e-5*abs(x)) for x,e in zip(a,errors,strict=True)]
            return {'elements':len(errors),'max_absolute_error':max(errors),'max_tolerance_ratio':max(ratios),'failing_elements':sum(v>1 for v in ratios),'byte_exact':all(x==y for x,y in zip(a,b,strict=True))}
        results={}
        for side in ['python','rust']:
            results[f'{side}_same_input_linear']=cmp(t[f'{side}_torch_linear'],r[f'{side}_flex_linear'])
            residual=t[f'{side}_residual'];linear=r[f'{side}_flex_linear'];block=r[f'{side}_flex_block']
            results[f'{side}_identical_operands_add']=cmp([f32(a+b) for a,b in zip(residual,linear,strict=True)],block)
            results[f'{side}_saved_reconstruction']=cmp(t[f'{side}_saved_block'],block)
            results[f'{side}_torch_to_accurate']=cmp(t[f'{side}_accurate_linear_f32'],t[f'{side}_torch_linear'])
            results[f'{side}_flex_to_accurate']=cmp(t[f'{side}_accurate_linear_f32'],linear)
        assert results['rust_saved_reconstruction']['byte_exact']
        assert results['python_identical_operands_add']['byte_exact'] and results['rust_identical_operands_add']['byte_exact']
        i=4359;fields={'python_residual':t['python_residual'][i],'rust_residual':t['rust_residual'][i],
                      'torch_linear_python_input':t['python_torch_linear'][i],'torch_linear_rust_input':t['rust_torch_linear'][i],
                      'flex_linear_python_input':r['python_flex_linear'][i],'flex_linear_rust_input':r['rust_flex_linear'][i],
                      'python_block':t['python_saved_block'][i],'rust_block':t['rust_saved_block'][i],
                      'accurate_linear_python_input':t['python_accurate_linear_f32'][i],'accurate_linear_rust_input':t['rust_accurate_linear_f32'][i]}
        pieces={'upstream_residual':fields['rust_residual']-fields['python_residual'],
                'upstream_ff_input_through_torch':fields['torch_linear_rust_input']-fields['torch_linear_python_input'],
                'same_input_linear_backend':fields['flex_linear_rust_input']-fields['torch_linear_rust_input']}
        total=fields['rust_block']-fields['python_block'];pieces['residual_add_rounding_difference']=total-math.fsum(pieces.values())
        assert math.fsum(pieces.values())==total
        point={'index':i,'coordinate':[4,1,3,7],'values':fields,'signed_error_decomposition':pieces,'signed_total':total,'limit':2e-6+2e-5*abs(fields['python_block'])}
        out.json('kernel-comparisons.json',results);out.json('remaining-point.json',point)
        summary={'full_forward_calls':0,'training':False,'same_input_linear_comparisons_pass':all(results[f'{s}_same_input_linear']['failing_elements']==0 for s in ['python','rust']),
                 'identical_operand_add_byte_exact':True,'Rust_saved_block_reproduced_byte_exact':True,
                 'point':point,'R1_complete':False,'resources':check.check()}
        out.json('summary.json',summary);print(json.dumps(summary));status='complete'
    finally:out.close(status)
if __name__=='__main__':main()
