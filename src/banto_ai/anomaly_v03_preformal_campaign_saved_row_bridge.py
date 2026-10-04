"""Link one retained invented campaign declaration to its saved six rows.

This pure boundary accepts caller-pinned historical bytes.  It neither
reopens the saved observation payloads nor reauthenticates old processes, and
it cannot produce a 40-cluster input or formal evaluation credit.
"""
from __future__ import annotations

import copy
from pathlib import PureWindowsPath

from . import anomaly_v03 as v
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_preformal_campaign_metadata as campaign
from . import anomaly_v03_preformal_saved_row_reread as saved_row_reread
from . import anomaly_v03_preformal_saved_row_coverage as coverage


FORMAT = 'anomaly-v03-preformal-campaign-saved-row-bridge-v1'
STARTED_FORMAT = 'anomaly-v03-preformal-campaign-started-checkpoint-v1'
TERMINAL_FORMAT = 'anomaly-v03-preformal-campaign-completed-checkpoint-v1'
MAX_CHECKPOINT = 4096
MAX_OWNER_RECEIPT = 32 * 1024
OWNER_RECEIPT_FORMAT = 'anomaly-v03-preformal-two-slot-owned-cli-receipt-v1'
OWNER_RECEIPT_FIELDS = frozenset({
    'format', 'scope', 'phase', 'anchor_pin', 'journal_count',
    'journal_head_sha256', 'chunk_index', 'attempt', 'attempt_root',
    'manifest_pin', 'status', 'cli_exit_code', 'cli_exit_confirmed',
    'cli_process', 'cli_stderr_pin', 'cli_stdout_pin',
    'cli_supervision_pin', 'request_pin', 'inner', 'invented_only',
    'actual_registered_observations_read',
    'campaign_coherence_authenticated', 'campaign_evaluations_credited',
    'formal_permission', 'full_end_to_end_budget_measured',
})

STARTED_FIELDS = frozenset({
    'format', 'anchor_pin', 'previous_checkpoint_pin',
    'preflight_intention_pin', 'prepare_receipt_pin',
    'started_record_pin', 'record_count', 'head_sha256',
    'launch_authorized', 'resume_authorized',
    'campaign_evaluations_credited', 'formal_permission',
})
TERMINAL_FIELDS = frozenset({
    'format', 'anchor_pin', 'previous_checkpoint_pin',
    'generation_receipt_pin', 'saved_reread_receipt_pin',
    'run_request_control_pin', 'reread_request_control_pin',
    'completed_record_pin', 'record_count', 'head_sha256',
    'invented_only', 'actual_registered_observations_read',
    'campaign_coherence_authenticated', 'launch_authorized',
    'resume_authorized', 'campaign_evaluations_credited',
    'formal_permission',
})

ENTRY_PINS = {
    'result': 'fresh_reread_result',
    'rows': 'rows',
    'budget': 'fresh_reread_budget_receipt',
    'supervision': 'fresh_reread_supervision',
    'stdout': 'fresh_reread_stdout',
    'receipt': 'saved_receipt',
    'report': 'saved_report',
    'savepoint': 'saved_savepoint',
    'outer': 'outer_result',
}


def _same(actual, wanted, label):
    evidence._same(actual, wanted, label)


def _checkpoint(raw, expected_pin, fields, label):
    campaign._pin(expected_pin, 'external ' + label)
    v.require(type(raw) is bytes and 0 < len(raw) <= MAX_CHECKPOINT and
              campaign.pin(raw) == expected_pin, label + ' external pin')
    value = v.strict_json(raw)
    v.require(type(value) is dict and set(value) == fields and
              raw == v.canonical_json(value) + b'\n',
              label + ' canonical LF fields')
    return value


