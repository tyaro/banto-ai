"""Collect pinned invented saved-row chunks without inventing a campaign origin.

Every input is a caller-retained byte string and external pin.  The collector
rechecks one chunk's saved-row projection and the reread receipts, then records
which frozen slots are present.  Matching individual chunks, including all 480,
cannot authenticate a common producer campaign or authorize an aggregate.
"""
from __future__ import annotations

import copy
from pathlib import PureWindowsPath
import re

from . import anomaly_v03 as v
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_registered_saved_row_lineage as lineage
from . import anomaly_v03_registered_saved_summary as saved


FORMAT = 'anomaly-v03-preformal-saved-row-coverage-v1'
REREAD_FORMAT = 'anomaly-v03-preformal-saved-row-reread-v1'
MANIFEST_FORMAT = 'anomaly-v03-preformal-owned-generated-external-pins-v1'
SAVEPOINT_FORMAT = 'anomaly-v03-preformal-invented-partial-savepoint-v1'
CHILD_FORMAT = 'anomaly-v03-preformal-saved-row-reread-child-v1'
BUDGET_FORMAT = 'anomaly-v03-fixture-resource-budget-v1'
SUPERVISION_FORMAT = 'anomaly-v03-owned-process-monitor-v1'
RAW_LIMITS = {
    'result': 32 * 1024, 'rows': 512 * 1024,
    'manifest': 256 * 1024, 'receipt': saved.MAX_RECEIPT,
    'report': saved.MAX_REPORT, 'savepoint': 16 * 1024,
    'budget': 32 * 1024, 'supervision': 32 * 1024,
    'stdout': 1024 * 1024, 'outer': lineage.MAX_OUTER,
}
MAX_TOTAL_INPUT_BYTES = 256 * 1024**2
MANIFEST_FIELDS = {
    'format', 'scope', 'root', 'revision', 'chunk_index', 'recipe_id',
    'source', 'source_snapshots', 'source_snapshot_pins', 'output_pins',
    'output_file_count', 'output_bytes', 'invented_only',
    'actual_registered_observations_read', 'formal_permission',
}


def _load(raw, pin, maximum, name, *, canonical=True):
    evidence._pin(pin)
    v.require(type(raw) is bytes and 0 < len(raw) <= maximum,
              name + ' byte bound')
    evidence._raw(raw, pin, 'external ' + name + ' pin')
    value = v.strict_json(raw)
    if canonical:
        v.require(raw == v.canonical_json(value), 'canonical ' + name + ' bytes')
    v.require(type(value) is dict, name + ' object')
    return value


def _same(actual, expected, label):
    evidence._same(actual, expected, label)


def _closed(value, fields, label):
    for name, wanted in fields.items():
        _same(value.get(name), wanted, label + ' ' + name)


def _pins(value, label):
    v.require(type(value) is dict, label + ' pin inventory')
    for name, pin in value.items():
        v.safe_relative_path(name)
        evidence._pin(pin)
        v.require(pin['bytes'] > 0, label + ' nonempty pin')


