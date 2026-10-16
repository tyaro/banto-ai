"""Freeze same-input norm/attention diagnosis and one source-backed LN candidate."""
import json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/public-data'),str(ROOT/'models/mini-transformer')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_compare import floats
def main():
    out=Files(ROOT/'artifacts/rust-r1-upstream-fixture-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        phase={'scope':'same saved block1 inputs: six LayerNorm and four attention modules; no full forward or learning',
               'hypotheses':['balanced moments versus native moments','LayerNorm per-element sqrt division versus single reciprocal multiplication','attention projection/mask/softmax/mixing rounding'],
               'candidate':'only LayerNorm: centered * reciprocal(sqrt(var+eps)) * weight + bias; same float32 balanced moments/eps/weights',
               'basis':'PyTorch v2.14 CPU LayerNorm computes a row inverse std then multiplies centered input by it; current Rust divides each value by sqrt',
               'source_url':'https://github.com/pytorch/pytorch/blob/v2.14.0/aten/src/ATen/native/cpu/layer_norm_kernel.cpp',
               'candidate_gate':'all same-input candidate norms within original normalized tolerance and aggregate squared error smaller than division across all six inputs; no selection by failing point; attention unchanged if local comparisons pass',
               'confirm':'if gate passes, one general all-LayerNorm repair and original seven-case comparison under unchanged R0.1; residual failure retained without arithmetic search',
               'memory_cap_bytes':2*1024**3,'child_seconds':870,'parent_seconds':900,'training':False,'targets_or_test_truth':False}
        out.json('phase.json',phase)
        cfg=ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json';c=json.loads(cfg.read_bytes())
        out.sources([Path(__file__),ROOT/'crates/banto-ai/src/model.rs',ROOT/'models/mini-transformer/small_model.py',cfg])
        for e in c['references'][:2]:assert digest(ROOT/e['path'])==e['sha256']
        layout=json.loads((ROOT/c['references'][1]['path']).read_bytes());raw=(ROOT/c['references'][0]['path']).read_bytes()
        import torch
        import torch.nn.functional as F
        torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
        arrays={};weights={}
        for e in layout['tensors']:
            if e['name'].startswith('model::blocks.1.'):
                name=e['name'][7:];weights[name]=torch.tensor(floats(raw,e),dtype=torch.float32).reshape(e['shape'])
                arrays[name]=weights[name]
        cert={};roots=[]
        for side,name in [('python','rust-r1-python-reference-20261016'),('rust','rust-r1-burn-predictions2-20261016')]:
            if side=='python':name='rust-r1-python-reference-20261016'
            folder=ROOT/'artifacts'/name;verify_closed(folder);roots.append({'path':str(folder.relative_to(ROOT)),'sha256':digest(folder/'root-closed.json')})
            m=json.loads((folder/('fixtures.json' if side=='python' else 'traces-layout.json')).read_bytes());case=m['cases'][0];assert case['id']=='train-first'
            payload=(folder/('python-traces.bin' if side=='python' else 'rust-traces.bin')).read_bytes()
            ts={e['name']:torch.tensor(floats(payload,e),dtype=torch.float32).reshape(e['shape']) for e in case['traces']}
            a=ts['blocks.0'];b=a+ts['blocks.1.temporal'].reshape(8,3,5,64);cc=b+ts['blocks.1.variate'].reshape(8,5,3,64).transpose(1,2)
            for j,x in enumerate([a,b,cc]):
                x=x.reshape(120,64);base=f'{side}.norm{j}';arrays[base+'.input']=x
                y,mu,inv=torch.native_layer_norm(x,[64],weights[f'blocks.1.norms.{j}.weight'],weights[f'blocks.1.norms.{j}.bias'],1e-5)
                arrays[base+'.reference']=y;arrays[base+'.native_mean']=mu;arrays[base+'.native_inverse_std']=inv
                cert[base]=bool(torch.equal(y,ts[f'blocks.1.norms.{j}'].reshape(120,64)))
                if side=='python':assert cert[base]
            for kind in ['temporal','variate']:
                n=5 if kind=='temporal' else 3;batch=24 if kind=='temporal' else 40
                x=ts['blocks.1.norms.0'].reshape(24,5,64) if kind=='temporal' else ts['blocks.1.norms.1'].transpose(1,2).reshape(40,3,64)
                base=f'{side}.{kind}';arrays[base+'.input']=x
                prefix=f'blocks.1.{kind}'
                q,k,v=[F.linear(x,weights[prefix+'.'+layer+'.weight'],weights[prefix+'.'+layer+'.bias']).reshape(batch,n,4,16).transpose(1,2) for layer in ['q','k','v']]
                logits=(q@k.transpose(-2,-1))/4
                if kind=='temporal':logits=logits.masked_fill(~torch.ones(5,5,dtype=torch.bool).tril(),-torch.inf)
                probs=logits.softmax(-1);mixed=(probs@v).transpose(1,2).reshape(batch,n,64)
                y=F.linear(mixed,weights[prefix+'.out.weight'],weights[prefix+'.out.bias'])
                for key,value in [('q',q),('k',k),('v',v),('logits',logits),('probs',probs),('mixed',mixed),('reference',y)]:arrays[base+'.'+key]=value
                cert[base]=bool(torch.equal(y,ts[prefix]));
                if side=='python':assert cert[base]
            check.check()
        raw=bytearray();entries={}
        for name,tensor in arrays.items():
            vs=tensor.contiguous().flatten().tolist();start=len(raw);raw+=struct.pack('<'+'f'*len(vs),*vs)
            entries[name]={'shape':list(tensor.shape),'offset_bytes':start,'length_bytes':len(vs)*4}
        out.write('tensors.bin',bytes(raw));out.json('manifest.json',{'schema':'banto.r1-upstream-diagnosis.v1','tensors':entries,'payload_sha256':digest(out.root/'tensors.bin'),'source_closures':roots,'phase_sha256':digest(out.root/'phase.json'),'contract_sha256':digest(cfg)})
        out.json('summary.json',{'full_forward_calls':0,'training':False,'native_norm_calls':6,'attention_modules':4,'python_saved_stages_reconstructed':cert,'resources':check.check()})
        print(json.dumps({'status':'complete','manifest_sha256':digest(out.root/'manifest.json'),'tensor_bytes':len(raw)}));status='complete'
    finally:out.close(status)
if __name__=='__main__':main()
