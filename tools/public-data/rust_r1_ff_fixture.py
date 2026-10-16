"""Fixed same-input ff.2/residual diagnosis from closed R1 tensors; no full forward."""
import json,struct,sys,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/public-data'),str(ROOT/'models/mini-transformer')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_compare import floats
def main():
    out=Files(ROOT/'artifacts/rust-r1-ff-fixture-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        out.json('phase.json',{'scope':'same-input block1 ff.2 and residual diagnosis; no full forward, training or labels','hypotheses':['upstream error propagated through ff.2','same-input GEMM reduction/bias error','residual-add rounding amplifies cancellation'],'fixed_contract':'unchanged R0.1; no widened tolerances','inputs':'all train-first block1 saved tensors, Python and balanced Rust; entire 120-row shape, not just failing point','operations':'2 PyTorch linear calls plus residual reconstruction and independent high-precision saved dot diagnostic','stop':'reconstruction mismatch or unexplained difference; no arbitrary arithmetic search','memory_cap_bytes':2*1024**3,'child_seconds':870,'parent_seconds':900})
        cfg=ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json';c=json.loads(cfg.read_bytes())
        out.sources([Path(__file__),ROOT/'tools/public-data/rust_r1_compare.py',ROOT/'crates/banto-ai/src/model.rs',cfg])
        refs=[ROOT/'artifacts'/n for n in ['rust-r1-python-reference-20261016','rust-r1-burn-predictions2-20261016']]
        for p in refs:verify_closed(p)
        for e in c['references'][:2]:assert digest(ROOT/e['path'])==e['sha256']
        layout=json.loads((ROOT/c['references'][1]['path']).read_bytes());state=(ROOT/c['references'][0]['path']).read_bytes()
        import torch
        import torch.nn.functional as F
        torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
        tensors={}
        for e in layout['tensors']:
            if e['name'] in ['model::blocks.1.ff.2.weight','model::blocks.1.ff.2.bias']:
                tensors[e['name'].split('::')[1]]=torch.tensor(floats(state,e),dtype=torch.float32).reshape(e['shape'])
        weight=tensors['blocks.1.ff.2.weight'];bias=tensors['blocks.1.ff.2.bias']
        arrays={'weight':weight,'bias':bias};exact={};certificates={}
        for side,folder in zip(['python','rust'],refs,strict=True):
            man=json.loads((folder/('fixtures.json' if side=='python' else 'traces-layout.json')).read_bytes())
            case=man['cases'][0];assert case['id']=='train-first' and case['batch']==8
            raw=(folder/('python-traces.bin' if side=='python' else 'rust-traces.bin')).read_bytes()
            traces={e['name']:torch.tensor(floats(raw,e),dtype=torch.float32).reshape(e['shape']) for e in case['traces']}
            residual=traces['blocks.0']+traces['blocks.1.temporal'].reshape(8,3,5,64)
            residual=residual+traces['blocks.1.variate'].reshape(8,5,3,64).transpose(1,2)
            x=traces['blocks.1.ff.1'];linear=F.linear(x,weight,bias)
            result=residual+linear
            arrays[f'{side}_input']=x;arrays[f'{side}_residual']=residual
            arrays[f'{side}_torch_linear']=linear;arrays[f'{side}_torch_block']=result
            arrays[f'{side}_saved_block']=traces['blocks.1']
            certificates[side]={'torch_reconstruction_equal_saved_block':bool(torch.equal(result,traces['blocks.1'])),'max_reconstruction_error':float((result-traces['blocks.1']).abs().max())}
            # Independent float64 summation is diagnosis only, never a model output.
            rows=x.reshape(-1,128).tolist();w=weight.tolist();b=bias.tolist();flat=linear.flatten().tolist()
            accurate=[math.fsum([*(a*z for a,z in zip(row,wr,strict=True)),bv]) for row in rows for wr,bv in zip(w,b,strict=True)]
            arrays[f'{side}_accurate_linear_f32']=torch.tensor(accurate,dtype=torch.float32).reshape(8,3,5,64)
            exact[side]={'max_torch_dot_absolute_error_to_f64':max(abs(a-z) for a,z in zip(accurate,flat,strict=True))}
        assert certificates['python']['torch_reconstruction_equal_saved_block']
        payload=bytearray();entries={}
        for name,tensor in arrays.items():
            v=tensor.contiguous().flatten().tolist();offset=len(payload);payload+=struct.pack('<'+'f'*len(v),*v)
            entries[name]={'shape':list(tensor.shape),'offset_bytes':offset,'length_bytes':len(v)*4}
        out.write('tensors.bin',bytes(payload));out.json('manifest.json',{'schema':'banto.r1-ff-diagnosis.v1','payload_sha256':digest(out.root/'tensors.bin'),'tensors':entries,'source_closures':[{'path':str(p.relative_to(ROOT)),'sha256':digest(p/'root-closed.json')} for p in refs],'model_payload_sha256':c['references'][0]['sha256'],'contract_sha256':digest(cfg)})
        out.json('summary.json',{'training':False,'full_forward_calls':0,'torch_linear_calls':2,'case':'train-first','reconstruction':certificates,'accurate_dot_diagnosis':exact,'resources':check.check()})
        print(json.dumps(certificates));status='complete'
    finally:out.close(status)
if __name__=='__main__':main()
