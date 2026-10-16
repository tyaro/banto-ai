"""Bounded own-process SGEMM metadata/code reads; no BLAS call or tensor math."""
import argparse
import bisect
import ctypes
import hashlib
import io
import json
import os
import platform
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
CONFIG=ROOT/'examples/configs/rust-r1-sgemm-readonly-20261016.json'
DECL=ROOT/'artifacts/rust-r1-sgemm-declaration-20261016'
SDK=Path('/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk/usr/include')

def sources():return [Path(__file__),CONFIG,ROOT/'crates/banto-ai/src/model.rs',ROOT/'Cargo.lock',ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json']

def declare():
    out=Files(DECL);status='failed';check=MacCheckpoint(seconds=870)
    try:
        roots=[ROOT/'artifacts'/n for n in ['rust-r1-fused-linear-results-20261016','rust-r1-linear-python-20261016','rust-r1-linear-source-20261016']]
        for p in roots:verify_closed(p)
        out.sources(sources());out.json('phase.json',json.loads(CONFIG.read_bytes()));out.json('source-pins.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in sources()]);out.json('root-pins.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p/'root-closed.json')} for p in roots])
        for name in ['mach_vm.h','mach_init.h']:
            p=SDK/'mach'/name;out.write(name,p.read_bytes())
        out.json('sdk-pins.json',[{'path':str(SDK/'mach'/n),'sha256':digest(SDK/'mach'/n)} for n in ['mach_vm.h','mach_init.h']]);out.json('summary.json',{'declared_before_memory_reads':True,'numerical_kernels':0,'resources':check.check()});print(json.dumps({'declared':True}));status='complete'
    finally:out.close(status)

def verify_pins():
    verify_closed(DECL)
    for p in json.loads((DECL/'source-pins.json').read_bytes()):assert digest(ROOT/p['path'])==p['sha256']
    for p in json.loads((DECL/'root-pins.json').read_bytes()):verify_closed(ROOT/p['path']);assert digest(ROOT/p['path']/'root-closed.json')==p['sha256']
    for p in json.loads((DECL/'sdk-pins.json').read_bytes()):assert digest(Path(p['path']))==p['sha256']

