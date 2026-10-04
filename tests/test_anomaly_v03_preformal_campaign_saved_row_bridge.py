"""Externally pinned journal-to-row links remain partial and fail closed."""
from __future__ import annotations

import copy
from pathlib import PureWindowsPath
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_preformal_campaign_metadata as campaign
from banto_ai import anomaly_v03_preformal_campaign_saved_row_bridge as bridge
from tests import test_anomaly_v03_preformal_saved_row_coverage as coverage_fixture
from tests.test_anomaly_v03_preformal_campaign_metadata import Journal


def fixture(*, real_coverage=False):
    journal = Journal()
    journal.complete(0)
    if real_coverage:
        attempt_root = campaign.attempt_root(journal.plan, 0, 1)
        parent = PureWindowsPath(attempt_root).parent
        reread_root = str(parent /
                          'anomaly-v03-preformal-saved-row-reread-h001')
        with patch.object(coverage_fixture, 'ROOT', attempt_root), \
             patch.object(coverage_fixture, 'OUTPUT', reread_root), \
             patch.object(coverage_fixture, 'REVISION',
                          journal.plan['source']['revision']):
            entry, objects = coverage_fixture.make_entry()
        objects['manifest']['recipe_id'] = journal.plan['recipe_id']
        coverage_fixture.rewrap(entry, 'manifest', objects['manifest'])
        objects['stdout']['manifest_pin'] = entry['expected_pins']['manifest']
        coverage_fixture.rewrap(entry, 'stdout', objects['stdout'])
        objects['supervision']['output'] = entry['expected_pins']['stdout']
        coverage_fixture.rewrap(entry, 'supervision', objects['supervision'])
        objects['result']['manifest_path'] = str(parent /
            'anomaly-v03-preformal-generated-pinsets-h001' / 'pins.json')
        objects['result']['manifest_pin'] = entry['expected_pins']['manifest']
        objects['result']['child_stdout_pin'] = entry['expected_pins']['stdout']
        objects['result']['reader_supervision_pin'] = \
            entry['expected_pins']['supervision']
        coverage_fixture.rewrap(entry, 'result', objects['result'])
    else:
        entry = {'expected_pins': {}}
        for name in bridge.ENTRY_PINS | {'manifest': 'manifest'}:
            raw = (v.canonical_json({'rows': [
                {'identity': identity}
                for identity in v.evaluation_inventory('holdout')[:6]]})
                if name == 'rows' else
                v.canonical_json({'format': bridge.coverage.CHILD_FORMAT})
                if name == 'stdout' else name.encode())
            entry[name + '_raw'] = raw
            entry['expected_pins'][name] = campaign.pin(raw)

    started = v.strict_json(journal.raws[0])
    completed = v.strict_json(journal.raws[1])
    for name, evidence_name in bridge.ENTRY_PINS.items():
        completed['evidence_pins'][evidence_name] = entry['expected_pins'][name]
    completed['evidence_pins']['fresh_reread_rows'] = entry['expected_pins']['rows']
    if real_coverage:
        completed['saved_output_pins'] = objects['manifest']['output_pins']
        completed['evidence_pins']['saved_registry'] = \
            completed['saved_output_pins']['saved/registry.json']
    for name, output_name in (
        ('receipt', 'saved/receipt.json'),
        ('report', 'saved/report.json'),
        ('savepoint', 'saved/savepoint.json'),
    ):
        completed['saved_output_pins'][output_name] = entry['expected_pins'][name]
    if not real_coverage:
        entry['manifest_raw'] = v.canonical_json({
            'output_pins': completed['saved_output_pins']})
        entry['expected_pins']['manifest'] = campaign.pin(
            entry['manifest_raw'])
    started['manifest_pin'] = entry['expected_pins']['manifest']
    completed['manifest_pin'] = entry['expected_pins']['manifest']
    journal.raws[0] = campaign.encode_record(started)
    completed['previous_sha256'] = campaign.pin(journal.raws[0])['sha256']
    journal.raws[1] = campaign.encode_record(completed)
    journal.reduce()

    started_pin = campaign.pin(journal.raws[0])
    completed_pin = campaign.pin(journal.raws[1])
    started_checkpoint = {
        'format': bridge.STARTED_FORMAT,
        'anchor_pin': journal.plan_pin,
        'previous_checkpoint_pin': campaign.pin(b'initial checkpoint'),
        'preflight_intention_pin': campaign.pin(b'preflight intention'),
        'prepare_receipt_pin': campaign.pin(b'prepare receipt'),
        'started_record_pin': started_pin,
        'record_count': 1, 'head_sha256': started_pin['sha256'],
        'launch_authorized': False, 'resume_authorized': False,
        'campaign_evaluations_credited': 0, 'formal_permission': False,
    }
    started_raw = v.canonical_json(started_checkpoint) + b'\n'
    started_checkpoint_pin = campaign.pin(started_raw)

    def owner_receipt(phase):
        evidence = completed['evidence_pins']
        if phase == 'run-budget':
            inner = {
                'evidence_pins': {
                    name: evidence[name]
                    for name in campaign.REQUIRED_EVIDENCE_NAMES
                    if name != 'rows'},
                'outer_result_pin': evidence['outer_result'],
                'result_pin': evidence['two_role_budget_result'],
                'saved_output_pins': completed['saved_output_pins'],
            }
        else:
            inner = {
                'evidence_pins': {
                    name: evidence[name]
                    for name in ('rows', *campaign.FRESH_REREAD_EVIDENCE_NAMES)},
                'fresh_reread_invocation_pin': campaign.pin(b'invocation'),
                'outer_result_pin': evidence['outer_result'],
                'result_pin': evidence['fresh_reread_result'],
            }
        return {
            'format': bridge.OWNER_RECEIPT_FORMAT,
            'scope': 'invented-two-slot-owned-cli-only',
            'phase': phase, 'anchor_pin': journal.plan_pin,
            'journal_count': 1, 'journal_head_sha256': started_pin['sha256'],
            'chunk_index': 0, 'attempt': 1,
            'attempt_root': completed['attempt_root'],
            'manifest_pin': completed['manifest_pin'],
            'status': 'verified', 'cli_exit_code': 0,
            'cli_exit_confirmed': True, 'cli_process': {'pid': 7},
            'cli_stderr_pin': campaign.pin(b''),
            'cli_stdout_pin': campaign.pin(b'stdout'),
            'cli_supervision_pin': campaign.pin(b'supervision'),
            'request_pin': campaign.pin(b'request'), 'inner': inner,
            'invented_only': True,
            'actual_registered_observations_read': False,
            'campaign_coherence_authenticated': False,
            'campaign_evaluations_credited': 0,
            'formal_permission': False,
            'full_end_to_end_budget_measured': False,
        }

    generation_raw = v.canonical_json(owner_receipt('run-budget')) + b'\n'
    reread_raw = v.canonical_json(owner_receipt('saved-reread')) + b'\n'
    terminal_checkpoint = {
        'format': bridge.TERMINAL_FORMAT,
        'anchor_pin': journal.plan_pin,
        'previous_checkpoint_pin': started_checkpoint_pin,
        'generation_receipt_pin': campaign.pin(generation_raw),
        'saved_reread_receipt_pin': campaign.pin(reread_raw),
        'run_request_control_pin': campaign.pin(b'run request control'),
        'reread_request_control_pin': campaign.pin(b'reread request control'),
        'completed_record_pin': completed_pin,
        'record_count': 2, 'head_sha256': completed_pin['sha256'],
        'invented_only': True, 'actual_registered_observations_read': False,
        'campaign_coherence_authenticated': False,
        'launch_authorized': False, 'resume_authorized': False,
        'campaign_evaluations_credited': 0, 'formal_permission': False,
    }
    terminal_raw = v.canonical_json(terminal_checkpoint) + b'\n'
    row = {
        'chunk_index': 0, 'registered_seed_index': 0,
        'registered_seed': journal.plan['chunks'][0]['registered_seed'],
        'layout': 0, 'latest_attempt': 1,
        'source_root': completed['attempt_root'],
        'historic_source_revision': journal.plan['source']['revision'],
        'recipe_id': journal.plan['recipe_id'],
        'registry_pin': journal.plan['registry_pin'],
        'savepoint_pin': entry['expected_pins']['savepoint'],
        'result_pin': entry['expected_pins']['result'],
        'rows_pin': entry['expected_pins']['rows'],
    }
    coverage_result = {
        'format': bridge.coverage.FORMAT, 'invented_only': True,
        'status': 'partial_coverage_unanchored',
        'planned_chunks': 480, 'planned_evaluations': 2880,
        'bound_chunks': 1, 'bound_evaluations': 6,
        'chunk_indices': [0],
        'missing_chunk_indices': list(range(1, 480)),
        'producer_campaign_anchor': None,
        'campaign_coherence_authenticated': False,
        'saved_payload_bytes_reopened_here': False,
        'reader_execution_authenticated_here': False,
        'clusters': None, 'diagnostics': None, 'slice_source': None,
        'registered_observations_read': False,
        'actual_registered_observations_read': False,
        'campaign_evaluations_credited': 0,
        'formal_permission': False, 'analysis_authorized': False,
        'promotion_allowed': False, 'independent_s6_complete': False,
        'chunks': [row],
    }
    args = [journal.plan_raw, journal.raws, started_raw, terminal_raw, entry]
    pins = {
        'generation_receipt_raw': generation_raw,
        'saved_reread_receipt_raw': reread_raw,
        'expected_plan_pin': journal.plan_pin,
        'expected_started_checkpoint_pin': started_checkpoint_pin,
        'expected_terminal_checkpoint_pin': campaign.pin(terminal_raw),
    }
    return args, pins, coverage_result


