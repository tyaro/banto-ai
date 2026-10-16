"""Bounded read-only Mach-O attribution; scientific arithmetic is not executed."""
import argparse
import bisect
import ctypes
import hashlib
import json
import mmap
import re
import struct
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_moments_audit import TORCH_INCLUDE
CONFIG=ROOT/'examples/configs/rust-r1-binary-audit-20261016-r2.json'
DECLARATION=ROOT/'artifacts/rust-r1-binary-declaration2-20261016'


def paths():
    return [Path(__file__),ROOT/'tools/public-data/rust_r1_binary_audit.py',CONFIG,ROOT/'crates/banto-ai/src/model.rs',ROOT/'Cargo.lock',
            TORCH_INCLUDE/'ATen/native/cpu/moments_utils.h',
            TORCH_INCLUDE/'ATen/cpu/vec/vec128/vec128_float_neon.h',
            ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json']


def declare():
    out=Files(DECLARATION);status='failed';check=MacCheckpoint(seconds=870)
    try:
        c=json.loads(CONFIG.read_bytes());p=ROOT/c['binary']
        assert p.is_file() and not p.is_symlink()
        previous=ROOT/'artifacts/rust-r1-moments-audit-20261016';verify_closed(previous)
        out.sources(paths());out.json('phase.json',c)
        out.json('source-pins.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in paths()])
        out.json('binary-pin.json',{'path':c['binary'],'bytes':p.stat().st_size,'sha256':digest(p)})
        out.json('prior-pin.json',{'path':str(previous.relative_to(ROOT)),'closure_sha256':digest(previous/'root-closed.json')})
        out.json('summary.json',{'declared_before_disassembly':True,'model_forward':0,'resources':check.check()})
        print(json.dumps({'declared':True,'binary_bytes':p.stat().st_size}));status='complete'
    finally:out.close(status)


def macho(path,cap):
    with path.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as raw:
        header=struct.unpack_from('<IiiIIIII',raw)
        assert header[0]==0xfeedfacf and header[1]==0x100000c,'expected thin arm64 Mach-O'
        offset=32;sections=[];segments=[];symtab=None;function_starts=None;uuid=None
        for _ in range(header[4]):
            cmd,size=struct.unpack_from('<II',raw,offset);assert size>=8
            if cmd==2:symtab=struct.unpack_from('<IIII',raw,offset+8)
            if cmd==0x1b:uuid=bytes(raw[offset+8:offset+24]).hex()
            if cmd==0x26:function_starts=struct.unpack_from('<II',raw,offset+8)
            if cmd==0x19:
                seg=struct.unpack_from('<II16sQQQQiiII',raw,offset)
                segments.append({'name':seg[2].rstrip(b'\0').decode(),'addr':seg[3],'size':seg[4],'fileoff':seg[5],'filesize':seg[6]})
                for i in range(seg[9]):
                    s=struct.unpack_from('<16s16sQQIIIIIIII',raw,offset+72+i*80)
                    sections.append({'name':s[0].rstrip(b'\0').decode(),'segment':s[1].rstrip(b'\0').decode(),
                                     'addr':s[2],'size':s[3],'fileoff':s[4],'index':len(sections)+1})
            offset+=size
        assert symtab and function_starts and uuid
        text=next(s for s in sections if s['name']=='__text' and s['segment']=='__TEXT')
        base=next(s['addr'] for s in segments if s['name']=='__TEXT')
        starts=[];offset,length=function_starts;end=offset+length;addr=base
        while offset<end:
            delta=shift=0
            while True:
                b=raw[offset];offset+=1;delta|=(b&127)<<shift
                if not b&128:break
                shift+=7;assert shift<64
            if not delta:break
            addr+=delta;starts.append(addr)
        symoff,nsyms,stroff,strsize=symtab;matches=[]
        for i in range(nsyms):
            si,kind,sect,desc,addr=struct.unpack_from('<IBBHQ',raw,symoff+i*16)
            if sect!=text['index'] or kind&0xe!=0xe or kind&0xe0:continue
            assert si<strsize
            stop=raw.find(b'\0',stroff+si,stroff+strsize);assert stop>=0
            name=raw[stroff+si:stop].decode('utf-8','replace')
            if 'LayerNormKernelImplInternalIf' in name or 'RowwiseMomentsImplIf' in name:
                matches.append({'symbol':name,'address':addr})
        # Source width 64 / four NEON lanes gives one chunk and depth <= 4.
        # Other template depths and cold error paths are not on this branch.
        selected=[r for r in matches if '.cold.' not in r['symbol'] and
                  ('LayerNormKernelImplInternalIf' in r['symbol'] or 'RowwiseMomentsImplIfLx4E' in r['symbol'])]
        regions=[]
        for addr in sorted({r['address'] for r in selected}):
            assert addr in starts,'symbol is not a function start'
            i=bisect.bisect_right(starts,addr);stop=starts[i] if i<len(starts) else text['addr']+text['size']
            limit=min(stop,addr+cap);fileoff=text['fileoff']+addr-text['addr'];code=bytes(raw[fileoff:fileoff+limit-addr])
            regions.append({'address':addr,'end':limit,'function_end':stop,'truncated':limit<stop,
                            'symbols':[r['symbol'] for r in matches if r['address']==addr],
                            'bytes':len(code),'sha256':hashlib.sha256(code).hexdigest(),'code_hex':code.hex()})
        assert 0<len(regions)<=6,('ambiguous or missing float LayerNorm regions',len(regions))
        return {'uuid':uuid,'text':text,'symbol_count':nsyms,'function_count':len(starts),'matched_symbols':matches,'selected_symbols':selected,'regions':regions}


def inspect():
    out=Files(ROOT/'artifacts/rust-r1-binary-audit2-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        verify_closed(DECLARATION)
        pins=json.loads((DECLARATION/'source-pins.json').read_bytes())
        for p in pins:assert digest(ROOT/p['path'])==p['sha256']
        binary=json.loads((DECLARATION/'binary-pin.json').read_bytes());path=ROOT/binary['path']
        assert path.stat().st_size==binary['bytes'] and digest(path)==binary['sha256']
        out.sources(paths());out.json('phase.json',{'declaration_sha256':digest(DECLARATION/'root-closed.json'),'scope':'binary/source only; no arithmetic kernels'})
        meta=macho(path,json.loads(CONFIG.read_bytes())['region_limit_bytes'])
        out.json('mach-o.json',meta)
        tool=subprocess.run(['/usr/bin/xcrun','--find','llvm-objdump'],capture_output=True,timeout=20)
        assert tool.returncode==0,tool.stderr.decode();executable=tool.stdout.decode().strip()
        version=subprocess.run([executable,'--version'],capture_output=True,timeout=20)
        assert version.returncode==0
        out.json('tool.json',{'executable':executable,'sha256':digest(Path(executable)),'version':version.stdout.decode(),'discovery_exit':tool.returncode,'version_exit':version.returncode})
        commands=[];signals=[]
        for i,region in enumerate(meta['regions']):
            cmd=[executable,'--disassemble','--no-show-raw-insn',f"--start-address={region['address']}",f"--stop-address={region['end']}",str(path)]
            result=subprocess.run(cmd,capture_output=True,timeout=45)
            assert len(result.stdout)<=1024**2 and len(result.stderr)<=128*1024,'tool stdio cap'
            out.write(f'region-{i}.stdout',result.stdout);out.write(f'region-{i}.stderr',result.stderr)
            commands.append({'argv':cmd,'exit':result.returncode});assert result.returncode==0
            lines=result.stdout.decode().splitlines()
            signals.append({'region':i,'start':region['address'],'FMA_lines':[line for line in lines if re.search(r'\b(fmadd|fmsub|fnmadd|fnmsub|fmla|fmls)\b',line)],'lines':len(lines)})
            check.check()
        out.json('commands.json',commands);out.json('fma-inventory.json',signals)
        import torch
        lib=ctypes.CDLL('/usr/lib/libSystem.B.dylib');lib._dyld_image_count.restype=ctypes.c_uint32
        lib._dyld_get_image_name.argtypes=[ctypes.c_uint32];lib._dyld_get_image_name.restype=ctypes.c_char_p
        loaded=[]
        for i in range(lib._dyld_image_count()):
            name=lib._dyld_get_image_name(i)
            if name and Path(name.decode()).name=='libtorch_cpu.dylib':loaded.append(str(Path(name.decode()).resolve()))
        assert loaded==[str(path.resolve())],loaded
        assert digest(path)==binary['sha256']
        for p in pins:assert digest(ROOT/p['path'])==p['sha256']
        out.json('runtime-binding.json',{'torch_version':torch.__version__,'torch_git_version':torch.version.git_version,'loaded_cpu_dylib':loaded,'binary_pin':binary})
        out.json('summary.json',{'regions':len(meta['regions']),'truncated_regions':sum(r['truncated'] for r in meta['regions']),
                                'FMA_instruction_lines':sum(len(r['FMA_lines']) for r in signals),
                                'loaded_binary_exact':True,'numeric_reconstructions':0,'full_forward':0,'training':False,
                                'core_changed':False,'R1_complete':False,'resources':check.check()})
        print(json.dumps({'regions':len(meta['regions']),'FMA_instruction_lines':sum(len(r['FMA_lines']) for r in signals),'loaded_binary_exact':True}));status='complete'
    finally:out.close(status)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['declare','inspect']);a=p.parse_args()
    declare() if a.phase=='declare' else inspect()
