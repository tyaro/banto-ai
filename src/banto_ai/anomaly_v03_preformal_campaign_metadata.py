"""Pure invented campaign plan and append-only journal validation.

The journal records caller declarations.  Even a complete 480-chunk history
does not authenticate a producer, saved bytes, process exits, or a common
execution budget.  Its retry transitions never authorize native resume;
an owner must independently reconcile and reap all processes first.  No
observation is generated or read here.
"""
from __future__ import annotations

import copy
import hashlib
import math
from pathlib import PureWindowsPath
import re

from . import anomaly_v03 as v
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_consumer_input as input_contract
from . import anomaly_v03_registered_saved_summary as saved


PLAN_FORMAT = 'anomaly-v03-preformal-invented-campaign-plan-v1'
RECORD_FORMAT = 'anomaly-v03-preformal-invented-campaign-record-v1'
OUTPUT_FORMAT = 'anomaly-v03-preformal-invented-campaign-journal-check-v1'
SCOPE = 'invented-registered-format-metadata-only'
RECIPE = 'hand-normal-v1'
ATTEMPT_PREFIX = 'anomaly-v03-preformal-registered-attempt-'
MAX_PLAN_BYTES = 512 * 1024
MAX_RECORD_BYTES = 16 * 1024
MAX_RECORDS = 480 * 4 * 2
MAX_TOTAL_RECORD_BYTES = 32 * 1024**2
MAX_ATTEMPTS = 4
FROZEN_REGISTRY_BYTES = 10679
REQUIRED_EVIDENCE_NAMES = (
    'generator_invocation', 'generator_supervision', 'generator_stdout',
    'initial_saved_reader_invocation', 'initial_saved_reader_supervision',
    'initial_saved_reader_stdout',
    'outer_result', 'saved_receipt', 'saved_report', 'saved_savepoint',
    'saved_registry', 'rows', 'two_role_budget_result',
    'two_role_budget_receipt',
)
FRESH_REREAD_EVIDENCE_NAMES = (
    'fresh_reread_result', 'fresh_reread_supervision',
    'fresh_reread_stdout', 'fresh_reread_budget_receipt',
    'fresh_reread_rows',
)
EVIDENCE_NAMES = REQUIRED_EVIDENCE_NAMES + FRESH_REREAD_EVIDENCE_NAMES
BUDGET_LIMITS = (
    'wall_seconds', 'parent_private_bytes', 'directory_bytes',
    'directory_entries', 'directory_depth',
    'minimum_commit_headroom_bytes', 'minimum_free_ram_bytes',
    'minimum_free_disk_bytes',
)
RUNTIME_FIELDS = {
    'architecture', 'compiler', 'filesystem', 'gil_disabled',
    'implementation', 'os', 'os_build', 'os_major', 'os_minor', 'os_ubr',
    'pointer_bits', 'python_dll_raw_sha256', 'python_exe_raw_sha256',
    'python_version', 'release', 'source_tag',
}
PLAN_FIELDS = {
    'format', 'scope', 'mode', 'campaign_id', 'root', 'path_code',
    'registry_pin', 'recipe_id', 'registered_seed_consumed', 'source',
    'runtime_candidate', 'budget_candidate', 'identity_plan_sha256',
    'chunk_identity_hashes_sha256',
    'chunks', 'chunks_sha256', 'planned_counts', 'invented_only',
    'actual_registered_observations_read', 'campaign_evaluations_credited',
    'campaign_coherence_authenticated', 'campaign_completed',
    'launch_authorized', 'resume_authorized',
    'full_end_to_end_budget_measured',
    'formal_permission', 'analysis_authorized', 'promotion_allowed',
    'independent_s6_complete',
}


def _keys(value, names, label):
    v.require(type(value) is dict and set(value) == set(names), label + ' fields')


def _same(actual, expected, label):
    v.require(v.canonical_json(actual) == v.canonical_json(expected), label)


def _hex(value, length, label):
    v.require(type(value) is str and
              re.fullmatch(r'[0-9a-f]{' + str(length) + r'}', value), label)


def _pin(value, label, *, positive=True):
    evidence._pin(value)
    if positive:
        v.require(value['bytes'] > 0, label + ' empty pin')


