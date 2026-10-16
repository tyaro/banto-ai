"""Frozen all-layer arithmetic audit: reference, own-input, same-input paths."""
import json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/public-data'),str(ROOT/'models/mini-transformer')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_compare import floats
CASES=['train-first','train-last','zero','constant','floor-below','floor-equal','floor-above']
def catalog():
    nodes=['context_center','context_scale','normalized_context','patch','tokens']
    for i in range(2):
        p=f'blocks.{i}'
        for j,kind in [(0,'temporal'),(1,'variate')]:
            nodes.append(f'{p}.norms.{j}')
            nodes.extend(f'{p}.{kind}.{s}' for s in ['q','k','v','logits','probs','mixed'])
            nodes.extend([f'{p}.{kind}',f'{p}.residual{j}'])
        nodes.extend([f'{p}.norms.2',f'{p}.ff.0',f'{p}.ff.1',f'{p}.ff.2',p])
    return nodes+['final_norm','head','normalized_quantiles','quantiles']
def main():
    out=Files(ROOT/'artifacts/rust-r1-layer-fixture2-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        ref=ROOT/'artifacts/rust-r1-python-reference-20261016';rs=ROOT/'artifacts/rust-r1-burn-predictions3-20261016'
        for p in [ref,rs]:verify_closed(p)
        contract={'schema':'banto.r1-all-layer-audit.v1','cases':CASES,'nodes':catalog(),
          'scope':'diagnosis only; no core/model change, candidate selection, training, labels or performance evaluation',
          'source_model_sha256':digest(ROOT/'crates/banto-ai/src/model.rs'),
          'reference_closure_sha256':digest(ref/'root-closed.json'),'rust_closure_sha256':digest(rs/'root-closed.json'),
          'three_values':'PP=P(P_inputs), RR=R(R_inputs), RP=R(P_inputs); inputs include every branch operand and pinned weights',
          'signed_decomposition':'total=RR-PP; local=RP-PP; propagated=RR-RP; exact float64 decomposition of stored f32, no rounding-bound claim',
          'granularity':'55 fixed kernel boundaries: context moments/normalization, patch/tokens, both blocks all norms, q/k/v projections, masked logits, softmax, mixing, out, three residual sums, FF linear/GELU/linear, final norm/head/ordered quantiles/physical restoration',
          'layouts':'same logical f32 bytes and shapes; reconstruct q/k/v transpose layouts identically for RP attention products; layout differences may be included in local error',
          'anchors':'all 23 saved named outputs per case must be byte-exact in each backend own-path replay; do not attribute original mismatch on anchor failure',
          'metrics':['element count','max absolute error','RMS','max fixed tolerance ratio','failing element count','max f32 ULP distance','signed decomposition closure','local and propagated error L1','mask identity'],
          'tolerance':'unchanged R0.1; additional primitive comparisons are diagnostic, not added original R1 gates; physical quantile limit uses saved T32 and PP center',
          'zero_missing':'observed zero/constant/floor cases retained, no imputation; only -infinity masked logits allowed; reject NaN/unexpected infinity',
          'stop':'one reference diagnostic replay and one Rust own-path replay per case, plus 385 isolated same-input node evaluations; preserve negative results; no arithmetic repair or repeated full confirmation in this unit',
          'limits':{'parent_seconds':900,'child_seconds':870,'memory_each_bytes':2*1024**3,'build_cache_bytes':1536*1024**2,'artifact_bytes':768*1024**2,'single_file_bytes':32*1024**2,'evidence_bytes':16*1024**2,'evidence_part_bytes':256*1024,'jobs':1,'threads':1}}
        assert len(catalog())==55
        cfgpath=ROOT/'examples/configs/rust-r1-all-layer-audit-20261016.json'
        assert json.loads(cfgpath.read_bytes())==contract
        out.json('phase.json',contract)
        out.json('harness-repair.json',{'prior_root':'artifacts/rust-r1-layer-fixture-20261016','reason':'plain tensor functional replay under default grad mode failed strict zero/blocks.0.variate anchor; bind original nn modules/parameters and no_grad exactly as fixed reference; no core/model/contract/tolerance changes; stop if this still does not reproduce all anchors'})
        cfg=ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json';c=json.loads(cfg.read_bytes())
        out.sources([Path(__file__),ROOT/'crates/banto-ai/src/model.rs',ROOT/'models/mini-transformer/small_model.py',cfg,cfgpath])
        for e in c['references'][:2]:assert digest(ROOT/e['path'])==e['sha256']
        l=json.loads((ROOT/c['references'][1]['path']).read_bytes());wraw=(ROOT/c['references'][0]['path']).read_bytes()
        import torch
        import torch.nn.functional as F
        torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
        from small_model import SmallForecaster
        arrays={};weights={};state={}
        for e in l['tensors']:
            if e['name'].startswith('model::'):
                n=e['name'][7:]
                if e['dtype']=='float32-le':t=torch.tensor(floats(wraw,e),dtype=torch.float32).reshape(e['shape'])
                else:t=torch.tensor(list(wraw[e['offset_bytes']:e['offset_bytes']+e['length_bytes']]),dtype=torch.bool).reshape(e['shape'])
                state[n]=t
        model=SmallForecaster(state['scale_floor'],series_attention='full');model.load_state_dict(state,strict=True);model.eval();torch.set_grad_enabled(False)
        weights={**dict(model.named_parameters()),**dict(model.named_buffers())};modules=dict(model.named_modules())
        for n,t in weights.items():
            if t.dtype==torch.float32:arrays['weight/'+n]=t
        rm=json.loads((ref/'fixtures.json').read_bytes());sm=json.loads((rs/'traces-layout.json').read_bytes())
        rraw=(ref/'python-traces.bin').read_bytes();sraw=(rs/'rust-traces.bin').read_bytes();inputs=(ref/'inputs.bin').read_bytes()
        cases=[];cert=[]
        for left,right in zip(rm['cases'],sm['cases'],strict=True):
            cid=left['id'];b=left['batch'];assert cid==right['id'] and b==right['batch'];nodes={}
            def put(n,t):nodes[n]=t;return t
            x=torch.tensor(floats(inputs,{**left,'shape':[b,3,128]}),dtype=torch.float32).reshape(b,3,128);arrays[cid+'/input']=x
            def linear(x,n):return modules[n](x)
            def norm(x,n):return modules[n](x)
            def attn(x,n,causal):
                bb,nn,_=x.shape;raw=[put(n+'.'+k,linear(x,n+'.'+k)) for k in ['q','k','v']]
                q,k,v=[t.reshape(bb,nn,4,16).transpose(1,2) for t in raw]
                logits=q@k.transpose(-2,-1)/4
                if causal:logits=logits.masked_fill(~torch.ones(nn,nn,dtype=torch.bool).tril(),-torch.inf)
                put(n+'.logits',logits);p=put(n+'.probs',logits.softmax(-1));mixed=put(n+'.mixed',(p@v).transpose(1,2).reshape(bb,nn,64))
                return put(n,linear(mixed,n+'.out'))
            mu=put('context_center',x.mean(-1,keepdim=True));scale=put('context_scale',torch.maximum(x.std(-1,correction=0,keepdim=True),weights['scale_floor'].reshape(1,3,1)))
            z=put('normalized_context',(x-mu)/scale);patch=put('patch',linear(z.reshape(b,3,4,32),'patch'))
            tokens=put('tokens',torch.cat([patch,weights['horizon'].reshape(1,1,1,64).expand(b,3,1,64)],2)+weights['position'].reshape(1,1,5,64))
            for i in range(2):
                n=f'blocks.{i}';z=put(n+'.norms.0',norm(tokens,n+'.norms.0'))
                t=attn(z.reshape(b*3,5,64),n+'.temporal',True);tokens=put(n+'.residual0',tokens+t.reshape(b,3,5,64))
                z=put(n+'.norms.1',norm(tokens,n+'.norms.1'));v=attn(z.transpose(1,2).reshape(b*5,3,64),n+'.variate',False)
                tokens=put(n+'.residual1',tokens+v.reshape(b,5,3,64).transpose(1,2));z=put(n+'.norms.2',norm(tokens,n+'.norms.2'))
                h=put(n+'.ff.0',linear(z,n+'.ff.0'));h=put(n+'.ff.1',F.gelu(h));ff=put(n+'.ff.2',linear(h,n+'.ff.2'));tokens=put(n,tokens+ff)
            last=put('final_norm',norm(tokens[:,:,-1],'final_norm'));head=put('head',linear(last,'head'));raw=head.reshape(b,3,32,3);mid=raw[...,0]
            q=put('normalized_quantiles',torch.stack([mid-F.softplus(raw[...,1]),mid,mid+F.softplus(raw[...,2])],-1));put('quantiles',q*scale[...,None]+mu[...,None])
            assert list(nodes)==catalog()
            for e in left['traces']:
                expected=torch.tensor(floats(rraw,e),dtype=torch.float32).reshape(e['shape']);assert torch.equal(nodes[e['name']],expected),(cid,e['name'])
            for n,t in nodes.items():arrays[cid+'/pp/'+n]=t
            for e in right['traces']:arrays[cid+'/anchor/'+e['name']]=torch.tensor(floats(sraw,e),dtype=torch.float32).reshape(e['shape'])
            cert.append({'case':cid,'reference_saved_anchors_exact':len(left['traces'])});cases.append({'id':cid,'batch':b,'nodes':list(nodes),'anchors':[e['name'] for e in right['traces']]});check.check()
        assert [c['id'] for c in cases]==CASES
        payload=bytearray();entries={}
        for name,t in arrays.items():
            vals=t.contiguous().flatten().tolist();offset=len(payload);payload+=struct.pack('<'+'f'*len(vals),*vals)
            entries[name]={'shape':list(t.shape),'offset_bytes':offset,'length_bytes':len(vals)*4}
        out.write('tensors.bin',bytes(payload));out.json('manifest.json',{'schema':contract['schema'],'cases':cases,'tensors':entries,'payload_sha256':digest(out.root/'tensors.bin'),'contract_sha256':digest(cfgpath),'train_scale32':rm['train_scale32']})
        out.json('summary.json',{'cases':7,'nodes_per_case':55,'reference_anchors':cert,'reference_diagnostic_replays':7,'training':False,'R1_tolerances_changed':False,'resources':check.check()})
        print(json.dumps({'status':'complete','manifest_sha256':digest(out.root/'manifest.json'),'tensor_bytes':len(payload)}));status='complete'
    finally:out.close(status)
if __name__=='__main__':main()
