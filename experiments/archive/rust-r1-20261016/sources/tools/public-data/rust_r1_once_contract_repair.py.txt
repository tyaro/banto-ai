"""SDK source audit, then a separately declared public-API metadata binding."""
import argparse
import ctypes
import hashlib
import io
import json
import plistlib
import re
import struct
import sys
import traceback
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_publish_preparation import validate_root
from rust_r1_sgemm_warm_binding import verify_declaration as verify_warm, CONFIG as WARM_CONFIG
from rust_r1_sgemm_readonly import Runtime

SDK=Path('/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
CONFIG=ROOT/'examples/configs/rust-r1-sgemm-once-semantics-admission-20261016.json'
BIND=ROOT/'examples/configs/rust-r1-once-api-binding-20261016.json'
SOURCE=ROOT/'artifacts/rust-r1-once-source-20261016'
DECL=ROOT/'artifacts/rust-r1-once-source-declaration-20261016'
BDECL=ROOT/'artifacts/rust-r1-once-api-repair-declaration-20261016'
BOUT=ROOT/'artifacts/rust-r1-once-api-repair-binding-20261016'
WARM=ROOT/'artifacts/rust-r1-sgemm-warm-binding-20261016'
PUBLIC={
  'retrieved_date_Asia_Tokyo':'2026-10-16',
  'api_url':'https://developer.apple.com/documentation/dispatch/dispatch_once-c.func',
  'public_contract_paraphrase':'dispatch_once runs its block once during the application lifetime. Concurrent callers wait for completion. Call it before accessing initialized variables. The predicate needs global or static storage. The documented contract does not assign a public meaning to the integer52638546.',
  'retrieval':'Official page search text available through web tool; HTML open required JavaScript and Markdown fetch returned unsupported content-type. This record is an attributed paraphrase, not an archived full page or matching runtime source.',
  'internal_source_requirement':'SDK stub version1605.0.2 is not the installed-runtime identity. Exact internal interpretation requires matching runtime version/image provenance and exact implementation source; neither is established by SDK alone. No other-version implementation used.'}

def sources():
    return [Path(__file__),ROOT/'tools/public-data/rust_r1_once_contract.py',ROOT/'examples/configs/rust-r1-once-api-format-repair-20261016.json',CONFIG,BIND,WARM_CONFIG,ROOT/'tools/public-data/rust_r1_sgemm_warm_binding.py',
        ROOT/'tools/public-data/rust_r1_sgemm_readonly.py',ROOT/'tools/public-data/rust_r1_publish_preparation.py',
        ROOT/'tools/macos_demand_runtime.py',ROOT/'models/mini-transformer/metropt_multiday.py',
        ROOT/'crates/banto-ai/src/model.rs',ROOT/'Cargo.lock',ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json']

def external():
    return [SDK/'usr/include/dispatch/once.h',SDK/'usr/include/dispatch/base.h',
        SDK/'usr/share/man/man3/dispatch_once.3',SDK/'usr/lib/system/libdispatch.tbd',
        SDK/'SDKSettings.json',SDK/'System/Library/CoreServices/SystemVersion.plist',
        Path('/Applications/Xcode.app/Contents/version.plist')]

def roots():
    return [WARM,WARM.with_name(WARM.name+'-records'),ROOT/'artifacts/rust-r1-sgemm-warm-results-20261016',
        ROOT/'artifacts/rust-r1-sgemm-query-20261016',ROOT/'artifacts/rust-r1-sgemm-core-20261016']

def pin(out, prior=()):
    verify_warm(); out.sources(sources())
    out.json('source-pins.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in sources()])
    out.json('external-pins.json',[{'path':str(p),'sha256':digest(p)} for p in external()])
    out.json('root-pins.json',[validate_root(p) for p in [*roots(),*prior]])

def verify(declaration):
    verify_warm(); verify_closed(declaration)
    for p in json.loads((declaration/'source-pins.json').read_bytes()): assert digest(ROOT/p['path'])==p['sha256']
    for p in json.loads((declaration/'external-pins.json').read_bytes()): assert digest(Path(p['path']))==p['sha256']
    for p in json.loads((declaration/'root-pins.json').read_bytes()): assert validate_root(ROOT/p['root'])==p

def branch(root,pc):
    reg=json.loads((root/'region.json').read_bytes()); raw=(root/'code.bin').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==reg['sha256']
    offset=pc-reg['image_virtual_address']; assert offset>=0 and offset%4==0 and offset+4<=len(raw)
    word=struct.unpack_from('<I',raw,offset)[0]; op=word>>26; assert op in (0b100101,0b000101)
    imm=word&0x3ffffff; imm=imm-(1<<26) if imm&(1<<25) else imm
    return {'source_root':str(root.relative_to(ROOT)),'pc':hex(pc),'word':hex(word),'kind':'BL' if op==0b100101 else 'B','target':hex(pc+4*imm)}

def declare():
    out=Files(DECL); status='failed'; check=MacCheckpoint(seconds=870)
    try:
        pin(out); out.json('phase.json',json.loads(CONFIG.read_bytes())); out.json('official-api-paraphrase.json',PUBLIC)
        out.json('summary.json',{'SDK_scope_fixed':True,'new_numeric_calls':0,'new_live_reads':0,'resources':check.check()})
        status='complete'; print(json.dumps({'source_declared':True}))
    finally: out.close(status)

def audit():
    out=Files(SOURCE); status='failed'; check=MacCheckpoint(seconds=870)
    try:
        verify(DECL); out.sources(sources())
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
            for i,p in enumerate(external()): z.writestr(f'{i}-{p.name}',p.read_bytes())
        out.write('SDK-sources.zip',buffer.getvalue()); out.json('external-pins.json',json.loads((DECL/'external-pins.json').read_bytes()))
        once=external()[0].read_text(); base=external()[1].read_text(); man=external()[2].read_text(); tbd=external()[3].read_text()
        needles={'once.h':['typedef intptr_t dispatch_once_t;','It must be initialized to zero.',
            'Always call dispatch_once() before using or testing any variables that are',
            'if (DISPATCH_EXPECT(*predicate, ~0l) != ~0l)',
            'DISPATCH_COMPILER_CAN_ASSUME(*predicate == ~0l);'],
            'base.h':['#define DISPATCH_COMPILER_CAN_ASSUME(expr) __builtin_assume(expr)',
                '#define dispatch_compiler_barrier()  __asm__ __volatile__("" ::: "memory")'],
            'dispatch_once.3':['must have global or static scope.','function is a wrapper around']}
        texts={'once.h':once,'base.h':base,'dispatch_once.3':man}; matched=[]
        for name,items in needles.items():
            for item in items:
                hits=[i for i,line in enumerate(texts[name].splitlines(),1) if item in line]; assert hits,(name,item)
                matched.append({'file':name,'lines':hits,'text':item})
        settings=json.loads(external()[4].read_bytes()); sdkver=plistlib.loads(external()[5].read_bytes()); xcode=plistlib.loads(external()[6].read_bytes())
        version=re.search(r'^current-version:\s+(\S+)',tbd,re.M).group(1); assert version=='1605.0.2'
        assert '_dispatch_once,' in tbd and '_dispatch_once_f,' in tbd
        identity={'SDK_version':settings['Version'],'SDK_build':sdkver['ProductBuildVersion'],'Xcode_short_version':xcode['CFBundleShortVersionString'],
            'Xcode_build':xcode['ProductBuildVersion'],'SDK_stub_current_version':version,'SDK_stub_is_runtime_identity':False,
            'saved_warm_OS':json.loads((WARM/'image-metadata.json').read_bytes())['platform']}
        interpretation={'minus_one_is_inline_fastpath':True,'inline_contains_compiler_assumption':True,
            'public_API_completion_is_synchronous':True,'private_predicate_encoding_proved':False,
            'saved_52638546_not_interpreted':True,'SDK_does_not_identify_installed_dispatch_image':True,
            'old_minus_one_gate_still_failed':True,'query_and_core_public_api_identity_not_yet_bound':True,
            'required_next_observation':'Metadata-only exact saved-BL target to loaded dispatch_once symbol equality; then public API inference only, no private predicate decoding.'}
        out.json('matched-source-lines.json',matched); out.json('identity.json',identity); out.json('official-api-paraphrase.json',PUBLIC)
        out.json('interpretation.json',interpretation); verify(DECL)
        out.json('summary.json',{'source_audit_complete':True,'private_encoding_proved':False,'old_warm_gate_pass':False,
            'new_numeric_calls':0,'new_live_reads':0,'R1_complete':False,'R2_started':False,'resources':check.check()})
        status='complete'; print(json.dumps({'source_audit_complete':True,'private_encoding_proved':False,'SDK_stub_version':version}))
    except BaseException:
        out.json('failure.json',{'traceback':traceback.format_exc()},True); raise
    finally: out.close(status)

def bind_declare():
    out=Files(BDECL); status='failed'; check=MacCheckpoint(seconds=870)
    try:
        verify(DECL); verify_closed(SOURCE); pin(out,[DECL,SOURCE])
        config=json.loads(BIND.read_bytes()); selected=[]
        for s in config['selector']['sources']:
            result=branch(ROOT/s['root'],int(s['instruction'],16)); assert result['kind']=='BL' and result['target']==config['selector']['BL_target_virtual']; selected.append(result)
        out.json('phase.json',config); out.json('saved-BL-selectors.json',selected)
        out.json('summary.json',{'declared_before_metadata_binding':True,'new_numeric_calls':0,'new_live_reads':0,'resources':check.check()})
        status='complete'; print(json.dumps({'API_binding_declared':True,'selectors':len(selected)}))
    finally: out.close(status)

def bind():
    out=Files(BOUT); status='failed'; check=MacCheckpoint(seconds=870)
    try:
        verify(BDECL); out.sources(sources()); out.json('phase.json',json.loads(BIND.read_bytes()))
        rt=Runtime(); meta=rt.metadata(); out.json('libBLAS-metadata.json',meta)
        assert meta['image_UUID']=='31104d4f4a7e3fa79e1855937b2011f2' and rt.cpu_hash=='ca979f3619acb92240c2ef46d7581b1a388761e0fccfa7dc491a7eaa153d584a'
        saved=json.loads((WARM/'image-metadata.json').read_bytes()); assert json.loads(json.dumps(meta['platform']))==saved['platform']
        config=json.loads(BIND.read_bytes()); wanted=int(config['selector']['BL_target_virtual'],16)+rt.slide
        public=ctypes.cast(getattr(rt.system,'dispatch_once'),ctypes.c_void_p).value
        class Info(ctypes.Structure): _fields_=[('fname',ctypes.c_char_p),('fbase',ctypes.c_void_p),('sname',ctypes.c_char_p),('saddr',ctypes.c_void_p)]
        rt.system.dladdr.argtypes=[ctypes.c_void_p,ctypes.POINTER(Info)]; info=Info()
        rc=rt.system.dladdr(wanted,ctypes.byref(info))
        binding={'saved_target_virtual':config['selector']['BL_target_virtual'],'shared_cache_slide':rt.slide,
            'wanted_runtime_address':wanted,'public_symbol_runtime_address':public,'dladdr_return':rc,
            'image':info.fname.decode() if rc and info.fname else None,'symbol':info.sname.decode() if rc and info.sname else None,
            'symbol_start':info.saddr,'image_base':info.fbase,'public_function_called':False}
        out.json('API-binding.json',binding)
        assert rc and public==wanted==info.saddr and binding['symbol']=='dispatch_once' and binding['image']=='/usr/lib/system/libdispatch.dylib'
        matches=[]
        for i in range(rt.system._dyld_image_count()):
            name=rt.system._dyld_get_image_name(i)
            if name and name.decode()==binding['image']: matches.append((rt.system._dyld_get_image_header(i),rt.system._dyld_get_image_vmaddr_slide(i)))
        assert len(matches)==1; header,slide=matches[0]; assert slide==rt.slide and header==info.fbase
        rawhead=rt.read(header,32,32,'dispatch Mach-O header'); h=struct.unpack('<IiiIIIII',rawhead)
        assert h[0]==0xfeedfacf and h[1]==0x100000c and h[4]<512 and 0<h[5]<=65536
        raw=rt.read(header+32,h[5],65536,'dispatch Mach-O load commands')
        uuid=None; dylib=None; segments=[]; offset=0
        for _ in range(h[4]):
            cmd,size=struct.unpack_from('<II',raw,offset); assert size>=8 and offset+size<=len(raw)
            if cmd==0x1b: uuid=raw[offset+8:offset+24].hex()
            if cmd==0xd:
                c=struct.unpack_from('<IIIIII',raw,offset); assert 24<=c[2]<size
                name=raw[offset+c[2]:offset+size].split(b'\0',1)[0].decode(); v=c[4]
                dylib={'install_name':name,'current_version':f'{v>>16}.{(v>>8)&255}.{v&255}'}
            if cmd==0x19:
                c=struct.unpack_from('<II16sQQQQiiII',raw,offset)
                segments.append({'name':c[2].rstrip(b'\0').decode(),'address':c[3],'size':c[4],'initprot':c[8]})
            offset+=size
        assert offset==len(raw) and uuid and dylib and dylib['install_name']==binding['image']
        assert any(s['name']=='__TEXT' and s['initprot']&1 and s['initprot']&4 and s['address']+slide<=wanted<s['address']+slide+s['size'] for s in segments)
        out.write('dispatch-header.bin',rawhead); out.write('dispatch-load-commands.bin',raw)
        out.json('dispatch-image.json',{'UUID':uuid,**dylib,'segments':segments,'slide':slide,'metadata_only':True,
            'SDK_stub_version':json.loads((SOURCE/'identity.json').read_bytes())['SDK_stub_current_version'],
            'private_predicate_encoding_proved':False})
        out.json('memory-reads.json',rt.reads); verify(BDECL)
        out.json('summary.json',{'exact_public_API_identity':True,'selectors':2,'public_function_calls':0,
            'new_tensor_BLAS_calls':0,'new_executable_reads':0,'new_configuration_reads':0,'dispatch_header_reads':2,
            'private_predicate_encoding_proved':False,'old_warm_gate_pass':False,'R1_complete':False,'R2_started':False,'resources':check.check()})
        status='complete'; print(json.dumps({'exact_public_API_identity':True,'dispatch_UUID':uuid,'dispatch_version':dylib['current_version']}))
    except BaseException:
        out.json('failure.json',{'traceback':traceback.format_exc()},True); raise
    finally: out.close(status)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('phase',choices=['declare','audit','bind_declare','bind']); a=p.parse_args(); globals()[a.phase]()