class Runtime:
    def __init__(self):
        os.environ['VECLIB_MAXIMUM_THREADS']='1'
        import torch
        assert torch.version.git_version=='08187d9e0fba026dc8217405802ab5381dc88d90';torch.set_num_threads(1);torch.set_num_interop_threads(1)
        self.system=ctypes.CDLL('/usr/lib/libSystem.B.dylib');self.task=ctypes.c_uint32.in_dll(self.system,'mach_task_self_').value
        self.system.mach_vm_read_overwrite.argtypes=[ctypes.c_uint32,ctypes.c_uint64,ctypes.c_uint64,ctypes.c_uint64,ctypes.POINTER(ctypes.c_uint64)];self.system.mach_vm_read_overwrite.restype=ctypes.c_int
        dylib=ROOT/'environments/demand-macos/.venv/lib/python3.14/site-packages/torch/lib/libtorch_cpu.dylib';self.cpu_hash=digest(dylib);self.cpu=ctypes.CDLL(str(dylib))
        class DlInfo(ctypes.Structure):_fields_=[('fname',ctypes.c_char_p),('fbase',ctypes.c_void_p),('sname',ctypes.c_char_p),('saddr',ctypes.c_void_p)]
        self.system.dladdr.argtypes=[ctypes.c_void_p,ctypes.POINTER(DlInfo)];self.system.dladdr.restype=ctypes.c_int
        address=ctypes.cast(getattr(self.cpu,'sgemm_'),ctypes.c_void_p).value;info=DlInfo();assert self.system.dladdr(address,ctypes.byref(info))!=0
        self.address=address;self.image=info.fname.decode();self.symbol=info.sname.decode() if info.sname else None
        assert self.image.startswith('/System/Library/Frameworks/Accelerate.framework/') and self.image.endswith('/libBLAS.dylib') and self.symbol=='SGEMM'
        self.system._dyld_image_count.restype=ctypes.c_uint32;self.system._dyld_get_image_name.argtypes=[ctypes.c_uint32];self.system._dyld_get_image_name.restype=ctypes.c_char_p;self.system._dyld_get_image_header.argtypes=[ctypes.c_uint32];self.system._dyld_get_image_header.restype=ctypes.c_void_p;self.system._dyld_get_image_vmaddr_slide.argtypes=[ctypes.c_uint32];self.system._dyld_get_image_vmaddr_slide.restype=ctypes.c_int64
        found=[]
        for i in range(self.system._dyld_image_count()):
            name=self.system._dyld_get_image_name(i)
            if name and name.decode()==self.image:found.append((self.system._dyld_get_image_header(i),self.system._dyld_get_image_vmaddr_slide(i)))
        assert len(found)==1;self.header,self.slide=found[0];self.caps=json.loads(CONFIG.read_bytes())['read_caps'];self.reads=[]
    def read(self,address,size,cap,label):
        assert 0<size<=cap and 0<address<2**64 and address+size<=2**64
        buf=ctypes.create_string_buffer(size);count=ctypes.c_uint64();rc=self.system.mach_vm_read_overwrite(self.task,address,size,ctypes.addressof(buf),ctypes.byref(count))
        self.reads.append({'label':label,'address':address,'bytes':size,'returned_bytes':count.value,'kern_return':rc})
        assert rc==0 and count.value==size,(label,rc,count.value,size)
        return buf.raw
    def metadata(self):
        header=struct.unpack('<IiiIIIII',self.read(self.header,32,32,'Mach-O header'));assert header[0]==0xfeedfacf and header[1]==0x100000c
        assert header[4]<512 and 0<header[5]<=self.caps['header_load_commands_bytes']
        raw=self.read(self.header+32,header[5],self.caps['header_load_commands_bytes'],'Mach-O load commands');offset=0;segments=[];sections=[];starts=None;uuid=None
        for _ in range(header[4]):
            cmd,size=struct.unpack_from('<II',raw,offset);assert size>=8 and offset+size<=len(raw)
            if cmd==0x1b:uuid=raw[offset+8:offset+24].hex()
            if cmd==0x26:starts=struct.unpack_from('<II',raw,offset+8)
            if cmd==0x19:
                seg=struct.unpack_from('<II16sQQQQiiII',raw,offset);segments.append({'name':seg[2].rstrip(b'\0').decode(),'address':seg[3],'size':seg[4],'fileoff':seg[5],'filesize':seg[6],'initprot':seg[8]})
                for i in range(seg[9]):
                    s=struct.unpack_from('<16s16sQQIIIIIIII',raw,offset+72+i*80);sections.append({'name':s[0].rstrip(b'\0').decode(),'segment':s[1].rstrip(b'\0').decode(),'address':s[2],'size':s[3]})
            offset+=size
        assert offset==len(raw) and uuid and starts
        text=next(s for s in sections if s['name']=='__text' and s['segment']=='__TEXT');textseg=next(s for s in segments if s['name']=='__TEXT');link=next(s for s in segments if s['name']=='__LINKEDIT')
        assert textseg['initprot']&4 and textseg['initprot']&1
        dataoff,datasize=starts;assert link['fileoff']<=dataoff and dataoff+datasize<=link['fileoff']+link['filesize']
        data=self.read(link['address']+self.slide+dataoff-link['fileoff'],datasize,self.caps['function_starts_bytes'],'LC_FUNCTION_STARTS')
        functions=[];i=0;address=textseg['address']+self.slide
        while i<len(data):
            delta=shift=0
            while True:
                assert i<len(data) and shift<64;b=data[i];i+=1;delta|=(b&127)<<shift
                if not b&128:break
                shift+=7
            if delta==0:break
            address+=delta;functions.append(address);assert len(functions)<=self.caps['function_count']
        assert functions==sorted(set(functions));assert self.address in functions
        assert text['address']+self.slide<=self.address<text['address']+self.slide+text['size']
        self.functions=functions;self.text=text
        return {'image':self.image,'file_exists':Path(self.image).is_file(),'symbol':self.symbol,'runtime_symbol_address':self.address,'header_address':self.header,'slide':self.slide,'image_UUID':uuid,'cpu_subtype':header[2],'text':text,'segments':segments,'function_starts_count':len(functions),'function_starts_sha256':hashlib.sha256(data).hexdigest(),'function_starts':functions,'libtorch_cpu_sha256':self.cpu_hash,'platform':{'mac_ver':platform.mac_ver(),'uname':list(platform.uname())},'numerical_kernels':0}
    def region(self,address):
        assert address in self.functions
        i=bisect.bisect_right(self.functions,address);end=self.functions[i] if i<len(self.functions) else self.text['address']+self.slide+self.text['size']
        assert self.text['address']+self.slide<=address<end<=self.text['address']+self.slide+self.text['size']
        stop=min(end,address+self.caps['region_bytes']);data=self.read(address,stop-address,self.caps['region_bytes'],'executable region')
        return {'runtime_address':address,'image_virtual_address':address-self.slide,'function_end_virtual':end-self.slide,'bytes':len(data),'truncated':stop<end,'sha256':hashlib.sha256(data).hexdigest()},data

