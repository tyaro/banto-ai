"""Independently check a fresh invented saved-reader/row-projection receipt.

Only small, externally pinned control JSON is opened.  The 131 MB saved
observation payload remains outside this postcheck; the fresh child reader's
own signed-off report is checked as a retained claim, not replayed here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'artifacts/anomaly-v03-preformal-registered-attempt-g02'
PINSET = ROOT / 'artifacts/anomaly-v03-preformal-generated-pinsets-g02/pins.json'
PRIOR_ROWS = ROOT / 'artifacts/anomaly-v03-preformal-saved-row-lineage-01/result.json'
REREAD = ROOT / 'artifacts/anomaly-v03-preformal-saved-row-reread-r01'
OUTPUT = ROOT / 'artifacts/anomaly-v03-preformal-saved-row-reread-postcheck-r01/postcheck-result.json'
PINSET_PIN = {'bytes': 72149, 'sha256': '22ee6888d731c827162b09ef1332cb61fe6a5542372e3e499ea0088fd214f1ef'}
OLD_OUTER_PIN = {'bytes': 10528, 'sha256': '354c8ae043486c8f5ee2a99780ea5ee5a9395ed92daaca790187e8e9ab7c1179'}
PRIOR_ROWS_PIN = {'bytes': 116494, 'sha256': '27fda6488b0487254a85394d7af090dcb9ff7c54903ea5436a814d1eb8a7c621'}
MAX_CONTROL = 1024 * 1024


def need(condition: bool, label: str) -> None:
    if not condition:
        raise ValueError(label)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def pin(raw: bytes) -> dict:
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def check_pin(value: dict, label: str, maximum: int = MAX_CONTROL) -> None:
    need(type(value) is dict and set(value) == {'bytes', 'sha256'} and
         type(value.get('bytes')) is int and 0 < value['bytes'] <= maximum and
         type(value.get('sha256')) is str and
         re.fullmatch(r'[0-9a-f]{64}', value['sha256']) is not None,
         label + ' expected pin')


def read_pinned(path: Path, expected: dict, label: str,
                maximum: int = MAX_CONTROL) -> bytes:
    check_pin(expected, label, maximum)
    info = path.lstat()
    need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and
         not getattr(info, 'st_file_attributes', 0) & 0x400 and
         info.st_size == expected['bytes'], label + ' bounded regular file')
    raw = path.read_bytes()
    need(pin(raw) == expected, label + ' raw pin')
    return raw


def read_json(path: Path, expected: dict, label: str,
              maximum: int = MAX_CONTROL, *, canonical_required: bool = True) -> dict:
    raw = read_pinned(path, expected, label, maximum)
    value = json.loads(raw)
    need(type(value) is dict and
         (not canonical_required or canonical(value) == raw),
         label + ' canonical JSON object')
    return value


def exact(value: dict, fields: dict, label: str) -> None:
    need(type(value) is dict and all(
        key in value and type(value[key]) is type(wanted) and
        value[key] == wanted for key, wanted in fields.items()), label)


def cli_pin(text: str) -> dict:
    match = re.fullmatch(r'([1-9][0-9]*):([0-9a-f]{64})', text)
    if match is None:
        raise argparse.ArgumentTypeError('expected bytes:sha256')
    value = {'bytes': int(match.group(1)), 'sha256': match.group(2)}
    if value['bytes'] > MAX_CONTROL:
        raise argparse.ArgumentTypeError('control JSON exceeds byte bound')
    return value


def run(result_pin: dict, rows_pin: dict, budget_pin: dict) -> dict:
    need(not OUTPUT.parent.exists(), 'new postcheck output root required')
    manifest = read_json(PINSET, PINSET_PIN, 'old external pinset')
    old_outer = read_json(SOURCE / 'owned-generator/result.json', OLD_OUTER_PIN,
                          'old owned reader result')
    old_rows = read_json(PRIOR_ROWS, PRIOR_ROWS_PIN, 'old pinned row lineage')
    result = read_json(REREAD / 'result.json', result_pin, 'fresh reread result')
    rows = read_json(REREAD / 'rows.json', rows_pin, 'fresh row projection')
    budget = read_json(REREAD / 'resource-budget.json', budget_pin,
                       'fresh resource budget')

    exact(manifest, {'root': str(SOURCE), 'chunk_index': 0,
                     'output_file_count': 22, 'invented_only': True,
                     'actual_registered_observations_read': False,
                     'formal_permission': False}, 'old external pinset scope')
    output_pins = manifest['output_pins']
    need(type(output_pins) is dict and len(output_pins) == 22 and
         all(type(name) is str for name in output_pins),
         'exact external saved inventory')
    for name, expected in output_pins.items():
        check_pin(expected, 'external saved ' + name, 32 * 1024 * 1024)
    need(manifest['output_bytes'] == sum(value['bytes'] for value in output_pins.values()),
         'external saved payload byte total')
    exact(old_outer, {'status': 'verified', 'generated_output_pins': output_pins,
                      'owned_fixture_reader_exit_confirmed': True,
                      'actual_registered_observations_read': False,
                      'formal_permission': False,
                      'campaign_evaluations_credited': 0}, 'old reader anchor')
    old_reader = old_outer['reader_result']
    exact(old_reader, {'chunk_index': 0, 'latest_rows_bound': 6,
                       'saved_payload_bytes_verified': True,
                       'observation_to_summary_recomputed': True,
                       'clusters': None, 'diagnostics': None,
                       'slice_source': None, 'formal_permission': False,
                       'campaign_evaluations_credited': 0},
          'old full reader value')

    exact(result, {'format': 'anomaly-v03-preformal-saved-row-reread-v1',
                   'scope': 'one-invented-saved-chunk-reader-to-row-projection',
                   'status': 'verified', 'reason': None,
                   'source_root': str(SOURCE), 'output_root': str(REREAD),
                   'manifest_path': str(PINSET), 'manifest_pin': PINSET_PIN,
                   'old_outer_result_pin': OLD_OUTER_PIN,
                   'chunk_index': 0,
                   'historic_source_revision': manifest['revision'],
                   'external_saved_payload_bytes': manifest['output_bytes'],
                   'receipt_pin': output_pins['saved/receipt.json'],
                   'report_pin': output_pins['saved/report.json'],
                   'row_projection_pin': rows_pin,
                   'row_projection_path': str(REREAD / 'rows.json'),
                   'resource_budget_pin': budget_pin,
                   'budget_passed': True, 'child_status': 'complete',
                   'child_exit_confirmed': True,
                   'external_saved_payload_bytes_in_directory_budget': False,
                   'external_saved_payloads_reopened_in_child': True,
                   'fresh_saved_payload_bytes_rechecked_this_run': True,
                   'fresh_owned_reader_exit_confirmed_here': True,
                   'fresh_reader_equal_prior_reader': True,
                   'row_projection_in_same_budget': True,
                   'verified_chunks': 1, 'verified_evaluations': 6,
                   'source_closure_complete': False,
                   'runtime_closure_complete': False,
                   'execution_authenticated': False, 'result_trusted': False,
                   'campaign_completed': False,
                   'full_end_to_end_budget_measured': False,
                   'registered_observations_read': False,
                   'actual_registered_observations_read': False,
                   'campaign_evaluations_credited': 0,
                   'formal_permission': False, 'analysis_authorized': False,
                   'promotion_allowed': False, 'independent_s6_complete': False},
          'fresh reread scope and pins')
    need(type(result['current_revision']) is str and
         re.fullmatch(r'[0-9a-f]{40}', result['current_revision']) is not None and
         type(result['child_pid']) is int and result['child_pid'] > 0 and
         type(result['child_start_token']) is str and
         bool(result['child_start_token']),
         'fresh source revision and child identity')
    exact(budget, {'format': 'anomaly-v03-fixture-resource-budget-v1',
                   'scope': 'one-fixture-call-and-new-receipt-directory',
                   'shared_root': None, 'passed': True,
                   'monitor_exit_confirmed': True, 'stop_reason': None,
                   'observation_error': None, 'formal_permission': False},
          'fresh independent root resource receipt')
    need(type(budget['samples']) is int and budget['samples'] > 0 and
         type(budget['last']) is dict and
         budget['last']['directory_bytes'] < budget['limits']['directory_bytes'] and
         budget['last']['directory_entries'] < budget['limits']['directory_entries'],
         'fresh bounded budget samples')

    old_projected = dict(old_rows)
    need('retained_two_role_budget' in old_projected,
         'old-only two-role annotation present')
    old_projected.pop('retained_two_role_budget')
    need(rows == old_projected and type(rows.get('rows')) is list and
         len(rows['rows']) == 6,
         'exact six-row prior projection after removing only old budget annotation')
    exact(rows, {'format': 'anomaly-v03-registered-saved-row-lineage-v1',
                 'status': 'fixture_rows_bound_partial',
                 'verified_chunks': 1, 'planned_chunks': 480,
                 'verified_evaluations': 6, 'planned_evaluations': 2880,
                 'receipt_pin': output_pins['saved/receipt.json'],
                 'report_pin': output_pins['saved/report.json'],
                 'outer_result_pin': OLD_OUTER_PIN,
                 'clusters': None, 'diagnostics': None, 'slice_source': None,
                 'saved_payload_bytes_rechecked': False,
                 'reader_execution_authenticated_here': False,
                 'registered_observations_read': False,
                 'actual_registered_observations_read': False,
                 'formal_permission': False, 'analysis_authorized': False,
                 'promotion_allowed': False, 'independent_s6_complete': False,
                 'campaign_evaluations_credited': 0},
          'fresh projection partial scope')

    invocation_pin = result['invocation_pin']
    supervisor_pin = result['reader_supervision_pin']
    stdout_pin = result['child_stdout_pin']
    invocation_path = REREAD / 'owned-reader/invocation.json'
    invocation = read_json(invocation_path, invocation_pin,
                           'fresh child invocation')
    monitor = read_json(REREAD / 'owned-reader/supervision.json', supervisor_pin,
                        'fresh child supervision')
    stdout_raw = read_pinned(REREAD / 'owned-reader/worker/report.json',
                             stdout_pin, 'fresh child stdout')
    reply = json.loads(stdout_raw)
    need(type(reply) is dict and
         stdout_raw.strip() == json.dumps(reply, sort_keys=True).encode('utf-8'),
         'one fresh child JSON stdout')
    exact(invocation, {
        'format': 'anomaly-v03-preformal-saved-row-reread-invocation-v1',
        'source_root': str(SOURCE), 'output_root': str(REREAD),
        'manifest_path': str(PINSET), 'manifest_pin': PINSET_PIN,
        'external_pins': output_pins, 'chunk_index': 0,
        'current_revision': result['current_revision'],
        'current_source': result['selected_current_source'],
        'runtime': result['runtime'],
        'source_snapshots': manifest['source_snapshots'],
    }, 'fresh child invocation binding')
    need(type(invocation['invocation_id']) is str and
         re.fullmatch(r'[0-9a-f]{64}', invocation['invocation_id']) is not None,
         'fresh unique invocation id')
    exact(monitor, {'format': 'anomaly-v03-owned-process-monitor-v1',
                    'status': 'complete', 'exit_code': 0,
                    'worker_pid': result['child_pid'],
                    'worker_started': True,
                    'worker_exit_confirmed': True,
                    'stop_reason': None,
                    'observation_errors': [],
                    'output': stdout_pin,
                    'formal_permission': False},
          'fresh child supervised exit and stdout pin')
    need(type(monitor['argv']) is list and
         monitor['argv'][-2:] == [str(invocation_path), invocation_pin['sha256']] and
         monitor['runtime_before'] == monitor['runtime_after'],
         'fresh child command and stable runtime')
    exact(reply, {
        'format': 'anomaly-v03-preformal-saved-row-reread-child-v1',
        'status': 'read', 'invocation_id': invocation['invocation_id'],
        'source': result['selected_current_source'],
        'runtime': result['runtime'],
        'manifest_pin': PINSET_PIN,
        'output_pins': output_pins,
        'reader_result': old_reader,
        'actual_registered_observations_read': False,
        'formal_permission': False,
    }, 'fresh reader full result matches old pinned reader')
    exact(reply['process'], {'pid': result['child_pid'],
                             'start_token': result['child_start_token']},
          'fresh child start identity')
    need(type(reply['process']['parent_pid']) is int and
         reply['process']['parent_pid'] > 0 and
         reply['process']['parent_pid'] != result['child_pid'],
         'fresh child parent identity')

    receipt = {
        'format': 'anomaly-v03-preformal-saved-row-reread-postcheck-v1',
        'status': 'independent_saved_row_reread_postcheck_passed',
        'scope': 'small pinned control JSON only; external saved payload not reopened',
        'reread_result_pin': result_pin, 'rows_pin': rows_pin,
        'resource_budget_pin': budget_pin,
        'prior_lineage_pin': PRIOR_ROWS_PIN,
        'prior_outer_result_pin': OLD_OUTER_PIN,
        'manifest_pin': PINSET_PIN,
        'invocation_pin': invocation_pin,
        'reader_supervision_pin': supervisor_pin,
        'reader_stdout_pin': stdout_pin,
        'fresh_child_pid': result['child_pid'],
        'fresh_child_exit_confirmed': True,
        'fresh_reader_equal_prior_pinned_reader': True,
        'six_rows_equal_prior_projection': True,
        'budget_passed': True,
        'external_saved_payload_bytes': manifest['output_bytes'],
        'external_saved_payload_bytes_in_directory_budget': False,
        'current_saved_payload_bytes_read_by_postcheck': 0,
        'verified_chunks': 1, 'planned_chunks': 480,
        'clusters': None,
        'registered_observations_read': False,
        'formal_permission': False,
        'campaign_evaluations_credited': 0,
        'full_end_to_end_budget_measured': False,
    }
    output_raw = canonical(receipt)
    need(len(output_raw) <= 16 * 1024, 'small postcheck receipt')
    OUTPUT.parent.mkdir()
    with OUTPUT.open('xb') as handle:
        handle.write(output_raw)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result-pin', required=True, type=cli_pin)
    parser.add_argument('--rows-pin', required=True, type=cli_pin)
    parser.add_argument('--budget-pin', required=True, type=cli_pin)
    args = parser.parse_args()
    value = run(args.result_pin, args.rows_pin, args.budget_pin)
    print(json.dumps({'status': value['status'], 'output': str(OUTPUT),
                      'output_pin': pin(OUTPUT.read_bytes())}, sort_keys=True))


if __name__ == '__main__':
    main()
