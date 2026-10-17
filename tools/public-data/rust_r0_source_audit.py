"""Bounded official backend metadata and read-only local toolchain/API audit."""
import json,os,platform,subprocess,sys,tomllib,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(ROOT/'tools'))
from metropt_multiday import Files,digest
from macos_demand_runtime import MacCheckpoint
SOURCES=[
 ('burn-Cargo.toml','https://raw.githubusercontent.com/tracel-ai/burn/v0.22.0/crates/burn/Cargo.toml',True),
 ('burn-workspace.toml','https://raw.githubusercontent.com/tracel-ai/burn/v0.22.0/Cargo.toml',True),
 ('burn-flex-Cargo.toml','https://raw.githubusercontent.com/tracel-ai/burn/v0.22.0/crates/burn-flex/Cargo.toml',True),
 ('burn-LICENSE-MIT','https://raw.githubusercontent.com/tracel-ai/burn/v0.22.0/LICENSE-MIT',True),
 ('burn-LICENSE-APACHE','https://raw.githubusercontent.com/tracel-ai/burn/v0.22.0/LICENSE-APACHE',True),
 ('burn-docs.html','https://burn.dev/docs/burn/',True),
 ('burn-autodiff.html','https://burn.dev/docs/burn/backend/autodiff/index.html',True),
 ('burn-AdamW.html','https://burn.dev/docs/burn/optim/struct.AdamWConfig.html',True),
 ('burn-optimizer-state.html','https://burn.dev/docs/burn/optim/struct.ModuleOptimizer.html',True),
 ('burn-tensor.html','https://burn.dev/docs/burn/tensor/struct.Tensor.html',True),
 ('candle-README.md','https://raw.githubusercontent.com/huggingface/candle/main/README.md',False),
 ('tch-README.md','https://raw.githubusercontent.com/LaurentMazare/tch-rs/main/README.md',False)]


def main(output):
    out=Files(output);status='failed';check=MacCheckpoint(seconds=870)
    try:
        out.json('phase.json',{'scope':'Rust R0 source/toolchain/adapter candidate audit; no crate install, build, real training or model inference',
            'official_metadata_only':'no research dataset upload/download; GET public documentation/source',
            'candidate_limit':['Burn0.22 Flex CPU','Candle0.11 CPU','tch0.26 native LibTorch'],
            'no_global_toolchain_change':True,'target_candidate':'/Users/tyaromax/Documents/ScadaProject; user confirmation pending'})
        out.sources([Path(__file__),ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py'])
        fetched=[]
        for name,url,required in SOURCES:
            command=['curl','--fail','--silent','--show-error','--location','--max-time','20','--max-filesize','2097152',url]
            p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25)
            item={'name':name,'url':url,'command':command,'required':required,'exit':p.returncode,'stderr':p.stderr.decode(errors='replace')[:4096]}
            if p.returncode==0:
                if len(p.stdout)>2097152:raise ValueError('source body cap')
                out.write(name,p.stdout);item.update(bytes=len(p.stdout),sha256=digest(out.root/name))
            fetched.append(item);check.check()
        out.json('fetch-audit.json',fetched)
        if any(x['required'] and x['exit']!=0 for x in fetched):raise ValueError('required official source unavailable; preserve failure without selecting unseen dependency')
        package=tomllib.loads((out.root/'burn-Cargo.toml').read_text());workspace=tomllib.loads((out.root/'burn-workspace.toml').read_text())
        if package['package']['rust-version']!='1.95' or workspace['workspace']['package']['version']!='0.22.0':raise ValueError('expected exact backend source version changed')
        commands=[['/usr/bin/file','/Users/tyaromax/.cargo/bin/rustup'],['/Users/tyaromax/.cargo/bin/rustc','--version'],
                  ['/Users/tyaromax/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc','--version','--verbose'],
                  ['/Users/tyaromax/.rustup/toolchains/stable-aarch64-apple-darwin/bin/cargo','--version']]
        runtime=[]
        for cmd in commands:
            try:
                p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
                runtime.append({'command':cmd,'exit':p.returncode,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')})
            except OSError as e:runtime.append({'command':cmd,'exit':None,'os_error':str(e)})
        out.json('toolchain.json',{'machine':platform.machine(),'commands':runtime,'global_changes':False,'cargo_build_performed':False,'dependencies_resolved':False})
        target=Path('/Users/tyaromax/Documents/ScadaProject');names=['AGENTS.md','Cargo.toml','crates/scada-core/Cargo.toml','crates/scada-core/src/tag.rs','docs/scada_basic_design.md','docs/handoff.md']
        local=[{'path':str(target/name),'sha256':digest(target/name),'bytes':(target/name).stat().st_size} for name in names]
        out.json('adapter-readonly-pins.json',{'candidate_confirmed':False,'files':local,'external_project_writes':False,
            'observed_tag_fields':['tag_id','value','quality','source_timestamp','server_timestamp','sequence','scan_interval_ms','stale_after_ms','driver_id','endpoint_id','read_status','write_status'],
            'observed_quality':['Good','Uncertain','Bad','Stale','CommLost','OutOfRange','Manual','Simulated'],
            'current_is_usable':['Good','Uncertain','Manual','Simulated'],'warning':'model package quality policy must be explicit; do not inherit broad usability silently',
            'architecture':'Driver -> Driver Manager -> Tag Server -> Runtime -> Client; long training job outside Tauri/UI and real-time control path'})
        out.json('summary.json',{'status':'complete','selected_for_next_R1':'Burn=0.22.0, Flex CPU, first-order autodiff','upstream_license':workspace['workspace']['package']['license'],
            'MSRV':package['package']['rust-version'],'arm_toolchain_available':any(x['command'][0].endswith('/bin/rustc') and 'aarch64' in x['command'][0] and x.get('exit')==0 for x in runtime),
            'global_rustup_wrapper_usable':False,'crate_compile_and_numerical_parity_verified':False,'dependency_license_inventory_complete':False,'banto_integration_verified':False,'resources':check.check()})
        status='complete';print(json.dumps({'status':status,'backend':'Burn=0.22.0/Flex CPU','files_fetched':sum(x['exit']==0 for x in fetched)}))
    except BaseException:
        out.json('failure.json',{'traceback':traceback.format_exc()},True);raise
    finally:out.close(status)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();main(a.output)