def _chunk(entry):
    names = set(RAW_LIMITS)
    v.require(type(entry) is dict and set(entry) ==
              {name + '_raw' for name in names} | {'expected_pins'},
              'coverage entry fields')
    pins = entry['expected_pins']
    v.require(type(pins) is dict and set(pins) == names,
              'coverage external pin fields')
    values = {name: _load(entry[name + '_raw'], pins[name], RAW_LIMITS[name],
                          name, canonical=name != 'stdout')
              for name in RAW_LIMITS}
    result = values['result']; rows = values['rows']
    manifest = values['manifest']; receipt = values['receipt']
    report = values['report']; savepoint = values['savepoint']
    budget = values['budget']; supervision = values['supervision']
    stdout = values['stdout']; outer = values['outer']

    index = result.get('chunk_index')
    v.require(type(index) is int and 0 <= index < 480,
              'frozen coverage chunk index')
    _closed(result, {
        'format': REREAD_FORMAT,
        'scope': 'one-invented-saved-chunk-reader-to-row-projection',
        'status': 'verified', 'reason': None, 'budget_passed': True,
        'child_exit_confirmed': True, 'child_status': 'complete',
        'external_saved_payload_bytes_in_directory_budget': False,
        'external_saved_payloads_reopened_in_child': True,
        'fresh_saved_payload_bytes_rechecked_this_run': True,
        'fresh_owned_reader_exit_confirmed_here': True,
        'fresh_reader_equal_prior_reader': True,
        'row_projection_in_same_budget': True,
        'verified_chunks': 1, 'verified_evaluations': 6,
        'source_closure_complete': False, 'runtime_closure_complete': False,
        'execution_authenticated': False, 'result_trusted': False,
        'campaign_completed': False, 'full_end_to_end_budget_measured': False,
        'registered_observations_read': False,
        'actual_registered_observations_read': False,
        'campaign_evaluations_credited': 0, 'formal_permission': False,
        'analysis_authorized': False, 'promotion_allowed': False,
        'independent_s6_complete': False,
    }, 'reread result')
    _closed(manifest, {
        'format': MANIFEST_FORMAT,
        'scope': 'invented-registered-format-owned-generator-only',
        'chunk_index': index, 'invented_only': True,
        'actual_registered_observations_read': False,
        'formal_permission': False,
    }, 'external manifest')
    v.require(set(manifest) == MANIFEST_FIELDS,
              'exact external manifest fields')
    v.require(type(manifest['revision']) is str and
              re.fullmatch(r'[0-9a-f]{40}', manifest['revision']) and
              type(manifest['recipe_id']) is str and manifest['recipe_id'] and
              type(manifest['source_snapshot_pins']) is dict and
              manifest['source_snapshot_pins'],
              'historical recipe/source declaration')
    _pins(manifest['source_snapshot_pins'], 'historical source snapshots')
    v.require(type(manifest['source_snapshots']) is dict and
              set(manifest['source_snapshots']) == {manifest['revision']} and
              type(manifest['source']) is dict and
              manifest['source'].get('revision') == manifest['revision'],
              'historical source revision contract')
    _same(result.get('source_root'), manifest['root'], 'reread source root')
    _same(result.get('historic_source_revision'), manifest['revision'],
          'reread historical source revision')
    _same(result.get('manifest_pin'), pins['manifest'], 'reread manifest pin')
    _same(result.get('row_projection_pin'), pins['rows'], 'reread rows pin')
    _same(result.get('old_outer_result_pin'), pins['outer'], 'reread outer pin')
    _same(result.get('receipt_pin'), pins['receipt'], 'reread receipt pin')
    _same(result.get('report_pin'), pins['report'], 'reread report pin')
    _same(result.get('external_saved_payload_bytes'), manifest['output_bytes'],
          'reread external saved bytes')
    _same(result.get('resource_budget_pin'), pins['budget'], 'reread budget pin')
    _same(result.get('reader_supervision_pin'), pins['supervision'],
          'reread supervision pin')
    _same(result.get('child_stdout_pin'), pins['stdout'], 'reread stdout pin')
    _same(result.get('selected_current_source_after'),
          result.get('selected_current_source'), 'reread selected source stability')
    v.require(type(result.get('current_revision')) is str and
              re.fullmatch(r'[0-9a-f]{40}', result['current_revision']),
              'current source revision')
    v.require(type(result.get('selected_current_source')) is dict,
              'selected current source object')
    _same(result['selected_current_source'].get('revision'),
          result['current_revision'], 'reread current source revision')
    _same(result.get('runtime_after'), result.get('runtime'),
          'reread runtime stability')
    v.require(type(result.get('output_root')) is str and
              type(result.get('source_root')) is str and
              type(result.get('manifest_path')) is str and
              type(result.get('row_projection_path')) is str,
              'reread paths')
    for path in (result['output_root'], result['source_root'],
                 result['manifest_path'], result['row_projection_path']):
        evidence._absolute(path)
    source_path = PureWindowsPath(result['source_root'])
    output_path = PureWindowsPath(result['output_root'])
    v.require(source_path.name.startswith('anomaly-v03-preformal-registered-attempt-')
              and output_path.name.startswith('anomaly-v03-preformal-saved-row-reread-')
              and source_path.parent == output_path.parent and
              source_path != output_path,
              'distinct invented source and reread roots')
    suffix = source_path.name.removeprefix('anomaly-v03-preformal-registered-attempt-')
    _same(str(PureWindowsPath(result['manifest_path'])),
          str(source_path.parent /
              ('anomaly-v03-preformal-generated-pinsets-' + suffix) /
              'pins.json'), 'reread manifest path')
    _same(str(PureWindowsPath(result['row_projection_path'])),
          str(PureWindowsPath(result['output_root']) / 'rows.json'),
          'reread rows path')
    _same(PureWindowsPath(result['manifest_path']).name, 'pins.json',
          'reread manifest name')

    outputs = manifest['output_pins']
    _pins(outputs, 'manifest outputs')
    _same(manifest['output_file_count'], len(outputs),
          'manifest output file count')
    _same(manifest['output_bytes'], sum(pin['bytes'] for pin in outputs.values()),
          'manifest output bytes')
    _same(outputs.get('saved/receipt.json'), pins['receipt'],
          'manifest receipt pin')
    _same(outputs.get('saved/report.json'), pins['report'],
          'manifest report pin')
    _same(outputs.get('saved/savepoint.json'), pins['savepoint'],
          'manifest savepoint pin')
    _same(outer.get('generated_output_pins'), outputs,
          'prior owned output pins')

    v.require(set(savepoint) == {'format', 'mode', 'invented_only',
              'chunk_index', 'run_root', 'campaign_completed',
              'actual_registered_observations_read'},
              'exact invented savepoint fields')
    _closed(savepoint, {
        'format': SAVEPOINT_FORMAT, 'mode': saved.MODE,
        'invented_only': True, 'chunk_index': index,
        'campaign_completed': False,
        'actual_registered_observations_read': False,
        'run_root': str(PureWindowsPath(manifest['root']) / 'run-root'),
    }, 'invented savepoint')
    _same(receipt.get('savepoint_pin'), pins['savepoint'],
          'receipt savepoint pin')
    _same(receipt.get('registry_pin'), outputs.get('saved/registry.json'),
          'manifest frozen registry pin')
    _same(report.get('savepoint_pin'), pins['savepoint'],
          'report savepoint pin')
    _same(report.get('receipt_pin'), pins['receipt'],
          'report receipt pin')
    _same(report.get('payload_pins'),
          {name: pin for name, pin in outputs.items()
           if name not in {'saved/receipt.json', 'saved/report.json',
                           'saved/registry.json', 'saved/savepoint.json'}},
          'report payload output pins')

    _closed(budget, {'format': BUDGET_FORMAT, 'passed': True,
                     'monitor_exit_confirmed': True, 'stop_reason': None,
                     'formal_permission': False,
                     'enforcement': 'sampled-and-cooperative-not-hard-quota',
                     'scope': 'one-fixture-call-and-new-receipt-directory',
                     'shared_root': None}, 'budget receipt')
    v.require(type(budget.get('samples')) is int and budget['samples'] >= 2,
              'budget sample count')
    _closed(supervision, {'format': SUPERVISION_FORMAT,
                          'status': 'complete', 'exit_code': 0,
                          'worker_started': True,
                          'worker_exit_confirmed': True,
                          'stop_reason': None,
                          'formal_permission': False,
                          'output': pins['stdout'],
                          'worker_pid': result.get('child_pid')},
            'owned reader supervision')
    _closed(stdout, {'format': CHILD_FORMAT, 'status': 'read',
                     'manifest_pin': pins['manifest'],
                     'output_pins': outputs,
                     'source': result.get('selected_current_source'),
                     'runtime': result.get('runtime'),
                     'actual_registered_observations_read': False,
                     'formal_permission': False}, 'owned reader stdout')
    _same(stdout.get('process'), {
        'pid': result.get('child_pid'),
        'parent_pid': stdout.get('process', {}).get('parent_pid')
            if type(stdout.get('process')) is dict else None,
        'start_token': result.get('child_start_token')},
        'owned reader process token')
    v.require(type(stdout['process']['parent_pid']) is int and
              stdout['process']['parent_pid'] > 0,
              'owned reader parent PID')
    _same(stdout.get('reader_result'), outer.get('reader_result'),
          'fresh reader equals prior reader')
    _same(stdout['reader_result'].get('chunk_index'), index,
          'fresh reader chunk index')

    projected = lineage.bind_saved_reader_rows(
        entry['receipt_raw'], entry['report_raw'], entry['outer_raw'],
        chunk_index=index, expected_receipt_pin=pins['receipt'],
        expected_report_pin=pins['report'],
        expected_outer_result_pin=pins['outer'])
    _same(rows, projected, 'fresh reread row projection')
    _same(report.get('attempt'), rows.get('latest_attempt'),
          'latest report attempt')
    return {
        'chunk_index': index,
        'registered_seed_index': rows['registered_seed_index'],
        'registered_seed': rows['registered_seed'],
        'layout': rows['verified_layout'],
        'latest_attempt': rows['latest_attempt'],
        'source_root': manifest['root'],
        'historic_source_revision': manifest['revision'],
        'recipe_id': manifest['recipe_id'],
        'savepoint_pin': copy.deepcopy(pins['savepoint']),
        'result_pin': copy.deepcopy(pins['result']),
        'rows_pin': copy.deepcopy(pins['rows']),
        'registry_pin': copy.deepcopy(receipt['registry_pin']),
        '_source': manifest['source'],
        '_source_snapshots': manifest['source_snapshots'],
        '_source_snapshot_pins': manifest['source_snapshot_pins'],
    }


