"""Owned, bounded primary-number audit for an externally pinned fixture analysis."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

from . import anomaly_v03_fixture_numeric_audit as numeric
from . import anomaly_v03_reader_evidence as observed
from . import _anomaly_v03_reader_dependencies as dependencies
from . import _anomaly_v03_fixture_budget as budgets

v,io,evidence,supervisor = observed.v,observed.io,observed.evidence,observed.supervisor
ROOT = Path(__file__).resolve().parents[2]
FORMAT = 'anomaly-v03-fixture-audit-request-v1'
INVOCATION = 'anomaly-v03-fixture-audit-invocation-v1'
OPERATION = 'audit-invented-primary-numerics-v1'
INPUT_LIMITS = {'fixture/input.json':1024**2,'fixture/document.json':4*1024**2,
                'analysis/result.json':64*1024,'analysis/evidence.json':64*1024,'fixture/audit-operation.json':4096}
LIMITS = {'wall_seconds':60,'private_bytes':256*1024**2,'output_bytes':1024**2}
EXTRA_SOURCES = tuple('src/banto_ai/'+n+'.py' for n in
    ('anomaly_v03_fixture_numeric_audit','anomaly_v03_fixture_audit_worker','_anomaly_v03_reader_dependencies','_anomaly_v03_fixture_budget'))
SOURCE_FILES = tuple(sorted((*observed.SOURCE_FILES,*EXTRA_SOURCES)))
BOOTSTRAP = ('import sys;sys.path.insert(0,sys.argv.pop(1));'
    'from banto_ai.anomaly_v03_fixture_audit_worker import worker_main;raise SystemExit(worker_main(sys.argv[1:]))')


def operation_descriptor(revision, reference):
    return {'format':'anomaly-v03-fixture-audit-operation-v1','mode':'fixture','operation':OPERATION,
            'source_revision':revision,'analysis_reference':reference}


def _request(request):
    evidence._keys(request,'format mode role operation inputs analysis_reference','fixture audit request')
    v.require(request['format'] == FORMAT and request['mode'] == 'fixture' and request['role'] == 'audit'
              and request['operation'] == OPERATION,'non-fixture audit mode/role/operation is closed')
    reference = request['analysis_reference']
    evidence._keys(reference,'result_pin evidence_pin source_revision','retained analysis reference')
    evidence._pin(reference['result_pin']);evidence._pin(reference['evidence_pin']);evidence._digest(reference['source_revision'],40)
    evidence._keys(request['inputs'],' '.join(INPUT_LIMITS),'five audit inputs')
    for name,row in request['inputs'].items():
        evidence._keys(row,'path pin links','audit input record');evidence._absolute(row['path'])
        evidence._same(row['links'],1,'single-link audit input');evidence._pin(row['pin'])
        v.require(0 < row['pin']['bytes'] <= INPUT_LIMITS[name],'audit input limit')
    v.require(sum(r['pin']['bytes'] for r in request['inputs'].values()) <= 6*1024**2,'total audit input limit')
    for name,key in (('analysis/result.json','result_pin'),('analysis/evidence.json','evidence_pin')):
        evidence._same(request['inputs'][name]['pin'],reference[key],'external analysis reference')


def _load(request, revision):
    _request(request);raw = observed._inputs(request['inputs']);values = {n:v.strict_json(b) for n,b in raw.items()}
    for name in ('fixture/input.json','fixture/document.json','fixture/audit-operation.json'):
        v.require(raw[name] == v.canonical_json(values[name]),'canonical fixture audit input')
    reference = request['analysis_reference'];result = values['analysis/result.json'];record = values['analysis/evidence.json']
    evidence._same(values['fixture/audit-operation.json'],operation_descriptor(revision,reference),'audit operation/revision')
    for key,value in {'format':'anomaly-v03-fixture-worker-check-v1','status':'verified','role':'analysis','mode':'fixture',
        'operation':'assemble-invented-document-v1','fixture_inference_performed':True,'worker_exit_confirmed':True,
        'new_evaluations':0,'formal_permission':False,'registered_data_read':False}.items():
        evidence._same(result[key],value,'retained analysis result '+key)
    evidence._same(result['evidence_pin'],reference['evidence_pin'],'analysis evidence pin')
    evidence._same(result['document_pin'],request['inputs']['fixture/document.json']['pin'],'analysis document pin')
    for key,value in {'format':evidence.FORMAT,'mode':'fixture','role':'analysis'}.items():evidence._same(record[key],value,'analysis evidence '+key)
    for key in ('source_before','source_after'):evidence._same(record[key]['revision'],reference['source_revision'],'analysis source revision')
    evidence._same(record['inputs']['fixture/input.json'],request['inputs']['fixture/input.json']['pin'],'analysis numeric input pin')
    evidence._same(record['outputs'],{'fixture/document.json':result['document_pin']},'analysis output inventory')
    evidence._same(record['completion'],{'status':'completed','exit_code':0,'worker_exit_confirmed':True,'observation_errors':[]},'analysis completion')
    evidence._same(record['process']['pid'],result['worker_pid'],'retained analysis PID')
    draws = numeric.validate_input(values['fixture/input.json'])
    evidence._same(result['computation'],{'fixture_only':True,'clusters':40,'replicates':draws},'analysis dimensions')
    return raw,values


def _source(revision):
    return {'revision':revision,'sources':[{'path':n,'byte_count':(p:=observed._pin(observed._file(ROOT/n,1024**2)))['bytes'],
        'raw_sha256':p['sha256']} for n in SOURCE_FILES]}


def _git_sources(revision):
    _,snapshots,git = observed._git_sources(revision)
    v.require(not git('status','--porcelain').strip(),'audit candidate must be clean')
    for name in EXTRA_SOURCES:
        raw = git('show',revision+':'+name)
        v.require(raw == observed._file(ROOT/name,1024**2),'audit source differs from Git');snapshots[revision][name] = raw
    return _source(revision),snapshots,git


def worker_main(argv):
    try:
        v.require(len(argv) == 3,'audit worker arguments')
        path = Path(argv[0]);pin = {'bytes':int(argv[1]),'sha256':argv[2]}
        bundle = v.strict_json(observed.consumer.pinned.read_pinned(path,pin,64*1024))
        evidence._keys(bundle,'format invocation_id source request expected_output','audit invocation')
        evidence._same(bundle['format'],INVOCATION,'audit invocation format');evidence._digest(bundle['invocation_id'])
        evidence._source(bundle['source']);revision = bundle['source']['revision'];request = bundle['request']
        source_before = _source(revision);evidence._same(source_before,bundle['source'],'audit child source')
        creation = observed.creation_observation(os.getpid());runtime_before = observed._observed_runtime()
        inputs,values = _load(request,revision);deps_before = dependencies.collect(ROOT)
        report = numeric.audit_primary_document(values['fixture/input.json'],values['fixture/document.json'])
        output = v.canonical_json(report)
        evidence._raw(output,bundle['expected_output'],'independent audit verdict differs')
        payload = path.parent/'payload';payload.mkdir();io._exclusive(payload/'primary-audit.json',output)
        deps_after = dependencies.collect(ROOT);runtime_after = observed._observed_runtime();source_after = _source(revision)
        evidence._same({n:observed._pin(b) for n,b in observed._inputs(request['inputs']).items()},
                       {n:observed._pin(b) for n,b in inputs.items()},'audit input changed')
        evidence._raw(observed._file(path,64*1024),pin,'audit invocation changed')
        record = {'format':evidence.FORMAT,'mode':'fixture','role':'audit','invocation_id':bundle['invocation_id'],
            'source_before':source_before,'source_after':source_after,'runtime_before':runtime_before,'runtime_after':runtime_after,
            'process':{'pid':os.getpid(),'parent_pid':os.getppid(),'start_token':creation['start_token'],'argv':list(sys.orig_argv),'cwd':str(Path.cwd())},
            'inputs':{n:observed._pin(b) for n,b in inputs.items()},'outputs':{'fixture/primary-audit.json':observed._pin(output)},
            'completion':{'status':'completed','exit_code':0,'worker_exit_confirmed':True,'observation_errors':[]}}
        print(json.dumps({'evidence':record,'creation_observation':creation,'dependencies_before':deps_before,'dependencies_after':deps_after},sort_keys=True))
        return 0
    except (ValueError,OSError,KeyError,TypeError) as error:
        print(json.dumps({'status':'fixture_audit_rejected','detail':str(error),'formal_permission':False},sort_keys=True));return 2


def audit_with_evidence(request, *, expected_revision, receipt_parent, receipt_name, budget_limits=None, resource_budget=None):
    """Audit one pinned prior fixture output. Never rerun the analysis worker."""
    _request(request);evidence._digest(expected_revision,40);request = copy.deepcopy(request)
    budget_limits = budgets.limits(budget_limits)
    parent = io._local_parent(Path(receipt_parent));v.safe_relative_path(receipt_name)
    v.require('/' not in receipt_name and not receipt_name.casefold().startswith('anomaly-multiseed-v0'),'audit receipt name')
    target = io.regular_path(parent/receipt_name,directory=True,missing=True)
    v.require(not any(observed.reader._overlap(target,p) for p in (ROOT/'src',*(Path(r['path']).parent for r in request['inputs'].values()))),'audit receipt overlaps inputs/source')
    target.mkdir()
    budget = budgets.FixtureBudget(target,budget_limits,upstream=resource_budget)
    result = {**numeric.CLOSED,'format':'anomaly-v03-fixture-audit-check-v1','status':'failed','mode':'fixture','role':'audit',
        'operation':OPERATION,'fixture_numerical_audit_performed':False,'worker_exit_confirmed':False,'worker_pid':None,'new_evaluations':0}
    try:
        budget.start()
        source,source_bytes,git = _git_sources(expected_revision);observed._save(target/'source-tool.json',git.tool_record)
        budget.checkpoint()
        runtime,runtime_bytes = observed._expected_runtime();inputs,values = _load(request,expected_revision)
        budget.checkpoint()
        # Construct only the required success claim; parent does not recompute numerics.
        output = v.canonical_json(numeric.success_summary(values['fixture/input.json']));output_pin = observed._pin(output)
        bundle = {'format':INVOCATION,'invocation_id':secrets.token_hex(32),'source':source,'request':request,'expected_output':output_pin}
        bundle_raw = io.json_bytes(bundle);bundle_pin = observed._pin(bundle_raw);path = target/'invocation.json';io._exclusive(path,bundle_raw)
        expected = {'invocation_id':bundle['invocation_id'],'source':source,'runtime':runtime,'inputs':{n:observed._pin(b) for n,b in inputs.items()},
                    'outputs':{'fixture/primary-audit.json':output_pin}}
        argv = [sys.executable,'-I','-S','-B','-c',BOOTSTRAP,str(ROOT/'src'),str(path),str(bundle_pin['bytes']),bundle_pin['sha256']]
        launch = {}
        def boundary():
            budget.checkpoint()
            v.require(git('rev-parse','HEAD').decode().strip() == expected_revision,'audit revision changed')
            evidence._same(_source(expected_revision),source,'audit source changed')
            evidence._same({n:observed._pin(b) for n,b in observed._inputs(request['inputs']).items()},expected['inputs'],'parent audit inputs changed')
            evidence._raw(observed._file(path,64*1024),bundle_pin,'audit invocation changed')
            current,_ = observed._expected_runtime();evidence._same(current,runtime,'audit runtime changed')
        def started(process):
            launch.update(observed.creation_observation(process.pid,process._handle))
            expected['process'] = {'pid':process.pid,'parent_pid':os.getpid(),'start_token':launch['start_token'],'argv':list(argv),'cwd':str(ROOT)}
            observed._save(target/'launch.json',launch);observed._save(target/'expected.json',expected)
        monitor = supervisor.supervise(argv,ROOT,target/'worker',LIMITS,boundary=boundary,on_started=started,resource_probe=budget.probe)
        observed._save(target/'supervision.json',monitor)
        result.update(worker_exit_confirmed=monitor['worker_exit_confirmed'],worker_pid=monitor['worker_pid'],reason=monitor['stop_reason'] or 'worker_failed')
        if monitor['status'] == 'complete':
            budget.checkpoint()
            v.require(monitor['worker_exit_confirmed'] and monitor['exit_code'] == 0 and not monitor['observation_errors'],'audit owned completion')
            v.require(monitor['worker_pid'] == expected['process']['pid'],'audit owned PID')
            reply = v.strict_json(observed.consumer.pinned.read_pinned(target/'worker/report.json',monitor['output'],LIMITS['output_bytes']))
            evidence._keys(reply,'evidence creation_observation dependencies_before dependencies_after','audit envelope')
            evidence._same(reply['creation_observation'],launch,'audit owned creation mismatch')
            for name,value in (('launch.json',launch),('expected.json',expected)):
                evidence._raw(observed._file(target/name,64*1024),observed._pin(io.json_bytes(value)),'audit retained expectation changed')
            payload = io.regular_path(target/'payload',directory=True)
            v.require({p.name for p in payload.iterdir()} == {'primary-audit.json'},'audit output inventory')
            actual = observed._file(payload/'primary-audit.json',64*1024);evidence._raw(actual,output_pin,'audit output differs')
            record = io.json_bytes(reply['evidence']);record_pin = observed._pin(record)
            binding = evidence.validate_execution_evidence(record,expected_mode='fixture',expected_role='audit',expected_pin=record_pin,
                expected=expected,source_snapshots=source_bytes,runtime_snapshots=runtime_bytes,input_snapshots=inputs,
                output_snapshots={'fixture/primary-audit.json':actual})
            supplement = dependencies.verify_pair(reply['dependencies_before'],reply['dependencies_after'],root=ROOT,revision=expected_revision,git=git,required_sources=SOURCE_FILES)
            budget.checkpoint()
            io._exclusive(target/'evidence.json',record);observed._save(target/'binding.json',binding)
            observed._save(target/'dependencies.json',{'before':reply['dependencies_before'],'after':reply['dependencies_after']})
            observed._save(target/'dependency-crosscheck.json',supplement)
            result.update(status='verified',reason=None,fixture_numerical_audit_performed=True,analysis_reference=request['analysis_reference'],
                evidence_pin=record_pin,audit_pin=output_pin,invocation_pin=bundle_pin,selected_source_files=len(SOURCE_FILES),
                runtime_files=2,retained_input_files=5,dependency_observation=supplement,parent_and_child_creation_matched=True)
    except supervisor.UnreapedWorker as error:
        try:
            observed._save(target/'supervision.json',error.report);observed._save(target/'result.json',{**result,'reason':'worker_exit_unconfirmed'})
        finally:raise error
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as error:
        result.update(reason='fixture_audit_rejected',error_type=type(error).__name__,detail=str(error))
    finally:
        budgets.finish(budget,target,result,owner_error=sys.exception())
    budgets.save_result(target,result)
    return {**result,'check_directory':str(target),'result_pin':observed._pin(io.json_bytes(result))}
