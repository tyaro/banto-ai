"""Prepare an explicitly pinned reader candidate from a completed reference.

Preparation and checking are separate calls. No automatic profile replacement,
formal acceptance, campaign launch or in-memory-code attestation is provided.
"""
from pathlib import Path

from . import anomaly_v03_reader_evidence as observed
from . import _anomaly_v03_reader_dependencies as dependencies

v=observed.v;io=observed.io;evidence=observed.evidence;consumer=observed.consumer


def prepare_profile(reference_directory, *, expected_result_pin, expected_revision, profile_parent, profile_name):
    """Use an externally retained result pin; save one new candidate file.

    The reference must be an unprofiled successful dependency observation from
    this exact checkout/revision, stable across the read. Callers retain the
    returned pin before launching a subsequent reader with this candidate.
    """
    evidence._pin(expected_result_pin);evidence._digest(expected_revision,40)
    reference=io.regular_path(Path(reference_directory),directory=True)
    parent=io._local_parent(Path(profile_parent));v.safe_relative_path(profile_name)
    v.require('/' not in profile_name and profile_name.endswith('.json'),'dependency profile file name')
    target=io.regular_path(parent/profile_name,missing=True)
    v.require(not observed.reader._overlap(target,reference) and
              not observed.reader._overlap(target,observed.ROOT/'src'),'profile overlaps reference/source')
    def read(name,pin,maximum):
        raw=consumer.pinned.read_pinned(reference/name,pin,maximum)
        return v.strict_json(raw)
    result=read('result.json',expected_result_pin,64*1024)
    v.require(result['format']=='anomaly-v03-observed-reader-check-v1' and result['status']=='verified'
              and result['reader_exit_confirmed'] and 'dependency_profile_pin' not in result,
              'completed unprofiled reference required')
    for name,value in evidence.CLOSED.items():
        v.require(name in result and result[name]==value,'reference acceptance boundary')
    value=read('evidence.json',result['evidence_pin'],64*1024)
    binding=read('binding.json',result['binding_pin'],64*1024)
    v.require(binding['status']=='supplied_consumer_evidence_bound' and binding['evidence_pin']==result['evidence_pin'],
              'reference evidence binding')
    pair=read('dependencies.json',result['dependency_pin'],observed.DEPENDENCY_LIMITS['output_bytes'])
    stdout=read('worker/report.json',result['stdout_pin'],observed.DEPENDENCY_LIMITS['output_bytes'])
    consumer._same(stdout['evidence'],value,'reference stdout evidence')
    consumer._same(pair,{'before':stdout['dependencies_before'],'after':stdout['dependencies_after']},'reference stdout dependencies')
    v.require(value['format']==evidence.FORMAT and value['mode']==consumer.MODE and value['role']=='reader',
              'reference reader evidence')
    v.require(value['process']['pid']==result['reader_pid'] and value['completion']['status']=='completed'
              and value['completion']['worker_exit_confirmed'] and value['completion']['exit_code']==0
              and not value['completion']['observation_errors'],'reference completion')
    consumer._same(value['source_before'],value['source_after'],'reference source changed')
    consumer._same(value['runtime_before'],value['runtime_after'],'reference runtime changed')
    consumer._same(pair['before'],pair['after'],'reference imports changed during read')
    source,_,git=observed._git_sources(expected_revision)
    consumer._same(value['source_before'],source,'reference source differs from candidate')
    runtime,_=observed._expected_runtime()
    consumer._same(value['runtime_before'],runtime,'reference runtime differs from preparation')
    checked=dependencies.verify_pair(pair['before'],pair['after'],root=observed.ROOT,revision=expected_revision,
        git=git,required_sources=(*observed.SOURCE_FILES,'src/banto_ai/_anomaly_v03_reader_dependencies.py'))
    v.require(checked==result['dependency_observation'],'reference dependency summary')
    profile={'format':dependencies.PROFILE_FORMAT,'mode':consumer.MODE,'role':'reader',
        'acceptance':'candidate-not-accepted','source_revision':expected_revision,'root':str(observed.ROOT),
        'runtime':runtime,'snapshot':pair['before'],'boundary':dependencies.PROFILE_BOUNDARY,
        'reference':{'result_pin':dict(expected_result_pin),
                     **{n:result[n] for n in ('evidence_pin','dependency_pin','stdout_pin')}},
        'scope':dict(dependencies.SCOPE)}
    raw=io.json_bytes(profile);pin=observed._pin(raw)
    dependencies.load_profile(raw,pin,root=observed.ROOT,revision=expected_revision)
    io._exclusive(target,raw)
    return {**evidence.CLOSED,'status':'candidate_profile_prepared','profile_path':str(target),'profile_pin':pin,
            'reference_result_pin':dict(expected_result_pin),'source_revision':expected_revision,
            'project_files':checked['project_files'],'files':checked['files']}
