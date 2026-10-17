"""Retain an analysis-specific dependency candidate from a separate reference.

This profile covers saved-result preparation only. It neither accepts a formal
runtime nor permits numerical analysis or publication.
"""
from pathlib import Path

from . import anomaly_v03_reader_evidence as observed
from . import _anomaly_v03_reader_dependencies as dependencies

v=observed.v;io=observed.io;evidence=observed.evidence;consumer=observed.consumer
FORMAT='anomaly-v03-analysis-dependency-profile-v1'
OPERATION='prepare-saved-descriptive-result'
BOUNDARY='request-decoded-before-saved-result-preparation-and-staging-v1'
MAXIMUM=dependencies.PROFILE_MAX


def load_profile(raw, expected_pin, *, root, revision):
    """Decode only this role/operation, using the caller's retained byte pin."""
    v.require(type(raw) is bytes and 0<len(raw)<=MAXIMUM,'analysis dependency profile size')
    evidence._raw(raw,expected_pin,'retained analysis dependency profile pin')
    profile=v.strict_json(raw)
    evidence._keys(profile,'format mode role operation acceptance source_revision root runtime snapshot boundary reference scope',
        'analysis dependency profile fields')
    v.require(profile['format']==FORMAT and profile['mode']==consumer.MODE and profile['role']=='analysis'
        and profile['operation']==OPERATION and profile['acceptance']=='candidate-not-accepted',
        'analysis dependency profile role/mode/operation/acceptance')
    evidence._digest(revision,40)
    v.require(profile['source_revision']==revision and profile['root']==str(root),'analysis dependency profile source/root')
    v.require(profile['boundary']==BOUNDARY and profile['scope']==dependencies.SCOPE,'analysis dependency profile scope/boundary')
    evidence._runtime(profile['runtime'])
    evidence._keys(profile['reference'],'result_pin evidence_pin dependency_pin stdout_pin','analysis dependency profile reference')
    for pin in profile['reference'].values():evidence._pin(pin)
    snapshot=profile['snapshot']
    evidence._keys(snapshot,'format modules files native_files scope','analysis dependency profile snapshot')
    v.require(snapshot['format']==dependencies.FORMAT and snapshot['scope']==dependencies.SCOPE,'analysis dependency profile snapshot scope')
    v.require(type(snapshot['files']) is dict and 0<len(snapshot['files'])<=dependencies.MAX_FILES,'analysis dependency profile files')
    v.require(type(snapshot['modules']) is dict and len(snapshot['modules'])<=2048,'analysis dependency profile modules')
    return profile