def pin(raw):
    """Make a byte pin; callers must retain it outside the journal."""
    v.require(type(raw) is bytes, 'raw bytes required for pin')
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _source(value):
    _keys(value, {'revision', 'selected_files', 'scope'}, 'selected source')
    _hex(value['revision'], 40, 'selected source revision')
    v.require(value['scope'] == 'selected-working-git-raw-only-not-source-closure',
              'selected source scope')
    rows = value['selected_files']
    v.require(type(rows) is list and 1 <= len(rows) <= 64,
              'selected source file count')
    paths = []
    for row in rows:
        _keys(row, {'path', 'pin'}, 'selected source row')
        paths.append(v.safe_relative_path(row['path']))
        _pin(row['pin'], 'selected source')
        v.require(row['pin']['bytes'] <= 1024**2,
                  'selected source file byte bound')
    v.require(len({path.casefold() for path in paths}) == len(paths),
              'duplicate selected source file')


def require_generator_source_subset(plan_source, generator_source,
                                    generator_paths):
    """Require the generator's exact selected files with the plan's same pins.

    The plan may also pin owner/store files.  This checks declarations only;
    live raw bytes for all planned files are checked by the campaign store.
    """
    _source(plan_source)
    _source(generator_source)
    v.require(type(generator_paths) in (list, tuple) and generator_paths and
              all(type(path) is str for path in generator_paths),
              'generator source path contract')
    required = set(generator_paths)
    v.require(len(required) == len(generator_paths) and
              all(v.safe_relative_path(path) == path for path in required),
              'unique generator source paths')
    v.require(generator_source['revision'] == plan_source['revision'] and
              generator_source['scope'] == plan_source['scope'],
              'generator source revision/scope differs from plan')
    planned = {row['path']: row['pin']
               for row in plan_source['selected_files']}
    selected = {row['path']: row['pin']
                for row in generator_source['selected_files']}
    v.require(set(selected) == required and required <= set(planned),
              'exact generator source subset paths required')
    for path in required:
        _same(selected[path], planned[path],
              'generator source plan pin ' + path)


def _runtime(value):
    _keys(value, {'candidate_id', 'tuple', 'tuple_sha256', 'status'},
          'runtime candidate')
    candidate = value['candidate_id']
    v.require(type(candidate) is str and
              re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}-v[1-9][0-9]*',
                           candidate), 'versioned runtime candidate ID')
    v.require(value['status'] == 'not_adopted',
              'runtime candidate must remain unadopted')
    runtime = value['tuple']
    _keys(runtime, RUNTIME_FIELDS, 'runtime tuple')
    for name in ('architecture', 'compiler', 'filesystem', 'implementation',
                 'os', 'python_version', 'release', 'source_tag'):
        item = runtime[name]
        v.require(type(item) is str and 0 < len(item) <= 128,
                  'runtime tuple text ' + name)
    for name in ('os_build', 'os_major', 'os_minor', 'os_ubr', 'pointer_bits'):
        v.require(type(runtime[name]) is int and runtime[name] >= 0,
                  'runtime tuple integer ' + name)
    v.require(type(runtime['gil_disabled']) is bool,
              'runtime GIL flag')
    for name in ('python_dll_raw_sha256', 'python_exe_raw_sha256'):
        _hex(runtime[name], 64, 'runtime executable digest')
    _hex(value['tuple_sha256'], 64, 'runtime tuple digest')
    v.require(value['tuple_sha256'] == v.canonical_sha256(runtime),
              'runtime tuple digest mismatch')


def _budget(value):
    _keys(value, {'scope', 'status', 'enforcement', 'limits'},
          'budget candidate')
    _same([value['scope'], value['status'], value['enforcement']], [
        'invented-480-chunk-campaign-candidate', 'not_adopted',
        'sampled-and-cooperative-not-hard-quota'],
        'unadopted invented budget scope')
    limits = value['limits']
    _keys(limits, BUDGET_LIMITS, 'budget limits')
    for name in BUDGET_LIMITS:
        number = limits[name]
        if name == 'wall_seconds':
            v.require(type(number) in (int, float) and math.isfinite(number)
                      and number > 0, 'finite positive budget wall')
        else:
            v.require(type(number) is int and number > 0,
                      'positive budget limit ' + name)


