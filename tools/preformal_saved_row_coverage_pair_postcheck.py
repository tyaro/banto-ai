"""Independently check the retained c001/c011 invented coverage receipt.

This reopens only the twenty small externally pinned control JSON files.  It
does not reread saved evaluation payloads or authenticate a common campaign.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts'
PINSET_FORMAT = 'anomaly-v03-preformal-saved-row-coverage-pair-input-pins-v1'
COVERAGE_FORMAT = 'anomaly-v03-preformal-saved-row-coverage-v1'
SEED = 2792161106071485543
SLOTS = ((0, 'c001'), (1, 'c011'))
NAMES = ('result', 'rows', 'budget', 'supervision', 'stdout', 'manifest',
         'receipt', 'report', 'savepoint', 'outer')
ORDER = tuple((layer, candidate)
              for layer in ('core', 'quality-stress')
              for candidate in ('c0-diff-control', 'c1-phase-level',
                                'c2-phase-conditional'))
MAX_CONTROL = 1024 * 1024


def need(condition: bool, label: str) -> None:
    if not condition:
        raise ValueError(label)


def pin(raw: bytes) -> dict:
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def pin_arg(value: str) -> dict:
    match = re.fullmatch(r'([1-9][0-9]*):([0-9a-f]{64})', value)
    if match is None or int(match.group(1)) > MAX_CONTROL:
        raise argparse.ArgumentTypeError('expected bounded bytes:sha256')
    return {'bytes': int(match.group(1)), 'sha256': match.group(2)}


def _object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        need(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def _constant(value: str) -> object:
    raise ValueError('nonfinite JSON number: ' + value)


def read_json(path: Path, expected: dict, label: str, maximum: int,
              *, canonical_required: bool = True) -> dict:
    need(type(expected) is dict and set(expected) == {'bytes', 'sha256'} and
         type(expected['bytes']) is int and 0 < expected['bytes'] <= maximum and
         type(expected['sha256']) is str and
         re.fullmatch(r'[0-9a-f]{64}', expected['sha256']) is not None,
         label + ' expected pin')
    metadata = path.lstat()
    need(stat.S_ISREG(metadata.st_mode) and
         not (getattr(metadata, 'st_file_attributes', 0) & 0x400) and
         metadata.st_nlink == 1 and metadata.st_size == expected['bytes'],
         label + ' bounded regular file')
    raw = path.read_bytes()
    need(pin(raw) == expected, label + ' raw pin')
    value = json.loads(raw, object_pairs_hook=_object, parse_constant=_constant)
    need(type(value) is dict and
         (not canonical_required or canonical(value) == raw),
         label + ' JSON object/canonical bytes')
    return value


def exact(value: dict, expected: dict, label: str) -> None:
    need(type(value) is dict and all(type(value.get(key)) is type(wanted) and
         value.get(key) == wanted for key, wanted in expected.items()), label)


def sources(suffix: str) -> dict[str, str]:
    reread = 'artifacts/anomaly-v03-preformal-saved-row-reread-' + suffix
    generated = 'artifacts/anomaly-v03-preformal-generated-pinsets-' + suffix
    attempt = 'artifacts/anomaly-v03-preformal-registered-attempt-' + suffix
    return {
        'result': reread + '/result.json',
        'rows': reread + '/rows.json',
        'budget': reread + '/resource-budget.json',
        'supervision': reread + '/owned-reader/supervision.json',
        'stdout': reread + '/owned-reader/worker/report.json',
        'manifest': generated + '/pins.json',
        'receipt': attempt + '/saved/receipt.json',
        'report': attempt + '/saved/report.json',
        'savepoint': attempt + '/saved/savepoint.json',
        'outer': attempt + '/owned-generator/result.json',
    }


def _identity(layout: int, layer: str, candidate: str) -> dict:
    pair = f'anomaly-v03-holdout-seed-{SEED}-layout-{layout:02d}'
    dataset = f'{pair}-{layer}'
    return {'role': 'holdout', 'seed': SEED, 'layout': layout,
            'stratum': layer, 'candidate_id': candidate, 'pair_id': pair,
            'dataset_id': dataset, 'evaluation_id': f'{dataset}-{candidate}'}


def _check_chunk(index: int, files: dict, docs: dict, chunk: dict) -> tuple:
    refs = {name: files[name]['pin'] for name in NAMES}
    reread = docs['result']; rows = docs['rows']; manifest = docs['manifest']
    receipt = docs['receipt']; report = docs['report']; savepoint = docs['savepoint']
    budget = docs['budget']; supervision = docs['supervision']
    stdout = docs['stdout']; outer = docs['outer']
    outputs = manifest.get('output_pins')
    need(type(outputs) is dict and len(outputs) == 22 and
         manifest.get('output_file_count') == 22 and
         manifest.get('output_bytes') == sum(value['bytes'] for value in outputs.values()),
         f'chunk {index} 22 saved output pins')
    exact(manifest, {'format': 'anomaly-v03-preformal-owned-generated-external-pins-v1',
                     'scope': 'invented-registered-format-owned-generator-only',
                     'chunk_index': index, 'invented_only': True,
                     'actual_registered_observations_read': False,
                     'formal_permission': False}, f'chunk {index} manifest scope')
    for path, name in (('saved/receipt.json', 'receipt'),
                       ('saved/report.json', 'report'),
                       ('saved/savepoint.json', 'savepoint')):
        need(outputs.get(path) == refs[name], f'chunk {index} manifest {name} pin')
    exact(savepoint, {'chunk_index': index, 'invented_only': True,
                      'campaign_completed': False,
                      'actual_registered_observations_read': False},
          f'chunk {index} incomplete savepoint')
    exact(receipt, {'chunk_index': index, 'invented_only': True,
                    'savepoint_pin': refs['savepoint'],
                    'registry_pin': outputs['saved/registry.json']},
          f'chunk {index} receipt links')
    exact(report, {'chunk_index': index, 'invented_only': True,
                   'receipt_pin': refs['receipt'], 'savepoint_pin': refs['savepoint'],
                   'registry_pin': outputs['saved/registry.json']},
          f'chunk {index} report links')
    exact(outer, {'status': 'verified', 'reason': None,
                  'generated_output_pins': outputs,
                  'recipe_id': manifest['recipe_id'],
                  'owned_fixture_generator_exit_confirmed': True,
                  'owned_fixture_reader_exit_confirmed': True,
                  'actual_registered_observations_read': False,
                  'formal_permission': False,
                  'campaign_evaluations_credited': 0},
          f'chunk {index} prior two-role result')
    exact(reread, {'format': 'anomaly-v03-preformal-saved-row-reread-v1',
                   'status': 'verified', 'chunk_index': index,
                   'manifest_pin': refs['manifest'],
                   'row_projection_pin': refs['rows'],
                   'old_outer_result_pin': refs['outer'],
                   'receipt_pin': refs['receipt'], 'report_pin': refs['report'],
                   'resource_budget_pin': refs['budget'],
                   'reader_supervision_pin': refs['supervision'],
                   'child_stdout_pin': refs['stdout'],
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
                   'campaign_evaluations_credited': 0},
          f'chunk {index} fresh reread links')
    exact(budget, {'passed': True, 'monitor_exit_confirmed': True,
                   'formal_permission': False, 'stop_reason': None},
          f'chunk {index} fresh budget')
    exact(supervision, {'status': 'complete', 'exit_code': 0,
                        'worker_exit_confirmed': True,
                        'worker_pid': reread['child_pid'],
                        'output': refs['stdout'], 'formal_permission': False},
          f'chunk {index} fresh supervision')
    exact(stdout, {'status': 'read', 'manifest_pin': refs['manifest'],
                   'output_pins': outputs,
                   'reader_result': outer['reader_result'],
                   'formal_permission': False,
                   'actual_registered_observations_read': False},
          f'chunk {index} fresh reader stdout')
    exact(rows, {'format': 'anomaly-v03-registered-saved-row-lineage-v1',
                 'status': 'fixture_rows_bound_partial', 'chunk_index': index,
                 'registered_seed_index': 0, 'registered_seed': SEED,
                 'verified_layout': index, 'latest_attempt': 1,
                 'verified_chunks': 1, 'verified_evaluations': 6,
                 'planned_chunks': 480, 'planned_evaluations': 2880,
                 'receipt_pin': refs['receipt'], 'report_pin': refs['report'],
                 'outer_result_pin': refs['outer'],
                 'clusters': None, 'diagnostics': None, 'slice_source': None,
                 'actual_registered_observations_read': False,
                 'formal_permission': False, 'analysis_authorized': False,
                 'promotion_allowed': False, 'independent_s6_complete': False,
                 'campaign_evaluations_credited': 0},
          f'chunk {index} saved rows')
    attempts = receipt.get('attempts')
    projected = rows.get('rows'); reported = report.get('rows')
    need(type(attempts) is list and len(attempts) == 1 and
         attempts[0]['state'] == 'complete' and attempts[0]['attempt'] == 1 and
         report.get('attempt') == 1 and type(projected) is list and
         type(reported) is list and len(projected) == len(reported) == 6 and
         type(attempts[0]['evaluations']) is list and
         len(attempts[0]['evaluations']) == 6,
         f'chunk {index} complete six-slot attempt')
    identities = []
    for slot_index, ((layer, candidate), row, old, slot) in enumerate(zip(
            ORDER, projected, reported, attempts[0]['evaluations'])):
        identity = _identity(index, layer, candidate)
        need(old['identity'] == slot['identity'] == row['identity'] == identity,
             f'chunk {index} frozen row identity {slot_index}')
        expected_row = {
            'chunk_index': index, 'registered_seed_index': 0,
            'invented_cluster_id': 'invented-00', 'identity': identity,
            'attempt': 1, 'status': slot['status'],
            'profile_status': slot['profile_status'],
            'input_hashes': old['input_hashes'],
            'evaluation_pin': old['evaluation_pin'],
            'primary': old['primary'], 'slices': old['slices'],
        }
        need(type(row) is dict and row == expected_row and
             old['evaluation_outcome'] == slot['status'] and
             old['evaluation_pin']['sha256'] == slot['evaluation_sha256'] and
             old['input_hashes'] == slot['input_hashes'] and
             old['evaluation_pin'] in report['payload_pins'].values(),
             f'chunk {index} saved row/receipt {slot_index}')
        identities.append(identity['evaluation_id'])
    expected_chunk = {
        'chunk_index': index, 'registered_seed_index': 0,
        'registered_seed': SEED, 'layout': index, 'latest_attempt': 1,
        'source_root': manifest['root'],
        'historic_source_revision': manifest['revision'],
        'recipe_id': manifest['recipe_id'], 'savepoint_pin': refs['savepoint'],
        'result_pin': refs['result'], 'rows_pin': refs['rows'],
        'registry_pin': outputs['saved/registry.json'],
    }
    need(type(chunk) is dict and chunk == expected_chunk,
         f'chunk {index} coverage projection')
    return (tuple(identities), (manifest['revision'], manifest['recipe_id'],
                               outputs['saved/registry.json'], manifest['source'],
                               manifest['source_snapshots'],
                               manifest['source_snapshot_pins']))


def _artifact_path(value: str, label: str) -> Path:
    path = Path(value)
    need(path.is_absolute() and ARTIFACTS.resolve() in path.resolve().parents,
         label + ' absolute artifact path')
    return path


def run(pinset_path: Path, pinset_pin: dict, result_path: Path,
        result_pin: dict, output_root: Path) -> dict:
    need(output_root.parent == ARTIFACTS and not output_root.exists(),
         'fresh direct artifact output root')
    pinset = read_json(pinset_path, pinset_pin, 'external pair pinset', 16 * 1024)
    exact(pinset, {'format': PINSET_FORMAT, 'invented_only': True,
                   'formal_permission': False}, 'external pair scope')
    need(set(pinset) == {'format', 'invented_only', 'formal_permission', 'entries'} and
         type(pinset['entries']) is list and len(pinset['entries']) == 2,
         'two external entries')
    result = read_json(result_path, result_pin, 'coverage result', 64 * 1024)
    expected_missing = list(range(2, 480))
    expected_result = {
        'format': COVERAGE_FORMAT, 'mode': 'preformal-fixture',
        'invented_only': True, 'status': 'partial_coverage_unanchored',
        'scope': 'pinned-invented-saved-row-reread-coverage-only',
        'planned_chunks': 480, 'planned_evaluations': 2880,
        'bound_chunks': 2, 'bound_evaluations': 12,
        'chunk_indices': [0, 1], 'missing_chunk_indices': expected_missing,
        'per_chunk_savepoint_pins_checked': True,
        'cross_chunk_recipe_source_consistency_checked': True,
        'pinned_reread_receipts_checked': True,
        'saved_payload_bytes_reopened_here': False,
        'reader_execution_authenticated_here': False,
        'producer_campaign_anchor': None,
        'campaign_coherence_authenticated': False,
        'clusters': None, 'diagnostics': None, 'slice_source': None,
        'registered_observations_read': False,
        'actual_registered_observations_read': False,
        'campaign_evaluations_credited': 0, 'formal_permission': False,
        'analysis_authorized': False, 'promotion_allowed': False,
        'independent_s6_complete': False,
        'external_pinset_pin': pinset_pin,
    }
    exact(result, expected_result, 'incomplete coverage and closed formal scope')
    need(set(result) == set(expected_result) | {'chunks'},
         'exact coverage result fields')
    need(type(result.get('chunks')) is list and len(result['chunks']) == 2,
         'two coverage chunks')
    identities = []
    coherence = []
    source_pins = {}
    for (index, suffix), entry, chunk in zip(SLOTS, pinset['entries'],
                                              result['chunks']):
        need(type(entry) is dict and set(entry) ==
             {'chunk_index', 'attempt', 'files'} and
             type(entry['chunk_index']) is int and entry['chunk_index'] == index and
             type(entry['attempt']) is int and entry['attempt'] == 1 and
             type(entry['files']) is dict and set(entry['files']) == set(NAMES),
             f'chunk {index} exact ten-file inventory')
        expected_paths = sources(suffix)
        docs = {}
        for name, relative in expected_paths.items():
            descriptor = entry['files'][name]
            need(type(descriptor) is dict and set(descriptor) == {'path', 'pin'} and
                 descriptor['path'] == relative,
                 f'chunk {index} frozen {name} path')
            docs[name] = read_json(ROOT / relative, descriptor['pin'],
                                   f'chunk {index} {name}', MAX_CONTROL,
                                   canonical_required=name != 'stdout')
        row_ids, shared = _check_chunk(index, entry['files'], docs, chunk)
        identities.extend(row_ids)
        coherence.append(shared)
        source_pins[str(index)] = {name: entry['files'][name]['pin']
                                   for name in NAMES}
    need(len(identities) == len(set(identities)) == 12,
         'twelve distinct frozen evaluation identities')
    need(coherence[0] == coherence[1], 'cross-chunk source/recipe consistency')
    postcheck = {
        'format': 'anomaly-v03-preformal-saved-row-coverage-pair-postcheck-v1',
        'status': 'independent_partial_coverage_postcheck_passed',
        'scope': 'twenty-small-pinned-JSON-files-and-two-invented-coverage-rows',
        'external_pinset_pin': pinset_pin, 'coverage_result_pin': result_pin,
        'source_file_pins': source_pins,
        'files_checked': 20, 'rows_checked': 12,
        'bound_chunks': 2, 'missing_chunks': 478,
        'cluster_input_ready': False, 'producer_campaign_anchor': None,
        'campaign_coherence_authenticated': False,
        'saved_payload_bytes_reopened_here': False,
        'actual_registered_observations_read': False,
        'formal_permission': False, 'independent_s6_complete': False,
        'campaign_evaluations_credited': 0,
    }
    raw = canonical(postcheck)
    need(len(raw) <= 16 * 1024, 'small postcheck receipt')
    output_root.mkdir()
    output = output_root / 'postcheck-result.json'
    with output.open('xb') as handle:
        handle.write(raw)
    return {'status': postcheck['status'], 'output': str(output),
            'output_pin': pin(raw), 'files_checked': 20, 'rows_checked': 12,
            'missing_chunks': 478}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pinset', required=True)
    parser.add_argument('--pinset-pin', required=True, type=pin_arg)
    parser.add_argument('--result', required=True)
    parser.add_argument('--result-pin', required=True, type=pin_arg)
    parser.add_argument('--output-root', required=True)
    args = parser.parse_args()
    pinset_path = _artifact_path(args.pinset, 'pinset')
    result_path = _artifact_path(args.result, 'coverage result')
    output_root = _artifact_path(args.output_root, 'postcheck output root')
    print(json.dumps(run(pinset_path, args.pinset_pin, result_path,
                         args.result_pin, output_root), sort_keys=True))


if __name__ == '__main__':
    main()
