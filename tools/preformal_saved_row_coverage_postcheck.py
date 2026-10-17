"""Independently check the retained invented saved-row coverage receipt.

Only the ten small, externally pinned JSON records are reopened.  This does
not reread the saved observation/evaluation payloads or authenticate a shared
producer campaign.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat


ROOT = Path(__file__).resolve().parents[1]
PINSET = ROOT / 'artifacts/anomaly-v03-preformal-saved-row-coverage-pins-01/pins.json'
COVERAGE = ROOT / 'artifacts/anomaly-v03-preformal-saved-row-coverage-02/result.json'
OUTPUT = ROOT / 'artifacts/anomaly-v03-preformal-saved-row-coverage-postcheck-01/postcheck-result.json'
PINSET_PIN = {'bytes': 2078, 'sha256': '7e98a4b8e4c2a2475252ddc41f2327f7fac8aadf346f42eef23dd95fa2c5a013'}
SOURCES = {
    'result': 'artifacts/anomaly-v03-preformal-saved-row-reread-r01/result.json',
    'rows': 'artifacts/anomaly-v03-preformal-saved-row-reread-r01/rows.json',
    'budget': 'artifacts/anomaly-v03-preformal-saved-row-reread-r01/resource-budget.json',
    'supervision': 'artifacts/anomaly-v03-preformal-saved-row-reread-r01/owned-reader/supervision.json',
    'stdout': 'artifacts/anomaly-v03-preformal-saved-row-reread-r01/owned-reader/worker/report.json',
    'manifest': 'artifacts/anomaly-v03-preformal-generated-pinsets-g02/pins.json',
    'receipt': 'artifacts/anomaly-v03-preformal-registered-attempt-g02/saved/receipt.json',
    'report': 'artifacts/anomaly-v03-preformal-registered-attempt-g02/saved/report.json',
    'savepoint': 'artifacts/anomaly-v03-preformal-registered-attempt-g02/saved/savepoint.json',
    'outer': 'artifacts/anomaly-v03-preformal-registered-attempt-g02/owned-generator/result.json',
}
MAX_JSON = 1024 * 1024


def need(ok: bool, label: str) -> None:
    if not ok:
        raise ValueError(label)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def pin(raw: bytes) -> dict:
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def read_json(path: Path, expected: dict, label: str, *, canonical_required: bool = True) -> dict:
    need(type(expected) is dict and set(expected) == {'bytes', 'sha256'} and
         type(expected['bytes']) is int and 0 < expected['bytes'] <= MAX_JSON and
         type(expected['sha256']) is str and
         re.fullmatch(r'[0-9a-f]{64}', expected['sha256']) is not None,
         label + ' expected pin')
    meta = path.lstat()
    need(stat.S_ISREG(meta.st_mode) and
         not getattr(meta, 'st_file_attributes', 0) & 0x400 and
         meta.st_nlink == 1 and meta.st_size == expected['bytes'],
         label + ' bounded regular file')
    raw = path.read_bytes()
    need(pin(raw) == expected, label + ' raw pin')
    value = json.loads(raw)
    need(type(value) is dict and
         (not canonical_required or canonical(value) == raw),
         label + ' JSON object/canonical bytes')
    return value


def exact(value: dict, expected: dict, label: str) -> None:
    need(type(value) is dict and all(type(value.get(key)) is type(wanted) and
         value.get(key) == wanted for key, wanted in expected.items()), label)


def cli_pin(value: str) -> dict:
    match = re.fullmatch(r'([1-9][0-9]*):([0-9a-f]{64})', value)
    if match is None or int(match.group(1)) > 64 * 1024:
        raise argparse.ArgumentTypeError('expected bounded bytes:sha256')
    return {'bytes': int(match.group(1)), 'sha256': match.group(2)}


def run(coverage_pin: dict) -> dict:
    need(not OUTPUT.parent.exists(), 'postcheck output root already exists')
    pinset = read_json(PINSET, PINSET_PIN, 'external coverage pinset')
    exact(pinset, {'format': 'anomaly-v03-preformal-saved-row-coverage-input-pins-v1',
                   'invented_only': True, 'formal_permission': False},
          'external coverage scope')
    need(set(pinset) == {'format', 'invented_only', 'formal_permission', 'entries'} and
         type(pinset['entries']) is list and len(pinset['entries']) == 1,
         'one external entry')
    entry = pinset['entries'][0]
    need(type(entry) is dict and set(entry) == {'chunk_index', 'files'} and
         type(entry['chunk_index']) is int and entry['chunk_index'] == 0 and
         type(entry['files']) is dict and set(entry['files']) == set(SOURCES),
         'one exact ten-file inventory')
    documents = {}
    source_pins = {}
    for name, relative in SOURCES.items():
        descriptor = entry['files'][name]
        need(type(descriptor) is dict and set(descriptor) == {'path', 'pin'} and
             descriptor['path'] == relative, 'external path ' + name)
        source_pins[name] = descriptor['pin']
        documents[name] = read_json(ROOT / relative, descriptor['pin'],
                                    'external ' + name,
                                    canonical_required=name != 'stdout')
    result = read_json(COVERAGE, coverage_pin, 'coverage result')
    reread = documents['result']; rows = documents['rows']
    manifest = documents['manifest']; receipt = documents['receipt']
    report = documents['report']; savepoint = documents['savepoint']
    outer = documents['outer']; budget = documents['budget']
    supervision = documents['supervision']; stdout = documents['stdout']

    exact(result, {
        'format': 'anomaly-v03-preformal-saved-row-coverage-v1',
        'mode': 'preformal-fixture', 'invented_only': True,
        'status': 'partial_coverage_unanchored',
        'scope': 'pinned-invented-saved-row-reread-coverage-only',
        'planned_chunks': 480, 'planned_evaluations': 2880,
        'bound_chunks': 1, 'bound_evaluations': 6,
        'chunk_indices': [0], 'missing_chunk_indices': list(range(1, 480)),
        'per_chunk_savepoint_pins_checked': True,
        'cross_chunk_recipe_source_consistency_checked': False,
        'pinned_reread_receipts_checked': True,
        'saved_payload_bytes_reopened_here': False,
        'reader_execution_authenticated_here': False,
        'producer_campaign_anchor': None,
        'campaign_coherence_authenticated': False,
        'clusters': None, 'diagnostics': None, 'slice_source': None,
        'registered_observations_read': False,
        'actual_registered_observations_read': False,
        'campaign_evaluations_credited': 0,
        'formal_permission': False, 'analysis_authorized': False,
        'promotion_allowed': False, 'independent_s6_complete': False,
        'external_pinset_pin': PINSET_PIN,
    }, 'incomplete coverage and closed formal scope')
    need(set(result) == {'format', 'mode', 'invented_only', 'status', 'scope',
                         'planned_chunks', 'planned_evaluations', 'bound_chunks',
                         'bound_evaluations', 'chunk_indices', 'missing_chunk_indices',
                         'chunks', 'per_chunk_savepoint_pins_checked',
                         'cross_chunk_recipe_source_consistency_checked',
                         'pinned_reread_receipts_checked',
                         'saved_payload_bytes_reopened_here',
                         'reader_execution_authenticated_here',
                         'producer_campaign_anchor',
                         'campaign_coherence_authenticated', 'clusters',
                         'diagnostics', 'slice_source',
                         'registered_observations_read',
                         'actual_registered_observations_read',
                         'campaign_evaluations_credited', 'formal_permission',
                         'analysis_authorized', 'promotion_allowed',
                         'independent_s6_complete', 'external_pinset_pin'},
         'exact coverage result fields')

    outputs = manifest['output_pins']
    exact(manifest, {'format': 'anomaly-v03-preformal-owned-generated-external-pins-v1',
                     'scope': 'invented-registered-format-owned-generator-only',
                     'chunk_index': 0, 'invented_only': True,
                     'actual_registered_observations_read': False,
                     'formal_permission': False, 'output_file_count': 22},
          'invented manifest scope')
    need(type(outputs) is dict and len(outputs) == 22 and
         manifest['output_bytes'] == sum(value['bytes'] for value in outputs.values()),
         'manifest inventory count and bytes')
    for name, key in (('saved/receipt.json', 'receipt'),
                      ('saved/report.json', 'report'),
                      ('saved/savepoint.json', 'savepoint')):
        need(outputs[name] == source_pins[key], 'manifest ' + key + ' pin')
    exact(savepoint, {'format': 'anomaly-v03-preformal-invented-partial-savepoint-v1',
                      'chunk_index': 0, 'invented_only': True,
                      'campaign_completed': False,
                      'actual_registered_observations_read': False},
          'incomplete invented savepoint')
    exact(receipt, {'chunk_index': 0, 'invented_only': True,
                    'savepoint_pin': source_pins['savepoint'],
                    'registry_pin': outputs['saved/registry.json']},
          'receipt links')
    exact(report, {'chunk_index': 0, 'invented_only': True,
                   'receipt_pin': source_pins['receipt'],
                   'savepoint_pin': source_pins['savepoint'],
                   'registry_pin': outputs['saved/registry.json']},
          'report links')
    exact(outer, {'status': 'verified', 'reason': None,
                  'generated_output_pins': outputs,
                  'recipe_id': manifest['recipe_id'],
                  'owned_fixture_generator_exit_confirmed': True,
                  'owned_fixture_reader_exit_confirmed': True,
                  'actual_registered_observations_read': False,
                  'formal_permission': False,
                  'campaign_evaluations_credited': 0}, 'prior two-role result')
    exact(reread, {
        'format': 'anomaly-v03-preformal-saved-row-reread-v1',
        'status': 'verified', 'chunk_index': 0,
        'manifest_pin': source_pins['manifest'],
        'row_projection_pin': source_pins['rows'],
        'old_outer_result_pin': source_pins['outer'],
        'receipt_pin': source_pins['receipt'],
        'report_pin': source_pins['report'],
        'resource_budget_pin': source_pins['budget'],
        'reader_supervision_pin': source_pins['supervision'],
        'child_stdout_pin': source_pins['stdout'],
        'historic_source_revision': manifest['revision'],
        'source_root': manifest['root'],
        'verified_chunks': 1, 'verified_evaluations': 6,
        'budget_passed': True, 'child_exit_confirmed': True,
        'fresh_reader_equal_prior_reader': True,
        'fresh_saved_payload_bytes_rechecked_this_run': True,
        'row_projection_in_same_budget': True,
        'campaign_completed': False,
        'actual_registered_observations_read': False,
        'formal_permission': False,
        'campaign_evaluations_credited': 0,
    }, 'fresh reread links')
    exact(budget, {'passed': True, 'monitor_exit_confirmed': True,
                   'formal_permission': False, 'stop_reason': None},
          'fresh reread budget')
    exact(supervision, {'status': 'complete', 'exit_code': 0,
                        'worker_exit_confirmed': True,
                        'worker_pid': reread['child_pid'],
                        'output': source_pins['stdout'],
                        'formal_permission': False},
          'fresh reader supervision')
    exact(stdout, {'status': 'read', 'manifest_pin': source_pins['manifest'],
                   'output_pins': outputs,
                   'reader_result': outer['reader_result'],
                   'formal_permission': False,
                   'actual_registered_observations_read': False},
          'fresh reader stdout')

    exact(rows, {'format': 'anomaly-v03-registered-saved-row-lineage-v1',
                 'status': 'fixture_rows_bound_partial',
                 'chunk_index': 0, 'registered_seed_index': 0,
                 'verified_layout': 0, 'verified_chunks': 1,
                 'verified_evaluations': 6, 'planned_chunks': 480,
                 'planned_evaluations': 2880,
                 'receipt_pin': source_pins['receipt'],
                 'report_pin': source_pins['report'],
                 'outer_result_pin': source_pins['outer'],
                 'clusters': None, 'diagnostics': None,
                 'slice_source': None,
                 'actual_registered_observations_read': False,
                 'formal_permission': False, 'analysis_authorized': False,
                 'promotion_allowed': False,
                 'independent_s6_complete': False,
                 'campaign_evaluations_credited': 0},
          'one saved-row projection')
    attempts = receipt['attempts']
    reported_rows = report['rows']
    projected_rows = rows['rows']
    need(type(attempts) is list and len(attempts) == 1 and
         attempts[0]['state'] == 'complete' and
         attempts[0]['attempt'] == report['attempt'] == rows['latest_attempt'] == 1 and
         type(attempts[0]['evaluations']) is list and
         type(reported_rows) is list and type(projected_rows) is list and
         len(attempts[0]['evaluations']) == len(reported_rows) ==
         len(projected_rows) == 6,
         'one complete latest attempt and six rows')
    expected_order = [(layer, candidate)
                      for layer in ('core', 'quality-stress')
                      for candidate in ('c0-diff-control', 'c1-phase-level',
                                        'c2-phase-conditional')]
    for index, (row, old, slot) in enumerate(zip(
            projected_rows, reported_rows, attempts[0]['evaluations'])):
        identity = old['identity']
        layer, candidate = expected_order[index]
        exact(identity, {'role': 'holdout', 'seed': rows['registered_seed'],
                         'layout': 0, 'stratum': layer,
                         'candidate_id': candidate},
              'ordered identity ' + str(index))
        need(identity == slot['identity'], 'receipt identity ' + str(index))
        wanted = {
            'chunk_index': 0, 'registered_seed_index': 0,
            'invented_cluster_id': 'invented-00',
            'identity': identity, 'attempt': 1,
            'status': slot['status'], 'profile_status': slot['profile_status'],
            'input_hashes': old['input_hashes'],
            'evaluation_pin': old['evaluation_pin'],
            'primary': old['primary'], 'slices': old['slices'],
        }
        need(type(row) is dict and set(row) == set(wanted) and row == wanted,
             'exact projected row ' + str(index))
        need(old['evaluation_outcome'] == slot['status'] and
             old['evaluation_pin']['sha256'] == slot['evaluation_sha256'] and
             old['input_hashes'] == slot['input_hashes'] and
             old['evaluation_pin'] in report['payload_pins'].values(),
             'reported saved slot ' + str(index))
    need(len({row['identity']['evaluation_id'] for row in projected_rows}) == 6,
         'distinct evaluation identities')

    expected_chunk = {
        'chunk_index': 0, 'registered_seed_index': 0,
        'registered_seed': rows['registered_seed'], 'layout': 0,
        'latest_attempt': 1, 'source_root': manifest['root'],
        'historic_source_revision': manifest['revision'],
        'recipe_id': manifest['recipe_id'],
        'savepoint_pin': source_pins['savepoint'],
        'result_pin': source_pins['result'],
        'rows_pin': source_pins['rows'],
        'registry_pin': outputs['saved/registry.json'],
    }
    need(type(result['chunks']) is list and len(result['chunks']) == 1 and
         type(result['chunks'][0]) is dict and
         set(result['chunks'][0]) == set(expected_chunk) and
         result['chunks'][0] == expected_chunk,
         'exact saved-row coverage chunk')

    postcheck = {
        'format': 'anomaly-v03-preformal-saved-row-coverage-postcheck-v1',
        'status': 'independent_partial_coverage_postcheck_passed',
        'scope': 'ten-small-pinned-JSON-files-and-one-invented-coverage-result',
        'external_pinset_pin': PINSET_PIN,
        'coverage_result_pin': coverage_pin,
        'source_file_pins': source_pins,
        'files_checked': 10, 'rows_checked': 6,
        'bound_chunks': 1, 'missing_chunks': 479,
        'cluster_input_ready': False,
        'producer_campaign_anchor': None,
        'campaign_coherence_authenticated': False,
        'saved_payload_bytes_reopened_here': False,
        'actual_registered_observations_read': False,
        'formal_permission': False,
        'independent_s6_complete': False,
        'campaign_evaluations_credited': 0,
    }
    OUTPUT.parent.mkdir()
    with OUTPUT.open('xb') as handle:
        handle.write(canonical(postcheck))
    need(len(OUTPUT.read_bytes()) <= 8 * 1024, 'small postcheck receipt')
    return postcheck


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result-pin', required=True, type=cli_pin)
    args = parser.parse_args()
    value = run(args.result_pin)
    print(json.dumps({'status': value['status'], 'rows_checked': 6,
                      'output': str(OUTPUT),
                      'output_pin': pin(OUTPUT.read_bytes())}, sort_keys=True))


if __name__ == '__main__':
    main()
