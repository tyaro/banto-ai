"""One frozen artificial Torch reference; isolated root-edge lock proposal only."""
import difflib
from fractions import Fraction
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tomllib
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'models/mini-transformer'), str(ROOT/'tools/public-data')]
from metropt_multiday import Files, digest, verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_publish_preparation import validate_root
from rust_r2p_freeze import analytic_loss

PREFIX = 'rust-r2p-reference-20261016'
SPEC = 'examples/configs/rust-r2p-synthetic-protocol-20261016.json'
FIX = 'examples/configs/rust-r2p-synthetic-fixtures-20261016.json'
R0 = 'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json'
def read(p): return json.loads(Path(p).read_bytes())
def folder(s): return ROOT/'artifacts'/(PREFIX+s)
def pins():
    previous = ROOT/'artifacts/rust-r2p-specification-20261016'
    verify_closed(previous)
    return read(previous/'protected-source-pins.json') + read(previous/'input-and-protocol-pins.json')
def checkpins(p):
    for item in p: assert digest(ROOT/item['path']) == item['sha256'], item['path']
def sources():
    return [Path(__file__), ROOT/'tools/public-data/rust_r2p_freeze.py', ROOT/SPEC, ROOT/FIX, ROOT/R0,
            ROOT/'tools/macos_demand_runtime.py', ROOT/'models/mini-transformer/metropt_multiday.py']

def declare(out, check):
    p = pins(); checkpins(p)
    out.sources(sources()); out.json('protected-pins.json', p)
    out.json('admission.json', {
        'authorization': 'human: 固定した条件に沿ってCargo.lockの最小整合案を確認し人工データのPython参照を生成・保存',
        'scope': 'offline scratch lock proposal, then one artificial-only Torch CPU float32 reference; no Rust build/training',
        'lock_method': 'copy current workspace manifests/source into a fresh scratch root; remove only stale direct gemm edge; locked offline tree must pass; no resolver updates',
        'lock_acceptance': 'all package records and versions identical except that single root edge; active package/version and feature sets equal the closed pre-existing baseline',
        'source_lock_left_unchanged': True,
        'sequence_clarification': 'verified isolated consistency permits Python-only reference; actual workspace lock remains unapplied and Rust acceptance still requires applying this proposal as an explicit later change',
        'reference': {'loss_cases': 7, 'clip_cases': 4, 'AdamW_one_updates': 6, 'toy_updates': 8,
                      'native_backward_calls': 15, 'native_optimizer_updates': 14, 'native_clip_calls': 18, 'toy_probe_forwards': 9,
                      'dtype': 'CPU float32', 'threads': 1, 'interop_threads': 1, 'RNG_draws': 0,
                      'independent_checks': 'exact Fraction loss/gradient, scalar binary64 global clip and AdamW from decoded float32 input; toy scalar forward/loss/gradient and one-step scalar update from each saved native prior state',
                      'native_sequence': 'one continuous8; no restart/reference selection or alternative arithmetic search',
                      'scalar_math_not_float32_operation_order_claim': True},
        'gates': read(ROOT/R0)['tolerance'], 'limits': read(ROOT/SPEC)['limits'],
        'pointer_tracking': False, 'full_model': False, 'real_data': False, 'Rust_build_tests_training': False,
        'original_tolerance_unchanged': True, 'formal_R2_stopped': True, 'R1_unmet': True,
        'future_rejections_and_resume_tests_not_run': True, 'Windows_native_OS_tests': 'unrun', 'heartbeat': 'PAUSED'})
    out.json('summary.json', {'declaration_fixed': True, 'resources': check.check()})