def collect_saved_row_coverage(entries):
    """Check ordered chunk claims and report missing slots, with aggregates closed.

    This pure function does not open paths, reread saved payloads, or verify a
    shared producer anchor.  Even a complete inventory remains unanchored.
    """
    v.require(type(entries) is list and len(entries) <= 480,
              'bounded coverage entry list')
    raw_names = {name + '_raw' for name in RAW_LIMITS}
    total_bytes = 0
    for entry in entries:
        v.require(type(entry) is dict and set(entry) ==
                  raw_names | {'expected_pins'},
                  'coverage entry fields')
        for name in raw_names:
            raw = entry[name]
            v.require(type(raw) is bytes, 'coverage raw bytes required')
            total_bytes += len(raw)
            v.require(total_bytes <= MAX_TOTAL_INPUT_BYTES,
                      'total coverage input byte bound')
    checked = []
    previous = -1
    baseline = None
    for entry in entries:
        row = _chunk(entry)
        index = row['chunk_index']
        v.require(index > previous, 'strictly increasing unique chunk index')
        previous = index
        coherence = [row['historic_source_revision'], row['recipe_id'],
                     row['registry_pin'], row['_source'],
                     row['_source_snapshots'],
                     row['_source_snapshot_pins']]
        if baseline is None:
            baseline = coherence
        else:
            _same(coherence, baseline, 'cross-chunk recipe/source consistency')
        checked.append({key: value for key, value in row.items()
                        if not key.startswith('_')})
    observed = {row['chunk_index'] for row in checked}
    missing = [index for index in range(480) if index not in observed]
    return {
        'format': FORMAT, 'mode': saved.MODE, 'invented_only': True,
        'status': 'partial_coverage_unanchored' if missing else
                  'full_coverage_unanchored',
        'scope': 'pinned-invented-saved-row-reread-coverage-only',
        'planned_chunks': 480, 'planned_evaluations': 2880,
        'bound_chunks': len(checked), 'bound_evaluations': 6 * len(checked),
        'chunk_indices': [row['chunk_index'] for row in checked],
        'missing_chunk_indices': missing,
        'chunks': checked,
        'per_chunk_savepoint_pins_checked': bool(checked),
        'cross_chunk_recipe_source_consistency_checked': len(checked) > 1,
        'pinned_reread_receipts_checked': bool(checked),
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
    }
