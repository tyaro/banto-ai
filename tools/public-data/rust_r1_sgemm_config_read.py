"""One source-addressed 64-byte data read, no initialization or math call."""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_sgemm_readonly import Runtime,verify_pins,CONFIG as ORIGINAL
CONFIG=ROOT/'examples/configs/rust-r1-sgemm-config-read-20261016.json'
DECL=ROOT/'artifacts/rust-r1-sgemm-config-declaration-20261016'

def sources():return [Path(__file__),CONFIG,ORIGINAL,ROOT/'tools/public-data/rust_r1_sgemm_readonly.py',ROOT/'crates/banto-ai/src/model.rs',ROOT/'Cargo.lock']
def main(phase):
    out=Files(DECL if phase=='declare' else ROOT/'artifacts/rust-r1-sgemm-config-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        verify_pins();c=json.loads(CONFIG.read_bytes());source=ROOT/c['source_root'];verify_closed(source);out.sources(sources());out.json('phase.json',c)
        if phase=='declare':
            out.json('source-pins.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in sources()]);out.json('source-root-pin.json',{'path':c['source_root'],'sha256':digest(source/'root-closed.json')});out.json('summary.json',{'declared_before_data_read':True,'resources':check.check()});print(json.dumps({'declared':True}));status='complete';return
        verify_closed(DECL)
        for p in json.loads((DECL/'source-pins.json').read_bytes()):assert digest(ROOT/p['path'])==p['sha256']
        pin=json.loads((DECL/'source-root-pin.json').read_bytes());assert digest(source/'root-closed.json')==pin['sha256']
        rt=Runtime();meta=rt.metadata();assert meta['image_UUID']==c['image_UUID'];base=int(c['virtual_address'],16);size=c['bytes'];assert size==64
        segments=[s for s in meta['segments'] if s['initprot']&1 and not s['initprot']&4 and s['address']<=base and base+size<=s['address']+s['size']];assert len(segments)==1
        raw=rt.read(base+rt.slide,size,64,'source-addressed configuration data');out.write('configuration.bin',raw);out.json('data-binding.json',{'image_UUID':meta['image_UUID'],'segment':segments[0],'virtual_address':base,'runtime_address':base+rt.slide,'sha256':hashlib.sha256(raw).hexdigest(),'w14_at_950':struct.unpack_from('<i',raw,0)[0],'w8_at_958':struct.unpack_from('<i',raw,8)[0],'w8_at_980':struct.unpack_from('<i',raw,48)[0],'x1_at_968':hex(struct.unpack_from('<Q',raw,24)[0]),'once_at_988':struct.unpack_from('<q',raw,56)[0],'numeric_hot_path_proved':False})
        assert rt.read(base+rt.slide,size,64,'configuration data recheck')==raw
        out.json('memory-reads.json',rt.reads);summary={'configuration_bytes':64,'unchanged':True,'once_initialized':struct.unpack_from('<q',raw,56)[0]==-1,'initialization_invoked':False,'numerical_kernels':0,'full_forward':0,'training':False,'resources':check.check()};out.json('summary.json',summary);print(json.dumps(summary));verify_pins();status='complete'
    finally:out.close(status)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['declare','inspect']);a=p.parse_args();main(a.phase)