def elf(address,code):
    # Read-only disassembly container, never an executable used by this study.
    names=b'\0.text\0.shstrtab\0';codeoff=64;namesoff=codeoff+len(code);shoff=(namesoff+len(names)+7)&~7
    ident=b'\x7fELF'+bytes([2,1,1,0])+bytes(8)
    header=struct.pack('<16sHHIQQQIHHHHHH',ident,1,183,1,0,0,shoff,0,64,0,0,64,3,2)
    sections=bytes(64)+struct.pack('<IIQQQQIIQQ',1,1,6,address,codeoff,len(code),0,0,4,0)+struct.pack('<IIQQQQIIQQ',7,3,0,0,namesoff,len(names),0,0,1,0)
    return header+code+names+bytes(shoff-namesoff-len(names))+sections

def entry():
    out=Files(ROOT/'artifacts/rust-r1-sgemm-entry-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        verify_pins();out.sources(sources());out.json('phase.json',{'contract_sha256':digest(CONFIG),'scope':'SGEMM entry only; no callee or numerical execution'})
        runtime=Runtime();meta=runtime.metadata();out.json('image-metadata.json',meta);region,code=runtime.region(runtime.address);out.json('region.json',region);out.write('code.bin',code)
        container=elf(region['image_virtual_address'],code);out.write('region.elf',container)
        find=subprocess.run(['/usr/bin/xcrun','--find','llvm-objdump'],capture_output=True,timeout=20);assert find.returncode==0
        tool=Path(find.stdout.decode().strip());version=subprocess.run([str(tool),'--version'],capture_output=True,timeout=20);assert version.returncode==0
        cmd=[str(tool),'--arch-name=aarch64','--disassemble-all','--no-show-raw-insn',str(out.root/'region.elf')];result=subprocess.run(cmd,capture_output=True,timeout=45)
        out.write('disassembly.stdout',result.stdout);out.write('disassembly.stderr',result.stderr);assert len(result.stdout)<=1024**2 and len(result.stderr)<=128*1024 and result.returncode==0
        out.json('tool.json',{'path':str(tool),'sha256':digest(tool),'version':version.stdout.decode()});out.json('commands.json',{'discovery':{'argv':find.args,'exit':find.returncode,'stdout':find.stdout.decode(),'stderr':find.stderr.decode()},'version_exit':version.returncode,'disassembly':{'argv':cmd,'exit':result.returncode}})
        again=runtime.read(runtime.address,len(code),runtime.caps['region_bytes'],'executable region recheck');assert again==code
        out.json('memory-reads.json',runtime.reads);verify_pins();out.json('summary.json',{'entry_regions':1,'region_bytes':len(code),'truncated':region['truncated'],'loaded_region_unchanged':True,'shared_cache_image_UUID':meta['image_UUID'],'numerical_kernels':0,'full_forward':0,'training':False,'R1_complete':False,'resources':check.check()});print(json.dumps({'entry_read':True,'region_bytes':len(code),'truncated':region['truncated'],'image_UUID':meta['image_UUID']}));status='complete'
    finally:out.close(status)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['declare','entry']);a=p.parse_args();globals()[a.phase]()
