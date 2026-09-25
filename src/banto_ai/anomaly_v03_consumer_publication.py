"""Bounded selected-chunk publication metadata reader for a stopped writer.

Authenticate record relationships without opening observations, evaluations or
score ledgers. Controller closure is not proof of controller process exit.
The caller retains the verified adapter digest and closure hash externally.
"""
from __future__ import annotations

import hashlib
import math
import os
from pathlib import Path

from . import anomaly_v03 as v
from . import anomaly_v03_checkpoints as journal
from . import anomaly_v03_checkpoint_store as store
from . import anomaly_v03_attempt_descriptor as descriptor
from . import anomaly_v03_chunk_contract as contract
from . import anomaly_v03_chunk_audit as chunk_audit
from . import anomaly_v03_consumer_checkpoints as adapter
from . import anomaly_v03_consumer_input as consumer
from . import _anomaly_v03_io as storage
from . import _anomaly_v03_runtime as paths

MAX_CONTROL = 64 * 1024
MAX_MARKER = 256 * 1024
MAX_MANIFEST = 256 * 1024


def _read(path, digest, maximum, *, links=1):
    consumer._digest(digest)
    path = paths.regular_path(path, links=links)
    before = path.stat()
    v.require(before.st_size <= maximum, 'publication metadata byte limit')
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        v.require((opened.st_dev, opened.st_ino, opened.st_size, opened.st_nlink) ==
                  (before.st_dev, before.st_ino, before.st_size, links), 'metadata changed before read')
        raw = stream.read(maximum + 1)
    after = paths.regular_path(path, links=links).stat()
    v.require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
              (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'metadata changed during read')
    v.require(len(raw) == before.st_size <= maximum and hashlib.sha256(raw).hexdigest() == digest,
              'publication metadata hash/size mismatch')
    return raw


def _marker(raw):
    value = v.strict_json(raw)
    consumer._keys(value, 'schema_version marker_type payload_inventory inventory_sha256 native_acceptance performance_status',
                   'publication marker fields')
    consumer._same([value[k] for k in ('schema_version','marker_type','native_acceptance','performance_status')],
                   ['0.3','anomaly-v03-local-complete','not_completed','not_evaluated'], 'publication marker scope')
    entries = value['payload_inventory']
    v.require(type(entries) is list and 0 < len(entries) <= 512, 'publication inventory bound')
    names = []
    for entry in entries:
        consumer._keys(entry, 'path raw_sha256 canonical_sha256 row_count', 'publication entry fields')
        names.append(v.safe_relative_path(entry['path']))
        consumer._digest(entry['raw_sha256']); consumer._digest(entry['canonical_sha256'])
        v.require(type(entry['row_count']) is int and entry['row_count'] >= 0, 'publication row count')
    v.require(names == sorted(set(names)) and 'manifest.json' in names, 'publication inventory names')
    consumer._same(value['inventory_sha256'], v.canonical_sha256(entries), 'publication inventory digest')
    consumer._same(raw.decode('utf-8'), (v.canonical_json(value) + b'\n').decode('utf-8'), 'noncanonical marker')
    return {entry['path']: entry for entry in entries}


