"""R1 past-only Python forward references, no training or CARE test access."""
import json,struct,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'models/mini-transformer'),str(ROOT/'tools')]
from metropt_multiday import Files,digest
from macos_demand_runtime import MacCheckpoint
CONFIG=ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json'
def main(output):
    out=Files(output);check=MacCheckpoint(seconds=870);status='failed';opened=set()
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            p=str(args[0])
            if str(ROOT/'artifacts') in p:
                if any(v in p for v in ['test.bin','validation.bin','calibration.bin','care-evaluator','care-label','event-info','per-event.json']):
                    raise PermissionError('R1 must not open CARE test/truth')
                opened.add(p)
    sys.addaudithook(audit)
    try:
        out.json('phase.json',{'scope':'fixed fold0 selected-model forward on two saved train batches and five artificial cases','no_training_backward_or_optimizer':True,'no_CARE_test_or_truth':True,'expected_cases':['train-first','train-last','zero','constant','floor-below','floor-equal','floor-above'],'tolerance_source':str(CONFIG),'tolerance_sha256':digest(CONFIG)})
        out.sources([Path(__file__),ROOT/'models/mini-transformer/small_model.py',ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py',CONFIG])
        cfg=json.loads(CONFIG.read_bytes())
        for p in cfg['references']:
            assert digest(ROOT/p['path'])==p['sha256']
        assert digest(ROOT/cfg['model']['source'])==cfg['model']['sha256']
        import torch
        from small_model import SmallForecaster
        torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
        layout=json.loads((ROOT/cfg['references'][1]['path']).read_bytes());weights=(ROOT/cfg['references'][0]['path']).read_bytes()
        state={}
        for e in layout['tensors']:
            if not e['name'].startswith('model::'):continue
            b=weights[e['offset_bytes']:e['offset_bytes']+e['length_bytes']]
            if e['dtype']=='float32-le':v=[x[0] for x in struct.iter_unpack('<f',b)];dtype=torch.float32
            else:v=list(b);dtype=torch.bool
            state[e['name'][7:]]=torch.tensor(v,dtype=dtype).reshape(e['shape'])
        model=SmallForecaster(state['scale_floor'],series_attention='full');model.load_state_dict(state,strict=True);model.eval()
        raw=(ROOT/cfg['references'][2]['path']).read_bytes();cases=[]
        for step,name in enumerate(['train-first','train-last']):
            batch=[]
            for i in range(8):
                offset=(step*8+i)*(384+96)*4
                batch.append(list(struct.unpack_from('<384f',raw,offset)))
            cases.append((name,torch.tensor(batch,dtype=torch.float32).reshape(8,3,128)))
        floors=state['scale_floor'].tolist()
        cases.append(('zero',torch.zeros([1,3,128])))
        cases.append(('constant',torch.tensor([3.25,-1.5,0.]).reshape(1,3,1).expand(1,3,128).contiguous()))
        for level,name in [(.5,'floor-below'),(1.,'floor-equal'),(2.,'floor-above')]:
            cases.append((name,torch.tensor([[[f*level*(-1 if t%2 else 1) for t in range(128)] for f in floors]],dtype=torch.float32)))
        inputs=bytearray();expected=bytearray();index=[];certificate=[];floor_cases={}
        for name,x in cases:
            collected={};handles=[]
            for n,m in model.named_modules():
                if n in ['patch','final_norm','head','blocks.0','blocks.1'] or any(n==f'blocks.{i}.{v}' for i in range(2) for v in ['norms.0','norms.1','norms.2','temporal','variate','ff.1']):
                    handles.append(m.register_forward_hook(lambda m,a,y,n=n:collected.__setitem__(n,y.detach().clone())))
            handles.append(model.blocks[0].register_forward_pre_hook(lambda m,a:collected.__setitem__('tokens',a[0].detach().clone())))
            with torch.no_grad():f=model(x)
            for h in handles:h.remove()
            collected.update(context_center=f.mean,context_scale=f.scale,normalized_context=(x-f.mean)/f.scale,normalized_quantiles=f.normalized,quantiles=f.quantiles)
            offset=len(inputs);flat=x.flatten().tolist();inputs+=struct.pack('<'+'f'*len(flat),*flat)
            traces=[]
            for key,tensor in collected.items():
                assert bool(torch.isfinite(tensor).all());values=tensor.flatten().tolist();start=len(expected)
                expected+=struct.pack('<'+'f'*len(values),*values)
                traces.append({'name':key,'shape':list(tensor.shape),'offset_bytes':start,'length_bytes':len(values)*4})
            assert bool((f.quantiles[...,0]<=f.quantiles[...,1]).all()) and bool((f.quantiles[...,1]<=f.quantiles[...,2]).all())
            if name.startswith('floor-'):floor_cases[name]={'population_std':x.std(dim=-1,correction=0).flatten().tolist(),'scale':f.scale.flatten().tolist(),'floors':floors}
            index.append({'id':name,'batch':x.shape[0],'offset_bytes':offset,'length_bytes':len(flat)*4,'traces':traces});check.check()
        assert floor_cases['floor-equal']['population_std']==floors
        assert floor_cases['floor-below']['scale']==floors and all(a>b for a,b in zip(floor_cases['floor-above']['scale'],floors))
        out.write('inputs.bin',bytes(inputs));out.write('python-traces.bin',bytes(expected))
        manifest={'schema':'banto.r1-forward-fixtures.v1','cases':index,'inputs_sha256':digest(out.root/'inputs.bin'),'model_layout_path':cfg['references'][1]['path'],'model_layout_sha256':cfg['references'][1]['sha256'],'model_payload_path':cfg['references'][0]['path'],'model_payload_sha256':cfg['references'][0]['sha256'],'train_scale32':[v['T32'] for v in json.loads((ROOT/cfg['references'][3]['path']).read_bytes())['normalization']],'floor_certificates':floor_cases,'model_sha256':cfg['model']['sha256']}
        out.json('fixtures.json',manifest)
        out.json('summary.json',{'status':'complete','forward_calls':len(cases),'train_cases':2,'artificial_cases':5,'targets_skipped_not_decoded':True,'test_or_truth_opened':False,'training':False,'torch_version':torch.__version__,'threads':1,'artifact_paths_opened':sorted(opened),'resources':check.check()})
        print(json.dumps({'status':'complete','cases':len(cases),'model_parameters':sum(p.numel() for p in model.parameters()),'input_bytes':len(inputs),'trace_bytes':len(expected)}));status='complete'
    except BaseException:
        out.json('failure.json',{'traceback':traceback.format_exc()},True);raise
    finally:out.close(status)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();main(a.output)
