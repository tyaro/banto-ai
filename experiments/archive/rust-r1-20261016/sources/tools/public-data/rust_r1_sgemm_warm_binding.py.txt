"""One preregistered saved patch call; data-only warm configuration binding."""
import argparse
import hashlib
import json
import struct
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'models/mini-transformer'), str(ROOT/'tools/public-data')]
from metropt_multiday import Files, digest, verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_sgemm_readonly import Runtime, verify_pins, CONFIG as ORIGINAL, SDK
from rust_r1_compare import floats

CONFIG = ROOT/'examples/configs/rust-r1-sgemm-warm-binding-admission-20261016.json'
DECL = ROOT/'artifacts/rust-r1-sgemm-warm-declaration-20261016'
OUTPUT = ROOT/'artifacts/rust-r1-sgemm-warm-binding-20261016'
INPUT = ROOT/'artifacts/rust-r1-linear-python-20261016'
KEYS = ['train-first/input', 'weight/patch.weight', 'weight/patch.bias', 'train-first/python/fused']
SHAPES = [[8,3,4,32], [64,32], [64], [8,3,4,64]]
NAMES = ['rust-r1-sgemm-results-20261016', 'rust-r1-linear-python-20261016'] + [
    f'rust-r1-sgemm-{n}-20261016' for n in ['entry','forwarder','dispatch','core','small-tn','query']]
BASE, SIZE = 0x1e63de938, 88
UUID = '31104d4f4a7e3fa79e1855937b2011f2'

def sources():
    return [Path(__file__), CONFIG, ORIGINAL, ROOT/'tools/public-data/rust_r1_sgemm_readonly.py',
            ROOT/'tools/public-data/rust_r1_compare.py', ROOT/'crates/banto-ai/src/model.rs',
            ROOT/'Cargo.lock', ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json',
            ROOT/'tools/macos_demand_runtime.py', ROOT/'models/mini-transformer/metropt_multiday.py']

def inputs():
    m = json.loads((INPUT/'manifest.json').read_bytes())
    raw = (INPUT/'tensors.bin').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == m['payload_sha256']
    pins = []
    for key, shape in zip(KEYS, SHAPES, strict=True):
        e = m['tensors'][key]; assert e['shape'] == shape
        data = raw[e['offset_bytes']:e['offset_bytes']+e['length_bytes']]
        assert len(data) == e['length_bytes']
        pins.append({'key':key, **e, 'sha256':hashlib.sha256(data).hexdigest()})
    return m, raw, pins

def fields(raw):
    assert len(raw) == SIZE
    # Only instruction-referenced addresses are interpreted; no guessed semantic names.
    return {hex(a): {'type':t, 'value':struct.unpack_from(fmt,raw,a-BASE)[0]}
            for a,t,fmt in [(0x1e63de940,'int32','<i'),(0x1e63de950,'int32','<i'),
                (0x1e63de958,'int32','<i'),(0x1e63de960,'int32','<i'),
                (0x1e63de968,'uint64','<Q'),(0x1e63de980,'int32','<i'),(0x1e63de988,'int64','<q')]}

def verify_declaration():
    verify_pins(); verify_closed(DECL)
    for p in json.loads((DECL/'source-pins.json').read_bytes()):
        assert digest(ROOT/p['path']) == p['sha256']
    for p in json.loads((DECL/'root-pins.json').read_bytes()):
        verify_closed(ROOT/p['path']); assert digest(ROOT/p['path']/'root-closed.json') == p['sha256']
    for p in json.loads((DECL/'sdk-pins.json').read_bytes()):
        assert digest(Path(p['path'])) == p['sha256']
    assert inputs()[2] == json.loads((DECL/'input-pins.json').read_bytes())