def read_chunk_publication(run_root, plan, adapted, *, expected_mode, expected_adapter_sha256,
                           chunk_index, closed_sequence, expected_closed_sha256):
    """Read eight fixed metadata files, at most 1040 KiB, for one final attempt.

    run_root is the campaign's run/ directory. plan and adapted are already
    decoded. The adapter digest must belong to a previously verified adapter
    output. No caller-supplied file path in any loaded record is followed.
    This is an ordinary stopped-writer reader, not hostile concurrency defense.
    """
    v.require(type(expected_mode) is str and expected_mode == adapter.MODE, 'formal/unknown publication mode is closed')
    v.require(type(chunk_index) is int and 0 <= chunk_index < 120, 'chunk index')
    v.require(type(closed_sequence) is int and 1 <= closed_sequence <= 999999, 'closed sequence')
    consumer._digest(expected_adapter_sha256); consumer._digest(expected_closed_sha256)
    consumer._same(v.canonical_sha256(adapted), expected_adapter_sha256, 'external adapter digest mismatch')
    consumer._same([adapted['format'], adapted['mode'], adapted['validation_status']],
        [adapter.FORMAT, adapter.MODE, 'checkpoint_metadata_adapted'], 'adapter contract')
    v.require(adapted['journal_declares_coverage_complete'] is True and adapted['declared_complete_chunks'] == 120,
              'adapter coverage incomplete')
    journal.validate_plan(plan)
    binding = adapted['bindings']
    consumer._same(v.canonical_sha256(plan), binding['plan_sha256'], 'adapter plan mismatch')
    selected = adapted['chunks'][chunk_index]
    attempt = selected['attempts'][-1]
    consumer._same(selected['identities'], plan['chunks'][chunk_index]['identities'], 'adapter selected identities')
    v.require(selected['chunk_index'] == chunk_index and selected['selected_attempt'] == attempt['attempt']
              and attempt['status'] in journal.VERIFIED, 'adapter selected attempt')
    root = paths.regular_path(Path(run_root), directory=True)
    reads = {}
    def read(name, digest, maximum, links=1):
        raw = _read(root/name, digest, maximum, links=links)
        reads[name] = {'bytes': len(raw), 'sha256': digest}
        return raw
    closed = v.strict_json(read(f'control/{closed_sequence:06d}/closed.json', expected_closed_sha256, MAX_CONTROL))
    consumer._keys(closed, 'format sequence request_sha256 checkpoint elapsed_seconds_total status stop_reason previous_state_sha256 formal_permission', 'closed fields')
    consumer._same([closed[k] for k in ('format','sequence','status','stop_reason','formal_permission')],
        ['anomaly-v03-closed-invocation-v1',closed_sequence,'completed',None,False], 'controller closure incomplete')
    for key in ('request_sha256','previous_state_sha256'): consumer._digest(closed[key])
    elapsed = closed['elapsed_seconds_total']
    v.require(type(elapsed) in (int,float) and math.isfinite(elapsed) and elapsed >= 0, 'controller elapsed time')
    checkpoint = closed['checkpoint']
    consumer._keys(checkpoint, 'descriptor_pins receipt', 'closure checkpoint fields')
    pins = store.validate_receipt(root/'metadata', checkpoint['receipt'])
    consumer._same(pins, {'expected_plan_sha256': binding['plan_sha256'],
        'expected_record_count': binding['record_count'], 'expected_head_sha256': binding['head_sha256']}, 'closure journal mismatch')
    wanted_sequences = [str(row['attempts'][-1]['record_sequences'][-1]) for row in adapted['chunks']]
    v.require(type(checkpoint['descriptor_pins']) is dict and set(checkpoint['descriptor_pins']) == set(wanted_sequences),
              'closure descriptor inventory')
    for digest in checkpoint['descriptor_pins'].values(): consumer._digest(digest)
    sequence = attempt['record_sequences'][-1]
    raw_record = read(f'metadata/journal/{sequence:06d}.json', attempt['terminal_record_sha256'], 16*1024)
    record = v.strict_json(raw_record)
    v.require(raw_record == journal.encode_record(record), 'noncanonical terminal record')
    consumer._same([record['chunk_index'],record['attempt'],record['status'],record['context'],record['evidence']],
        [chunk_index,attempt['attempt'],attempt['status'],attempt['context'],attempt['evidence']], 'adapter terminal record mismatch')
    stem = f"attempts/chunks/{chunk_index:03d}/attempt-{attempt['attempt']:04d}/"
    desc = v.strict_json(read(stem+f'descriptors/{sequence:06d}.json', checkpoint['descriptor_pins'][str(sequence)], MAX_CONTROL))
    descriptor._validate(desc, plan, record, {'expected_plan_sha256': binding['plan_sha256'],
        'expected_record_count': sequence, 'expected_head_sha256': attempt['terminal_record_sha256']})
    artifacts = desc['artifacts']
    def artifact(role, name, maximum, links=1):
        entry = artifacts[role]
        v.require(type(entry['bytes']) is int and 0 < entry['bytes'] <= maximum, 'artifact declared byte limit')
        raw = read(stem+name, entry['sha256'], maximum, links)
        v.require(len(raw) == entry['bytes'], 'artifact declared size mismatch')
        return raw
    result_root = paths.regular_path(root/stem/'result', directory=True)
    v.require({p.name for p in result_root.iterdir()} == {'payload','marker-pending.json','.complete'}, 'publication control inventory')
    paths.regular_path(result_root/'payload', directory=True)
    marker_raw = artifact('marker','result/.complete',MAX_MARKER,2)
    pending_raw = read(stem+'result/marker-pending.json', artifacts['marker']['sha256'],MAX_MARKER,2)
    a,b = (paths.regular_path(result_root/name,links=2).stat() for name in ('.complete','marker-pending.json'))
    v.require((a.st_dev,a.st_ino) == (b.st_dev,b.st_ino) and marker_raw == pending_raw, 'marker hardlink identity mismatch')
    inventory = _marker(marker_raw)
    raw_manifest = read(stem+'result/payload/manifest.json',inventory['manifest.json']['raw_sha256'],MAX_MANIFEST)
    consumer._same(storage.payload_entry('manifest.json',raw_manifest),inventory['manifest.json'], 'manifest inventory binding')
    manifest = v.strict_json(raw_manifest)
    consumer._same(v.canonical_sha256(manifest),attempt['manifest_metadata_sha256'],'adapter manifest mismatch')
    contract.validate_manifest(manifest,plan,chunk_index,attempt['attempt'])
    v.require(manifest['state'] == 'complete', 'published manifest incomplete')
    consumer._same(manifest['runtime'],record['context']['runtime'],'published runtime mismatch')
    consumer._same(adapter._slots(manifest,selected['identities'],{}),attempt['evaluations'],'adapter evaluation slots mismatch')
    entries = [entry for row in manifest['datasets'] for entry in row['files']]
    entries += [slot['evaluation'] for slot in manifest['slots']]
    for entry in entries:
        v.require(entry['path'] in inventory and inventory[entry['path']]['raw_sha256'] == entry['sha256'],
                  'manifest file reference differs from marker')
    supervision = v.strict_json(artifact('producer_supervision','producer-control/supervision.json',MAX_CONTROL))
    chunk_audit.validate_supervision(supervision,plan,chunk_index,attempt['attempt'])
    consumer._same(supervision['runtime'],manifest['runtime'],'producer exit runtime mismatch')
    monitor = v.strict_json(artifact('audit_supervision','audit/supervision.json',MAX_CONTROL))
    consumer._same([monitor[k] for k in ('format','status','exit_code','worker_exit_confirmed','stop_reason',
                                        'observation_errors','formal_permission','performance_status')],
        ['anomaly-v03-owned-process-monitor-v1','complete',0,True,None,[],False,'not_evaluated'], 'audit exit incomplete')
    consumer._same({'before':monitor['runtime_before'],'after':monitor['runtime_after']},desc['audit_runtime'],'audit exit runtime mismatch')
    consumer._same(monitor['output'],{key:artifacts['audit_report'][key] for key in ('bytes','sha256')},'audit exit output mismatch')
    consumer._same(monitor['limits'],{'wall_seconds':600,'private_bytes':1024**3,'output_bytes':8*1024**2},'audit monitor limits')
    consumer._same(monitor['stderr'],{'bytes':0,'sha256':hashlib.sha256(b'').hexdigest()},'audit stderr record')
    v.require(type(monitor['elapsed_seconds']) in (int,float) and math.isfinite(monitor['elapsed_seconds'])
              and 0 <= monitor['elapsed_seconds'] <= 600, 'audit elapsed time limit')
    v.require(type(monitor['peak_worker_private_bytes']) is int and 0 <= monitor['peak_worker_private_bytes'] <= 1024**3
              and 0 < monitor['output']['bytes'] <= 8*1024**2, 'audit resource limit')
    return {'format':'anomaly-v03-consumer-publication-metadata-check-v1','mode':adapter.MODE,
        'status':'publication_metadata_verified','chunk_index':chunk_index,'attempt':attempt['attempt'],
        'evaluations':len(manifest['slots']),'adapter_sha256':expected_adapter_sha256,'closed_sha256':expected_closed_sha256,
        'files_read':reads,'metadata_bytes_read':sum(entry['bytes'] for entry in reads.values()),
        'publication_metadata_verified':True,'manifest_bytes_verified':True,'worker_exit_records_verified':True,
        'controller_closure_record_verified':True,'controller_process_exit_verified':False,
        'full_payload_bytes_verified':False,'audit_report_bytes_verified':False,'publication_verified':False,
        'source_runtime_accepted':False,'result_trusted':False,'execution_authorized':False,'analysis_authorized':False,
        'formal_permission':False,'promotion_allowed':False,'independent_s6_complete':False,
        'performance_status':'not_evaluated','selected_candidate':None,
        'next_step':'authenticate_selected_payload_bytes_before_analysis'}
