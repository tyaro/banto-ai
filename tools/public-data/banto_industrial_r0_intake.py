"""Read-only, pinned banto-industrial source intake for Rust adapter design."""
import io,json,hashlib,subprocess,sys,traceback,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(ROOT/'tools'))
from metropt_multiday import Files
from macos_demand_runtime import MacCheckpoint
COMMIT='93d99efa06e8eda8c623567c5d117409fb2a3c8b'
PATHS=['AGENTS.md','CLAUDE.md','docs/README.md','docs/implementation-checklist.md','Cargo.toml','rust-toolchain.toml','LICENSE','README.md','crates/banto-tagclient/src/types.rs','crates/banto-tagclient/src/lib.rs','crates/banto-tags/src/tag.rs','crates/banto-tsquery/src/types.rs','crates/banto-tstore/src/schema.rs','docs/banto-tagclient-design.md','docs/tag-server-design.md','apps/chronogazer/core/src/collect/history.rs','apps/banto-hub/core/Cargo.toml','apps/chronogazer/core/Cargo.toml','proto/tagserver/v1/tagserver.proto']
def main(output):
    out=Files(output);status='failed';check=MacCheckpoint(seconds=870)
    try:
        out.json('phase-before-read.json',{'target':'tyaro/banto-industrial','user_confirmed_name':'banto-industrial','commit':COMMIT,'read_only':True,'ScadaProject_excluded':True,'no_external_repository_edit_or_clone':True,'no_training_build_or_forward':True})
        out.sources([Path(__file__),ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py'])
        tree=json.loads((ROOT/'examples/configs/banto-industrial-tree-20261016.json').read_bytes())
        blobs={x['path']:x['sha'] for x in tree['tree'] if x['type']=='blob'}
        bundle=io.BytesIO();pins=[]
        with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
            for path in PATHS:
                url=f'https://raw.githubusercontent.com/tyaro/banto-industrial/{COMMIT}/{path}'
                cmd=['curl','--fail','--silent','--show-error','--location','--max-time','20','--max-filesize','2097152',url]
                p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25)
                item={'path':path,'url':url,'command':cmd,'exit':p.returncode,'stderr':p.stderr.decode(errors='replace')[:4096]}
                if p.returncode:out.json('partial-fetch.json',pins+[item]);raise ValueError('required source GET failed')
                raw=p.stdout;gitsha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
                if gitsha!=blobs[path]:raise ValueError('git blob mismatch '+path)
                item.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),git_blob_sha=gitsha)
                z.writestr(path,raw);pins.append(item);check.check()
        out.write('banto-industrial-source.zip',bundle.getvalue())
        out.json('source-pins.json',pins);out.json('tree.json',tree)
        out.json('summary.json',{'status':'complete','repository':'tyaro/banto-industrial','commit':COMMIT,'all_blobs_verified':True,'files':len(pins),'read_only':True,'external_edits':False,'ScadaProject_excluded':True,'resources':check.check()})
        print(json.dumps({'status':'complete','commit':COMMIT,'source_files':len(pins)}));status='complete'
    except BaseException:
        out.json('failure.json',{'traceback':traceback.format_exc()},True);raise
    finally:out.close(status)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();main(a.output)
