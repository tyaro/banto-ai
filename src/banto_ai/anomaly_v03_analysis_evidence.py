"""Observe engineering preparation of saved descriptive results in one child.

The analysis role here authenticates saved inputs and prepares four payloads.
It does not recompute statistics, publish a completed result, or accept a gate.
Reader profiles are not inputs to this role-specific entry point.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

from . import anomaly_v03_reader_evidence as observed
from . import _anomaly_v03_reader_dependencies as dependencies

consumer=observed.consumer;io=observed.io;v=observed.v;evidence=observed.evidence;supervisor=observed.supervisor
ROOT=Path(__file__).resolve().parents[2]
FORMAT='anomaly-v03-observed-analysis-request-v1'
INVOCATION='anomaly-v03-observed-analysis-invocation-v1'
OPERATION='prepare-saved-descriptive-result'
REQUEST_FIELDS='format mode role operation binding_savepoint report_savepoint analysis_input expected_binding_pin expected_report_pin'
EXTRA_SOURCES=('src/banto_ai/_anomaly_v03_reader_dependencies.py','src/banto_ai/anomaly_v03_analysis_evidence.py')
SOURCE_FILES=tuple(sorted((*observed.SOURCE_FILES,*EXTRA_SOURCES)))
PAYLOAD_LIMITS={**consumer.REPORT_LIMITS,'consumer-receipt.json':1024**2}
TOTAL_PAYLOAD_LIMIT=8*1024**2
LIMITS={'wall_seconds':30,'private_bytes':512*1024**2,'output_bytes':1024**2}
BOOTSTRAP='import sys;sys.path.insert(0,sys.argv.pop(1));from banto_ai.anomaly_v03_analysis_evidence import worker_main;raise SystemExit(worker_main(sys.argv[1:]))'


def _request(value):
    evidence._keys(value,REQUEST_FIELDS,'analysis request fields')
    v.require(value['format']==FORMAT and value['mode']==consumer.MODE and value['role']=='analysis'
              and value['operation']==OPERATION,'analysis role/mode/operation is closed')
    for name in ('binding_savepoint','report_savepoint','analysis_input'):
        v.require(type(value[name]) is str and Path(value[name]).is_absolute(),'explicit analysis input path')
    for name in ('expected_binding_pin','expected_report_pin'):observed.reader._pin_shape(value[name])


def _prepare(request):
    _request(request)
    return consumer.prepare_engineering_result(request['binding_savepoint'],request['report_savepoint'],request['analysis_input'],
        expected_mode=request['mode'],expected_binding_pin=request['expected_binding_pin'],expected_report_pin=request['expected_report_pin'])


def _payloads(files):
    v.require(type(files) is dict and set(files)==set(PAYLOAD_LIMITS),'analysis output inventory')
    v.require(all(type(raw) is bytes and 0<len(raw)<=PAYLOAD_LIMITS[name] for name,raw in files.items()),'analysis output file limit')
    v.require(sum(map(len,files.values()))<=TOTAL_PAYLOAD_LIMIT,'analysis total output limit')
    return {'analysis/'+name:observed._pin(raw) for name,raw in sorted(files.items())}


def _working_source(revision):
    source=observed._working_source(revision)
    for name in EXTRA_SOURCES:
        raw=observed._file(ROOT/name,1024**2)
        source['sources'].append({'path':name,'byte_count':len(raw),'raw_sha256':observed._pin(raw)['sha256']})
    source['sources'].sort(key=lambda r:r['path']);evidence._source(source)
    return source


def _git_sources(revision):
    source,snapshots,git=observed._git_sources(revision)
    for name in EXTRA_SOURCES:
        raw=git('show',revision+':'+name)
        v.require(len(raw)<=1024**2 and raw==observed._file(ROOT/name,1024**2),'analysis source differs from Git')
        snapshots[revision][name]=raw
    return _working_source(revision),snapshots,git


def worker_main(argv):
    try:
        v.require(len(argv)==3,'analysis worker arguments')
        pin={'bytes':int(argv[1]),'sha256':argv[2]};invocation_path=Path(argv[0])
        raw=consumer.pinned.read_pinned(invocation_path,pin,64*1024);bundle=v.strict_json(raw)
        evidence._keys(bundle,'format role operation invocation_id source inputs','analysis invocation fields')
        v.require(bundle['format']==INVOCATION and bundle['role']=='analysis' and bundle['operation']==OPERATION,'analysis invocation scope')
        evidence._digest(bundle['invocation_id']);evidence._source(bundle['source'])
        source_before=_working_source(bundle['source']['revision'])
        consumer._same(source_before,bundle['source'],'analysis child source differs')
        process=observed.creation_observation(os.getpid());runtime_before=observed._observed_runtime()
        inputs=observed._inputs(bundle['inputs']);request=v.strict_json(inputs['analysis/request.json']);_request(request)
        inputs['analysis/invocation.json']=raw;input_pins={n:observed._pin(b) for n,b in inputs.items()}
        deps_before=dependencies.collect(ROOT)
        files,receipt=_prepare(request);output_pins=_payloads(files)
        consumer._same(receipt['authenticated_files'],{r['path']:r['pin'] for n,r in bundle['inputs'].items()
            if n.startswith('authenticated/')},'analysis authenticated input inventory differs')
        target=invocation_path.parent/'payload';target.mkdir()
        for name in sorted(files):
            io._exclusive(target/name,files[name])
            evidence._raw(observed._file(target/name,PAYLOAD_LIMITS[name]),output_pins['analysis/'+name],'analysis output readback differs')
        deps_after=dependencies.collect(ROOT)
        runtime_after=observed._observed_runtime();source_after=_working_source(bundle['source']['revision'])
        consumer._same({n:observed._pin(b) for n,b in observed._inputs(bundle['inputs']).items()},
            {n:p for n,p in input_pins.items() if n!='analysis/invocation.json'},'analysis inputs changed during preparation')
        value={'format':evidence.FORMAT,'mode':consumer.MODE,'role':'analysis','invocation_id':bundle['invocation_id'],
            'source_before':source_before,'source_after':source_after,
            'process':{'pid':os.getpid(),'parent_pid':os.getppid(),'start_token':process['start_token'],
                       'argv':list(sys.orig_argv),'cwd':str(Path.cwd())},
            'runtime_before':runtime_before,'runtime_after':runtime_after,'inputs':input_pins,'outputs':output_pins,
            'completion':{'status':'completed','exit_code':0,'worker_exit_confirmed':True,'observation_errors':[]}}
        print(json.dumps({'evidence':value,'creation_observation':process,'dependencies_before':deps_before,
                          'dependencies_after':deps_after},sort_keys=True))
        return 0
    except (ValueError,OSError,KeyError,TypeError) as error:
        print(json.dumps({'status':'analysis_observation_rejected','error_type':type(error).__name__,
            'detail':str(error),'formal_permission':False},sort_keys=True));return 2


def prepare_with_evidence(request, *, expected_revision, receipt_parent, receipt_name):
    """Prepare a new evidence directory; original inputs remain read-only.

    Parent-retained expectations bind the analysis role, selected Git source,
    core runtime, owned child and all inputs/outputs. Full dependency snapshots
    are crosschecked against disk/Git after exit, not a frozen expected profile.
    """
    _request(request);evidence._digest(expected_revision,40);request=copy.deepcopy(request)
    parent=io._local_parent(Path(receipt_parent));v.safe_relative_path(receipt_name)
    v.require('/' not in receipt_name and not receipt_name.casefold().startswith('anomaly-multiseed-v0'),'analysis attempt name')
    target=io.regular_path(parent/receipt_name,directory=True,missing=True)
    blocked=[ROOT/'src',*(Path(request[n]).parent for n in ('binding_savepoint','report_savepoint','analysis_input'))]
    v.require(not any(observed.reader._overlap(target,p) for p in blocked),'analysis receipt overlaps inputs/source')
    target.mkdir()
    result={**evidence.CLOSED,'format':'anomaly-v03-observed-analysis-check-v1','status':'failed','role':'analysis',
        'operation':OPERATION,'worker_exit_confirmed':False,'worker_pid':None,'original_inputs_modified':False,
        'new_evaluations':0,'numerical_analysis_performed':False,'published':False}
    try:
        source,source_bytes,git=_git_sources(expected_revision);observed._save(target/'source-tool.json',git.tool_record)
        runtime,runtime_bytes=observed._expected_runtime()
        files,receipt=_prepare(request);output_pins=_payloads(files)
        request_raw=io.json_bytes(request);io._exclusive(target/'analysis-request.json',request_raw)
        records={'analysis/request.json':{'path':str(target/'analysis-request.json'),'pin':observed._pin(request_raw),'links':1}}
        for i,(path,pin) in enumerate(sorted(receipt['authenticated_files'].items())):
            records[f'authenticated/{i:02d}.json']={'path':path,'pin':pin,'links':1}
        input_bytes=observed._inputs(records)
        bundle={'format':INVOCATION,'role':'analysis','operation':OPERATION,'invocation_id':secrets.token_hex(32),'source':source,'inputs':records}
        bundle_raw=io.json_bytes(bundle);bundle_path=target/'invocation.json';io._exclusive(bundle_path,bundle_raw)
        bundle_pin=observed._pin(bundle_raw);input_bytes['analysis/invocation.json']=bundle_raw
        expected={'invocation_id':bundle['invocation_id'],'source':source,'runtime':runtime,
            'inputs':{n:observed._pin(b) for n,b in input_bytes.items()},'outputs':output_pins}
        argv=[sys.executable,'-I','-S','-B','-c',BOOTSTRAP,str(ROOT/'src'),str(bundle_path),str(bundle_pin['bytes']),bundle_pin['sha256']]
        launch={}
        def boundary():
            v.require(git('rev-parse','HEAD').decode().strip()==expected_revision,'analysis revision changed')
            consumer._same(_working_source(expected_revision),source,'analysis source changed')
            consumer._same({n:observed._pin(b) for n,b in observed._inputs(records).items()},
                {n:p for n,p in expected['inputs'].items() if n!='analysis/invocation.json'},'parent analysis inputs changed')
            evidence._raw(observed._file(bundle_path,64*1024),bundle_pin,'analysis invocation changed')
            current,_=observed._expected_runtime();consumer._same(current,runtime,'analysis runtime expectation changed')
        def started(process):
            launch.update(observed.creation_observation(process.pid,process._handle))
            expected['process']={'pid':process.pid,'parent_pid':os.getpid(),'start_token':launch['start_token'],'argv':list(argv),'cwd':str(ROOT)}
            observed._save(target/'launch.json',launch);observed._save(target/'expected.json',expected)
        monitor=supervisor.supervise(argv,ROOT,target/'worker',LIMITS,boundary=boundary,on_started=started)
        observed._save(target/'supervision.json',monitor)
        result.update(worker_exit_confirmed=monitor['worker_exit_confirmed'],worker_pid=monitor['worker_pid'],reason=monitor['stop_reason'] or 'worker_failed')
        if monitor['status']=='complete':
            v.require(monitor['worker_exit_confirmed'] and monitor['exit_code']==0 and not monitor['observation_errors'],'analysis owned worker completion')
            v.require(monitor['worker_pid']==expected['process']['pid'],'analysis owned PID changed')
            reply_raw=consumer.pinned.read_pinned(target/'worker/report.json',monitor['output'],LIMITS['output_bytes'])
            reply=v.strict_json(reply_raw);evidence._keys(reply,'evidence creation_observation dependencies_before dependencies_after','analysis envelope')
            evidence._raw(observed._file(target/'launch.json',4096),observed._pin(io.json_bytes(launch)),'analysis retained launch changed')
            evidence._raw(observed._file(target/'expected.json',64*1024),observed._pin(io.json_bytes(expected)),'analysis retained expectation changed')
            consumer._same(reply['creation_observation'],launch,'analysis child/owned creation differs')
            payload_root=io.regular_path(target/'payload',directory=True)
            v.require({p.name for p in payload_root.iterdir()}==set(files),'analysis saved output inventory')
            outputs={}
            for name,expected_raw in files.items():
                raw=observed._file(payload_root/name,PAYLOAD_LIMITS[name])
                evidence._raw(raw,output_pins['analysis/'+name],'analysis output differs from retained expectation')
                outputs['analysis/'+name]=raw
            raw_evidence=io.json_bytes(reply['evidence'])
            checked=evidence.validate_execution_evidence(raw_evidence,expected_mode=consumer.MODE,expected_role='analysis',
                expected_pin=observed._pin(raw_evidence),expected=expected,source_snapshots=source_bytes,
                runtime_snapshots=runtime_bytes,input_snapshots=input_bytes,output_snapshots=outputs)
            supplement=dependencies.verify_pair(reply['dependencies_before'],reply['dependencies_after'],root=ROOT,
                revision=expected_revision,git=git,required_sources=SOURCE_FILES)
            deps={'role':'analysis','operation':OPERATION,'before':reply['dependencies_before'],'after':reply['dependencies_after']}
            io._exclusive(target/'evidence.json',raw_evidence);observed._save(target/'binding.json',checked)
            observed._save(target/'dependencies.json',deps);observed._save(target/'dependency-crosscheck.json',supplement)
            result.update(status='verified',reason=None,evidence_pin=observed._pin(raw_evidence),binding_pin=observed._pin(io.json_bytes(checked)),
                dependency_pin=observed._pin(io.json_bytes(deps)),dependency_observation=supplement,stdout_pin=monitor['output'],
                selected_source_files=len(SOURCE_FILES),runtime_files=2,authenticated_input_files=len(input_bytes),
                payload_pins=output_pins,parent_and_child_creation_matched=True)
    except supervisor.UnreapedWorker as error:
        try:
            observed._save(target/'supervision.json',error.report)
            observed._save(target/'result.json',{**result,'reason':'worker_exit_unconfirmed'})
        finally:
            raise error
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as error:
        result.update(reason='evidence_rejected',error_type=type(error).__name__,detail=str(error))
    observed._save(target/'result.json',result)
    return {**result,'check_directory':str(target),'result_pin':observed._pin(io.json_bytes(result))}
