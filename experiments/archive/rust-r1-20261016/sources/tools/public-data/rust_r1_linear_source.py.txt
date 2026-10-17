"""Bounded official-source and installed-build intake for the linear boundary."""
import json
import sys
import urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer')]
from metropt_multiday import Files,digest
from macos_demand_runtime import MacCheckpoint
COMMIT='08187d9e0fba026dc8217405802ab5381dc88d90'

def main():
    out=Files(ROOT/'artifacts/rust-r1-linear-source-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        registry=ROOT/'environments/rust-cpu/cargo-home/registry/src/index.crates.io-1949cf8c6b5b557f'
        include=ROOT/'environments/demand-macos/.venv/lib/python3.14/site-packages/torch/include'
        sources=[Path(__file__),ROOT/'crates/banto-ai/src/model.rs',ROOT/'Cargo.lock',registry/'burn-flex-0.22.0/src/ops/matmul.rs',registry/'burn-flex-0.22.0/src/ops/float.rs',ROOT/'models/mini-transformer/small_model.py',include/'ATen/Config.h']
        out.sources(sources);pins=[]
        for rel in ['Linear.cpp','CPUBlas.cpp','LinearAlgebra.cpp','cpu/BlasKernel.cpp']:
            url=f'https://raw.githubusercontent.com/pytorch/pytorch/{COMMIT}/aten/src/ATen/native/{rel}'
            with urllib.request.urlopen(url,timeout=25) as response:
                assert response.status==200;raw=response.read(2*1024**2+1);assert len(raw)<=2*1024**2
            name=Path(rel).name;out.write(name,raw);pins.append({'url':url,'name':name,'sha256':digest(out.root/name),'bytes':len(raw)});check.check()
        import torch
        torch.set_num_threads(1);torch.set_num_interop_threads(1);assert torch.version.git_version==COMMIT
        out.json('source-pins.json',pins);out.json('build.json',{'torch_version':torch.__version__,'git_version':torch.version.git_version,'configuration':torch.__config__.show(),'parallel_info':torch.__config__.parallel_info(),'threads':torch.get_num_threads(),'interop_threads':torch.get_num_interop_threads()})
        out.json('phase.json',{'scope':'source/build read only; no arithmetic kernels, model forward or labels','model_before_sha256':digest(ROOT/'crates/banto-ai/src/model.rs'),'commit':COMMIT});out.json('summary.json',{'sources':4,'arithmetic_kernels':0,'resources':check.check()});print(json.dumps({'source_intake':True,'sources':4}));status='complete'
    finally:out.close(status)

if __name__=='__main__':main()
