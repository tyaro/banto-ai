"""Postprocessing only: neutral model/AdamW state from all fixed selected seeds.

No model construction, forward, backward, optimizer step, or metric computation.
PyTorch RNG bytes remain backend-specific; the exact sampler schedule is pinned.
"""
from io import BytesIO
import json
import math
from pathlib import Path
import struct
import sys
import traceback

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(ROOT/'tools'))
from metropt_multiday import CONFIG, Files, contract, digest, encode_f32, verify_closed
from macos_demand_runtime import MacCheckpoint


def append_tensor(binary,layout,name,tensor):
    while len(binary)%4:binary.append(0)
    values=tensor.detach().cpu().contiguous().reshape(-1).tolist()
    dtype=str(tensor.dtype)
    if dtype=='torch.float32':
        if not all(math.isfinite(x) for x in values):raise ValueError('nonfinite export tensor')
        raw=encode_f32(values);kind='float32-le';unpacked=list(struct.unpack('<'+'f'*len(values),raw))
    elif dtype in ('torch.bool','torch.uint8'):
        raw=bytes(int(x) for x in values);kind='bool-u8' if dtype=='torch.bool' else 'uint8'
        unpacked=[bool(x) for x in raw] if dtype=='torch.bool' else list(raw)
    else:raise ValueError('unsupported export dtype: '+dtype)
    if unpacked!=values:raise ValueError('neutral tensor roundtrip differs')
    layout.append({'name':name,'shape':list(tensor.shape),'dtype':kind,'offset_bytes':len(binary),'length_bytes':len(raw)})
    binary.extend(raw)


def main(campaign,output):
    files=Files(output);check=MacCheckpoint(seconds=870);status='failed'
    try:
        c=contract();campaign=Path(campaign)
        verify_closed(campaign/'scores')
        freeze=json.loads((campaign/'scores/freeze.json').read_bytes())
        expected=set(c['training']['init_seeds'])
        if {entry['seed'] for entry in freeze['units']}!=expected:raise ValueError('incomplete freeze')
        files.sources([Path(__file__),ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py'])
        files.write('config.json',CONFIG.read_bytes())
        import torch
        exports=[]
        for seed in c['training']['init_seeds']:
            root=campaign/('unit-'+str(seed));verify_closed(root)
            entry=next(x for x in freeze['units'] if x['seed']==seed)
            if digest(root/'root-closed.json')!=entry['closure_sha256']:raise ValueError('seed closure changed after freeze')
            selection=json.loads((root/'selection.json').read_bytes())
            for variant in c['model']['variants']:
                selected=selection['variants'][variant];source=root/selected['path']
                if digest(source)!=selected['sha256']:raise ValueError('checkpoint pin')
                state=torch.load(source,map_location='cpu',weights_only=True)
                if state['step']!=selected['step'] or state['schedule_sha256']!=digest(root/'schedule.json'):raise ValueError('step/schedule pin')
                model=state['model'];optimizer=state['optimizer'];groups=optimizer['param_groups']
                if len(groups)!=1:raise ValueError('fixed model expects one optimizer group')
                buffers={'scale_floor','position','time_mask'}
                names=[name for name in model if name not in buffers]
                if len(names)!=len(groups[0]['params']):raise ValueError('parameter mapping length')
                if sum(model[name].numel() for name in names)!=109024:raise ValueError('parameter count')
                binary=bytearray();layout=[]
                for name,tensor in model.items():append_tensor(binary,layout,'model::'+name,tensor)
                mapping=[]
                for identifier,name in zip(groups[0]['params'],names,strict=True):
                    parameter_state=optimizer['state'].get(identifier,{})
                    mapping.append({'optimizer_id':identifier,'parameter_name':name,'state_present':bool(parameter_state)})
                    for field,tensor in parameter_state.items():
                        if field not in ('step','exp_avg','exp_avg_sq'):raise ValueError('unknown optimizer state')
                        if field!='step' and tensor.shape!=model[name].shape:raise ValueError('moment/parameter shape')
                        if field=='exp_avg_sq' and not bool((tensor>=0).all()):raise ValueError('negative second moment')
                        if field=='step' and tensor.item()!=state['step']:raise ValueError('optimizer step mismatch')
                        append_tensor(binary,layout,'adamw::'+name+'::'+field,tensor)
                append_tensor(binary,layout,'torch_rng_backend_specific',state['torch_rng'])
                stem=str(seed)+'-'+variant
                files.write(stem+'.bin',bytes(binary))
                files.json(stem+'-layout.json',{'schema':'banto.python-learning-reference.v1','seed':seed,'variant':variant,
                           'checkpoint_sha256':selected['sha256'],'step':state['step'],'config_sha256':state['config_sha256'],
                           'schedule_sha256':state['schedule_sha256'],'schedule_source':str((root/'schedule.json').resolve()),
                           'sampler_position':state['sampler_position'],'tensors':layout,'optimizer_parameter_mapping':mapping,
                           'optimizer_param_groups':groups,'model_buffers':sorted(buffers),'series_mask':'reconstruct from variant; not persistent',
                           'rng_note':'opaque PyTorch RNG bytes, not a Rust RNG implementation','tensor_roundtrip_exact':True})
                exports.append({'seed':seed,'variant':variant,'step':state['step'],'tensor_count':len(layout),'binary_bytes':len(binary)})
                check.check()
        files.json('summary.json',{'status':'neutral-learning-references-exported','exports':exports,'selection_rule':'all 3 registered seeds, both variants; no best seed',
                   'model_forward_calls':0,'optimizer_updates':0,'new_training':False,'new_scoring':False,'rust_implementation_verified':False,
                   'rust_resume_verified':False,'resources':check.check()})
        status='complete';print(json.dumps({'status':status,'exports':exports}))
    except BaseException:
        failure={'traceback':traceback.format_exc()}
        try:failure['resources']=check.check()
        except BaseException as e:failure['resource_observation_failure']=repr(e)
        files.json('failure.json',failure,True);raise
    finally:files.close(status)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--campaign',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();main(a.campaign,a.output)
