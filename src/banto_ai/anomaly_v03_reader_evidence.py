"""Opt-in observed reader: selected Git bytes + owned process + saved inputs.

Ordinary single-writer engineering only. Python executable/DLL observations and
ten selected source files are NOT a complete runtime or dependency closure.
No principal changes, formal acceptance, numerical replay or new evaluations.
"""
from __future__ import annotations

import copy
import ctypes
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys

from . import anomaly_v03_consumer_reader as reader
from . import anomaly_v03_consumer_evidence as evidence

consumer=reader.consumer;io=reader.io;v=reader.v;supervisor=reader.supervisor
ROOT=Path(__file__).resolve().parents[2]
MIB=1024**2
SOURCE_FILES=tuple(sorted('src/banto_ai/'+n+'.py' for n in (
    'anomaly_v03_reader_evidence','anomaly_v03_consumer_evidence','anomaly_v03_consumer_reader',
    'anomaly_v03_process_supervisor','anomaly_v03_engineering_consumer','anomaly_v03',
    'anomaly_v03_engineering_contract','_anomaly_v03_io','_anomaly_v03_runtime','_anomaly_v03_engineering_runtime')))
BOOTSTRAP='import sys;sys.path.insert(0,sys.argv.pop(1));from banto_ai.anomaly_v03_reader_evidence import worker_main;raise SystemExit(worker_main(sys.argv[1:]))'
FORMAT='anomaly-v03-observed-reader-invocation-v1'
DEPENDENCY_LIMITS={**reader.LIMITS,'output_bytes':1024**2}


def _pin(raw):return consumer._pin(raw)
def _save(path,value):io._exclusive(path,io.json_bytes(value))


def _file(path, maximum=16*MIB, *, links=1):
    path=io.regular_path(Path(path),links=links)
    before=path.stat();v.require(before.st_size<=maximum,'observation file size limit')
    with path.open('rb') as f:
        opened=os.fstat(f.fileno())
        v.require((before.st_dev,before.st_ino,before.st_size)==(opened.st_dev,opened.st_ino,opened.st_size),'opened object changed')
        raw=f.read(maximum+1)
        after_handle=os.fstat(f.fileno())
    after=io.regular_path(path,links=links).stat()
    stamp=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)
    v.require(stamp(before)==stamp(opened)==stamp(after_handle)==stamp(after) and len(raw)==before.st_size,
              'observation file changed')
    return raw


def creation_observation(pid, handle=None):
    """Query only the supplied owned handle, or this current process."""
    kernel,w=supervisor.resources._windows()
    kernel.GetCurrentProcess.restype=w.HANDLE
    kernel.GetProcessId.argtypes=[w.HANDLE];kernel.GetProcessId.restype=w.DWORD
    kernel.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)]
    kernel.GetProcessTimes.restype=w.BOOL
    handle=kernel.GetCurrentProcess() if handle is None else int(handle)
    v.require(kernel.GetProcessId(handle)==pid,'owned process identity')
    values=[w.FILETIME() for _ in range(4)]
    v.require(kernel.GetProcessTimes(handle,*(ctypes.byref(x) for x in values)),'process creation observation')
    created=(values[0].dwHighDateTime<<32)|values[0].dwLowDateTime
    v.require(created>0,'missing process creation time')
    record={'pid':pid,'creation_time_100ns':created}
    return {**record,'start_token':v.canonical_sha256(record)}