def prepare_profile(reference_directory, *, expected_result_pin, expected_revision, profile_parent, profile_name):
    """Save one new candidate from an externally pinned, unprofiled reference."""
    from . import anomaly_v03_analysis_evidence as analysis
    evidence._pin(expected_result_pin);evidence._digest(expected_revision,40)
    reference=io.regular_path(Path(reference_directory),directory=True)
    parent=io._local_parent(Path(profile_parent));v.safe_relative_path(profile_name)
    v.require('/' not in profile_name and profile_name.endswith('.json'),'analysis dependency profile file name')
    target=io.regular_path(parent/profile_name,missing=True)
    v.require(not observed.reader._overlap(target,reference) and not observed.reader._overlap(target,analysis.ROOT/'src'),
        'profile overlaps reference/source')
    def read(name,pin,maximum):
        return v.strict_json(consumer.pinned.read_pinned(reference/name,pin,maximum))
    result=read('result.json',expected_result_pin,64*1024)
    v.require(result['format']=='anomaly-v03-observed-analysis-check-v1' and result['status']=='verified'
        and result['role']=='analysis' and result['operation']==OPERATION and result['worker_exit_confirmed'] is True
        and 'dependency_profile_pin' not in result,'completed unprofiled analysis reference required')
    for name,value in {**evidence.CLOSED,'numerical_analysis_performed':False,'published':False,'new_evaluations':0}.items():
        v.require(name in result and result[name]==value,'analysis reference acceptance boundary')
    value=read('evidence.json',result['evidence_pin'],64*1024)
    request=read('analysis-request.json',value['inputs']['analysis/request.json'],64*1024);analysis._request(request)
    inputs=[Path(request[n]).parent for n in ('binding_savepoint','report_savepoint','analysis_input')]
    v.require(not any(observed.reader._overlap(target,path) for path in inputs),'profile overlaps original inputs')
    binding=read('binding.json',result['binding_pin'],64*1024)
    v.require(binding['status']=='supplied_consumer_evidence_bound' and binding['evidence_pin']==result['evidence_pin'],
        'analysis reference evidence binding')
    pair=read('dependencies.json',result['dependency_pin'],analysis.LIMITS['output_bytes'])
    stdout=read('worker/report.json',result['stdout_pin'],analysis.LIMITS['output_bytes'])
    consumer._same(stdout['evidence'],value,'analysis reference stdout evidence')
    consumer._same(pair,{'role':'analysis','operation':OPERATION,'before':stdout['dependencies_before'],
        'after':stdout['dependencies_after']},'analysis reference stdout dependencies')
    v.require(value['format']==evidence.FORMAT and value['mode']==consumer.MODE and value['role']=='analysis',
        'analysis reference evidence role')
    v.require(value['process']['pid']==result['worker_pid'] and value['completion']['status']=='completed'
        and value['completion']['worker_exit_confirmed'] is True and value['completion']['exit_code']==0
        and not value['completion']['observation_errors'],'analysis reference completion')
    payload=io.regular_path(reference/'payload',directory=True)
    v.require({p.name for p in payload.iterdir()}==set(analysis.PAYLOAD_LIMITS),'analysis reference payload inventory')
    files={name:consumer.pinned.read_pinned(payload/name,result['payload_pins']['analysis/'+name],limit)
        for name,limit in analysis.PAYLOAD_LIMITS.items()}
    consumer._same(analysis._payloads(files),value['outputs'],'analysis reference payload evidence')
    consumer._same(value['source_before'],value['source_after'],'analysis reference source changed')
    consumer._same(value['runtime_before'],value['runtime_after'],'analysis reference runtime changed')
    consumer._same(pair['before'],pair['after'],'analysis reference imports changed during preparation')
    source,_,git=analysis._git_sources(expected_revision)
    consumer._same(value['source_before'],source,'analysis reference source differs from candidate')
    runtime,_=observed._expected_runtime()
    consumer._same(value['runtime_before'],runtime,'analysis reference runtime differs from preparation')
    checked=dependencies.verify_pair(pair['before'],pair['after'],root=analysis.ROOT,revision=expected_revision,
        git=git,required_sources=analysis.SOURCE_FILES)
    consumer._same(checked,result['dependency_observation'],'analysis reference dependency summary')
    profile={'format':FORMAT,'mode':consumer.MODE,'role':'analysis','operation':OPERATION,
        'acceptance':'candidate-not-accepted','source_revision':expected_revision,'root':str(analysis.ROOT),
        'runtime':runtime,'snapshot':pair['before'],'boundary':BOUNDARY,
        'reference':{'result_pin':dict(expected_result_pin),
            **{n:result[n] for n in ('evidence_pin','dependency_pin','stdout_pin')}},'scope':dict(dependencies.SCOPE)}
    raw=io.json_bytes(profile);pin=observed._pin(raw);load_profile(raw,pin,root=analysis.ROOT,revision=expected_revision)
    io._exclusive(target,raw)
    return {**evidence.CLOSED,'status':'candidate_profile_prepared','role':'analysis','operation':OPERATION,
        'profile_path':str(target),'profile_pin':pin,'reference_result_pin':dict(expected_result_pin),
        'source_revision':expected_revision,'files':len(profile['snapshot']['files']),
        'modules':len(profile['snapshot']['modules']),'automatic_update':False}