def declare():
    out = Files(DECL); status = 'failed'; check = MacCheckpoint(seconds=870)
    try:
        verify_pins()
        roots = [ROOT/'artifacts'/n for n in NAMES]
        for root in roots: verify_closed(root)
        _,_,pins = inputs()
        out.sources(sources()); out.json('phase.json', json.loads(CONFIG.read_bytes()))
        out.json('source-pins.json', [{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in sources()])
        out.json('root-pins.json', [{'path':str(p.relative_to(ROOT)),'sha256':digest(p/'root-closed.json')} for p in roots])
        out.json('input-pins.json', pins)
        out.json('sdk-pins.json', [{'path':str(SDK/'mach'/n),'sha256':digest(SDK/'mach'/n)} for n in ['mach_vm.h','mach_init.h']])
        out.json('summary.json', {'declared_before_operator':True,'torch_imports':0,'CPU_linear_calls':0,'resources':check.check()})
        status='complete'; print(json.dumps({'declared':True,'input_entries':len(pins)}))
    finally: out.close(status)

def run():
    out = Files(OUTPUT); status='failed'; check = MacCheckpoint(seconds=870)
    try:
        verify_declaration(); out.sources(sources())
        out.json('phase.json', {'admission_sha256':digest(CONFIG),'CPU_linear_calls_limit':1,'new_executable_reads':0,'full_model_calls':0,'training':False})
        rt=Runtime(); meta=rt.metadata(); out.json('image-metadata.json',meta)
        assert meta['image_UUID']==UUID and rt.cpu_hash=='ca979f3619acb92240c2ef46d7581b1a388761e0fccfa7dc491a7eaa153d584a'
        segments=[s for s in meta['segments'] if s['name']=='__DATA_DIRTY' and s['initprot']&1 and not s['initprot']&4 and s['address']<=BASE and BASE+SIZE<=s['address']+s['size']]
        assert len(segments)==1
        before=rt.read(BASE+rt.slide,SIZE,SIZE,'warm data before single patch'); out.write('configuration-before.bin',before)
        out.json('data-bounds.json', {'segment':segments[0],'virtual_start':hex(BASE),'runtime_start':BASE+rt.slide,'bytes':SIZE})
        import torch
        m,raw,pins=inputs()
        def tensor(key):
            e=m['tensors'][key]
            return torch.tensor(floats(raw,e),dtype=torch.float32,device='cpu').reshape(e['shape'])
        layer=torch.nn.Linear(32,64,device='meta')
        layer.weight=torch.nn.Parameter(tensor('weight/patch.weight'))
        layer.bias=torch.nn.Parameter(tensor('weight/patch.bias')); layer.eval()
        x=tensor('train-first/input')
        assert x.is_contiguous() and layer.weight.is_contiguous() and layer.bias.is_contiguous()
        assert torch.get_num_threads()==torch.get_num_interop_threads()==1
        out.json('operator-binding.json', {'input_pins':pins,'CPU_linear_calls_planned':1,'meta_constructor':True,'no_grad':True,'x_stride':list(x.stride()),'weight_stride':list(layer.weight.stride()),'bias_stride':list(layer.bias.stride()),'CPU_random_initialization':False,'torch_version':torch.__version__,'torch_git':torch.version.git_version,'threads':torch.get_num_threads(),'interop_threads':torch.get_num_interop_threads()})
        with torch.no_grad(): y=layer(x)  # The only CPU Linear forward in this unit.
        after=rt.read(BASE+rt.slide,SIZE,SIZE,'warm data after single patch'); out.write('configuration-after.bin',after)
        again=rt.read(BASE+rt.slide,SIZE,SIZE,'warm data after stability recheck'); out.write('configuration-recheck.bin',again)
        out.json('memory-reads.json',rt.reads)
        assert list(y.shape)==[8,3,4,64] and y.is_contiguous()
        actual=struct.pack('<6144f',*y.reshape(-1).tolist()); out.write('patch-output.bin',actual)
        e=m['tensors']['train-first/python/fused']; expected=raw[e['offset_bytes']:e['offset_bytes']+e['length_bytes']]
        differences=sum(a!=b for a,b in zip(struct.iter_unpack('<I',actual),struct.iter_unpack('<I',expected),strict=True))
        b,a=fields(before),fields(after)
        stable=after==again; initialized=a['0x1e63de988']['value']==-1
        query=1 if stable and initialized and a['0x1e63de940']['value']==1 else None
        out.json('configuration-fields.json', {'before':b,'after':a,'stable':stable,'once_initialized':initialized,'proven_query_result':query,'query_called_directly':False,'TLS_read':False,'reason':'TLS nonzero returns1; otherwise initialized global@940; global1 proves either branch' if query==1 else 'unresolved: no retry or extra query permitted'})
        comparison={'elements':6144,'bit_mismatches':differences,'bytes_equal':actual==expected,'actual_sha256':hashlib.sha256(actual).hexdigest(),'original_sha256':hashlib.sha256(expected).hexdigest()}
        out.json('output-comparison.json',comparison)
        assert actual==expected, 'original saved patch output differs; no retry'
        assert stable and initialized, 'warm configuration not stable/initialized; no retry'
        verify_declaration()
        summary={'CPU_linear_calls':1,'original_patch_bit_exact':True,'patch_elements':6144,'stable_configuration':stable,'once_initialized':initialized,'proven_query_result':query,'new_executable_reads':0,'data_reads':3,'bytes_per_data_read':SIZE,'new_Rust_candidates':0,'full_model_calls':0,'R1_complete':False,'R2_started':False,'training':False,'resources':check.check()}
        out.json('summary.json',summary); print(json.dumps(summary)); status='complete'
    except BaseException:
        out.json('failure.json',{'traceback':traceback.format_exc()},True); raise
    finally: out.close(status)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('phase',choices=['declare','run']); a=p.parse_args(); globals()[a.phase]()
