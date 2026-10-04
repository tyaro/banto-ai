"""Independent, read-only check of one retained invented six-row lineage.

This checks saved JSON and pin links without importing the lineage producer or
reading any registered observation payload. It does not authenticate the old
reader process or grant formal evaluation credit.
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
LINEAGE = ROOT / 'artifacts/anomaly-v03-preformal-saved-row-lineage-01/result.json'
OUTPUT = ROOT / 'artifacts/anomaly-v03-preformal-saved-row-lineage-postcheck-01/postcheck-result.json'
PINSET_PIN = {'bytes': 72149, 'sha256': '22ee6888d731c827162b09ef1332cb61fe6a5542372e3e499ea0088fd214f1ef'}
BUDGETED_PIN = {'bytes': 1654, 'sha256': 'd1a8c738e61fd0ad48d99675ca12cb2aea937152bafca29a543398061e9ceda7'}
RESOURCE_PIN = {'bytes': 3618, 'sha256': 'c1dd3e838930cd318ee8c51634d7d54faaacfcae7d70d3065f8e15a3878a72a2'}
OUTER_PIN = {'bytes': 10528, 'sha256': '354c8ae043486c8f5ee2a99780ea5ee5a9395ed92daaca790187e8e9ab7c1179'}
MAX_JSON = 512 * 1024


def need(condition: bool, label: str) -> None:
    if not condition:
        raise ValueError(label)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def pin(raw: bytes) -> dict:
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def read_json(path: Path, expected: dict, label: str) -> dict:
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
    need(type(value) is dict and canonical(value) == raw, label + ' canonical JSON')
    return value


def exact(value: dict, expected: dict, label: str) -> None:
    need(type(value) is dict and all(type(value.get(key)) is type(wanted) and
         value.get(key) == wanted for key, wanted in expected.items()), label)


def cli_pin(text: str) -> dict:
    match = re.fullmatch(r'([1-9][0-9]*):([0-9a-f]{64})', text)
    if match is None:
        raise argparse.ArgumentTypeError('expected bytes:sha256')
    result = {'bytes': int(match.group(1)), 'sha256': match.group(2)}
    if result['bytes'] > MAX_JSON:
        raise argparse.ArgumentTypeError('lineage result exceeds JSON bound')
    return result


def run(result_pin: dict) -> dict:
    need(not OUTPUT.parent.exists(), 'postcheck output root already exists')
    pins = read_json(PINSET, PINSET_PIN, 'external g02 pinset')
    budgeted = read_json(SOURCE / 'budgeted-result.json', BUDGETED_PIN,
                         'prior budgeted result')
    resource = read_json(SOURCE / 'resource-budget.json', RESOURCE_PIN,
                         'prior resource receipt')
    outer = read_json(SOURCE / 'owned-generator/result.json', OUTER_PIN,
                      'prior owned two-role result')
    output_pins = pins['output_pins']
    need(type(output_pins) is dict and len(output_pins) == 22,
         'external generated output inventory')
    receipt_pin = output_pins['saved/receipt.json']
    report_pin = output_pins['saved/report.json']
    receipt = read_json(SOURCE / 'saved/receipt.json', receipt_pin,
                        'prior saved receipt')
    report = read_json(SOURCE / 'saved/report.json', report_pin,
                       'prior saved report')
    result = read_json(LINEAGE, result_pin, 'new lineage result')

    exact(pins, {'invented_only': True, 'chunk_index': 0,
                 'actual_registered_observations_read': False,
                 'formal_permission': False, 'output_file_count': 22,
                 'root': str(SOURCE)}, 'external g02 scope')
    exact(budgeted, {'status': 'verified', 'root': str(SOURCE),
                     'inner_result_pin': OUTER_PIN,
                     'resource_budget_pin': RESOURCE_PIN,
                     'external_manifest_pin': PINSET_PIN,
                     'shared_budget_passed': True,
                     'both_owned_exits_reported': True,
                     'full_end_to_end_budget_measured': False,
                     'actual_registered_observations_read': False,
                     'formal_permission': False,
                     'campaign_evaluations_credited': 0},
          'prior budget links and scope')
    exact(resource, {'root': str(SOURCE), 'passed': True,
                     'sampler_exit_confirmed': True,
                     'both_owned_exits_reported': True,
                     'actual_registered_observations_read': False,
                     'formal_permission': False,
                     'campaign_evaluations_credited': 0},
          'prior resource scope')
    exact(outer, {'status': 'verified', 'reason': None,
                  'generated_output_pins': output_pins,
                  'owned_fixture_generator_exit_confirmed': True,
                  'owned_fixture_reader_exit_confirmed': True,
                  'actual_registered_observations_read': False,
                  'formal_permission': False,
                  'campaign_evaluations_credited': 0},
          'prior owned result')
    exact(outer['reader_result'], {
        'chunk_index': 0, 'latest_rows_bound': 6,
        'receipt_pin': receipt_pin, 'report_pin': report_pin,
        'clusters': None, 'diagnostics': None, 'slice_source': None,
        'actual_registered_observations_read': False,
        'formal_permission': False, 'independent_s6_complete': False,
        'campaign_evaluations_credited': 0}, 'prior owned reader result')
    exact(receipt, {'chunk_index': 0, 'invented_only': True},
          'prior saved receipt')
    exact(report, {'chunk_index': 0, 'invented_only': True,
                   'receipt_pin': receipt_pin,
                   'payload_pins': {name: value for name, value in output_pins.items()
                                    if not name.startswith('saved/')}},
          'prior saved report')
    attempts = receipt['attempts']
    need(type(attempts) is list and len(attempts) == 1 and
         attempts[0]['state'] == 'complete' and
         attempts[0]['attempt'] == report['attempt'] == 1,
         'one completed saved attempt')

    exact(result, {'format': 'anomaly-v03-registered-saved-row-lineage-v1',
                   'status': 'fixture_rows_bound_partial', 'mode': 'preformal-fixture',
                   'invented_only': True, 'chunk_index': 0,
                   'receipt_pin': receipt_pin, 'report_pin': report_pin,
                   'outer_result_pin': OUTER_PIN,
                   'registered_seed_index': 0,
                   'invented_cluster_id': 'invented-00',
                   'verified_layout': 0, 'verified_layouts_for_seed': 1,
                   'planned_layouts_for_seed': 12,
                   'verified_chunks': 1, 'planned_chunks': 480,
                   'verified_evaluations': 6, 'planned_evaluations': 2880,
                   'clusters': None, 'diagnostics': None, 'slice_source': None,
                   'receipt_report_outer_bytes_verified': True,
                   'owned_reader_result_consistency_checked': True,
                   'saved_payload_bytes_rechecked': False,
                   'reader_execution_authenticated_here': False,
                   'registered_observations_read': False,
                   'actual_registered_observations_read': False,
                   'formal_permission': False, 'analysis_authorized': False,
                   'promotion_allowed': False, 'independent_s6_complete': False,
                   'campaign_evaluations_credited': 0},
          'new partial lineage scope')
    exact(result['retained_two_role_budget'], {
        'budgeted_result_pin': BUDGETED_PIN,
        'resource_budget_pin': RESOURCE_PIN,
        'shared_budget_passed_in_prior_run': True,
        'prior_scope': resource['scope'],
        'current_lineage_trial_in_prior_budget': False},
        'new lineage prior-budget links')

    rows = result['rows']
    old_rows = report['rows']
    slots = attempts[0]['evaluations']
    need(type(rows) is list and type(old_rows) is list and
         type(slots) is list and len(rows) == len(old_rows) == len(slots) == 6,
         'six ordered rows and slots')
    expected_order = [(layer, candidate) for layer in ('core', 'quality-stress')
                      for candidate in ('c0-diff-control', 'c1-phase-level',
                                        'c2-phase-conditional')]
    row_pins = []
    for index, (row, old, slot) in enumerate(zip(rows, old_rows, slots)):
        identity = old['identity']
        layer, candidate = expected_order[index]
        exact(identity, {'role': 'holdout', 'seed': result['registered_seed'],
                         'layout': 0, 'stratum': layer,
                         'candidate_id': candidate},
              f'ordered registered identity {index}')
        need(identity == slot['identity'], f'saved slot identity {index}')
        expected_row = {
            'chunk_index': 0, 'registered_seed_index': 0,
            'invented_cluster_id': 'invented-00',
            'identity': identity, 'attempt': 1,
            'status': slot['status'],
            'profile_status': slot['profile_status'],
            'input_hashes': old['input_hashes'],
            'evaluation_pin': old['evaluation_pin'],
            'primary': old['primary'], 'slices': old['slices'],
        }
        need(type(row) is dict and set(row) == set(expected_row) and
             row == expected_row, f'exact report projection row {index}')
        need(old['evaluation_outcome'] == slot['status'] and
             old['input_hashes'] == slot['input_hashes'] and
             old['evaluation_pin']['sha256'] == slot['evaluation_sha256'] and
             old['evaluation_pin'] in report['payload_pins'].values(),
             f'saved report slot binding {index}')
        row_pins.append(pin(canonical(row)))
    need(result['registered_seed'] == slots[0]['identity']['seed'] and
         len({row['identity']['evaluation_id'] for row in rows}) == 6,
         'one registered seed and six distinct evaluations')

    postcheck = {
        'format': 'anomaly-v03-preformal-saved-row-lineage-postcheck-v1',
        'status': 'independent_saved_row_lineage_postcheck_passed',
        'scope': 'read-only g02 invented one-chunk row and prior-budget pin check',
        'lineage_result_pin': result_pin,
        'prior_pinset_pin': PINSET_PIN,
        'prior_receipt_pin': receipt_pin,
        'prior_report_pin': report_pin,
        'prior_owned_result_pin': OUTER_PIN,
        'prior_budgeted_result_pin': BUDGETED_PIN,
        'prior_resource_budget_pin': RESOURCE_PIN,
        'ordered_row_pins': row_pins,
        'rows_checked': 6, 'chunk_index': 0,
        'registered_seed_index': 0, 'verified_layouts_for_seed': 1,
        'verified_chunks': 1, 'planned_chunks': 480,
        'cluster_input_ready': False,
        'actual_registered_observations_read': False,
        'formal_permission': False,
        'independent_s6_complete': False,
        'full_end_to_end_budget_measured': False,
        'campaign_evaluations_credited': 0,
    }
    OUTPUT.parent.mkdir()
    with OUTPUT.open('xb') as handle:
        handle.write(canonical(postcheck))
    need(pin(OUTPUT.read_bytes())['bytes'] <= 16 * 1024,
         'small postcheck receipt')
    return postcheck


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result-pin', required=True, type=cli_pin)
    args = parser.parse_args()
    value = run(args.result_pin)
    print(json.dumps({'status': value['status'], 'rows_checked': 6,
                      'output': str(OUTPUT),
                      'output_pin': pin(OUTPUT.read_bytes())},
                     sort_keys=True))


if __name__ == '__main__':
    main()