def _runtime_core():
    observed=supervisor.resources.probe_runtime(ROOT)
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
        cpu=winreg.QueryValueEx(key,'ProcessorNameString')[0].strip()
    kernel,w=supervisor.resources._windows()
    kernel.GetModuleFileNameW.argtypes=[w.HMODULE,w.LPWSTR,w.DWORD];kernel.GetModuleFileNameW.restype=w.DWORD
    buffer=ctypes.create_unicode_buffer(32768)
    size=kernel.GetModuleFileNameW(sys.dllhandle,buffer,len(buffer))
    v.require(0<size<len(buffer),'loaded Python DLL path')
    paths={'python/executable':Path(sys.executable),'python/shared-library':Path(buffer.value)}
    snapshots={n:_file(p) for n,p in paths.items()}
    v.require(_pin(snapshots['python/executable'])['sha256']==observed['python_exe_raw_sha256'] and
              _pin(snapshots['python/shared-library'])['sha256']==observed['python_dll_raw_sha256'],'loaded Python identity changed')
    profile={'platform':{'system':'Windows','release':observed['release'],'build':observed['os_build'],
        'ubr':observed['os_ubr'],'architecture':observed['architecture'],'cpu_identity':cpu},
        'python':{'implementation':observed['implementation'],'version':observed['python_version'],
                  'pointer_bits':observed['pointer_bits'],'gil_disabled':observed['gil_disabled']},
        'files':{n:{'physical_path':str(p),'category':'python','pin':_pin(snapshots[n])} for n,p in paths.items()}}
    return profile,snapshots


def _expected_runtime():
    """Host values + explicit launch policy, retained before the worker starts."""
    profile,snapshots=_runtime_core();base=Path(sys.base_prefix)
    profile['startup']={'flags':dict(evidence.FLAGS),'sys_path':[str(ROOT/'src'),
        str(base/'python314.zip'),str(base/'DLLs'),str(base/'Lib'),str(base)],'site_imported':False,'hooks':[]}
    evidence._runtime(profile)
    return profile,snapshots


def _observed_runtime():
    profile,_=_runtime_core()
    profile['startup']={'flags':{n:getattr(sys.flags,n) for n in evidence.FLAGS},'sys_path':list(sys.path),
        'site_imported':'site' in sys.modules,'hooks':[n for n in ('sitecustomize','usercustomize') if n in sys.modules]}
    evidence._runtime(profile)
    return profile


def _working_source(revision):
    return {'revision':revision,'sources':[{'path':n,'byte_count':len(raw),'raw_sha256':_pin(raw)['sha256']}
        for n in SOURCE_FILES for raw in [_file(ROOT/n,MIB)]]}


def _git_sources(revision):
    evidence._digest(revision,40)
    executable=shutil.which('git');v.require(executable is not None,'Git unavailable')
    tool_path=Path(executable);links=tool_path.lstat().st_nlink
    v.require(links>=1,'invalid Git link count')
    executable=str(io.regular_path(tool_path,links=links))
    tool_pin=_pin(_file(tool_path,links=links))
    def git(*args):
        evidence._raw(_file(tool_path,links=links),tool_pin,'Git bytes changed')
        result=subprocess.check_output([executable,'-c','core.fsmonitor=false','-C',str(ROOT),*args],
            stdin=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW,
            env={**os.environ,'GIT_OPTIONAL_LOCKS':'0','GIT_NO_LAZY_FETCH':'1'})
        evidence._raw(_file(tool_path,links=links),tool_pin,'Git bytes changed')
        return result
    git.tool_record={'path':executable,'pin':tool_pin,'hardlinks':links,'full_tool_runtime_closure':False}
    v.require(git('rev-parse','HEAD').decode().strip()==revision,'reader revision changed')
    snapshots={n:git('show',revision+':'+n) for n in SOURCE_FILES}
    v.require(all(len(raw)<=MIB and _file(ROOT/n,MIB)==raw for n,raw in snapshots.items()),'selected working/Git bytes differ')
    return _working_source(revision),{revision:snapshots},git


def _inputs(records):
    v.require(type(records) is dict and 1<=len(records)<=32,'reader input inventory')
    total=0;result={}
    for name,row in records.items():
        v.safe_relative_path(name);evidence._keys(row,'path pin links','reader input fields');evidence._pin(row['pin'])
        v.require(type(row['links']) is int and row['links'] in (1,2),'reader input link count')
        total+=row['pin']['bytes'];v.require(row['pin']['bytes']<=16*MIB and total<=32*MIB,'reader input size limit')
        raw=_file(row['path'],row['pin']['bytes'],links=row['links'])
        evidence._raw(raw,row['pin'],'reader input changed');result[name]=raw
    return result


