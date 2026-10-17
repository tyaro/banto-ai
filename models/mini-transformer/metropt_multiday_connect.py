"""M0 only: boundary checks and two untrained forward calls, never fits/scores."""
from io import BytesIO
import hashlib
import json
import math
from pathlib import Path
import platform
import struct
import sys
import traceback

from metropt_multiday import ROOT, CONFIG, CONFIG_SHA, Files, Reader, contract, common_origins, encode_f32, scales
sys.path.insert(0,str(ROOT/'tools'))
from macos_demand_runtime import MacCheckpoint


def portable_state(state, parameter_names):
    raw=bytearray();layout=[]
    for name,tensor in state.items():
        while len(raw)%4:raw.append(0)
        start=len(raw);flat=tensor.detach().contiguous().reshape(-1).tolist()
        if str(tensor.dtype)=='torch.float32':data=encode_f32(flat);dtype='float32-le'
        elif str(tensor.dtype)=='torch.bool':data=bytes(int(x) for x in flat);dtype='bool-u8'
        else:raise ValueError('unsupported portable dtype')
        raw.extend(data)
        layout.append({'name':name,'shape':list(tensor.shape),'dtype':dtype,'offset_bytes':start,'length_bytes':len(data),
                       'role':'parameter' if name in parameter_names else 'buffer','sha256':hashlib.sha256(data).hexdigest()})
    return bytes(raw),{'schema':'banto.small-forecaster.state.v1','tensors':layout,
                       'series_mask':'nonpersistent; reconstruct full/self-only from variant config','alignment_bytes':4}


def main(dataset,output):
    files=Files(output);check=MacCheckpoint(seconds=870);status='failed'
    try:
        c=contract()
        files.json('phase.json',{'phase':'M0 adapter and untrained connection','plan_id':c['plan_id'],
                   'config_authorization_supersession':'latest direct human instruction for M0 only',
                   'optimizer_updates_allowed':0,'validation_test_forward_allowed':0})
        sources=[Path(__file__),Path(__file__).with_name('metropt_multiday.py'),Path(__file__).with_name('small_model.py'),
                 ROOT/'tools/macos_demand_runtime.py']
        for name in ('metropt_multiday_run.py','metropt_multiday_score.py'):
            p=Path(__file__).with_name(name)
            if p.exists():sources.append(p)
        files.sources(sources);files.write('config.json',CONFIG.read_bytes())
        reader=Reader(dataset,'train')
        tests=[]
        def expect_exception(name,fn,error):
            try:fn()
            except error:tests.append(name)
            else:raise AssertionError(name)
        expect_exception('split/day mismatch rejected',lambda:reader.context((c['calendar']['selected_days']['test'][0],128)),ValueError)
        expect_exception('origin before context boundary rejected',lambda:reader.context((reader.days[0],127)),ValueError)
        expect_exception('cross-day slice rejected',lambda:reader._slice(reader.keys[0],-1,128),ValueError)
        test_reader=Reader(dataset,'test')
        expect_exception('test targets denied before quantity read',lambda:test_reader.targets(test_reader.keys[0]),PermissionError)
        zero=[[0.0]*1440 for _ in range(3)];valid=[[True]*1440 for _ in range(3)]
        keep,excluded=common_origins(zero,valid,'train')
        assert len(keep)==1281 and not excluded
        tests.append('observed zero remains valid')
        valid[0][0]=False;keep,excluded=common_origins(zero,valid,'train')
        assert excluded==[128] and len(keep)==1280
        tests.append('quality missing is not converted to observed zero')
        expect_exception('90 percent support failure rejected',lambda:common_origins(zero,[[False]*1440 for _ in range(3)],'test'),ValueError)
        zero_stats=scales([zero]);assert all(s['sigma64']==0 and s['T32']>0 and s['floor32']>0 for s in zero_stats)
        tests.append('constant series scale remains finite positive')
        schedules=[]
        for seed in c['training']['sampler_seeds']:
            schedule=reader.schedule(seed)
            assert len(schedule)==4096 and all(len(batch)==8 and all(tuple(k) in reader.allowed for k in batch) for batch in schedule)
            files.json('schedule-'+str(seed)+'.json',schedule);schedules.append({'seed':seed,'updates':len(schedule),'samples':32768})
        tests.append('all three fixed schedules use train common support')
        import torch
        from small_model import SmallForecaster
        torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
        check.check();torch.manual_seed(c['training']['init_seeds'][0])
        floor=torch.tensor([s['floor32'] for s in reader.stats],dtype=torch.float32)
        full=SmallForecaster(floor,series_attention='full').eval()
        control=SmallForecaster(floor,series_attention='self-only').eval();control.load_state_dict(full.state_dict())
        count=sum(p.numel() for p in full.parameters());assert count==109024
        assert all(torch.equal(full.state_dict()[n],t) for n,t in control.state_dict().items())
        assert not torch.equal(full.series_mask,control.series_mask)
        raw=BytesIO();torch.save(full.state_dict(),raw);files.write('initial.pt',raw.getvalue())
        binary,layout=portable_state(full.state_dict(),set(dict(full.named_parameters())))
        files.write('initial-portable.bin',binary);files.json('initial-layout.json',layout)
        # Independently unpack the neutral format, checking every named state tensor.
        for item in layout['tensors']:
            data=binary[item['offset_bytes']:item['offset_bytes']+item['length_bytes']]
            unpacked=list(struct.unpack('<'+'f'*(len(data)//4),data)) if item['dtype']=='float32-le' else [bool(x) for x in data]
            assert unpacked==full.state_dict()[item['name']].reshape(-1).tolist()
        tests.append('portable initial state roundtrip exact')
        key=reader.keys[0];x,y=reader.batch([key])
        assert tuple(x.shape)==(1,3,128) and tuple(y.shape)==(1,3,32)
        predictions={}
        with torch.no_grad():
            for name,model in [('full',full),('self-only',control)]:
                pred=model(x).quantiles
                assert tuple(pred.shape)==(1,3,32,3) and bool(torch.isfinite(pred).all())
                assert bool((pred[...,0]<=pred[...,1]).all()) and bool((pred[...,1]<=pred[...,2]).all())
                predictions[name]=pred[0].tolist();check.check()
        files.json('forward-reference.json',{'key':key,'context':x[0].tolist(),'predictions':predictions,
                   'untrained':True,'future_actuals_saved':False,'float32_cpu':True})
        files.json('checks.json',{'checks':tests,'count':len(tests)})
        summary={'status':'m0-connection-complete','plan_id':c['plan_id'],'config_sha256':CONFIG_SHA,
                 'first_train_origin':key,'context_shape':list(x.shape),'target_shape':list(y.shape),'prediction_shape':[1,3,32,3],
                 'parameters_per_variant':count,'model_forward_calls':2,'optimizer_updates':0,'training_runs':0,
                 'validation_test_forward_calls':0,'performance_scoring_runs':0,'can_launch_learning':False,
                 'common_windows':c['calendar']['candidate_windows'],'schedule_metadata':schedules,
                 'runtime':{'python':platform.python_version(),'torch':torch.__version__,'platform':platform.platform()},
                 'resources':check.check(),'rust_state_fixture':True,'rust_implementation_verified':False}
        files.json('summary.json',summary);status='complete'
        print(json.dumps(summary))
    except BaseException:
        failure={'traceback':traceback.format_exc()}
        try:failure['resources']=check.check()
        except BaseException as e:failure['resource_observation_failure']=repr(e)
        files.json('failure.json',failure,True);raise
    finally:files.close(status)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();main(a.dataset,a.output)
