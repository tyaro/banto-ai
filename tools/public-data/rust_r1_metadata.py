"""Inspect resolved active Rust dependencies without starting a compiler."""
import io,json,re,subprocess,sys,tomllib,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'models/mini-transformer'),str(ROOT/'tools')]
from metropt_multiday import Files,digest
from macos_demand_runtime import MacCheckpoint
def main(output,metadata_input=None):
    out=Files(output);status='failed';check=MacCheckpoint(seconds=870)
    try:
        out.json('phase.json',{'scope':'offline dependency metadata, effective features and active license inventory only','compile':False,'upstream_lock_seed':'artifacts/rust-r1-lock-seed-20261016','unused_legacy_yanked_branch_must_not_be_active':True})
        out.sources([Path(__file__),ROOT/'Cargo.toml',ROOT/'crates/banto-ai/Cargo.toml',ROOT/'Cargo.lock',ROOT/'tools/public-data/macos_rust_run.py'])
        cmd=['/Users/tyaromax/.rustup/toolchains/stable-aarch64-apple-darwin/bin/cargo','metadata','--offline','--locked','--format-version','1','--filter-platform','aarch64-apple-darwin']
        if metadata_input:
            source=Path(metadata_input);closure=json.loads((source.parent/'root-closed.json').read_bytes())
            pin=next(x for x in closure['files'] if x['name']==source.name)
            assert digest(source)==pin['sha256'] and json.loads((source.parent/'command-exit.json').read_bytes())['exit']==0
            assert digest(ROOT/'Cargo.lock')==digest(ROOT/'artifacts/rust-r1-metadata-20261016-records/Cargo.lock')
            out.write('metadata.json',source.read_bytes());out.json('command-exit.json',{'reused_successful_metadata':str(source),'source_closure_sha256':digest(source.parent/'root-closed.json'),'reason':'license archive timestamp correction only; no repeated dependency query','exit':0})
        else:
            with (out.root/'metadata.json').open('xb') as stream:
                p=subprocess.run(cmd,cwd=ROOT,stdout=stream,stderr=subprocess.PIPE,timeout=120)
            out.write('metadata-stderr.txt',p.stderr);out.json('command-exit.json',{'command':cmd,'exit':p.returncode})
            if p.returncode:raise RuntimeError('metadata failed')
        assert (out.root/'metadata.json').stat().st_size<=32*1024**2
        m=json.loads((out.root/'metadata.json').read_bytes());packages={p['id']:p for p in m['packages']};nodes={p['id']:p for p in m['resolve']['nodes']}
        tree_root=ROOT/'artifacts/rust-r1-effective-features-20261016';tree=(tree_root/'stdout.txt').read_text()
        assert json.loads((tree_root/'exit.json').read_bytes())['returncode']==0
        feature_map={}
        for line in tree.splitlines():
            desc,features=line.split('|',1);match=re.match(r'^(\S+) v(\S+)',desc);assert match,line
            pair=match.groups();values=features.removesuffix(' (*)').strip()
            feature_map[pair]=sorted(v for v in values.split(',') if v)
        active=set()
        for pair in feature_map:
            matches=[key for key,p in packages.items() if (p['name'],p['version'])==pair]
            assert len(matches)==1,pair
            active.add(matches[0])
        out.json('active-tree-pin.json',{'path':str(tree_root),'stdout_sha256':digest(tree_root/'stdout.txt'),'closure_sha256':digest(tree_root/'root-closed.json'),'reason':'cargo metadata resolve includes inactive optional branches; use cargo tree normal/build as effective graph'})
        inventory=[];licenses=io.BytesIO();seen=set()
        with zipfile.ZipFile(licenses,'w',zipfile.ZIP_DEFLATED) as z:
            for key in sorted(active):
                p=packages[key];folder=Path(p['manifest_path']).parent
                item={'name':p['name'],'version':p['version'],'license':p.get('license'),'license_file':p.get('license_file'),'source':p['source'],'features':feature_map[(p['name'],p['version'])]}
                candidates=[f for f in folder.iterdir() if f.is_file() and f.name.lower().startswith(('license','copying','copyright'))]
                if p.get('license_file'):candidates.append(folder/p['license_file'])
                item['license_documents']=[]
                for path in sorted(set(candidates)):
                    if path.exists() and path.is_file() and not path.is_symlink():
                        arc=p['name']+'-'+p['version']+'/'+path.name
                        if arc not in seen:
                            z.writestr(arc,path.read_bytes());seen.add(arc)
                        item['license_documents'].append({'path':path.name,'sha256':digest(path)})
                assert p.get('license') or item['license_documents'],p['name']
                inventory.append(item);check.check()
        names={p['name'] for p in inventory}
        assert 'burn-flex' in names and not names.intersection({'burn-tch','tch','torch-sys','burn-cubecl','burn-remote','burn-ndarray'})
        assert not names.intersection({'rayon','macerator'}),'CPU first parity must be single-thread non-SIMD feature path'
        out.json('active-dependencies.json',inventory);out.write('active-license-documents.zip',licenses.getvalue())
        out.write('Cargo.lock',(ROOT/'Cargo.lock').read_bytes())
        lock=tomllib.loads((ROOT/'Cargo.lock').read_text())
        legacy=[{'name':p['name'],'version':p['version'],'active':p['name'] in names} for p in lock['package'] if p['name'] in ['zip','tch','burn-tch','torch-sys']]
        out.json('summary.json',{'status':'complete','active_dependencies':len(active),'flex_cpu_only':True,'single_thread_features':True,'legacy_locked_packages':legacy,'active_license_inventory_complete':True,'downstream_without_lock_resolution_verified':False,'cargo_lock_sha256':digest(ROOT/'Cargo.lock'),'resources':check.check()})
        print(json.dumps({'active_dependencies':len(active),'flex_cpu_only':True,'legacy_branch_active':False}));status='complete'
    finally:out.close(status)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--metadata-input');a=p.parse_args();main(a.output,a.metadata_input)
