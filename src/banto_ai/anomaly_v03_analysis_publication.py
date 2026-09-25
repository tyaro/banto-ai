"""Publish retained analysis payloads, then run a separate observed reader.

The caller retains the analysis result pin and the returned chain receipt pin.
The publication marker authenticates four payloads; a separate pinned receipt
binds that marker to historical analysis evidence. No numerical audit is run.
"""
from __future__ import annotations

import copy
import os
from pathlib import Path
import subprocess

from . import anomaly_v03_analysis_evidence as analysis

observed=analysis.observed;consumer=analysis.consumer;io=analysis.io;v=analysis.v
evidence=analysis.evidence;profiles=analysis.profiles;supervisor=analysis.supervisor
ROOT=analysis.ROOT
SOURCE='src/banto_ai/anomaly_v03_analysis_publication.py'
FORMAT='anomaly-v03-analysis-publication-chain-v1'


def _prepared(reference, result_pin, revision):
    """Reauthenticate fixed saved evidence and staged bytes, without replay."""
    retained={}
    def read(name,pin,limit):
        raw=consumer.pinned.read_pinned(reference/name,pin,limit);retained[name]=raw
        return v.strict_json(raw)
    result=read('result.json',result_pin,64*1024)
    consumer._fields(result,{**evidence.CLOSED,'format':'anomaly-v03-observed-analysis-check-v1',
        'status':'verified','role':'analysis','operation':analysis.OPERATION,'worker_exit_confirmed':True,
        'numerical_analysis_performed':False,'published':False,'new_evaluations':0},'verified analysis required')
    value=read('evidence.json',result['evidence_pin'],64*1024)
    consumer._fields(value,{'format':evidence.FORMAT,'mode':consumer.MODE,'role':'analysis'},'analysis evidence role')
    consumer._same(value['source_before'],value['source_after'],'analysis source changed')
    v.require(value['source_before']['revision']==revision,'analysis revision mismatch')
    consumer._same(value['runtime_before'],value['runtime_after'],'analysis runtime changed')
    consumer._fields(value['completion'],{'status':'completed','exit_code':0,'worker_exit_confirmed':True,
        'observation_errors':[]},'analysis completion')
    v.require(value['process']['pid']==result['worker_pid'],'analysis PID binding')
    binding=read('binding.json',result['binding_pin'],64*1024)
    consumer._fields(binding,{**evidence.CLOSED,'status':'supplied_consumer_evidence_bound',
        'evidence_pin':result['evidence_pin']},'analysis evidence binding')
    bound=read('dependency-profile-binding.json',result['dependency_profile_binding_pin'],64*1024)
    consumer._fields(bound,{**evidence.CLOSED,'status':'retained_candidate_profile_matched','role':'analysis',
        'operation':analysis.OPERATION,'mode':consumer.MODE,'source_revision':revision,
        'profile_pin':result['dependency_profile_pin'],'comparison':'exact-before-and-after'},'analysis profile binding')
    profile_raw=consumer.pinned.read_pinned(reference/'dependency-profile.json',result['dependency_profile_pin'],profiles.MAXIMUM)
    retained['dependency-profile.json']=profile_raw
    profile=profiles.load_profile(profile_raw,result['dependency_profile_pin'],root=ROOT,revision=revision)
    consumer._same(bound['reference_result_pin'],profile['reference']['result_pin'],'analysis profile reference')
    consumer._same(value['inputs']['analysis/dependency-profile.json'],result['dependency_profile_pin'],'analysis profile input')
    pair=read('dependencies.json',result['dependency_pin'],analysis.LIMITS['output_bytes'])
    stdout=read('worker/report.json',result['stdout_pin'],analysis.LIMITS['output_bytes'])
    consumer._same(stdout['evidence'],value,'analysis stdout evidence')
    consumer._same(pair,{'role':'analysis','operation':analysis.OPERATION,
        'before':stdout['dependencies_before'],'after':stdout['dependencies_after']},'analysis dependency evidence')
    for phase in ('before','after'):
        analysis.dependencies.match_profile(profile,pair[phase],value['runtime_'+phase],phase=phase)
    request=read('analysis-request.json',value['inputs']['analysis/request.json'],64*1024);analysis._request(request)
    payload=io.regular_path(reference/'payload',directory=True)
    v.require({p.name for p in payload.iterdir()}==set(analysis.PAYLOAD_LIMITS),'staged payload inventory')
    files={name:consumer.pinned.read_pinned(payload/name,result['payload_pins']['analysis/'+name],limit)
        for name,limit in analysis.PAYLOAD_LIMITS.items()}
    pins=analysis._payloads(files)
    consumer._same(pins,result['payload_pins'],'staged result inventory')
    consumer._same(pins,value['outputs'],'staged analysis evidence outputs')
    expected,_=analysis._prepare(request)
    consumer._same(files,expected,'staged payload differs from authenticated originals')
    retained.update({'payload/'+name:raw for name,raw in files.items()})
    return request,files,result,retained


