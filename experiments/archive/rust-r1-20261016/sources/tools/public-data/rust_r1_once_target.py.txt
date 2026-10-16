"""One exact 64-byte target after SDK ABI and own-task mapping checks."""
import argparse
import ctypes
import hashlib
import io
import json
import struct
import subprocess
import sys
import traceback
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_publish_preparation import validate_root
from rust_r1_once_contract import branch,verify as old_verify,DECL as OLD_DECL,SDK
from rust_r1_once_contract_repair import BDECL as OLD_REPAIR_DECL
from rust_r1_sgemm_readonly import Runtime,elf
from rust_r1_once_publish import NAMES as OLD_NAMES

ADMISSION=ROOT/'examples/configs/rust-r1-once-call-target-admission-20261016.json'
CONFIG=ROOT/'examples/configs/rust-r1-once-target-execution-20261016.json'
CSOURCE=ROOT/'tools/public-data/rust_r1_once_vm_abi.c'
DECL=ROOT/'artifacts/rust-r1-once-target-declaration-20261016'
ABI=ROOT/'artifacts/rust-r1-once-target-abi-20261016'
OUTPUT=ROOT/'artifacts/rust-r1-once-target-20261016'
WARM=ROOT/'artifacts/rust-r1-sgemm-warm-binding-20261016'

class Region(ctypes.Structure):
    _pack_=4
    _fields_=[('protection',ctypes.c_int32),('max_protection',ctypes.c_int32),('inheritance',ctypes.c_uint32),
        ('offset',ctypes.c_uint64),('user_tag',ctypes.c_uint32),('pages_resident',ctypes.c_uint32),
        ('pages_shared_now_private',ctypes.c_uint32),('pages_swapped_out',ctypes.c_uint32),
        ('pages_dirtied',ctypes.c_uint32),('ref_count',ctypes.c_uint32),('shadow_depth',ctypes.c_uint16),
        ('external_pager',ctypes.c_uint8),('share_mode',ctypes.c_uint8),('is_submap',ctypes.c_int32),
        ('behavior',ctypes.c_int32),('object_id',ctypes.c_uint32),('user_wired_count',ctypes.c_uint16),
        ('flags',ctypes.c_uint16),('pages_reusable',ctypes.c_uint32),('object_id_full',ctypes.c_uint64),
        ('pages_wired',ctypes.c_uint32),('wire_tag',ctypes.c_uint16),('__padding0',ctypes.c_uint16)]

