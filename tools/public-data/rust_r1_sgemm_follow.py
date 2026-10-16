"""One preregistered direct-call target from previously closed SGEMM bytes."""
import argparse
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_sgemm_readonly import Runtime,elf,verify_pins,CONFIG as ORIGINAL

def sources(config):return [Path(__file__),config,ROOT/'tools/public-data/rust_r1_sgemm_readonly.py',ORIGINAL,ROOT/'crates/banto-ai/src/model.rs',ROOT/'Cargo.lock',ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json']

def selected(config):
    c=json.loads(config.read_bytes());source=ROOT/c['source_root'];verify_closed(source)
    region=json.loads((source/'region.json').read_bytes());raw=(source/'code.bin').read_bytes();assert hashlib.sha256(raw).hexdigest()==region['sha256']
    pc=int(c['source_instruction_virtual'],16);offset=pc-region['image_virtual_address'];assert offset>=0 and offset%4==0 and offset+4<=len(raw)
    word=struct.unpack_from('<I',raw,offset)[0]
    kind='BL' if word>>26==0b100101 else 'B' if word>>26==0b000101 else None
    assert kind==c['instruction_kind']
    imm=word&0x3ffffff;imm=imm-(1<<26) if imm&(1<<25) else imm
    target=pc+4*imm;assert target==int(c['target_virtual'],16)
    return c,{'source':c['source_root'],'instruction_virtual':pc,'instruction_word':hex(word),'kind':kind,'target_virtual':target,'source_sha256':region['sha256']}

def main(phase,config):
    c,selection=selected(config);declaration=ROOT/c['declaration_root'];out=Files(declaration if phase=='declare' else ROOT/c['output_root']);status='failed';check=MacCheckpoint(seconds=870)
    try:
        verify_pins();out.sources(sources(config));out.json('phase.json',c);out.json('selection.json',selection)
        if phase=='declare':
            pins=[]
            for rel in c['prior_region_roots']:
                p=ROOT/rel;verify_closed(p);pins.append({'path':rel,'sha256':digest(p/'root-closed.json')})
            out.json('root-pins.json',pins);out.json('source-pins.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in sources(config)]);out.json('summary.json',{'declared_before_target_read':True,'numerical_kernels':0,'resources':check.check()});print(json.dumps({'declared':True,'target_virtual':c['target_virtual']}));status='complete';return
        verify_closed(declaration)
        for p in json.loads((declaration/'source-pins.json').read_bytes()):assert digest(ROOT/p['path'])==p['sha256']
        priors=[]
        for p in json.loads((declaration/'root-pins.json').read_bytes()):verify_closed(ROOT/p['path']);assert digest(ROOT/p['path']/'root-closed.json')==p['sha256'];priors.append(json.loads((ROOT/p['path']/'region.json').read_bytes()))
        rt=Runtime();meta=rt.metadata();assert meta['image_UUID']==c['expected_image_UUID'];out.json('image-metadata.json',meta)
        old=json.loads((ROOT/c['source_root']/'region.json').read_bytes());assert rt.read(old['image_virtual_address']+rt.slide,old['bytes'],rt.caps['region_bytes'],'source function recheck')==(ROOT/c['source_root']/'code.bin').read_bytes()
        region,code=rt.region(selection['target_virtual']+rt.slide)
        unique={p['image_virtual_address']:p['bytes'] for p in priors};assert region['image_virtual_address'] not in unique;unique[region['image_virtual_address']]=len(code)
        assert len(unique)<=rt.caps['region_count_total'] and sum(unique.values())<=rt.caps['region_bytes_total']
        out.json('region.json',region);out.write('code.bin',code);out.write('region.elf',elf(region['image_virtual_address'],code))
        toolmeta=json.loads((ROOT/'artifacts/rust-r1-sgemm-entry-20261016/tool.json').read_bytes());tool=Path(toolmeta['path']);assert digest(tool)==toolmeta['sha256']
        cmd=[str(tool),'--arch-name=aarch64','--disassemble-all','--section=.text','--no-show-raw-insn',str(out.root/'region.elf')];result=subprocess.run(cmd,capture_output=True,timeout=45)
        out.write('disassembly.stdout',result.stdout);out.write('disassembly.stderr',result.stderr);assert result.returncode==0 and len(result.stdout)<=1024**2 and len(result.stderr)<=128*1024
        out.json('commands.json',{'argv':cmd,'exit':result.returncode,'tool_sha256':digest(tool)});assert rt.read(region['runtime_address'],len(code),rt.caps['region_bytes'],'target function recheck')==code
        out.json('memory-reads.json',rt.reads);verify_pins();out.json('summary.json',{'selected_regions_this_phase':1,'total_unique_regions':len(unique),'total_unique_region_bytes':sum(unique.values()),'target_truncated':region['truncated'],'bytes_unchanged':True,'numerical_kernels':0,'full_forward':0,'training':False,'R1_complete':False,'resources':check.check()});print(json.dumps({'read':True,'target_virtual':c['target_virtual'],'bytes':len(code),'truncated':region['truncated'],'total_regions':len(unique)}));status='complete'
    finally:out.close(status)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['declare','inspect']);p.add_argument('--config',required=True);a=p.parse_args();main(a.phase,ROOT/a.config)
