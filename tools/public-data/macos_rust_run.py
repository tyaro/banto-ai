"""Run one bounded Rust command with process-group memory and immutable logs."""
import argparse,ctypes,json,os,resource,selectors,signal,subprocess,sys,time,traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'models/mini-transformer'),str(ROOT/'tools')]
from metropt_multiday import Files,digest
from macos_demand_runtime import _UsageV0,memory_observation
CAP=2*1024**3
LIB=ctypes.CDLL('/usr/lib/libproc.dylib',use_errno=True)
LIB.proc_listpgrppids.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_int]
LIB.proc_listpgrppids.restype=ctypes.c_int
LIB.proc_pid_rusage.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_void_p]
LIB.proc_pid_rusage.restype=ctypes.c_int
def group_memory(pgid):
    buf=(ctypes.c_int*16384)()
    n=LIB.proc_listpgrppids(pgid,buf,ctypes.sizeof(buf))
    if n<0:raise OSError('proc_listpgrppids failed')
    pids=sorted({pid for pid in buf if pid>0})
    if len(pids)>=16384:raise RuntimeError('pid group capacity')
    total={'footprint':0,'rss':0};rows=[]
    for pid in pids:
        u=_UsageV0()
        if LIB.proc_pid_rusage(pid,0,ctypes.byref(u))==0:
            total['footprint']+=int(u.phys_footprint);total['rss']+=int(u.resident_size)
            rows.append({'pid':pid,'start_abstime':int(u.proc_start_abstime),'footprint':int(u.phys_footprint),'rss':int(u.resident_size)})
    return total,rows
def source_files():
    paths=[Path(__file__),ROOT/'tools/macos_demand_runtime.py',ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'Cargo.toml',ROOT/'rust-toolchain.toml',ROOT/'crates/banto-ai/Cargo.toml',ROOT/'.cargo/config.toml']
    paths.extend(p for p in (ROOT/'crates/banto-ai').rglob('*') if p.is_file() and p.suffix in ['.rs','.md'])
    if (ROOT/'Cargo.lock').exists():paths.append(ROOT/'Cargo.lock')
    return paths
def disk_bytes():
    total=0
    for folder in [ROOT/'environments/rust-cpu/cargo-home',ROOT/'target']:
        if not folder.exists():continue
        for base,dirs,names in os.walk(folder):
            for name in names:
                p=Path(base)/name
                try:
                    if p.is_file() and not p.is_symlink():total+=p.stat().st_size
                except FileNotFoundError:pass # temporary compiler/cache file disappeared
    return total