def lock(out, check):
    verify_closed(folder('-declaration')); checkpins(pins())
    scratch = ROOT/'outputs'/PREFIX/'lock-workspace'
    scratch.mkdir(parents=True, exist_ok=False)
    copied = [ROOT/n for n in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml', '.cargo/config.toml']]
    copied += [p for p in (ROOT/'crates/banto-ai').rglob('*') if p.is_file() and (p.suffix == '.rs' or p.name in ['Cargo.toml', 'README.md'])]
    for p in copied:
        dest = scratch/p.relative_to(ROOT); dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as f: f.write(p.read_bytes())
    before = (ROOT/'Cargo.lock').read_bytes(); old = tomllib.loads(before.decode())
    text = before.decode(); blocks = text.split('[[package]]')
    selected = [i for i,b in enumerate(blocks) if re.search(r'^name = "banto-ai"$', b, re.M)]
    assert len(selected) == 1
    i = selected[0]; assert blocks[i].count(' "gemm",\n') == 1
    blocks[i] = blocks[i].replace(' "gemm",\n', '', 1)
    candidate = '[[package]]'.join(blocks).encode(); new = tomllib.loads(candidate.decode())
    expected = json.loads(json.dumps(old)); root = next(p for p in expected['package'] if p['name']=='banto-ai')
    root['dependencies'].remove('gemm'); assert new == expected
    # Only the fresh scratch copy is updated; immutable original bytes are saved below.
    (scratch/'Cargo.lock').write_bytes(candidate)
    out.sources(sources()+copied); out.write('Cargo.lock.before', before); out.write('Cargo.lock.proposed', candidate)
    out.write('Cargo.lock.diff', ''.join(difflib.unified_diff(text.splitlines(True), candidate.decode().splitlines(True), fromfile='Cargo.lock.original', tofile='Cargo.lock.proposed')).encode())
    commands = []
    cargo = '/Users/tyaromax/.rustup/toolchains/stable-aarch64-apple-darwin/bin/cargo'
    for name,args in [('packages', ['-e','normal,build','--prefix','none']), ('features', ['-e','features','--prefix','none'])]:
        argv = [cargo,'tree','--locked','--offline','-p','banto-ai',*args]
        result = subprocess.run(argv,cwd=scratch,capture_output=True,timeout=120)
        assert len(result.stdout)<=1048576 and len(result.stderr)<=131072
        out.write('cargo-'+name+'.stdout',result.stdout); out.write('cargo-'+name+'.stderr',result.stderr)
        commands.append({'argv':argv,'cwd':str(scratch),'exit':result.returncode})
        out.json('command-'+name+'.json',commands[-1]); assert result.returncode==0, result.stderr.decode()
        assert (scratch/'Cargo.lock').read_bytes()==candidate
        check.check()
    def packages(raw):
        return {m.groups() for line in raw.splitlines() if (m:=re.match(r'^(\S+) v([^ ]+)',line))}
    def features(raw):
        return {m.group(0) for line in raw.splitlines() if (m:=re.match(r'^\S+ feature "[^"]+"',line))}
    baseline = ROOT/'artifacts/rust-r1-fused-linear-dependencies-20261016'; verify_closed(baseline)
    currentpackages = packages((out.root/'cargo-packages.stdout').read_text())
    currentfeatures = features((out.root/'cargo-features.stdout').read_text())
    assert currentpackages == {tuple(p) for p in read(baseline/'packages.json')}
    assert currentfeatures == set(read(baseline/'effective-features.json'))
    b = io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(scratch.rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(scratch).as_posix())
    out.write('scratch-workspace.zip', b.getvalue())
    out.json('scratch-pins.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in sorted(scratch.rglob('*')) if p.is_file()])
    out.json('active-graph.json', {'packages':sorted(currentpackages),'features':sorted(currentfeatures), 'baseline':validate_root(baseline)})
    checkpins(pins())
    out.json('summary.json', {'isolated_proposal_verified':True,'original_workspace_lock_applied':False,
              'only_change':'remove banto-ai direct gemm dependency edge','lock_package_records':len(new['package']),
              'package_versions_unchanged':True,'active_packages':len(currentpackages),'active_features_unchanged':True,
              'automatic_experimental_features_restored':False,'build_tests':0,'resources':check.check()})
    print(json.dumps({'isolated_lock_verified':True,'active_packages':len(currentpackages),'original_lock_changed':False}))

class Capture:
    def __init__(self, torch, tolerances):
        self.torch=torch; self.tolerances=tolerances; self.raw=bytearray(); self.layout=[]; self.checks=[]
    def tensor(self, label, tensor):
        assert tensor.dtype==self.torch.float32 and tensor.device.type=='cpu'
        values=tensor.detach().contiguous().reshape(-1).tolist(); assert all(math.isfinite(v) for v in values)
        raw=struct.pack('<'+'f'*len(values),*values); offset=len(self.raw); self.raw.extend(raw)
        item={'name':label,'shape':list(tensor.shape),'values':values,'dtype':'float32-le',
              'offset':offset,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        assert label not in {x['name'] for x in self.layout}; self.layout.append(item); return values
    def gate(self, name, native, expected, kind):
        a=list(native); b=list(expected); assert len(a)==len(b) and a
        assert all(math.isfinite(x) for x in a+b)
        tol=self.tolerances[kind]; differences=[abs(x-y) for x,y in zip(a,b)]
        bad=sum(d>tol['atol']+tol['rtol']*abs(y) for d,y in zip(differences,b))
        norm=math.sqrt(math.fsum(y*y for y in b)); delta=math.sqrt(math.fsum(d*d for d in differences))
        rel=delta/norm if norm else None
        passed=bad==0 and (kind!='gradient' or (rel<=tol['relative_L2_max'] if norm else delta<=tol['atol']))
        self.checks.append({'name':name,'category':kind,'elements':len(a),'max_abs':max(differences),
                            'element_failures':bad,'relative_L2':rel,'candidate_L2':math.sqrt(math.fsum(x*x for x in a)), 'pass':passed})
        assert passed, self.checks[-1]

def flat(groups): return [x for group in groups for x in group]
def scalar_clip(groups):
    norm=math.sqrt(math.fsum(x*x for x in flat(groups))); coef=min(1.,1./(norm+1e-6))
    return norm,coef,[[x*coef for x in row] for row in groups]
def scalar_update(parameters, gradients, moments, variances, step, recipe):
    b1,b2=recipe['betas']; lr=recipe['lr']; t=step+1
    m=[[b1*x+(1-b1)*g for x,g in zip(row,gs)] for row,gs in zip(moments,gradients)]
    v=[[b2*x+(1-b2)*g*g for x,g in zip(row,gs)] for row,gs in zip(variances,gradients)]
    p=[[x*(1-lr*recipe['weight_decay'])-lr*(mm/(1-b1**t))/(math.sqrt(vv/(1-b2**t))+recipe['eps'])
        for x,mm,vv in zip(row,ms,vs)] for row,ms,vs in zip(parameters,m,v)]
    return p,m,v

def reference(out, check):
    verify_closed(folder('-declaration')); verify_closed(folder('-lock'))
    assert read(folder('-lock')/'summary.json')['isolated_proposal_verified']
    checkpins(pins()); out.sources(sources()+[ROOT/p['path'] for p in pins() if '/torch/' in p['path']])
    import torch
    assert sys.version_info[:3]==(3,14,8) and torch.version.git_version==read(ROOT/SPEC)['runtime']['torch_git']
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    assert torch.get_num_threads()==torch.get_num_interop_threads()==1
    fx=read(ROOT/FIX); c=Capture(torch, read(ROOT/R0)['tolerance']); recipe=fx['optimizer_recipe']
    def tensor(values, shape): return torch.tensor(values,dtype=torch.float32,device='cpu').reshape(shape)
    tau=tensor(fx['quantiles'],[3]); c.tensor('quantiles',tau)
    def loss(pred,y,center,scale):
        r=((y-center)/scale).unsqueeze(-1)-pred
        return torch.maximum(tau*r,(tau-1)*r).mean()
    def clip(ps,label):
        assert all(p.grad is not None and torch.isfinite(p.grad).all().item() for p in ps)
        raw=[c.tensor(label+f'/raw-gradient/{i}',p.grad) for i,p in enumerate(ps)]
        norm=torch.nn.utils.clip_grad_norm_(ps,1.,error_if_nonfinite=True,foreach=False)
        c.tensor(label+'/global-norm',norm); c.tensor(label+'/clip-coefficient',torch.clamp(1./(norm+1e-6),max=1.))
        clipped=[c.tensor(label+f'/clipped-gradient/{i}',p.grad) for i,p in enumerate(ps)]
        _,_,expected=scalar_clip(raw); c.gate(label+'/clip',flat(clipped),flat(expected),'gradient')
        return raw,clipped
    def optimizer(ps):
        return torch.optim.AdamW(ps,lr=recipe['lr'],betas=tuple(recipe['betas']),eps=recipe['eps'],
                               weight_decay=recipe['weight_decay'],amsgrad=False,maximize=False,foreach=False,fused=False)
    def state(opt,ps,label):
        p=[c.tensor(label+f'/parameter/{i}',v) for i,v in enumerate(ps)]
        m=[c.tensor(label+f'/moment1/{i}',opt.state[v]['exp_avg']) for i,v in enumerate(ps)]
        v=[c.tensor(label+f'/moment2/{i}',opt.state[v]['exp_avg_sq']) for i,v in enumerate(ps)]
        steps=[int(opt.state[p]['step'].item()) for p in ps]
        assert all(opt.state[p]['step'].item()==s for p,s in zip(ps,steps)) and len(set(steps))==1
        for i,p0 in enumerate(ps): c.tensor(label+f'/step-tensor/{i}',opt.state[p0]['step'])
        return p,m,v,steps[0]
    oracles=[]; journal=[]
    for case in fx['loss_cases']:
        B,C,H,Q=case['shape']; label=case['id']; pred=tensor(case['prediction'],[B,C,H,Q]).requires_grad_()
        y=tensor(case['actual'],[B,C,H]); center=tensor(case['center'],[B,C,1]); scale=tensor(case['scale'],[B,C,1])
        for n,t in [('prediction',pred),('actual',y),('center',center),('scale',scale)]: c.tensor(label+'/'+n,t)
        l=loss(pred,y,center,scale); l.backward()
        a=analytic_loss(case); oracles.append(a)
        c.gate(label+'/loss',c.tensor(label+'/loss',l),[float(Fraction(a['loss_rational']))],'normalized_loss')
        c.gate(label+'/gradient',c.tensor(label+'/gradient',pred.grad),[float(Fraction(x)) for x in a['prediction_gradient_rational']],'gradient')
        check.check()
    for case in fx['clip_cases']:
        ps=[torch.nn.Parameter(torch.zeros(s,dtype=torch.float32)) for s in case['shapes']]
        for p,g in zip(ps,case['gradients']): p.grad=tensor(g,list(p.shape))
        clip(ps,case['id']); check.check()
    for case in fx['optimizer_cases']:
        names=fx['optimizer_parameter_order']; ps=[torch.nn.Parameter(tensor(fx['optimizer_initial_parameters'][n]['values'],fx['optimizer_initial_parameters'][n]['shape'])) for n in names]
        opt=optimizer(ps); label=case['id']
        for i,p in enumerate(ps):
            p.grad=tensor(case['gradients'][i],list(p.shape))
            opt.state[p]={'step':tensor([case['step_before']],[]),'exp_avg':tensor(case['m_before'][i],list(p.shape)),
                          'exp_avg_sq':tensor(case['v_before'][i],list(p.shape))}
        p0,m0,v0,s0=state(opt,ps,label+'/before'); raw,clipped=clip(ps,label)
        # Scalar mathematical update from independent global clip, not native clipped gradient.
        expected=scalar_update(p0,scalar_clip(raw)[2],m0,v0,s0,recipe)
        opt.step(); pn,mn,vn,sn=state(opt,ps,label+'/after'); assert sn==s0+1
        for values,ref,kind in zip([pn,mn,vn],expected,['one_step_parameter','first_moment','second_moment']): c.gate(label+'/'+kind,flat(values),flat(ref),kind)
        journal.append({'case':label,'ordered_names':names,'step_before':s0,'step_after':sn}); check.check()
    toy=fx['toy_training']; names=toy['parameter_order']
    ps=[torch.nn.Parameter(tensor(toy['parameters'][n]['values'],toy['parameters'][n]['shape'])) for n in names]
    opt=optimizer(ps)
    for p in ps: opt.state[p]={'step':tensor([0],[]),'exp_avg':torch.zeros_like(p),'exp_avg_sq':torch.zeros_like(p)}
    center=tensor(toy['buffers']['center']['values'],[1,1,1]); scale=tensor(toy['buffers']['scale']['values'],[1,1,1])
    probe=tensor(toy['probe_x'],[1,1,2,2]); c.tensor('toy/probe-input',probe); c.tensor('toy/center',center); c.tensor('toy/scale',scale)
    def forward(x): return x@ps[0].T+ps[1]
    def scalar_forward(xs, pv):
        w,b=pv; return [xs[h*2]*w[q*2]+xs[h*2+1]*w[q*2+1]+b[q] for h in range(2) for q in range(3)]
    def probe_check(step,pv):
        with torch.no_grad(): q=forward(probe)
        c.gate(f'toy/probe/{step}',c.tensor(f'toy/probe/{step}',q),scalar_forward(toy['probe_x'],pv),'normalized_activation')
    initial=state(opt,ps,'toy/step0'); probe_check(0,initial[0])
    for step,batch_id in enumerate(toy['schedule'],1):
        batch=next(b for b in toy['batch_table'] if b['id']==batch_id); label=f'toy/update{step}'
        p0,m0,v0,s0=state(opt,ps,label+'/before'); assert s0==step-1
        opt.zero_grad(set_to_none=True)
        x=tensor(batch['x'],[1,1,2,2]); y=tensor(batch['target'],[1,1,2]); c.tensor(label+'/x',x); c.tensor(label+'/target',y)
        q=forward(x); l=loss(q,y,center,scale); l.backward()
        qmath=scalar_forward(batch['x'],p0); loss_kind='normalized_loss' if step==1 else 'eight_step_loss'
        c.gate(label+'/prediction',c.tensor(label+'/prediction',q),qmath,'normalized_activation')
        grads=[]; total=0.
        for h in range(2):
            for qi,t in enumerate([.1,.5,.9]):
                r=batch['target'][h]-qmath[h*3+qi]; total+=max(t*r,(t-1)*r)
                grads.append((-t if r>0 else 1-t if r<0 else .5-t)/6)
        gw=[sum(grads[h*3+qi]*batch['x'][h*2+j] for h in range(2)) for qi in range(3) for j in range(2)]
        gb=[sum(grads[h*3+qi] for h in range(2)) for qi in range(3)]
        c.gate(label+'/loss',c.tensor(label+'/loss',l),[total/6],loss_kind)
        raw,clipped=clip(ps,label); c.gate(label+'/analytic-gradient',flat(raw),gw+gb,'gradient')
        expected=scalar_update(p0,scalar_clip([gw,gb])[2],m0,v0,s0,recipe)
        opt.step(); pn,mn,vn,sn=state(opt,ps,label+'/after'); assert sn==step
        kinds=['one_step_parameter' if step==1 else 'eight_step_parameter','first_moment','second_moment']
        for values,ref,kind in zip([pn,mn,vn],expected,kinds): c.gate(label+'/'+kind,flat(values),flat(ref),kind)
        probe_check(step,pn); journal.append({'case':'toy','batch':batch_id,'ordered_names':names,'global_step':sn,'per_parameter_steps':[sn,sn],'schedule_next':step})
        check.check()
    out.write('reference.f32',bytes(c.raw)); out.json('reference-layout.json',c.layout)
    out.json('independent-checks.json',c.checks); out.json('analytic-loss-oracles.json',oracles); out.json('state-journal.json',journal)
    out.json('runtime.json',{'python':sys.version,'torch':torch.__version__,'torch_git':torch.version.git_version,
                           'threads':torch.get_num_threads(),'interop_threads':torch.get_num_interop_threads(),'dtype':'float32-le CPU',
                           'optimizer_recipe':recipe,'capturable':False,'differentiable':False,'RNG_draws':0,
                           'protocol_sha256':digest(ROOT/SPEC),'fixtures_sha256':digest(ROOT/FIX),
                           'schedule_sha256':hashlib.sha256(json.dumps(toy['schedule'],separators=(',',':')).encode()).hexdigest()})
    checkpins(pins()); out.json('protected-pins-after.json',pins())
    out.json('summary.json',{'Python_reference_frozen':True,'loss_cases':7,'clip_cases':4,'optimizer_cases':6,'toy_updates':8,
        'native_optimizer_updates':14,'backward_calls':15,'clip_calls':18,'toy_probe_forwards':9,
        'checks':len(c.checks),'all_checks_pass':all(x['pass'] for x in c.checks),'saved_tensors':len(c.layout),'saved_float32_values':len(c.raw)//4,
        'reference_sha256':digest(out.root/'reference.f32'),'Rust_training_executed':False,'Rust_resume_verified':False,
        'R1_pass':False,'formal_R2_started':False,'resources':check.check()})
    print(json.dumps({'Python_reference_frozen':True,'checks':len(c.checks),'all_checks_pass':True,'float32_values':len(c.raw)//4}))

def main():
    phase=sys.argv[1]; suffix={'declare':'-declaration','lock':'-lock','reference':'-numeric'}[phase]
    out=Files(folder(suffix)); check=MacCheckpoint(seconds=870); status='failed'
    try:
        {'declare':declare,'lock':lock,'reference':reference}[phase](out,check); status='complete'
    except BaseException:
        out.json('failure.json',{'traceback':traceback.format_exc(),'phase':phase,'resources':check.check()},True)
        raise
    finally: out.close(status)
if __name__=='__main__': main()