def worker_main(argv):
    try:
        v.require(len(argv)==3,'observed worker arguments')
        bundle_pin={'bytes':int(argv[1]),'sha256':argv[2]}
        raw=consumer.pinned.read_pinned(Path(argv[0]),bundle_pin,64*1024)
        bundle=v.strict_json(raw)
        evidence._keys(bundle,'format invocation_id source inputs'+(' observe_dependencies' if 'observe_dependencies' in bundle else ''),'observed invocation fields')
        observe_dependencies=bundle.get('observe_dependencies',False)
        v.require(type(observe_dependencies) is bool,'dependency observation option')
        v.require(bundle['format']==FORMAT,'observed invocation format');evidence._digest(bundle['invocation_id'])
        evidence._source(bundle['source'])
        source_before=_working_source(bundle['source']['revision'])
        consumer._same(source_before,bundle['source'],'child selected source differs')
        process=creation_observation(os.getpid())
        runtime_before=_observed_runtime()
        inputs=_inputs(bundle['inputs']);request=v.strict_json(inputs['reader/request.json']);reader._request(request)
        inputs['reader/invocation.json']=raw;input_pins={n:_pin(b) for n,b in inputs.items()}
        dependency_reply={}
        if observe_dependencies:
            from . import _anomaly_v03_reader_dependencies as dependencies
            dependency_reply['dependencies_before']=dependencies.collect(ROOT)
        result=reader.verify_saved_publication(request);result['request_pin']=input_pins['reader/request.json']
        output=io.json_bytes(result)
        if observe_dependencies:
            dependency_reply['dependencies_after']=dependencies.collect(ROOT)
        runtime_after=_observed_runtime();source_after=_working_source(bundle['source']['revision'])
        consumer._same({n:_pin(b) for n,b in _inputs(bundle['inputs']).items()},
            {n:p for n,p in input_pins.items() if n!='reader/invocation.json'},'child inputs changed during read')
        value={'format':evidence.FORMAT,'mode':consumer.MODE,'role':'reader','invocation_id':bundle['invocation_id'],
            'source_before':source_before,'source_after':source_after,
            'process':{'pid':os.getpid(),'parent_pid':os.getppid(),'start_token':process['start_token'],
                       'argv':list(sys.orig_argv),'cwd':str(Path.cwd())},
            'runtime_before':runtime_before,'runtime_after':runtime_after,'inputs':input_pins,
            'outputs':{'reader/report.json':_pin(output)},
            # Parent must still confirm exit from its owned handle before validation.
            'completion':{'status':'completed','exit_code':0,'worker_exit_confirmed':True,'observation_errors':[]}}
        print(json.dumps({'evidence':value,'reader_report':result,'creation_observation':process,**dependency_reply},sort_keys=True))
        return 0
    except (ValueError,OSError,KeyError,TypeError) as error:
        print(json.dumps({'status':'reader_observation_rejected','error_type':type(error).__name__,'detail':str(error),
                          'formal_permission':False},sort_keys=True));return 2