def main(records,cmd,build_budget=None):
    out=Files(ROOT/records);status='failed';proc=None;started=time.monotonic();rc=None;failure=None
    streams={'stdout':bytearray(),'stderr':bytearray()};limits={'stdout':1024**2,'stderr':128*1024}
    peak={'footprint':0,'rss':0,'processes':0,'monitor_inclusive_footprint':0,'monitor_inclusive_rss':0};observed={};samples=0;largest_interval=0.;last=started;disk=0
    env=os.environ.copy();native='/Users/tyaromax/.rustup/toolchains/stable-aarch64-apple-darwin/bin'
    selected={'CARGO_HOME':str(ROOT/'environments/rust-cpu/cargo-home'),'CARGO_TARGET_DIR':str(ROOT/'target'),'RUSTC':native+'/rustc','RUSTDOC':native+'/rustdoc','CARGO_BUILD_JOBS':'1','CARGO_NET_RETRY':'0','CARGO_HTTP_TIMEOUT':'20','CARGO_INCREMENTAL':'0','RAYON_NUM_THREADS':'1'}
    env.update(selected);env['PATH']=native+os.pathsep+env.get('PATH','')
    scanner=ThreadPoolExecutor(max_workers=1);disk_future=scanner.submit(disk_bytes)
    try:
        disk_cap=768*1024**2;budget_pin=None;extra_sources=[]
        if build_budget is not None:
            budget_path=(ROOT/build_budget).resolve()
            if not budget_path.is_relative_to(ROOT):raise ValueError('budget must be repository-local')
            budget=json.loads(budget_path.read_bytes())
            if (budget['schema']!='banto.rust-r1-build-budget.v1' or budget['cache_disk_cap_bytes']!=1536*1024**2
                or budget['memory_cap_bytes']!=CAP or budget['child_seconds']!=870 or budget['parent_seconds']!=900
                or not budget['artifact_and_evidence_limits_unchanged']):raise ValueError('invalid R1 build budget')
            disk_cap=budget['cache_disk_cap_bytes'];budget_pin={'path':str(budget_path.relative_to(ROOT)),'sha256':digest(budget_path)};extra_sources=[budget_path]
        out.json('phase.json',{'parent_seconds':900,'child_seconds':870,'memory_cap_bytes':CAP,'sample_interval_requested':.02,'process_group_includes_compiler_linker':True,'hard_os_cap':False,'cache_disk_cap_bytes':disk_cap,'build_budget':budget_pin,'no_license_acceptance':True})
        out.json('command.json',{'argv':cmd,'cwd':str(ROOT),'environment_overrides':selected})
        out.sources(source_files()+extra_sources)
        proc=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        sel=selectors.DefaultSelector()
        for key,pipe in [('stdout',proc.stdout),('stderr',proc.stderr)]:
            os.set_blocking(pipe.fileno(),False);sel.register(pipe,selectors.EVENT_READ,key)
        next_disk=0.
        while sel.get_map() or proc.poll() is None:
            now=time.monotonic();elapsed=now-started
            if elapsed>870:raise TimeoutError('child/group 870s cap')
            largest_interval=max(largest_interval,now-last);last=now
            current,rows=group_memory(proc.pid);own=memory_observation();samples+=1
            for x in rows:observed[str((x['pid'],x['start_abstime']))]=x
            peak['footprint']=max(peak['footprint'],current['footprint']);peak['rss']=max(peak['rss'],current['rss']);peak['processes']=max(peak['processes'],len(rows))
            peak['monitor_inclusive_footprint']=max(peak['monitor_inclusive_footprint'],current['footprint']+own['phys_footprint_bytes'])
            peak['monitor_inclusive_rss']=max(peak['monitor_inclusive_rss'],current['rss']+own['resident_bytes'])
            if max(peak['monitor_inclusive_footprint'],peak['monitor_inclusive_rss'],own['peak_rss_bytes'])>CAP:raise MemoryError('sampled group + supervisor 2GiB cap')
            if disk_future.done() and elapsed>=next_disk:
                disk=max(disk,disk_future.result());next_disk=elapsed+1.
                if disk>disk_cap:raise RuntimeError('build/dependency cache disk cap')
                disk_future=scanner.submit(disk_bytes)
            for key,_ in sel.select(.02):
                data=os.read(key.fileobj.fileno(),65536)
                if not data:sel.unregister(key.fileobj);key.fileobj.close();continue
                label=key.data;remaining=limits[label]-len(streams[label]);streams[label].extend(data[:remaining])
                if len(data)>remaining:raise RuntimeError(label+' byte cap; preserved prefix')
        rc=proc.wait()
        disk=max(disk,disk_future.result(timeout=10))
        if disk>disk_cap:raise RuntimeError('final build/dependency cache disk cap')
        if budget_pin and digest(budget_path)!=budget_pin['sha256']:raise RuntimeError('build budget changed during command')
        _,leftovers=group_memory(proc.pid)
        if leftovers:raise RuntimeError('command exited with surviving group descendants')
        status='complete' if rc==0 else 'failed'
    except BaseException:
        failure=traceback.format_exc()
        if proc:
            try:os.killpg(proc.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:rc=proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL);rc=proc.wait()
    finally:
        scanner.shutdown(wait=True)
        out.write('stdout.txt',bytes(streams['stdout']),True);out.write('stderr.txt',bytes(streams['stderr']),True)
        if failure:out.json('failure.json',{'traceback':failure},True)
        if (ROOT/'Cargo.lock').exists():out.write('Cargo.lock',(ROOT/'Cargo.lock').read_bytes(),True)
        out.json('state.json',{'source_pins_after':[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in source_files()],'observed_processes':list(observed.values())},True)
        out.json('exit.json',{'returncode':rc,'elapsed_seconds':time.monotonic()-started,'sampled_group_peak':peak,'sample_count':samples,'largest_interval_seconds':largest_interval,'sampled_cache_bytes':disk,'child_wait_peak_rss_bytes':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'sampling_limitations':'short-lived children between samples may be missed; no hard OS cap; detached process groups are not guaranteed','scope':'one command plus same-session compiler/linker/build-script descendants','memory_cap_bytes':CAP,'windows_equivalent':False},True)
        out.close(status)
    print(json.dumps({'status':status,'returncode':rc,'records':records,'peak':peak}))
    return 0 if status=='complete' else 1
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--records',required=True);p.add_argument('--build-budget');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    if a.command[:1]==['--']:a.command.pop(0)
    sys.exit(main(a.records,a.command,a.build_budget))