def publish_and_check(reference_directory, *, expected_mode, expected_analysis_result_pin, expected_revision,
                      output_parent, output_name, receipt_parent, receipt_name):
    """One ordinary writer followed by one reader; never resume/overwrite.

Only a caller-pinned, profiled analysis success can supply payloads. Receipt
failure never removes a publication. Unconfirmed publication and reader failure
remain separate states, and an unreaped reader retains its original owner.
"""
    v.require(expected_mode==consumer.MODE,'formal/unknown publication chain mode is closed')
    evidence._pin(expected_analysis_result_pin);evidence._digest(expected_revision,40)
    result_pin=copy.deepcopy(expected_analysis_result_pin)
    reference=io.regular_path(Path(reference_directory),directory=True)
    parent=io._local_parent(Path(output_parent));checks=io._local_parent(Path(receipt_parent))
    for name in (output_name,receipt_name):
        v.safe_relative_path(name)
        v.require('/' not in name and not name.casefold().startswith('anomaly-multiseed-v0'),'chain attempt name')
    publication=io.regular_path(parent/output_name,directory=True,missing=True)
    target=io.regular_path(checks/receipt_name,directory=True,missing=True)
    for path in (publication,target):
        v.require(not any(observed.reader._overlap(path,p) for p in (reference,ROOT/'src')),'chain overlaps analysis/source')
    v.require(not observed.reader._overlap(publication,target),'chain receipt overlaps publication')
    # Inspect the pinned request before creating anything, to protect its inputs.
    request,files,selected,retained=_prepared(reference,result_pin,expected_revision)
    sources=[Path(request[n]).parent for n in ('binding_savepoint','report_savepoint','analysis_input')]
    v.require(not any(observed.reader._overlap(path,p) for path in (publication,target) for p in sources),'chain overlaps original inputs')
    source,_,git=analysis._git_sources(expected_revision)
    consumer._same(v.strict_json(retained['evidence.json'])['source_before'],source,'analysis source differs from publisher')
    connector_raw=git('show',expected_revision+':'+SOURCE)
    consumer._same(observed._file(ROOT/SOURCE,1024**2),connector_raw,'publication connector differs from Git')
    target.mkdir()
    outer={**evidence.CLOSED,'format':FORMAT,'mode':consumer.MODE,'status':'failed',
        'analysis_result_pin':result_pin,'analysis_directory':str(reference),'source_revision':expected_revision,
        'connector_source_pin':observed._pin(connector_raw),'analysis_worker_pid':selected['worker_pid'],
        'writer_pid':os.getpid(),'publication_root':str(publication),'publication_status':'not_started',
        'reader_exit_confirmed':False,'writer_closed_before_reader':False,'new_evaluations':0,
        'numerical_analysis_performed':False,'independent_numerical_audit_performed':False}
    def verify(saved):
        consumer._same(set(saved),set(files),'chain publication inventory')
        for name,raw in files.items():consumer._same(saved[name],raw,'chain publication bytes')
    def unchanged():
        for name,raw in retained.items():
            evidence._raw(observed._file(reference/name,len(raw)),observed._pin(raw),'retained analysis changed')
        consumer._same(observed._file(ROOT/SOURCE,1024**2),connector_raw,'publication connector changed')
    try:
        unchanged();outer['publication_status']='unconfirmed'
        published=io.publish_local_result(parent,output_name,files,verify_semantics=verify)
        outer.update(publication_status='completed',marker_raw_sha256=published['marker_raw_sha256'],writer_closed_before_reader=True)
        local=io.verify_local_publication(publication,expected_marker_sha256=published['marker_raw_sha256'],verify_semantics=verify)
        publication_binding={**evidence.CLOSED,'format':'anomaly-v03-analysis-publication-binding-v1','mode':consumer.MODE,
            'analysis_result_pin':result_pin,'analysis_evidence_pin':selected['evidence_pin'],
            'analysis_profile_pin':selected['dependency_profile_pin'],'analysis_profile_binding_pin':selected['dependency_profile_binding_pin'],
            'source_revision':expected_revision,'connector_source_pin':outer['connector_source_pin'],
            'publication_root':str(publication),'marker_raw_sha256':published['marker_raw_sha256'],
            'payload_pins':selected['payload_pins'],'payloads':local['payloads'],
            'analysis_execution_binding_reused':True,'writer_closed_before_reader':True,'numerical_analysis_performed':False}
        binding_raw=io.json_bytes(publication_binding);io._exclusive(target/'publication-binding.json',binding_raw)
        outer['publication_binding_pin']=observed._pin(binding_raw)
        reader_request={'format':observed.reader.FORMAT,'mode':consumer.MODE,'publication_root':str(publication),
            'expected_marker_sha256':published['marker_raw_sha256'],
            **{n:request[n] for n in ('binding_savepoint','report_savepoint','analysis_input','expected_binding_pin','expected_report_pin')}}
        checked=observed.check_with_evidence(reader_request,expected_revision=expected_revision,receipt_parent=target,
            receipt_name='reader',observe_dependencies=True)
        outer.update(reader_exit_confirmed=checked['reader_exit_confirmed'],reader_pid=checked['reader_pid'],
            reader_result_pin=checked['result_pin'])
        v.require(checked['status']=='verified' and checked['reader_exit_confirmed'] is True,'post-publication reader failed')
        v.require(checked['reader_pid']!=os.getpid(),'distinct reader process required')
        unchanged()
        evidence._raw(observed._file(target/'publication-binding.json',64*1024),outer['publication_binding_pin'],
            'retained publication binding changed')
        outer.update(status='analysis_publication_reader_verified',reason=None,payloads=4,
            payload_bytes=sum(map(len,files.values())),reader_evidence_pin=checked['evidence_pin'])
    except supervisor.UnreapedWorker as error:
        try:observed._save(target/'result.json',{**outer,'reason':'reader_exit_unconfirmed'})
        finally:raise error
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as error:
        outer.update(reason='publication_chain_rejected',error_type=type(error).__name__,detail=str(error))
    raw=io.json_bytes(outer);io._exclusive(target/'result.json',raw)
    return {**outer,'check_directory':str(target),'result_pin':observed._pin(raw)}
