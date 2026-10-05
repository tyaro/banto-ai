"""Ordinary, sequential owned writer/reader for five previously audited fixture payloads.

The caller authenticates saved receipt pins. This binds their supplied bytes; it
does not authenticate historical execution or adopt formal scientific contracts.
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
from . import _anomaly_v03_fixture_budget as budgets

v,io,evidence,supervisor = observed.v,observed.io,observed.evidence,observed.supervisor
ROOT = Path(__file__).resolve().parents[2]
FORMAT = 'anomaly-v03-fixture-publication-request-v1'
INVOCATION = 'anomaly-v03-fixture-publication-invocation-v1'
PAYLOADS = ('analysis.json','coverage.json','diagnostics.json','execution.json','verification.json')
INPUTS = ('analysis/result.json','analysis/evidence.json','analysis/binding.json','analysis/document.json',
          'audit/result.json','audit/evidence.json','audit/verdict.json',*('wrapper/'+n for n in PAYLOADS))
LIMITS = {'wall_seconds':60,'private_bytes':256*1024**2,'output_bytes':1024**2}
EXTRA_SOURCES = tuple('src/banto_ai/'+n+'.py' for n in
    ('anomaly_v03_fixture_publication','_anomaly_v03_reader_dependencies','_anomaly_v03_fixture_budget'))
SOURCE_FILES = tuple(sorted((*observed.SOURCE_FILES,*EXTRA_SOURCES)))
BOOTSTRAP = ('import sys;sys.path.insert(0,sys.argv.pop(1));'
    'from banto_ai.anomaly_v03_fixture_publication import worker_main;raise SystemExit(worker_main(sys.argv[1:]))')
CLOSED = {**evidence.CLOSED,'formal_document_emitted':False,'formal_document_validated':False,
    'campaign_evaluations_credited':0,'registered_data_read':False,'formal_bootstrap_performed':False}


def _same_fields(value, expected, label):
    for key,want in expected.items():evidence._same(value[key],want,label+' '+key)


def _request(request):
    evidence._keys(request,'format mode inputs analysis_reference audit_reference','publication request')
    v.require(request['format'] == FORMAT and request['mode'] == 'fixture','only fixture publication is open')
    evidence._keys(request['inputs'],' '.join(INPUTS),'publication inputs')
    for name,row in request['inputs'].items():
        evidence._keys(row,'path pin links','publication input');evidence._absolute(row['path'])
        evidence._pin(row['pin']);evidence._same(row['links'],1,'single-link saved input')
        cap = 4*1024**2 if name.startswith('wrapper/') or name == 'analysis/document.json' else 64*1024
        v.require(0 < row['pin']['bytes'] <= cap,'saved fixture input limit')
    v.require(sum(r['pin']['bytes'] for r in request['inputs'].values()) <= 12*1024**2,'total saved input limit')
    for role in ('analysis','audit'):
        ref = request[role+'_reference'];evidence._keys(ref,'result_pin evidence_pin source_revision','saved reference')
        evidence._digest(ref['source_revision'],40)
        for name in ('result','evidence'):
            evidence._pin(ref[name+'_pin'])
            evidence._same(request['inputs'][role+'/'+name+'.json']['pin'],ref[name+'_pin'],'external '+role+' reference')


def _load(request):
    _request(request);raw = observed._inputs(request['inputs']);values = {n:v.strict_json(b) for n,b in raw.items()}
    a,ar = values['analysis/result.json'],values['analysis/evidence.json']
    b,br = values['audit/result.json'],values['audit/evidence.json']
    doc,verdict = values['analysis/document.json'],values['audit/verdict.json']
    for role,result,record in (('analysis',a,ar),('audit',b,br)):
        ref = request[role+'_reference']
        _same_fields(result,{'status':'verified','mode':'fixture','role':role,'worker_exit_confirmed':True,
            'new_evaluations':0,'formal_permission':False,'registered_data_read':False,'resource_budget_passed':True},role+' result')
        _same_fields(record,{'format':evidence.FORMAT,'mode':'fixture','role':role},role+' evidence')
        evidence._same(result['evidence_pin'],ref['evidence_pin'],role+' evidence pin')
        evidence._same(record['source_before'],record['source_after'],role+' sources changed')
        evidence._same(record['source_before']['revision'],ref['source_revision'],role+' revision')
        evidence._same(record['completion'],{'status':'completed','exit_code':0,'worker_exit_confirmed':True,'observation_errors':[]},role+' completion')
        evidence._same(record['process']['pid'],result['worker_pid'],role+' PID')
    _same_fields(a,{'format':'anomaly-v03-fixture-worker-check-v1','operation':'assemble-invented-document-v1',
                    'fixture_inference_performed':True},'analysis result')
    _same_fields(b,{'format':'anomaly-v03-fixture-audit-check-v1','operation':'audit-invented-primary-and-slices-v1',
        'fixture_numerical_audit_performed':True,'fixture_slice_audit_performed':True,
        'analysis_reference':request['analysis_reference']},'combined audit result')
    for name,pin in (('analysis/document.json',a['document_pin']),('analysis/binding.json',a['binding_pin']),('audit/verdict.json',b['audit_pin'])):
        evidence._raw(raw[name],pin,'saved output pin')
    evidence._same(ar['outputs'],{'fixture/document.json':a['document_pin']},'analysis output')
    evidence._same(br['outputs'],{'fixture/primary-and-slices-audit.json':b['audit_pin']},'audit output')
    for name,pin in {'fixture/document.json':a['document_pin'],'fixture/input.json':ar['inputs']['fixture/input.json'],
        'fixture/slices.json':ar['inputs']['fixture/slices.json'],'analysis/result.json':request['analysis_reference']['result_pin'],
        'analysis/evidence.json':a['evidence_pin']}.items():evidence._same(br['inputs'][name],pin,'audit input binding')
    binding = values['analysis/binding.json']
    _same_fields(binding,{**evidence.CLOSED,'status':'supplied_consumer_evidence_bound','mode':'fixture','role':'analysis',
        'evidence_pin':a['evidence_pin'],'input_pins':ar['inputs'],'output_pins':ar['outputs'],
        'source_descriptor':ar['source_before'],'invocation_id':ar['invocation_id']},'saved analysis binding')
    _same_fields(doc,{k:value for k,value in CLOSED.items() if k not in ('execution_authenticated','source_closure_complete','runtime_closure_complete')},'document scope')
    draws = doc['fixture_draws']
    v.require(isinstance(draws,list) and 1 <= len(draws) <= 8 and all(len(d) == 40 for d in draws),'bounded fixture draws')
    evidence._same(a['computation'],{'fixture_only':True,'clusters':40,'replicates':len(draws)},'analysis dimensions')
    _same_fields(verdict,{'format':'anomaly-v03-fixture-primary-and-slices-audit-v1','status':'primary_and_slice_numerics_matched',
        'fixture_only':True,'fixture_numerical_audit_performed':True,'fixture_slice_audit_performed':True,
        'clusters':40,'replicates':len(draws),'candidate_tables':9,'primary_estimates':117,'paired_estimates':72,'gates':180,
        'input_canonical_sha256':doc['input_canonical_sha256'],'formal_permission':False,'independent_s6_complete':False},'audit scope')
    _same_fields(verdict['slice_audit'],{'status':'slice_numerics_matched','main_slice_rows':1233,'diagnostic_rows':2835,
        'diagnostic_tables':9,'input_canonical_sha256':doc['input_canonical_sha256'],
        'slice_input_canonical_sha256':doc['slice_input_canonical_sha256']},'slice audit scope')
    evidence._same(doc['input_canonical_sha256'],ar['inputs']['fixture/input.json']['sha256'],'primary input digest')
    evidence._same(doc['slice_input_canonical_sha256'],ar['inputs']['fixture/slices.json']['sha256'],'slice input digest')
    files = {n:raw['wrapper/'+n] for n in PAYLOADS}
    evidence._same({n:observed._pin(b) for n,b in files.items()},a['wrapper_payload_pins'],'five saved wrapper pins')
    for name,data in files.items():
        value = values['wrapper/'+name]
        v.require(data == v.canonical_json(value),'canonical wrapper bytes')
        _same_fields(value,{**CLOSED,'published':False,'independent_numerical_audit_performed':False,
            'numerical_analysis_performed':False,'mode':'fixture','invented_only':True,
            'format':'anomaly-v03-'+name[:-5]+'-wrapper-fixture-v1'},'wrapper scope')
    x = values['wrapper/execution.json']
    _same_fields(x,{'analysis_binding':binding,'input_pins':ar['inputs'],
        'operation':{'format':'anomaly-v03-wrapper-fixture-operation-v1','mode':'fixture','operation':a['operation'],
                     'source_revision':request['analysis_reference']['source_revision']},
        'stages':{'producer':'fixture_declarations_only','analysis':'supplied_evidence_bound','audit':'not_run','writer':'not_run','reader':'not_run'}},'execution mapping')
    _same_fields(values['wrapper/analysis.json'],{**{k:doc[k] for k in ('document_draft','fixture_draws','fixture_packet')},
        'fixture_input_canonical_sha256':doc['input_canonical_sha256']},'analysis mapping')
    _same_fields(values['wrapper/diagnostics.json'],{'series':doc['diagnostic_series'],'details':doc['diagnostic_details'],
        'slice_input_canonical_sha256':doc['slice_input_canonical_sha256']},'diagnostic mapping')
    coverage = values['wrapper/coverage.json']
    evidence._raw(v.canonical_json(coverage['declarations']),ar['inputs']['fixture/coverage.json'],'coverage declaration pin')
    _same_fields(coverage['summary'],{'complete':True,'state':'complete','scope':'invented-declarations-only'},'coverage scope')
    _same_fields(values['wrapper/verification.json'],{'status':'fixture_wrapper_bound','formal_ready':False,'inference_recomputed':False,
        'missing_formal_fields':['status','provenance','analysis_consumer','bootstrap']},'verification scope')
    for key in ('status','provenance','analysis_consumer','bootstrap'):evidence._same(doc['document_draft'][key],None,'formal field closed')
    # LocalPublication requires one LF; retain original pins as separate inputs.
    return raw,{n:b+b'\n' for n,b in files.items()}


def _marker(files):
    entries = io.inventory(files)
    return io.json_bytes({'schema_version':'0.3','marker_type':'anomaly-v03-local-complete','payload_inventory':entries,
        'inventory_sha256':v.canonical_sha256(entries),'native_acceptance':'not_completed','performance_status':'not_evaluated'})


def _semantic(files):
    def check(actual):v.require(actual == files,'published bytes differ from audited wrapper')
    return check


def _readback(request,files,marker):
    return io.json_bytes({**CLOSED,'format':'anomaly-v03-fixture-publication-readback-v1','mode':'fixture',
        'status':'five_saved_payloads_matched','analysis_reference':request['analysis_reference'],
        'audit_reference':request['audit_reference'],'payload_pins':{n:observed._pin(b) for n,b in files.items()},
        'marker_pin':observed._pin(marker),'inference_recomputed':False})


def _source(revision):
    return {'revision':revision,'sources':[{'path':n,'byte_count':(p:=observed._pin(observed._file(ROOT/n,1024**2)))['bytes'],
        'raw_sha256':p['sha256']} for n in SOURCE_FILES]}


def _git_sources(revision, *, git_reader=None, role='writer'):
    if git_reader is None:
        _,snapshots,git = observed._git_sources(revision)
    else:
        from .anomaly_v03_preformal_analysis_git import OwnedFixtureGit
        v.require(role in ('writer', 'reader'), 'publication owned Git role')
        git = OwnedFixtureGit(git_reader, root=ROOT, revision=revision, role=role)
        v.require(git('rev-parse','HEAD').decode().strip() == revision,
                  role + ' owned Git HEAD')
        snapshots = {revision: {}}
        for name in observed.SOURCE_FILES:
            raw = git('show',revision+':'+name)
            v.require(raw == observed._file(ROOT/name,1024**2),
                      role + ' working/Git bytes differ')
            snapshots[revision][name] = raw
    v.require(not git('status','--porcelain').strip(),'publication candidate must be clean')
    for name in EXTRA_SOURCES:
        raw = git('show',revision+':'+name)
        v.require(raw == observed._file(ROOT/name,1024**2),'publication source differs from Git');snapshots[revision][name] = raw
    return _source(revision),snapshots,git


def _cached_git(git, revision, snapshots):
    """Reuse immutable blobs only within this call; working files stay rechecked."""
    blobs = dict(snapshots[revision])
    def cached(*args):
        if len(args) != 2 or args[0] != 'show' or not args[1].startswith(revision+':'):return git(*args)
        name = args[1][41:];v.safe_relative_path(name)
        if name not in blobs:
            v.require(len(blobs) < 64,'publication Git blob inventory limit')
            raw = git(*args);v.require(len(raw) <= 1024**2,'publication Git blob limit');blobs[name] = raw
        return blobs[name]
    cached.tool_record = git.tool_record
    return cached


def _role_outputs(role,request,files,marker):
    if role == 'writer':return {'publication/'+n:b for n,b in files.items()}|{'publication/.complete':marker}
    return {'verification/readback.json':_readback(request,files,marker)}


def _verify_publication(publication,files,marker):
    io.verify_local_publication(publication,expected_marker_sha256=observed._pin(marker)['sha256'],verify_semantics=_semantic(files))


def worker_main(argv):
    try:
        v.require(len(argv) == 3,'publication worker arguments')
        path = Path(argv[0]);pin = {'bytes':int(argv[1]),'sha256':argv[2]}
        bundle = v.strict_json(observed.consumer.pinned.read_pinned(path,pin,64*1024))
        evidence._keys(bundle,'format invocation_id source request role publication expected_outputs'+
            (' dependency_profile_pin' if 'dependency_profile_pin' in bundle else ''),'publication invocation')
        evidence._same(bundle['format'],INVOCATION,'invocation format');evidence._digest(bundle['invocation_id'])
        role = bundle['role'];v.require(role in ('writer','reader'),'publication role')
        evidence._source(bundle['source']);revision = bundle['source']['revision']
        publication = Path(bundle['publication']);evidence._absolute(str(publication))
        v.require(publication == path.parent.parent/'published','owned publication destination')
        source_before = _source(revision);evidence._same(source_before,bundle['source'],'child source')
        creation = observed.creation_observation(os.getpid());runtime_before = observed._observed_runtime()
        inputs,files = _load(bundle['request']);marker = _marker(files)
        outputs = _role_outputs(role,bundle['request'],files,marker)
        evidence._same({n:observed._pin(b) for n,b in outputs.items()},bundle['expected_outputs'],'expected role output')
        profile = None
        if 'dependency_profile_pin' in bundle:
            raw_profile = observed._file(path.parent/'dependency-profile.json',
                                         dependencies.PROFILE_MAX)
            profile = dependencies.load_five_role_profile(
                raw_profile, bundle['dependency_profile_pin'], role=role,
                root=ROOT, revision=revision)
        deps_before = dependencies.collect(ROOT)
        if profile is not None:
            dependencies.match_five_role_profile(profile, deps_before,
                                                 runtime_before, phase='before')
        if role == 'writer':
            def precommit_recheck():
                if profile is None:return
                source_at_commit = _source(revision)
                evidence._same(source_at_commit,bundle['source'],'writer source before commit')
                v.require(observed._inputs(bundle['request']['inputs']) == inputs,
                          'writer saved inputs changed before commit')
                evidence._raw(observed._file(path,64*1024),pin,
                              'writer invocation changed before commit')
                deps_at_commit = dependencies.collect(ROOT)
                runtime_at_commit = observed._observed_runtime()
                dependencies.match_five_role_profile(profile, deps_at_commit,
                                                     runtime_at_commit, phase='after')
            io.publish_local_result(publication.parent,publication.name,files,
                                    verify_semantics=_semantic(files),
                                    precommit_recheck=precommit_recheck if profile is not None else None)
        _verify_publication(publication,files,marker)
        if role == 'reader':io._exclusive(path.parent/'readback.json',outputs['verification/readback.json'])
        deps_after = dependencies.collect(ROOT);runtime_after = observed._observed_runtime();source_after = _source(revision)
        if profile is not None:
            dependencies.match_five_role_profile(profile, deps_after,
                                                 runtime_after, phase='after')
        v.require(observed._inputs(bundle['request']['inputs']) == inputs,'saved inputs changed')
        evidence._raw(observed._file(path,64*1024),pin,'invocation changed')
        inputs = inputs|{'operation/invocation.json':io.json_bytes(bundle)}
        record = {'format':evidence.FORMAT,'mode':'fixture','role':role,'invocation_id':bundle['invocation_id'],
            'source_before':source_before,'source_after':source_after,'runtime_before':runtime_before,'runtime_after':runtime_after,
            'process':{'pid':os.getpid(),'parent_pid':os.getppid(),'start_token':creation['start_token'],'argv':list(sys.orig_argv),'cwd':str(Path.cwd())},
            'inputs':{n:observed._pin(b) for n,b in inputs.items()},'outputs':{n:observed._pin(b) for n,b in outputs.items()},
            'completion':{'status':'completed','exit_code':0,'worker_exit_confirmed':True,'observation_errors':[]}}
        print(json.dumps({'evidence':record,'creation_observation':creation,'dependencies_before':deps_before,'dependencies_after':deps_after},sort_keys=True));return 0
    except (ValueError,OSError,KeyError,TypeError) as error:
        print(json.dumps({'status':'fixture_publication_rejected','detail':str(error),'formal_permission':False},sort_keys=True));return 2


def _retain_role_observation_pins(role,target,monitor,dependency_pair):
    """Pin parent-held observations, then reject changed saved copies."""
    v.require(role in ('writer','reader'),'publication role')
    stdout_pin = dict(monitor['output']);evidence._pin(stdout_pin)
    supervision_pin = observed._pin(io.json_bytes(monitor))
    dependency_pin = observed._pin(io.json_bytes(dependency_pair))
    observed._save(target/'dependencies.json',dependency_pair)
    for name,saved_pin,maximum in (('supervision.json',supervision_pin,64*1024),
                                   ('worker/report.json',stdout_pin,LIMITS['output_bytes']),
                                   ('dependencies.json',dependency_pin,LIMITS['output_bytes'])):
        evidence._raw(observed._file(target/name,maximum),saved_pin,'retained '+role+' '+name+' changed')
    return {'dependency_pin':dependency_pin,'stdout_pin':stdout_pin,'supervision_pin':supervision_pin}


def _run_role(role,request,target,publication,revision,budget,files,inputs,
              source_context,dependency_profile=None, *, owned_git=False):
    target.mkdir();source,source_bytes,git = source_context
    v.require(not owned_git or (role in ('writer', 'reader') and dependency_profile is None),
              'owned publication Git excludes profiles and other roles')
    profile = None
    if dependency_profile is not None:
        evidence._keys(dependency_profile, 'raw pin' +
            (' path' if 'path' in dependency_profile else ''), role + ' supplied profile')
        if 'path' in dependency_profile:
            evidence._raw(observed._file(dependency_profile['path'],
                                         dependencies.PROFILE_MAX),
                          dependency_profile['pin'], role + ' external profile changed')
        profile = dependencies.load_five_role_profile(
            dependency_profile['raw'], dependency_profile['pin'], role=role,
            root=ROOT, revision=revision)
        io._exclusive(target/'dependency-profile.json', dependency_profile['raw'])
    if budget.upstream is not None and hasattr(budget.upstream, 'record_role'):
        budget.upstream.checkpoint(role)
    budget.checkpoint()
    v.require(git('rev-parse','HEAD').decode().strip() == revision and not git('status','--porcelain').strip(),'publication candidate changed')
    evidence._same(_source(revision),source,'role source changed')
    observed._save(target/'source-tool.json',git.tool_record)
    runtime,runtime_bytes = observed._expected_runtime();marker = _marker(files)
    outputs = _role_outputs(role,request,files,marker)
    bundle = {'format':INVOCATION,'invocation_id':secrets.token_hex(32),'source':source,'request':request,'role':role,
        'publication':str(publication),'expected_outputs':{n:observed._pin(b) for n,b in outputs.items()}}
    if profile is not None:
        bundle['dependency_profile_pin'] = copy.deepcopy(dependency_profile['pin'])
    raw = io.json_bytes(bundle);pin = observed._pin(raw);path = target/'invocation.json';io._exclusive(path,raw)
    all_inputs = inputs|{'operation/invocation.json':raw}
    expected = {'invocation_id':bundle['invocation_id'],'source':source,'runtime':runtime,
        'inputs':{n:observed._pin(b) for n,b in all_inputs.items()},'outputs':bundle['expected_outputs']}
    argv = [sys.executable,'-I','-S','-B','-c',BOOTSTRAP,str(ROOT/'src'),str(path),str(pin['bytes']),pin['sha256']]
    launch = {}
    def boundary():
        budget.checkpoint()
        v.require(git('rev-parse','HEAD').decode().strip() == revision,'publication revision changed')
        evidence._same(_source(revision),source,'publication source changed')
        v.require(observed._inputs(request['inputs']) == inputs,'parent saved inputs changed')
        evidence._raw(observed._file(path,64*1024),pin,'publication invocation changed')
        current,_ = observed._expected_runtime();evidence._same(current,runtime,'publication runtime changed')
        if profile is not None:
            evidence._raw(observed._file(target/'dependency-profile.json',
                                         dependencies.PROFILE_MAX),
                          dependency_profile['pin'], role + ' profile changed')
    def started(process):
        launch.update(observed.creation_observation(process.pid,process._handle))
        expected['process'] = {'pid':process.pid,'parent_pid':os.getpid(),'start_token':launch['start_token'],'argv':list(argv),'cwd':str(ROOT)}
        observed._save(target/'launch.json',launch);observed._save(target/'expected.json',expected)
    try:
        monitor = supervisor.supervise(argv,ROOT,target/'worker',LIMITS,boundary=boundary,on_started=started,resource_probe=budget.probe)
    except supervisor.UnreapedWorker as error:
        try:observed._save(target/'supervision.json',error.report)
        finally:raise error
    observed._save(target/'supervision.json',monitor)
    v.require(monitor['status'] == 'complete' and monitor['worker_exit_confirmed'] and monitor['exit_code'] == 0
        and not monitor['observation_errors'],'owned '+role+' did not complete')
    v.require(monitor['worker_pid'] == expected['process']['pid'],'owned PID')
    reply = v.strict_json(observed.consumer.pinned.read_pinned(target/'worker/report.json',monitor['output'],LIMITS['output_bytes']))
    evidence._keys(reply,'evidence creation_observation dependencies_before dependencies_after','publication envelope')
    evidence._same(reply['creation_observation'],launch,'owned creation mismatch')
    for name,value in (('launch.json',launch),('expected.json',expected)):
        evidence._raw(observed._file(target/name,64*1024),observed._pin(io.json_bytes(value)),'retained expectation changed')
    boundary();_verify_publication(publication,files,marker)
    if role == 'reader':evidence._raw(observed._file(target/'readback.json',64*1024),observed._pin(outputs['verification/readback.json']),'reader output')
    record = io.json_bytes(reply['evidence']);record_pin = observed._pin(record)
    binding = evidence.validate_execution_evidence(record,expected_mode='fixture',expected_role=role,expected_pin=record_pin,
        expected=expected,source_snapshots=source_bytes,runtime_snapshots=runtime_bytes,input_snapshots=all_inputs,output_snapshots=outputs)
    supplement = dependencies.verify_pair(reply['dependencies_before'],reply['dependencies_after'],root=ROOT,revision=revision,git=git,required_sources=SOURCE_FILES)
    if profile is not None:
        for phase in ('before', 'after'):
            dependencies.match_five_role_profile(
                profile, reply['dependencies_' + phase],
                reply['evidence']['runtime_' + phase], phase=phase)
        boundary()
    budget.checkpoint();io._exclusive(target/'evidence.json',record);observed._save(target/'binding.json',binding)
    dependency_pair = {'before':reply['dependencies_before'],'after':reply['dependencies_after']}
    observation_pins = _retain_role_observation_pins(role,target,monitor,dependency_pair)
    observed._save(target/'dependency-crosscheck.json',supplement)
    receipt = {'status':'verified','role':role,'worker_pid':monitor['worker_pid'],'worker_exit_confirmed':True,
        'evidence_pin':record_pin,'invocation_pin':pin,'binding_pin':observed._pin(io.json_bytes(binding)),
        'source_revision':revision,'dependency_observation':supplement,**observation_pins,
        'profile_required':profile is not None,'before_work_profile_enforcement':profile is not None}
    if owned_git:
        receipt['source_tool_pin'] = observed._pin(observed._file(target/'source-tool.json',16*1024))
    if profile is not None:
        receipt['dependency_profile_pin'] = copy.deepcopy(dependency_profile['pin'])
        receipt['before_work_profile_enforcement'] = True
    observed._save(target/'result.json',receipt)
    if budget.upstream is not None and hasattr(budget.upstream, 'record_role'):
        raw_receipt = io.json_bytes(receipt)
        evidence._raw(observed._file(target/'result.json', 64*1024),
                      observed._pin(raw_receipt), 'retained '+role+' result changed')
        budget.upstream.record_role(role, 'verified',
            result_pin=observed._pin(raw_receipt), worker_pid=monitor['worker_pid'],
            exit_confirmed=monitor['worker_exit_confirmed'])
    return receipt


def publish_with_evidence(request, *, expected_revision, receipt_parent, receipt_name,
                          budget_limits=None, resource_budget=None,
                          dependency_profiles=None, writer_git_reader=None, reader_git_reader=None):
    """Reuse pinned analysis and combined audit. Publish once, then read after reaping writer."""
    _request(request);evidence._digest(expected_revision,40);request = copy.deepcopy(request)
    v.require(dependency_profiles is None or
              (type(dependency_profiles) is dict and
               set(dependency_profiles) == {'writer', 'reader'}),
              'writer/reader profile inventory')
    v.require(writer_git_reader is None or dependency_profiles is None,
              'owned writer Git excludes unowned profile loaders')
    v.require(reader_git_reader is None or writer_git_reader is not None,
              'owned reader Git requires owned writer Git')
    budget_limits = budgets.limits(budget_limits)
    parent = io._local_parent(Path(receipt_parent));v.safe_relative_path(receipt_name)
    v.require('/' not in receipt_name and not receipt_name.casefold().startswith('anomaly-multiseed-v0'),'receipt name')
    target = io.regular_path(parent/receipt_name,directory=True,missing=True)
    v.require(not any(observed.reader._overlap(target,p) for p in (ROOT/'src',*(Path(r['path']).parent for r in request['inputs'].values()))),'receipt overlaps inputs/source')
    target.mkdir();publication = target/'published';budget = budgets.FixtureBudget(
        target,budget_limits,upstream=resource_budget,publication_roots=[publication])
    result = {**CLOSED,'format':'anomaly-v03-fixture-publication-check-v1','mode':'fixture','status':'failed',
        'publication_status':'not_started','reader_status':'not_started','inference_recomputed':False,'new_evaluations':0,
        'analysis_runs':0,'audit_runs':0,'analysis_reference':request['analysis_reference'],'audit_reference':request['audit_reference'],
        'profile_required':dependency_profiles is not None,'before_work_profile_enforcement':False}
    if resource_budget is not None:
        result['shared_budget_root'] = str(resource_budget.root)
    try:
        budget.start();inputs,files = _load(request);budget.checkpoint()
        source,source_bytes,git = _git_sources(expected_revision,
            **({} if writer_git_reader is None else {'git_reader':writer_git_reader}))
        source_context = source,source_bytes,_cached_git(git,expected_revision,source_bytes)
        budget.checkpoint()
        result['publication_status'] = 'unconfirmed'
        writer = _run_role('writer',request,target/'writer',publication,expected_revision,budget,files,inputs,source_context,
                           *((dependency_profiles['writer'],) if dependency_profiles is not None else ()),
                           **({} if writer_git_reader is None else {'owned_git':True}))
        result.update(publication_status='completed',writer=writer)
        result['reader_status'] = 'unconfirmed'
        if writer_git_reader is not None:
            budget.checkpoint()
            reader_source,reader_bytes,reader_git = _git_sources(expected_revision,
                **({} if reader_git_reader is None else {'git_reader':reader_git_reader, 'role':'reader'}))
            evidence._same(reader_source,source,'writer/reader selected source differs')
            source_context = reader_source,reader_bytes,_cached_git(reader_git,expected_revision,reader_bytes)
        reader = _run_role('reader',request,target/'reader',publication,expected_revision,budget,files,inputs,source_context,
                           *((dependency_profiles['reader'],) if dependency_profiles is not None else ()),
                           **({} if reader_git_reader is None else {'owned_git':True}))
        result.update(reader_status='completed',reader=reader)
        budget.checkpoint();v.require(observed._inputs(request['inputs']) == inputs,'final saved inputs changed')
        # The reader verified publication before its receipt was retained.  A
        # change after that read must not be promoted by the outer receipt.
        _verify_publication(publication,files,_marker(files))
        for role,receipt in (('writer',writer),('reader',reader)):
            evidence._raw(observed._file(target/role/'result.json',64*1024),
                          observed._pin(io.json_bytes(receipt)),
                          'final retained '+role+' result changed')
        binding = {**CLOSED,'format':'anomaly-v03-fixture-publication-binding-v1','mode':'fixture','scope':'supplied-fixture-bytes-and-owned-local-processes',
            'analysis_reference':request['analysis_reference'],'audit_reference':request['audit_reference'],
            'payload_pins':{n:observed._pin(b) for n,b in files.items()},'marker_pin':observed._pin(_marker(files)),
            'writer_evidence_pin':writer['evidence_pin'],'reader_evidence_pin':reader['evidence_pin'],
            'saved_payload_pins':{n:request['inputs']['wrapper/'+n]['pin'] for n in PAYLOADS},
            'serialization':'saved-canonical-json-plus-one-LF','writer_reaped_before_reader_start':True,'analysis_runs':0,'audit_runs':0,'inference_recomputed':False}
        observed._save(target/'publication-binding.json',binding)
        result.update(status='verified',publication_binding_pin=observed._pin(io.json_bytes(binding)),payload_files=5,
            marker_pin=binding['marker_pin'],selected_source_files=len(SOURCE_FILES),runtime_files=2,retained_input_files=len(INPUTS))
        if dependency_profiles is not None:
            result['before_work_profile_enforcement'] = True
    except supervisor.UnreapedWorker as error:
        try:observed._save(target/'unreaped.json',{'worker_exit_confirmed':False,'publication_status':result['publication_status']})
        finally:raise error
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as error:
        result.update(reason='fixture_publication_rejected',error_type=type(error).__name__,detail=str(error))
    finally:budgets.finish(budget,target,result,owner_error=sys.exception())
    budgets.save_result(target,result)
    return {**result,'check_directory':str(target),'result_pin':observed._pin(io.json_bytes(result))}