def _owner_receipt(raw, expected_pin, phase, plan_pin, started_pin, record):
    campaign._pin(expected_pin, 'externally pinned ' + phase + ' receipt')
    v.require(type(raw) is bytes and 0 < len(raw) <= MAX_OWNER_RECEIPT and
              campaign.pin(raw) == expected_pin,
              phase + ' receipt external pin')
    value = v.strict_json(raw)
    v.require(type(value) is dict and set(value) == OWNER_RECEIPT_FIELDS and
              raw == v.canonical_json(value) + b'\n',
              phase + ' canonical LF receipt fields')
    for name, wanted in (
        ('format', OWNER_RECEIPT_FORMAT),
        ('scope', 'invented-two-slot-owned-cli-only'),
        ('phase', phase), ('anchor_pin', plan_pin),
        ('journal_count', 1),
        ('journal_head_sha256', started_pin['sha256']),
        ('chunk_index', 0), ('attempt', 1),
        ('attempt_root', record['attempt_root']),
        ('manifest_pin', record['manifest_pin']),
        ('status', 'verified'), ('cli_exit_code', 0),
        ('cli_exit_confirmed', True), ('invented_only', True),
        ('actual_registered_observations_read', False),
        ('campaign_coherence_authenticated', False),
        ('campaign_evaluations_credited', 0),
        ('formal_permission', False),
        ('full_end_to_end_budget_measured', False),
    ):
        _same(value[name], wanted, phase + ' receipt ' + name)
    for name in ('request_pin', 'cli_stdout_pin', 'cli_supervision_pin'):
        campaign._pin(value[name], phase + ' receipt ' + name)
    campaign._pin(value['cli_stderr_pin'], phase + ' receipt stderr',
                  positive=False)
    v.require(type(value['cli_process']) is dict and
              type(value['inner']) is dict,
              phase + ' receipt process and inner objects')
    return value


