"""Saved all-node signed decomposition; fixed R1 thresholds are unchanged."""
import json,math,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/public-data'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools')]
from metropt_multiday import Files,digest,verify_closed
from rust_r1_compare import floats
from macos_demand_runtime import MacCheckpoint
def key(x):
    bits=struct.unpack('<I',struct.pack('<f',x))[0]
    return 0x80000000-(bits&0x7fffffff) if bits>>31 else 0x80000000+bits
def family(n):
    if n.startswith('context_') or n=='normalized_context':return 'context_normalization'
    if '.norms.' in n or n=='final_norm':return 'layer_norm'
    if n.endswith(('.residual0','.residual1')) or n in ['blocks.0','blocks.1']:return 'residual_sum'
    if '.temporal' in n or '.variate' in n:
        s=n.split('.')[-1];return 'attention_'+({'q':'projection','k':'projection','v':'projection','probs':'softmax','logits':'logits','mixed':'mixing'}.get(s,'output_projection'))
    if '.ff.' in n:return 'gelu' if n.endswith('.ff.1') else 'ff_linear'
    return n
def main():
    out=Files(ROOT/'artifacts/rust-r1-layer-comparison-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        ref=ROOT/'artifacts/rust-r1-layer-fixture2-20261016';rs=ROOT/'artifacts/rust-r1-layer-kernel-20261016'
        for p in [ref,rs]:verify_closed(p)
        contract=ROOT/'examples/configs/rust-r1-all-layer-audit-20261016.json';c=json.loads(contract.read_bytes())
        assert digest(ROOT/'crates/banto-ai/src/model.rs')==c['source_model_sha256']
        out.json('phase.json',{'scope':'signed exact decomposition of saved f32 at all declared nodes; no new kernels','contract_sha256':digest(contract),'training':False,'repairs_selected':False,'local_error_interpretation':'same-input implementation discrepancy, may include rounding and transcendental approximations; not a proven roundoff-only bound','propagation_interpretation':'same Rust operation with own-path operands versus frozen Python-path operands; logical shape/transpose layout matched, not a Jacobian estimate'})
        out.sources([Path(__file__),contract,ROOT/'tools/public-data/rust_r1_compare.py',ROOT/'crates/banto-ai/src/model.rs'])
        l=json.loads((ref/'manifest.json').read_bytes());r=json.loads((rs/'manifest.json').read_bytes())
        assert l['contract_sha256']==digest(contract) and r['fixture_manifest_sha256']==digest(ref/'manifest.json')
        lb=(ref/'tensors.bin').read_bytes();rb=(rs/'tensors.bin').read_bytes()
        assert digest(ref/'tensors.bin')==l['payload_sha256'] and digest(rs/'tensors.bin')==r['payload_sha256']
        old=ROOT/'artifacts/rust-r1-python-reference-20261016';verify_closed(old);om=json.loads((old/'fixtures.json').read_bytes());ob=(old/'python-traces.bin').read_bytes()
        # Check bit identity rather than torch.equal's numerical zero equality.
        for oldcase in om['cases']:
            for e in oldcase['traces']:
                p=l['tensors'][oldcase['id']+'/pp/'+e['name']]
                assert lb[p['offset_bytes']:p['offset_bytes']+p['length_bytes']]==ob[e['offset_bytes']:e['offset_bytes']+e['length_bytes']]
        results=[];groups={};case_rows=[];r1_bad=r1_elements=0;decomp_max=0.;mask_values=0
        for case in l['cases']:
            cid=case['id'];centers=floats(lb,l['tensors'][cid+'/pp/context_center']);case_local=case_total=0
            for node in case['nodes']:
                p=l['tensors'][cid+'/pp/'+node];rr=r['tensors'][cid+'/rr/'+node];rp=r['tensors'][cid+'/rp/'+node]
                assert p['shape']==rr['shape']==rp['shape']
                xs=floats(lb,p);ys=floats(rb,rr);zs=floats(rb,rp)
                total=[];local=[];prop=[];tol_total=tol_local=0.;bad_total=bad_local=0;ulp_total=ulp_local=ulp_prop=0;closure=0.;mask=0;examples=[]
                for i,(x,y,z) in enumerate(zip(xs,ys,zs,strict=True)):
                    if not all(math.isfinite(v) for v in [x,y,z]):
                        assert node.endswith('.logits') and x==y==z==float('-inf');mask+=1;continue
                    t=y-x;lo=z-x;up=y-z;error=abs(t-math.fsum([lo,up]));closure=max(closure,error)
                    if node=='quantiles':
                        v=(i//96)%3;b=i//288;limit=1e-4*l['train_scale32'][v]+2e-5*abs(x-centers[b*3+v])
                    else:limit=2e-6+2e-5*abs(x)
                    bt=abs(t)>limit;bl=abs(lo)>limit;bad_total+=bt;bad_local+=bl
                    if (bt or bl) and len(examples)<5:examples.append({'index':i,'PP':x,'RR':y,'RP':z,'total':t,'local':lo,'propagated':up,'limit':limit,'total_fail':bt,'local_fail':bl})
                    total.append(t);local.append(lo);prop.append(up);tol_total=max(tol_total,abs(t)/limit);tol_local=max(tol_local,abs(lo)/limit)
                    ulp_total=max(ulp_total,abs(key(y)-key(x)));ulp_local=max(ulp_local,abs(key(z)-key(x)));ulp_prop=max(ulp_prop,abs(key(y)-key(z)))
                assert closure==0,(cid,node,closure)
                def metrics(v):return {'max_abs':max(map(abs,v),default=0.),'RMS':math.sqrt(math.fsum(x*x for x in v)/len(v)) if v else 0.,'L1':math.fsum(map(abs,v))}
                row={'case':cid,'node':node,'family':family(node),'shape':p['shape'],'elements':len(xs),'finite_elements':len(total),'mask_exact_values':mask,'R1_original_gate':node in case['anchors'],'total':metrics(total),'local':metrics(local),'propagated':metrics(prop),'total_max_tolerance_ratio':tol_total,'local_max_tolerance_ratio':tol_local,'total_failing_elements':bad_total,'local_failing_elements':bad_local,'total_max_ULP':ulp_total,'local_max_ULP':ulp_local,'propagated_max_ULP':ulp_prop,'decomposition_max_residual':closure,'failure_examples':examples}
                results.append(row);case_local+=bad_local;case_total+=bad_total;mask_values+=mask;decomp_max=max(decomp_max,closure)
                if node in case['anchors']:r1_bad+=bad_total;r1_elements+=len(xs)
                g=groups.setdefault(family(node),{'node_comparisons':0,'elements':0,'local_failing_elements':0,'total_failing_elements':0,'local_L1':0.,'propagated_L1':0.,'total_L1':0.,'local_max_abs':0.,'propagated_max_abs':0.,'total_max_abs':0.})
                g['node_comparisons']+=1;g['elements']+=len(xs);g['local_failing_elements']+=bad_local;g['total_failing_elements']+=bad_total
                for kind in ['local','propagated','total']:g[kind+'_L1']+=row[kind]['L1'];g[kind+'_max_abs']=max(g[kind+'_max_abs'],row[kind]['max_abs'])
            case_rows.append({'case':cid,'primitive_local_failing_elements':case_local,'primitive_total_failing_elements':case_total});check.check()
        assert len(results)==385 and r1_elements==389214 and r1_bad==1
        out.json('node-comparisons.json',results);out.json('family-comparisons.json',groups);out.json('case-comparisons.json',case_rows)
        out.json('original-gate-failures.json',[e for e in results if e['R1_original_gate'] and e['total_failing_elements']])
        summary={'diagnosis_complete':True,'cases':7,'nodes_per_case':55,'node_comparisons':385,'primitive_elements':sum(e['elements'] for e in results),'local_failing_elements':sum(e['local_failing_elements'] for e in results),'total_failing_elements':sum(e['total_failing_elements'] for e in results),'local_failing_nodes':sum(e['local_failing_elements']>0 for e in results),'total_failing_nodes':sum(e['total_failing_elements']>0 for e in results),'mask_identity_values':mask_values,'signed_decomposition_max_residual':decomp_max,'reference_saved_anchors_byte_exact':161,'rust_saved_anchors_byte_exact':161,'R1_original_elements':r1_elements,'R1_original_failing_elements':r1_bad,'R1_complete':False,'core_changed':False,'model_candidates_tried':0,'training':False,'resources':check.check()}
        out.json('summary.json',summary);print(json.dumps(summary));status='complete'
    finally:out.close(status)
if __name__=='__main__':main()