def _base36(index):
    digits = '0123456789abcdefghijklmnopqrstuvwxyz'
    v.require(type(index) is int and 0 <= index < 480, 'chunk index')
    return digits[index // 36] + digits[index % 36]


def attempt_root(plan, chunk_index, attempt):
    """Derive a short sibling root required by the existing generator."""
    v.require(type(plan) is dict and 'root' in plan and
              'campaign_id' in plan and 'path_code' in plan,
              'campaign root descriptor')
    v.require(type(attempt) is int and 1 <= attempt <= MAX_ATTEMPTS,
              'bounded attempt number')
    root = PureWindowsPath(plan['root'])
    suffix = plan['path_code'] + _base36(chunk_index) + str(attempt)
    return str(root.parent / (ATTEMPT_PREFIX + suffix))


def fixed_plan(campaign_id, root, path_code, registry_pin, source,
               runtime, budget_candidate):
    """Freeze the complete identity order as metadata, without seed use."""
    _hex(campaign_id, 64, 'new campaign ID')
    v.require(type(path_code) is str and
              re.fullmatch(r'[a-z]', path_code), 'one-character path code')
    evidence._absolute(root)
    local_root = PureWindowsPath(root)
    v.require(local_root.parent.name.casefold() == 'artifacts' and
              local_root.name == 'anomaly-v03-preformal-campaign-' +
              campaign_id[:8] and str(local_root) == root,
              'dedicated campaign metadata root')
    _pin(registry_pin, 'frozen registry')
    v.require(registry_pin['bytes'] == FROZEN_REGISTRY_BYTES and
              registry_pin['sha256'] == v.REGISTRY_RAW_SHA256,
              'frozen registry raw pin')
    _source(source)
    _runtime(runtime)
    _budget(budget_candidate)
    identities = v.evaluation_inventory('holdout')
    v.require(len(identities) == 2880, 'frozen holdout metadata count')
    chunks = []
    for index in range(480):
        group = identities[index * 6:index * 6 + 6]
        v.require(len(group) == 6 and len({x['seed'] for x in group}) == 1
                  and len({x['layout'] for x in group}) == 1,
                  'frozen six-identity chunk')
        chunks.append({
            'chunk_index': index, 'registered_seed': group[0]['seed'],
            'registered_seed_index': index // 12,
            'layout': group[0]['layout'],
            'identities_sha256': v.canonical_sha256(group),
        })
    normalized_source = copy.deepcopy(source)
    normalized_source['selected_files'].sort(key=lambda row: row['path'])
    result = {
        'format': PLAN_FORMAT, 'scope': SCOPE, 'mode': 'preformal-fixture',
        'campaign_id': campaign_id, 'root': root, 'path_code': path_code,
        'registry_pin': copy.deepcopy(registry_pin),
        'recipe_id': RECIPE, 'registered_seed_consumed': False,
        'source': normalized_source,
        'runtime_candidate': copy.deepcopy(runtime),
        'budget_candidate': copy.deepcopy(budget_candidate),
        'identity_plan_sha256': v.canonical_sha256(identities),
        'chunk_identity_hashes_sha256': v.canonical_sha256(
            [row['identities_sha256'] for row in chunks]),
        'chunks': chunks, 'chunks_sha256': v.canonical_sha256(chunks),
        'planned_counts': {'seeds': 40, 'layouts_per_seed': 12,
                           'strata_per_layout': 2, 'candidates_per_stratum': 3,
                           'chunks': 480, 'evaluations': 2880},
        'invented_only': True,
        'actual_registered_observations_read': False,
        'campaign_evaluations_credited': 0,
        'campaign_coherence_authenticated': False,
        'campaign_completed': False,
        'launch_authorized': False,
        'resume_authorized': False,
        'full_end_to_end_budget_measured': False,
        'formal_permission': False, 'analysis_authorized': False,
        'promotion_allowed': False, 'independent_s6_complete': False,
    }
    v.require(len(v.canonical_json(result)) + 1 <= MAX_PLAN_BYTES,
              'campaign plan byte bound')
    return result


def validate_plan(plan):
    _keys(plan, PLAN_FIELDS, 'campaign plan')
    wanted = fixed_plan(plan['campaign_id'], plan['root'], plan['path_code'],
                        plan['registry_pin'], plan['source'],
                        plan['runtime_candidate'], plan['budget_candidate'])
    _same(plan, wanted, 'frozen invented campaign plan changed')
    return plan


def encode_plan(plan):
    validate_plan(plan)
    return v.canonical_json(plan) + b'\n'


def _blank_evidence():
    return {name: None for name in EVIDENCE_NAMES}


def make_record(plan_pin, previous_sha256, sequence, chunk_index, attempt,
                state, attempt_path, manifest_pin, *, source_revision,
                runtime_tuple_sha256, evidence_pins=None,
                saved_output_pins=None, reason=None):
    """Construct a declaration; reduce_journal checks its history."""
    return {
        'format': RECORD_FORMAT, 'anchor_pin': copy.deepcopy(plan_pin),
        'previous_sha256': previous_sha256, 'sequence': sequence,
        'chunk_index': chunk_index, 'attempt': attempt,
        'attempt_root': attempt_path, 'state': state,
        'manifest_pin': copy.deepcopy(manifest_pin),
        'source_revision': source_revision,
        'runtime_tuple_sha256': runtime_tuple_sha256,
        'evidence_pins': copy.deepcopy(
            _blank_evidence() if evidence_pins is None else evidence_pins),
        'saved_output_pins': copy.deepcopy(saved_output_pins),
        'reason': reason,
    }


def encode_record(record):
    v.require(type(record) is dict, 'campaign record object')
    raw = v.canonical_json(record) + b'\n'
    v.require(len(raw) <= MAX_RECORD_BYTES, 'campaign record byte bound')
    return raw


def _output_names(chunk_index):
    identities = v.evaluation_inventory('holdout')[chunk_index * 6:
                                                   chunk_index * 6 + 6]
    names = {'saved/receipt.json', 'saved/report.json',
             'saved/savepoint.json', 'saved/registry.json'}
    for identity in identities:
        names.add(saved._payload_path(identity))
        for kind in input_contract.INPUT_HASHES:
            names.add(saved._payload_path(identity, kind))
    v.require(len(names) == 22, 'frozen saved output inventory')
    return names


def _record(record, plan, plan_pin, sequence, previous):
    _keys(record, {'format', 'anchor_pin', 'previous_sha256', 'sequence',
                   'chunk_index', 'attempt', 'attempt_root', 'state',
                   'manifest_pin', 'source_revision', 'runtime_tuple_sha256',
                   'evidence_pins', 'saved_output_pins', 'reason'},
          'campaign record')
    _same([record['format'], record['anchor_pin'], record['previous_sha256'],
           record['sequence']], [RECORD_FORMAT, plan_pin, previous, sequence],
          'campaign record chain/anchor/sequence')
    index, attempt = record['chunk_index'], record['attempt']
    v.require(type(index) is int and 0 <= index < 480,
              'campaign record chunk index')
    v.require(type(attempt) is int and 1 <= attempt <= MAX_ATTEMPTS,
              'campaign record attempt')
    _same(record['attempt_root'], attempt_root(plan, index, attempt),
          'derived sibling attempt root')
    _pin(record['manifest_pin'], 'prelaunch manifest')
    _same(record['source_revision'], plan['source']['revision'],
          'campaign source revision')
    _same(record['runtime_tuple_sha256'],
          plan['runtime_candidate']['tuple_sha256'],
          'campaign runtime tuple digest')
    state = record['state']
    v.require(type(state) is str and state in ('started', 'completed', 'failed'),
              'campaign record state')
    pins = record['evidence_pins']
    _keys(pins, EVIDENCE_NAMES, 'attempt evidence pins')
    for name, item in pins.items():
        if item is not None:
            _pin(item, name)
    outputs = record['saved_output_pins']
    if outputs is not None:
        v.require(type(outputs) is dict and
                  set(outputs) <= _output_names(index),
                  'saved output pin names')
        for name, item in outputs.items():
            v.safe_relative_path(name)
            _pin(item, 'saved output ' + name)
    if state == 'started':
        v.require(all(item is None for item in pins.values()) and
                  outputs is None and record['reason'] is None,
                  'started record must precede execution evidence')
    elif state == 'completed':
        v.require(all(item is not None for item in pins.values()) and
                  outputs is not None and set(outputs) == _output_names(index)
                  and record['reason'] is None,
                  'completed declaration requires exact saved evidence pins')
        _same(pins['rows'], pins['fresh_reread_rows'],
              'fresh reread row pin selection')
        for label, name in (
            ('saved_receipt', 'saved/receipt.json'),
            ('saved_report', 'saved/report.json'),
            ('saved_savepoint', 'saved/savepoint.json'),
            ('saved_registry', 'saved/registry.json'),
        ):
            _same(pins[label], outputs[name],
                  'completed saved control pin ' + label)
        _same(outputs['saved/registry.json'], plan['registry_pin'],
              'completed frozen registry pin')
    else:
        v.require(type(record['reason']) is str and
                  record['reason'] in ('worker_exit', 'resource_limit',
                    'integrity', 'interrupted', 'verification_failed',
                    'source_runtime_changed'),
                  'classified failed attempt reason')


def reduce_journal(plan_raw, record_raws, *, expected_plan_pin,
                   expected_record_count, expected_head_sha256):
    """Validate an externally pinned raw history; report declarations only."""
    _pin(expected_plan_pin, 'external plan')
    v.require(type(plan_raw) is bytes and
              0 < len(plan_raw) <= MAX_PLAN_BYTES and
              pin(plan_raw) == expected_plan_pin,
              'external plan bytes/SHA mismatch')
    plan = v.strict_json(plan_raw)
    v.require(type(plan) is dict and plan_raw == encode_plan(plan),
              'canonical LF plan required')
    v.require(type(expected_record_count) is int and
              0 <= expected_record_count <= MAX_RECORDS,
              'external record count')
    _hex(expected_head_sha256, 64, 'external journal head')
    v.require(type(record_raws) is list and
              len(record_raws) == expected_record_count,
              'journal count/truncation')
    previous = expected_plan_pin['sha256']
    next_index = 0
    current = None
    completed = []
    failed_attempts = 0
    seen_roots = set()
    total_bytes = 0
    for sequence, raw in enumerate(record_raws, 1):
        v.require(type(raw) is bytes and 0 < len(raw) <= MAX_RECORD_BYTES,
                  'bounded raw journal record')
        total_bytes += len(raw)
        v.require(total_bytes <= MAX_TOTAL_RECORD_BYTES,
                  'journal aggregate byte bound')
        record = v.strict_json(raw)
        v.require(raw == encode_record(record),
                  'canonical LF journal record required')
        _record(record, plan, expected_plan_pin, sequence, previous)
        index, attempt, state = (record['chunk_index'], record['attempt'],
                                 record['state'])
        v.require(index == next_index,
                  'campaign chunk gap/duplicate/reverse order')
        if current is None or current['state'] == 'failed':
            wanted_attempt = 1 if current is None else current['attempt'] + 1
            v.require(state == 'started' and attempt == wanted_attempt and
                      (current is None or current['reason'] not in
                       ('integrity', 'source_runtime_changed')),
                      'new attempt must follow allowed failure')
            v.require(record['attempt_root'].casefold() not in seen_roots,
                      'reused attempt root')
            seen_roots.add(record['attempt_root'].casefold())
        else:
            v.require(current['state'] == 'started' and
                      state in ('completed', 'failed') and
                      attempt == current['attempt'],
                      'invalid attempt state transition')
            for name in ('attempt_root', 'manifest_pin', 'source_revision',
                         'runtime_tuple_sha256'):
                _same(record[name], current[name],
                      'attempt context changed: ' + name)
        if state == 'completed':
            completed.append(index)
            next_index += 1
            current = None
        else:
            if state == 'failed':
                failed_attempts += 1
            current = record
        previous = hashlib.sha256(raw).hexdigest()
    v.require(previous == expected_head_sha256,
              'external journal head mismatch')
    missing = list(range(next_index, 480))
    return {
        'format': OUTPUT_FORMAT, 'scope': SCOPE,
        'mode': 'preformal-fixture', 'invented_only': True,
        'status': 'declarations_complete_unverified' if not missing else
                  'partial_declarations_unverified',
        'plan_pin': copy.deepcopy(expected_plan_pin),
        'record_count': expected_record_count,
        'head_sha256': previous,
        'declared_completed_chunks': len(completed),
        'declared_completed_evaluations': 6 * len(completed),
        'completed_chunk_indices': completed,
        'missing_chunk_indices': missing,
        'failed_attempt_count': failed_attempts,
        'next_chunk_index': next_index if missing else None,
        'latest_unfinished_state': current['state'] if current else None,
        'producer_campaign_anchor': None,
        'campaign_coherence_authenticated': False,
        'producer_execution_authenticated': False,
        'saved_payload_bytes_verified': False,
        'source_closure_complete': False,
        'runtime_closure_complete': False,
        'full_end_to_end_budget_measured': False,
        'launch_authorized': False,
        'resume_authorized': False,
        'clusters': None, 'diagnostics': None, 'slice_source': None,
        'actual_registered_observations_read': False,
        'registered_seed_consumed': False,
        'campaign_evaluations_credited': 0,
        'campaign_completed': False,
        'formal_permission': False, 'analysis_authorized': False,
        'promotion_allowed': False, 'independent_s6_complete': False,
    }