def bind_completed_saved_rows(plan_raw, record_raws,
                              started_checkpoint_raw, terminal_checkpoint_raw,
                              coverage_entry, *, generation_receipt_raw,
                              saved_reread_receipt_raw, expected_plan_pin,
                              expected_started_checkpoint_pin,
                              expected_terminal_checkpoint_pin):
    """Bind externally pinned slot-zero journal and saved-row control bytes.

    The three expected pins must have been retained outside these supplied
    bytes.  The terminal checkpoint pins the completed record and the started
    checkpoint, which pins the started record.  The completed record supplies
    the ten expected saved-row control pins; none are inferred from their own
    payload bytes.
    """
    campaign._pin(expected_plan_pin, 'external plan')
    v.require(type(plan_raw) is bytes and
              0 < len(plan_raw) <= campaign.MAX_PLAN_BYTES and
              campaign.pin(plan_raw) == expected_plan_pin,
              'external campaign plan pin')
    started = _checkpoint(started_checkpoint_raw,
                          expected_started_checkpoint_pin,
                          STARTED_FIELDS, 'started checkpoint')
    terminal = _checkpoint(terminal_checkpoint_raw,
                           expected_terminal_checkpoint_pin,
                           TERMINAL_FIELDS, 'terminal checkpoint')
    v.require(type(record_raws) is list and len(record_raws) == 2 and
              all(type(raw) is bytes and
                  0 < len(raw) <= campaign.MAX_RECORD_BYTES
                  for raw in record_raws),
              'two historical journal raw records')
    started_pin = campaign.pin(record_raws[0])
    completed_pin = campaign.pin(record_raws[1])
    for name in ('previous_checkpoint_pin', 'preflight_intention_pin',
                 'prepare_receipt_pin'):
        campaign._pin(started[name], 'started ' + name)
    for name in ('generation_receipt_pin', 'saved_reread_receipt_pin',
                 'run_request_control_pin', 'reread_request_control_pin'):
        campaign._pin(terminal[name], 'terminal ' + name)
    _same(started['format'], STARTED_FORMAT, 'started format')
    _same(started['anchor_pin'], expected_plan_pin, 'started anchor')
    _same(started['record_count'], 1, 'started record count')
    _same(started['started_record_pin'], started_pin, 'started record pin')
    _same(started['head_sha256'], started_pin['sha256'], 'started head')
    _same(terminal['format'], TERMINAL_FORMAT, 'terminal format')
    _same(terminal['anchor_pin'], expected_plan_pin, 'terminal anchor')
    _same(terminal['previous_checkpoint_pin'],
          expected_started_checkpoint_pin, 'terminal previous checkpoint')
    _same(terminal['record_count'], 2, 'terminal record count')
    _same(terminal['completed_record_pin'], completed_pin,
          'terminal completed record pin')
    _same(terminal['head_sha256'], completed_pin['sha256'], 'terminal head')
    for source, names in ((started, ('launch_authorized',
                                    'resume_authorized', 'formal_permission')),
                          (terminal, ('actual_registered_observations_read',
                                      'campaign_coherence_authenticated',
                                      'launch_authorized', 'resume_authorized',
                                      'formal_permission'))):
        for name in names:
            _same(source[name], False, 'closed checkpoint ' + name)
        _same(source['campaign_evaluations_credited'], 0,
              'closed checkpoint credit')
    _same(terminal['invented_only'], True, 'terminal invented scope')

    state = campaign.reduce_journal(
        plan_raw, record_raws, expected_plan_pin=expected_plan_pin,
        expected_record_count=2,
        expected_head_sha256=completed_pin['sha256'])
    v.require(state['declared_completed_chunks'] == 1 and
              state['declared_completed_evaluations'] == 6 and
              state['completed_chunk_indices'] == [0] and
              state['missing_chunk_indices'] == list(range(1, 480)) and
              state['latest_unfinished_state'] is None and
              state['failed_attempt_count'] == 0 and
              state['campaign_coherence_authenticated'] is False and
              state['formal_permission'] is False,
              'one completed historical slot only')
    plan = v.strict_json(plan_raw)
    record = v.strict_json(record_raws[1])
    v.require(record['state'] == 'completed' and
              record['chunk_index'] == 0 and record['attempt'] == 1,
              'completed first attempt')
    generation = _owner_receipt(
        generation_receipt_raw, terminal['generation_receipt_pin'],
        'run-budget', expected_plan_pin, started_pin, record)
    reread = _owner_receipt(
        saved_reread_receipt_raw, terminal['saved_reread_receipt_pin'],
        'saved-reread', expected_plan_pin, started_pin, record)
    v.require(set(generation['inner']) == {
                  'evidence_pins', 'outer_result_pin', 'result_pin',
                  'saved_output_pins'} and
              set(reread['inner']) == {
                  'evidence_pins', 'fresh_reread_invocation_pin',
                  'outer_result_pin', 'result_pin'},
              'owner receipt inner fields')
    campaign._pin(reread['inner']['fresh_reread_invocation_pin'],
                  'fresh reread invocation')
    _same(generation['inner']['evidence_pins'],
          {name: record['evidence_pins'][name]
           for name in campaign.REQUIRED_EVIDENCE_NAMES if name != 'rows'},
          'generation receipt to completed evidence')
    _same(reread['inner']['evidence_pins'],
          {name: record['evidence_pins'][name]
           for name in ('rows', *campaign.FRESH_REREAD_EVIDENCE_NAMES)},
          'saved reread receipt to completed evidence')
    _same(generation['inner']['saved_output_pins'],
          record['saved_output_pins'],
          'generation receipt to completed saved outputs')
    _same(generation['inner']['outer_result_pin'],
          record['evidence_pins']['outer_result'],
          'generation receipt outer result pin')
    _same(reread['inner']['outer_result_pin'],
          record['evidence_pins']['outer_result'],
          'reread receipt outer result pin')
    _same(generation['inner']['result_pin'],
          record['evidence_pins']['two_role_budget_result'],
          'generation receipt result pin')
    _same(reread['inner']['result_pin'],
          record['evidence_pins']['fresh_reread_result'],
          'reread receipt result pin')
    for evidence_name, output_name in (
        ('saved_receipt', 'saved/receipt.json'),
        ('saved_report', 'saved/report.json'),
        ('saved_savepoint', 'saved/savepoint.json'),
    ):
        _same(record['evidence_pins'][evidence_name],
              record['saved_output_pins'][output_name],
              'completed evidence to saved output ' + evidence_name)
    expected_entry_pins = {
        name: record['evidence_pins'][evidence_name]
        for name, evidence_name in ENTRY_PINS.items()
    }
    expected_entry_pins['manifest'] = record['manifest_pin']
    _same(record['evidence_pins']['fresh_reread_rows'],
          expected_entry_pins['rows'], 'fresh reread row pin')
    v.require(type(coverage_entry) is dict and
              coverage_entry.get('expected_pins') == expected_entry_pins,
              'coverage pins must derive from completed journal')
    rows_coverage = coverage.collect_saved_row_coverage([coverage_entry])
    manifest = v.strict_json(coverage_entry['manifest_raw'])
    v.require(type(manifest) is dict and
              type(manifest.get('output_pins')) is dict,
              'saved output manifest inventory')
    _same(record['saved_output_pins'], manifest['output_pins'],
          'completed journal to full saved output manifest')
    v.require(rows_coverage['format'] == coverage.FORMAT and
              rows_coverage['invented_only'] is True and
              rows_coverage['status'] == 'partial_coverage_unanchored' and
              rows_coverage['planned_chunks'] == 480 and
              rows_coverage['planned_evaluations'] == 2880 and
              rows_coverage['bound_chunks'] == 1 and
              rows_coverage['bound_evaluations'] == 6 and
              rows_coverage['chunk_indices'] == [0] and
              rows_coverage['missing_chunk_indices'] == list(range(1, 480)) and
              type(rows_coverage['chunks']) is list and
              len(rows_coverage['chunks']) == 1 and
              rows_coverage['producer_campaign_anchor'] is None and
              rows_coverage['campaign_coherence_authenticated'] is False and
              rows_coverage['saved_payload_bytes_reopened_here'] is False and
              rows_coverage['reader_execution_authenticated_here'] is False and
              rows_coverage['clusters'] is None and
              rows_coverage['diagnostics'] is None and
              rows_coverage['slice_source'] is None and
              rows_coverage['registered_observations_read'] is False and
              rows_coverage['actual_registered_observations_read'] is False and
              rows_coverage['campaign_evaluations_credited'] == 0 and
              rows_coverage['formal_permission'] is False and
              rows_coverage['analysis_authorized'] is False and
              rows_coverage['promotion_allowed'] is False and
              rows_coverage['independent_s6_complete'] is False,
              'one partial saved-row coverage only')
    row = rows_coverage['chunks'][0]
    planned = plan['chunks'][0]
    for name, value in (
        ('chunk_index', 0),
        ('registered_seed_index', planned['registered_seed_index']),
        ('registered_seed', planned['registered_seed']),
        ('layout', planned['layout']),
        ('latest_attempt', 1),
        ('source_root', record['attempt_root']),
        ('historic_source_revision', plan['source']['revision']),
        ('recipe_id', plan['recipe_id']),
        ('registry_pin', plan['registry_pin']),
        ('savepoint_pin', expected_entry_pins['savepoint']),
        ('result_pin', expected_entry_pins['result']),
        ('rows_pin', expected_entry_pins['rows']),
    ):
        _same(row[name], value, 'plan/journal/saved row ' + name)
    rows = v.strict_json(coverage_entry['rows_raw'])['rows']
    stdout = v.strict_json(coverage_entry['stdout_raw'])
    if stdout['format'] == coverage.CAMPAIGN_CHILD_FORMAT:
        _same(stdout['campaign_context'], {
            'plan_path': str(PureWindowsPath(plan['root']) / 'plan.json'),
            'anchor_pin': expected_plan_pin,
            'chunk_index': 0, 'attempt': 1,
        }, 'campaign reader child to external plan and attempt')
        selected_rows = plan['source']['selected_files']
        selected = {row['path']: row['pin'] for row in selected_rows}
        v.require(len(selected) == len(selected_rows) and
                  len({name.casefold() for name in selected}) ==
                      len(selected_rows),
                  'unique plan source path inventory')
        child_source = stdout['source']
        child_rows = child_source.get('selected_files') if type(
            child_source) is dict else None
        if type(child_rows) is list and all(
                type(row) is dict and set(row) == {'path', 'pin'} and
                type(row['path']) is str for row in child_rows):
            child_paths = [row['path'] for row in child_rows]
        else:
            child_paths = []
        v.require(type(child_source) is dict and
                  set(child_source) == {'revision', 'selected_files', 'scope'} and
                  child_source.get('revision') ==
                      plan['source']['revision'] and
                  child_source.get('scope') == plan['source']['scope'] and
                  type(child_rows) is list and
                  len(child_rows) == len(saved_row_reread.SOURCE_FILES) and
                  len(set(child_paths)) == len(child_paths) and
                  len({name.casefold() for name in child_paths}) ==
                      len(child_paths) and
                  set(child_paths) == set(saved_row_reread.SOURCE_FILES) and
                  all(path in selected and selected[path] == row['pin']
                      for path, row in zip(child_paths, child_rows)),
                  'campaign reader child exact source pins match plan')
    v.require(type(rows) is list and len(rows) == 6,
              'six saved row identities')
    identities = [row['identity'] for row in rows]
    _same(identities, v.evaluation_inventory('holdout')[:6],
          'frozen first six identities')
    _same(v.canonical_sha256(identities), planned['identities_sha256'],
          'campaign planned six identities')

    return {
        'format': FORMAT, 'scope': 'one-retained-invented-slot-control-bytes-only',
        'status': 'partial_saved_row_journal_link_only',
        'invented_only': True,
        'historical_source_revision': plan['source']['revision'],
        'source_campaign_plan_pin': copy.deepcopy(expected_plan_pin),
        'started_checkpoint_pin': copy.deepcopy(expected_started_checkpoint_pin),
        'terminal_checkpoint_pin': copy.deepcopy(expected_terminal_checkpoint_pin),
        'generation_receipt_pin': copy.deepcopy(
            terminal['generation_receipt_pin']),
        'saved_reread_receipt_pin': copy.deepcopy(
            terminal['saved_reread_receipt_pin']),
        'completed_record_pin': copy.deepcopy(completed_pin),
        'journal_head_sha256': completed_pin['sha256'],
        'saved_rows_pin': copy.deepcopy(expected_entry_pins['rows']),
        'verified_chunks': 1, 'planned_chunks': 480,
        'verified_evaluations': 6, 'planned_evaluations': 2880,
        'chunk_indices': [0], 'missing_chunk_indices': list(range(1, 480)),
        'producer_campaign_anchor': None,
        'campaign_coherence_authenticated': False,
        'producer_execution_authenticated_here': False,
        'reader_execution_authenticated_here': False,
        'retained_owner_receipt_context_checked_here': True,
        'saved_payload_bytes_reopened_here': False,
        'source_closure_complete': False,
        'runtime_closure_complete': False,
        'full_end_to_end_budget_measured': False,
        'clusters': None, 'diagnostics': None, 'slice_source': None,
        'registered_observations_read': False,
        'actual_registered_observations_read': False,
        'campaign_evaluations_credited': 0,
        'formal_permission': False, 'analysis_authorized': False,
        'promotion_allowed': False, 'independent_s6_complete': False,
    }