class CampaignSavedRowBridgeTests(unittest.TestCase):
    def test_real_saved_row_collector_is_joined_to_pinned_journal(self):
        args, pins, _ = fixture(real_coverage=True)
        with patch('builtins.open', side_effect=AssertionError('unexpected I/O')):
            result = bridge.bind_completed_saved_rows(*args, **pins)
        self.assertEqual(result['status'], 'partial_saved_row_journal_link_only')
        self.assertEqual(result['verified_evaluations'], 6)
        self.assertEqual(result['missing_chunk_indices'], list(range(1, 480)))
        self.assertIsNone(result['clusters'])
        self.assertFalse(result['campaign_coherence_authenticated'])
        self.assertFalse(result['formal_permission'])

    def test_one_pinned_slot_links_without_aggregation_or_formal_credit(self):
        args, pins, covered = fixture()
        with patch('builtins.open', side_effect=AssertionError('unexpected I/O')):
            with patch.object(bridge.coverage, 'collect_saved_row_coverage',
                              return_value=covered) as collector:
                result = bridge.bind_completed_saved_rows(*args, **pins)
        collector.assert_called_once_with([args[4]])
        self.assertEqual(result['status'], 'partial_saved_row_journal_link_only')
        self.assertEqual((result['verified_chunks'], result['planned_chunks']),
                         (1, 480))
        self.assertEqual((result['verified_evaluations'],
                          result['planned_evaluations']), (6, 2880))
        self.assertEqual(result['missing_chunk_indices'], list(range(1, 480)))
        self.assertIsNone(result['producer_campaign_anchor'])
        self.assertIsNone(result['clusters'])
        self.assertIsNone(result['diagnostics'])
        self.assertIsNone(result['slice_source'])
        self.assertIs(result['retained_owner_receipt_context_checked_here'], True)
        for name in ('campaign_coherence_authenticated',
                     'producer_execution_authenticated_here',
                     'reader_execution_authenticated_here',
                     'saved_payload_bytes_reopened_here',
                     'formal_permission', 'analysis_authorized',
                     'promotion_allowed', 'independent_s6_complete'):
            self.assertIs(result[name], False, name)
        self.assertEqual(result['campaign_evaluations_credited'], 0)

    def test_external_trust_roots_and_checkpoint_chain_reject_tampering(self):
        args, pins, covered = fixture()
        for change in (
            lambda a, p: p.update(expected_plan_pin=campaign.pin(b'wrong')),
            lambda a, p: p.update(
                expected_started_checkpoint_pin=campaign.pin(b'wrong')),
            lambda a, p: p.update(
                expected_terminal_checkpoint_pin=campaign.pin(b'wrong')),
            lambda a, p: a.__setitem__(1, a[1][::-1]),
            lambda a, p: a[1].__setitem__(1, a[1][1] + b' '),
        ):
            with self.subTest(change=change):
                raw_args = copy.deepcopy(args)
                expected = copy.deepcopy(pins)
                change(raw_args, expected)
                with patch.object(bridge.coverage, 'collect_saved_row_coverage',
                                  return_value=covered), self.assertRaises(ValueError):
                    bridge.bind_completed_saved_rows(*raw_args, **expected)

    def test_rehashed_checkpoint_cannot_change_count_head_or_formal_flag(self):
        args, pins, covered = fixture()
        for change in (
            lambda c: c.update(record_count=3),
            lambda c: c.update(head_sha256='f' * 64),
            lambda c: c.update(formal_permission=True),
            lambda c: c.update(campaign_coherence_authenticated=True),
        ):
            raw_args = copy.deepcopy(args)
            expected = copy.deepcopy(pins)
            value = v.strict_json(raw_args[3])
            change(value)
            raw_args[3] = v.canonical_json(value) + b'\n'
            expected['expected_terminal_checkpoint_pin'] = campaign.pin(raw_args[3])
            with self.subTest(change=change):
                with patch.object(bridge.coverage, 'collect_saved_row_coverage',
                                  return_value=covered), self.assertRaises(ValueError):
                    bridge.bind_completed_saved_rows(*raw_args, **expected)

    def test_entry_pins_must_come_from_external_completed_record(self):
        args, pins, covered = fixture()
        args[4]['expected_pins']['rows'] = campaign.pin(b'other rows')
        with patch.object(bridge.coverage, 'collect_saved_row_coverage',
                          return_value=covered) as collector:
            with self.assertRaisesRegex(ValueError,
                                        'coverage pins must derive'):
                bridge.bind_completed_saved_rows(*args, **pins)
        collector.assert_not_called()

    def test_saved_control_output_pins_must_match_completed_evidence(self):
        for name in ('saved/receipt.json', 'saved/report.json',
                     'saved/savepoint.json'):
            args, pins, covered = fixture()
            record = v.strict_json(args[1][1])
            record['saved_output_pins'][name] = campaign.pin(b'wrong')
            args[1][1] = campaign.encode_record(record)
            terminal = v.strict_json(args[3])
            terminal['completed_record_pin'] = campaign.pin(args[1][1])
            terminal['head_sha256'] = terminal['completed_record_pin']['sha256']
            args[3] = v.canonical_json(terminal) + b'\n'
            pins['expected_terminal_checkpoint_pin'] = campaign.pin(args[3])
            with self.subTest(name=name):
                with patch.object(bridge.coverage, 'collect_saved_row_coverage',
                                  return_value=covered), self.assertRaises(ValueError):
                    bridge.bind_completed_saved_rows(*args, **pins)

    def test_terminal_receipts_must_match_completed_evidence(self):
        for receipt_name, inner_name, pin_field in (
            ('generation_receipt_raw', 'saved_output_pins',
             'generation_receipt_pin'),
            ('saved_reread_receipt_raw', 'evidence_pins',
             'saved_reread_receipt_pin'),
        ):
            args, pins, covered = fixture()
            owner = v.strict_json(pins[receipt_name])
            if inner_name == 'saved_output_pins':
                owner['inner'][inner_name]['saved/receipt.json'] = campaign.pin(
                    b'wrong saved receipt')
            else:
                owner['inner'][inner_name]['rows'] = campaign.pin(b'wrong rows')
            pins[receipt_name] = v.canonical_json(owner) + b'\n'
            terminal = v.strict_json(args[3])
            terminal[pin_field] = campaign.pin(pins[receipt_name])
            args[3] = v.canonical_json(terminal) + b'\n'
            pins['expected_terminal_checkpoint_pin'] = campaign.pin(args[3])
            with self.subTest(receipt=receipt_name):
                with patch.object(bridge.coverage, 'collect_saved_row_coverage',
                                  return_value=covered) as collector:
                    with self.assertRaises(ValueError):
                        bridge.bind_completed_saved_rows(*args, **pins)
                collector.assert_not_called()

    def test_plan_identity_and_coverage_mismatch_rejected(self):
        args, pins, covered = fixture()
        other = copy.deepcopy(covered)
        other['chunks'][0]['registered_seed_index'] = 1
        with patch.object(bridge.coverage, 'collect_saved_row_coverage',
                          return_value=other), self.assertRaises(ValueError):
            bridge.bind_completed_saved_rows(*args, **pins)
        args[4]['rows_raw'] = v.canonical_json({'rows': [
            {'identity': identity} for identity in
            v.evaluation_inventory('holdout')[6:12]]})
        with patch.object(bridge.coverage, 'collect_saved_row_coverage',
                          return_value=covered), self.assertRaises(ValueError):
            bridge.bind_completed_saved_rows(*args, **pins)


if __name__ == '__main__':
    unittest.main()