def check_with_evidence(request, *, expected_revision, receipt_parent, receipt_name, observe_dependencies=False):
    """After the single writer exits, bind a new reader attempt to retained pins.

    Only the selected source files must match the specified current Git commit;
    this is deliberately not a clean whole-checkout acceptance or a freeze.
    Original publications are read-only. An unreaped worker retains its owner.
    """
    reader._request(request);evidence._digest(expected_revision,40)
    v.require(type(observe_dependencies) is bool,'dependency observation option')
    limits=DEPENDENCY_LIMITS if observe_dependencies else reader.LIMITS
    request=copy.deepcopy(request)
    parent=io._local_parent(Path(receipt_parent));v.safe_relative_path(receipt_name)
    v.require('/' not in receipt_name and not receipt_name.casefold().startswith('anomaly-multiseed-v0'),'reader attempt name')
    target=io.regular_path(parent/receipt_name,directory=True,missing=True)
    blocked=[Path(request['publication_root']),ROOT/'src',
             *(Path(request[n]).parent for n in ('binding_savepoint','report_savepoint','analysis_input'))]
    v.require(not any(reader._overlap(target,p) for p in blocked),'evidence receipt overlaps inputs/source')
    target.mkdir()
    outer={**evidence.CLOSED,'status':'failed','format':'anomaly-v03-observed-reader-check-v1',
        'reader_exit_confirmed':False,'reader_pid':None,'new_evaluations':0,'original_publication_modified':False}
    try:
        source,source_bytes,git=_git_sources(expected_revision)
        _save(target/'source-tool.json',git.tool_record)
        runtime,runtime_bytes=_expected_runtime()
        prepared,receipt=consumer.prepare_engineering_result(request['binding_savepoint'],request['report_savepoint'],
            request['analysis_input'],expected_mode=request['mode'],expected_binding_pin=request['expected_binding_pin'],
            expected_report_pin=request['expected_report_pin'])
        expected_report=reader.verify_saved_publication(request)
        request_raw=io.json_bytes(request);io._exclusive(target/'reader-request.json',request_raw)
        expected_report['request_pin']=_pin(request_raw)
        records={'reader/request.json':{'path':str(target/'reader-request.json'),'pin':_pin(request_raw),'links':1}}
        for i,(path,pin) in enumerate(sorted(receipt['authenticated_files'].items())):
            records[f'authenticated/{i:02d}.json']={'path':path,'pin':pin,'links':1}
        publication=Path(request['publication_root'])
        for name,raw in prepared.items():
            records['publication/'+name]={'path':str(publication/'payload'/name),'pin':_pin(raw),'links':1}
        for name,label in (('.complete','complete'),('marker-pending.json','pending')):
            raw=_file(publication/name,16*1024,links=2)
            v.require(_pin(raw)['sha256']==request['expected_marker_sha256'],'marker anchor changed')
            records['publication/'+label+'.json']={'path':str(publication/name),'pin':_pin(raw),'links':2}
        input_bytes=_inputs(records)
        bundle={'format':FORMAT,'invocation_id':secrets.token_hex(32),'source':source,'inputs':records}
        if observe_dependencies:bundle['observe_dependencies']=True
        bundle_raw=io.json_bytes(bundle);bundle_path=target/'invocation.json';io._exclusive(bundle_path,bundle_raw)
        bundle_pin=_pin(bundle_raw);input_bytes['reader/invocation.json']=bundle_raw
        argv=[sys.executable,'-I','-S','-B','-c',BOOTSTRAP,str(ROOT/'src'),str(bundle_path),
              str(bundle_pin['bytes']),bundle_pin['sha256']]
        expected={'invocation_id':bundle['invocation_id'],'source':source,'runtime':runtime,
                  'inputs':{n:_pin(b) for n,b in input_bytes.items()}}
        launch_observed={}
        def boundary():
            v.require(git('rev-parse','HEAD').decode().strip()==expected_revision,'reader revision changed')
            consumer._same(_working_source(expected_revision),source,'selected source changed')
            consumer._same({n:_pin(b) for n,b in _inputs(records).items()},
                {n:p for n,p in expected['inputs'].items() if n!='reader/invocation.json'},'parent input changed')
            evidence._raw(_file(bundle_path,64*1024),bundle_pin,'invocation changed')
            current,current_bytes=_expected_runtime();consumer._same(current,runtime,'parent runtime expectation changed')
        def started(process):
            observed=creation_observation(process.pid,process._handle)
            launch_observed.update(observed)
            expected['process']={'pid':process.pid,'parent_pid':os.getpid(),'start_token':observed['start_token'],
                                 'argv':list(argv),'cwd':str(ROOT)}
            expected_report['reader_pid']=process.pid
            expected['outputs']={'reader/report.json':_pin(io.json_bytes(expected_report))}
            _save(target/'launch.json',observed);_save(target/'expected.json',expected)
        monitor=supervisor.supervise(argv,ROOT,target/'worker',limits,boundary=boundary,on_started=started)
        _save(target/'supervision.json',monitor)
        outer.update(reader_exit_confirmed=monitor['worker_exit_confirmed'],reader_pid=monitor['worker_pid'],
                     reason=monitor['stop_reason'] or 'worker_failed')
        if monitor['status']=='complete':
            v.require(monitor['worker_exit_confirmed'] and monitor['exit_code']==0 and not monitor['observation_errors'],
                      'owned worker completion required')
            v.require(monitor['worker_pid']==expected['process']['pid'],'owned worker PID changed')
            raw=consumer.pinned.read_pinned(target/'worker/report.json',monitor['output'],limits['output_bytes'])
            reply=v.strict_json(raw);evidence._keys(reply,'evidence reader_report creation_observation'+
                (' dependencies_before dependencies_after' if observe_dependencies else ''),'reader observation envelope')
            evidence._raw(_file(target/'launch.json',4096),_pin(io.json_bytes(launch_observed)),'retained launch changed')
            evidence._raw(_file(target/'expected.json',64*1024),_pin(io.json_bytes(expected)),'retained expectation changed')
            consumer._same(reply['creation_observation'],launch_observed,'child/owned creation differs')
            output=io.json_bytes(reply['reader_report']);evidence._raw(output,expected['outputs']['reader/report.json'],'reader output differs')
            if observe_dependencies:
                from . import _anomaly_v03_reader_dependencies as dependencies
                supplement=dependencies.verify_pair(reply['dependencies_before'],reply['dependencies_after'],
                    root=ROOT,revision=expected_revision,git=git,
                    required_sources=(*SOURCE_FILES,'src/banto_ai/_anomaly_v03_reader_dependencies.py'))
                dependency_value={'before':reply['dependencies_before'],'after':reply['dependencies_after']}
                _save(target/'dependencies.json',dependency_value)
                _save(target/'dependency-crosscheck.json',supplement)
                outer['dependency_observation']=supplement
                outer['dependency_pin']=_pin(io.json_bytes(dependency_value))
            # Extract from the parent's externally pinned, reaped stdout. Field
            # expectations come from preflight/owned launch, never from reply.
            raw_evidence=io.json_bytes(reply['evidence'])
            checked=evidence.validate_execution_evidence(raw_evidence,expected_mode=consumer.MODE,expected_role='reader',
                expected_pin=_pin(raw_evidence),expected=expected,source_snapshots=source_bytes,
                runtime_snapshots=runtime_bytes,input_snapshots=input_bytes,output_snapshots={'reader/report.json':output})
            io._exclusive(target/'reader-report.json',output);io._exclusive(target/'evidence.json',raw_evidence)
            _save(target/'binding.json',checked)
            outer.update(status='verified',reason=None,evidence_pin=_pin(raw_evidence),binding_pin=_pin(io.json_bytes(checked)),
                         selected_source_files=len(SOURCE_FILES),runtime_files=2,authenticated_input_files=len(input_bytes),
                         parent_and_child_creation_matched=True,stdout_pin=monitor['output'])
    except supervisor.UnreapedWorker as error:
        try:
            _save(target/'supervision.json',error.report)
            _save(target/'result.json',{**outer,'reason':'worker_exit_unconfirmed'})
        finally:
            raise error  # A receipt write failure must not hide the owned handle.
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as error:
        outer.update(reason='evidence_rejected',error_type=type(error).__name__,detail=str(error))
    _save(target/'result.json',outer)
    return {**outer,'check_directory':str(target),'result_pin':_pin(io.json_bytes(outer))}