def sources():
    return [Path(__file__),CSOURCE,ADMISSION,CONFIG,ROOT/'tools/public-data/rust_r1_sgemm_readonly.py',
        ROOT/'tools/public-data/rust_r1_once_contract.py',ROOT/'tools/public-data/rust_r1_once_contract_repair.py',
        ROOT/'tools/public-data/rust_r1_once_publish.py',ROOT/'tools/public-data/rust_r1_publish_preparation.py',
        ROOT/'tools/macos_demand_runtime.py',ROOT/'models/mini-transformer/metropt_multiday.py',
        ROOT/'crates/banto-ai/src/model.rs',ROOT/'crates/banto-ai/Cargo.toml',ROOT/'Cargo.lock',
        ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json']

def sdk_files():
    return [SDK/'usr/include'/n for n in ['mach/mach_vm.h','mach/mach_init.h','mach/vm_region.h',
        'mach/vm_prot.h','mach/vm_inherit.h','mach/vm_behavior.h','mach/arm/vm_types.h',
        'mach/arm/boolean.h','mach/memory_object_types.h','mach/mach_types.h','mach/message.h']]+[SDK/'SDKSettings.json']

def old_roots():
    names=OLD_NAMES+['rust-r1-once-results-20261016','rust-r1-once-results-20261016-records',
        'rust-r1-once-final-integrity-20261016-records','rust-r1-once-final-check2-20261016',
        'rust-r1-once-final-check2-20261016-records','rust-r1-sgemm-warm-binding-20261016',
        'rust-r1-sgemm-warm-binding-20261016-records','rust-r1-sgemm-results-20261016',
        'rust-r1-sgemm-query-20261016','rust-r1-sgemm-core-20261016']
    return [ROOT/'artifacts'/n for n in names]

def verify():
    old_verify(OLD_DECL); old_verify(OLD_REPAIR_DECL); verify_closed(DECL)
    for p in json.loads((DECL/'source-pins.json').read_bytes()): assert digest(ROOT/p['path'])==p['sha256']
    for p in json.loads((DECL/'SDK-pins.json').read_bytes()): assert digest(Path(p['path']))==p['sha256']
    for p in json.loads((DECL/'root-pins.json').read_bytes()): assert validate_root(ROOT/p['root'])==p
    for p in json.loads((DECL/'tool-pins.json').read_bytes()): assert digest(Path(p['path']))==p['sha256']

def check_abi(a):
    assert a['sizes']=={'region':ctypes.sizeof(Region),'natural_t':4,'mach_msg_type_number_t':4,
        'mach_vm_address_t':8,'mach_vm_size_t':8,'vm_map_read_t':4,'kern_return_t':4,
        'memory_object_offset_t':8,'vm_object_id_t':8}
    assert a['constants']=={'info_count':ctypes.sizeof(Region)//4,'read':1,'execute':4,'success':0}
    assert a['offsets']=={name:getattr(Region,name).offset for name,_ in Region._fields_}

def declare():
    out=Files(DECL); status='failed'; check=MacCheckpoint(seconds=870)
    try:
        old_verify(OLD_DECL); old_verify(OLD_REPAIR_DECL); out.sources(sources())
        out.json('source-pins.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in sources()])
        out.json('root-pins.json',[validate_root(p) for p in old_roots()])
        out.json('SDK-pins.json',[{'path':str(p),'sha256':digest(p)} for p in sdk_files()])
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
            for p in sdk_files(): z.writestr(str(p.relative_to(SDK)),p.read_bytes())
        out.write('SDK-sources.zip',buf.getvalue())
        commands=[]; tools=[]
        for name in ['clang','llvm-objdump']:
            q=subprocess.run(['/usr/bin/xcrun','--find',name],capture_output=True,timeout=20); assert q.returncode==0
            path=Path(q.stdout.decode().strip()); tools.append({'name':name,'path':str(path),'sha256':digest(path)})
            commands.append({'argv':q.args,'exit':q.returncode,'stdout':q.stdout.decode(),'stderr':q.stderr.decode()})
        out.json('tool-pins.json',tools); out.json('commands.json',commands)
        c=json.loads(ADMISSION.read_bytes()); s=c['selector']; selected=[]
        for key,pc in [('source_root','source_BL_virtual'),('second_source_root','second_BL_virtual')]:
            b=branch(ROOT/s[key],int(s[pc],16)); assert b['kind']=='BL' and b['target']==s['target_virtual']; selected.append(b)
        out.json('selectors.json',selected); out.json('phase.json',{'admission':c,'execution':json.loads(CONFIG.read_bytes())})
        out.json('summary.json',{'declared_before_mapping_and_read':True,'SDK_layout_proof_pending':True,'target_reads':0,'resources':check.check()})
        print(json.dumps({'declared':True,'prior_roots':len(old_roots())})); status='complete'
    finally: out.close(status)

def abi():
    out=Files(ABI); status='failed'; check=MacCheckpoint(seconds=870)
    try:
        verify(); out.sources(sources()); tools=json.loads((DECL/'tool-pins.json').read_bytes()); clang=next(p['path'] for p in tools if p['name']=='clang')
        binary=out.root/'sdk-abi'; assert not binary.exists()
        cmd=[clang,'-std=c11','-Wall','-Wextra','-Werror','-isysroot',str(SDK),str(CSOURCE),'-o',str(binary)]
        q=subprocess.run(cmd,capture_output=True,timeout=45); out.write('compile.stdout',q.stdout); out.write('compile.stderr',q.stderr)
        out.json('compile-command.json',{'argv':cmd,'exit':q.returncode}); assert q.returncode==0
        assert binary.stat().st_size<32*1024**2
        q=subprocess.run([str(binary)],capture_output=True,timeout=5); out.write('abi.stdout',q.stdout); out.write('abi.stderr',q.stderr)
        out.json('abi-command.json',{'argv':q.args,'exit':q.returncode,'binary_sha256':digest(binary)}); assert q.returncode==0
        a=json.loads(q.stdout); out.json('abi.json',a); check_abi(a); verify()
        out.json('summary.json',{'SDK_layout_verified':True,'all_fields':len(Region._fields_),'region_size':ctypes.sizeof(Region),'target_reads':0,'Mach_calls':0,'resources':check.check()})
        status='complete'; print(json.dumps({'ABI_verified':True,'size':ctypes.sizeof(Region)}))
    except BaseException:
        out.json('failure.json',{'traceback':traceback.format_exc()},True); raise
    finally: out.close(status)

def inspect():
    out=Files(OUTPUT); status='failed'; check=MacCheckpoint(seconds=870); rt=None
    try:
        verify(); verify_closed(ABI); check_abi(json.loads((ABI/'abi.json').read_bytes())); out.sources(sources())
        out.json('phase.json',{'admission_sha256':digest(ADMISSION),'execution_sha256':digest(CONFIG),'ABI_closure_sha256':digest(ABI/'root-closed.json')})
        rt=Runtime(); meta=rt.metadata(); out.json('libBLAS-metadata.json',meta)
        c=json.loads(CONFIG.read_bytes()); s=json.loads(ADMISSION.read_bytes())['selector']
        assert meta['image_UUID']==s['expected_libBLAS_UUID'] and rt.cpu_hash=='ca979f3619acb92240c2ef46d7581b1a388761e0fccfa7dc491a7eaa153d584a'
        assert json.loads(json.dumps(meta['platform']))==json.loads((WARM/'image-metadata.json').read_bytes())['platform']
        target=int(c['target_virtual'],16)+rt.slide; assert target%4==0 and c['code_bytes']==64
        rt.system.mach_vm_region_recurse.argtypes=[ctypes.c_uint32,ctypes.POINTER(ctypes.c_uint64),ctypes.POINTER(ctypes.c_uint64),
            ctypes.POINTER(ctypes.c_uint32),ctypes.POINTER(ctypes.c_int32),ctypes.POINTER(ctypes.c_uint32)]
        rt.system.mach_vm_region_recurse.restype=ctypes.c_int32
        calls=[]; depth=0; lo=0; hi=2**64; admitted=False; reason='depth cap'
        for _ in range(c['mapping_depth_cap']):
            address=ctypes.c_uint64(target); size=ctypes.c_uint64(); nest=ctypes.c_uint32(depth)
            info=Region(); count=ctypes.c_uint32(ctypes.sizeof(Region)//4)
            rc=rt.system.mach_vm_region_recurse(rt.task,ctypes.byref(address),ctypes.byref(size),ctypes.byref(nest),
                ctypes.cast(ctypes.byref(info),ctypes.POINTER(ctypes.c_int32)),ctypes.byref(count))
            row={'requested_address':target,'requested_depth':depth,'kern_return':rc,'returned_address':address.value,'returned_size':size.value,
                'returned_depth':nest.value,'returned_count':count.value,'info':{name:getattr(info,name) for name,_ in Region._fields_}}; calls.append(row)
            if rc!=0: reason='mapping query returned non-success'; break
            if count.value!=ctypes.sizeof(Region)//4: reason='SDK count mismatch'; break
            if not (address.value<=target<address.value+size.value<=2**64): reason='target not within returned region (hole or invalid bounds)'; break
            lo=max(lo,address.value); hi=min(hi,address.value+size.value)
            if not (lo<=target and target+64<=hi): reason='64bytes outside effective bounds'; break
            if info.is_submap:
                if nest.value<depth or nest.value>=c['mapping_depth_cap']: reason='invalid nesting depth'; break
                depth=nest.value+1; continue
            if (info.protection&5)!=5: reason='leaf is not readable and executable'; break
            admitted=True; reason='bounded readable executable leaf'; break
        mapping={'target_virtual':c['target_virtual'],'runtime_address':target,'slide':rt.slide,'bytes_requested':64,'queries':calls,
            'effective_begin':lo,'effective_end':hi,'admitted':admitted,'reason':reason}
        out.json('mapping.json',mapping)
        if not admitted:
            out.json('memory-reads.json',rt.reads); verify()
            out.json('summary.json',{'observation_complete':True,'scope_stop':True,'reason':reason,'target_code_reads':0,'target_code_bytes':0,
                'target_executions':0,'new_tensor_BLAS_calls':0,'R1_complete':False,'R2_started':False,'resources':check.check()})
            print(json.dumps({'target_read':False,'reason':reason,'mapping_queries':len(calls)})); status='complete'; return
        raw=rt.read(target,64,64,'fixed call target 64bytes'); out.write('code.bin',raw)
        region={'image_virtual_address':int(c['target_virtual'],16),'runtime_address':target,'bytes':64,
            'sha256':hashlib.sha256(raw).hexdigest(),'complete_function_boundary_known':False}
        out.json('region.json',region); out.write('region.elf',elf(region['image_virtual_address'],raw))
        tools=json.loads((DECL/'tool-pins.json').read_bytes()); objdump=next(p['path'] for p in tools if p['name']=='llvm-objdump')
        cmd=[objdump,'--arch-name=aarch64','--disassemble-all','--section=.text','--no-show-raw-insn',str(out.root/'region.elf')]
        q=subprocess.run(cmd,capture_output=True,timeout=20); out.write('disassembly.stdout',q.stdout); out.write('disassembly.stderr',q.stderr)
        out.json('commands.json',{'argv':cmd,'exit':q.returncode}); assert q.returncode==0 and len(q.stdout)<1024**2 and len(q.stderr)<128*1024
        assert rt.read(target,64,64,'fixed call target identical recheck')==raw
        out.json('memory-reads.json',rt.reads); verify()
        out.json('summary.json',{'observation_complete':True,'scope_stop':False,'target_code_reads':2,'unique_target_regions':1,'target_code_bytes':64,
            'bytes_unchanged':True,'target_executions':0,'other_target_reads':0,'new_tensor_BLAS_calls':0,'full_model_calls':0,
            'R1_complete':False,'R2_started':False,'resources':check.check()})
        print(json.dumps({'target_read':True,'bytes':64,'mapping_queries':len(calls),'sha256':region['sha256']})); status='complete'
    except BaseException:
        out.json('failure.json',{'traceback':traceback.format_exc()},True)
        if rt is not None and not (out.root/'memory-reads.json').exists(): out.json('memory-reads.json',rt.reads,True)
        raise
    finally: out.close(status)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('phase',choices=['declare','abi','inspect']); a=p.parse_args(); globals()[a.phase]()
