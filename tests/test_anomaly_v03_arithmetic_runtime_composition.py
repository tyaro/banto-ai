"""Externally pinned arithmetic candidates remain bound under common budgets."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_role_runtime_observation as observation
from banto_ai import anomaly_v03_preformal_bound_draw_bridge as bridge
from banto_ai import anomaly_v03_preformal_contiguous_document_budget as chain
from banto_ai import anomaly_v03_preformal_saved_row_document_budget as saved
from tests import test_anomaly_v03_preformal_contiguous_document_budget as helpers


REVISION = 'b' * 40


def candidates(root, sources, revision=REVISION):
    result = {}
    for role in ('analysis', 'audit'):
        profile = {'format': observation.FORMAT, 'mode': 'fixture',
            'acceptance': 'candidate-not-accepted', 'role': role,
            'operation': observation.OPERATIONS[role], 'source_root': str(root),
            'source_revision': revision, 'runtime': dict(observation.runtime.EXPECTED),
            'source_files': copy.deepcopy(sources),
            'stdlib_files': {'stdlib/example.py': observation._pin(b'example')},
            'native_files': {str(root / 'invented.dll'): observation._pin(b'native')},
            'cache_files': {}, 'scope': dict(observation.CLOSED)}
        raw = observation.v.canonical_json(profile)
        result[role] = {'raw': raw, 'expected_pin': observation._pin(raw)}
    return result


class RuntimeCompositionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.receipt = self.root / 'receipt'
        self.receipt.mkdir()
        self.sources = {name: observation._pin(b'invented-source') for name in bridge.SOURCE_NAMES}
        self.profiles = candidates(self.root, self.sources)
        root_patch = patch.object(bridge, 'ROOT', self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        helpers.FakeBudget.instances = []
        helpers.FakeBudget.stop_phase = None
        self.budget = helpers.FakeBudget(self.receipt, chain.LIMITS).start()
        self.result = {}

    def stage(self, profiles=None, **options):
        kwargs = dict(revision=REVISION, budget=self.budget, source_pins=self.sources,
                      runtime=observation.runtime.EXPECTED, result=self.result)
        kwargs.update(options)
        bridge.stage_runtime_profiles(self.receipt, self.profiles if profiles is None else profiles, **kwargs)

    def test_both_roles_and_exact_external_pins_are_required_before_staging(self):
        bad = copy.deepcopy(self.profiles)
        bad['audit']['raw'] += b' '
        for value in ({}, {'analysis': self.profiles['analysis']}, bad):
            with self.subTest(roles=list(value)), self.assertRaises(ValueError):
                self.stage(value)
        self.assertEqual(list(self.receipt.iterdir()), [])

    def test_same_source_bytes_do_not_allow_an_old_revision_or_a_role_swap(self):
        for profiles in (candidates(self.root, self.sources, 'a' * 40),
                         {'analysis': self.profiles['audit'], 'audit': self.profiles['analysis']}):
            with self.assertRaises(ValueError):
                bridge.validate_runtime_profiles(profiles, revision=REVISION)

    def test_caller_pin_mutation_cannot_change_retained_candidate(self):
        retained = bridge.validate_runtime_profiles(self.profiles, revision=REVISION)
        self.profiles['analysis']['expected_pin']['sha256'] = '0' * 64
        self.stage(retained)
        self.assertEqual(self.result['arithmetic_runtime_profile_pins']['analysis'],
                         observation._pin(retained['analysis']['raw']))
        self.assertFalse(self.result['arithmetic_runtime_observation_checked'])

    def test_second_role_source_mismatch_is_rejected_before_either_file_is_written(self):
        bad = copy.deepcopy(self.profiles)
        value = json.loads(bad['audit']['raw'])
        value['source_files'][bridge.SOURCE_NAMES[0]] = observation._pin(b'changed-source')
        raw = observation.v.canonical_json(value)
        bad['audit'] = {'raw': raw, 'expected_pin': observation._pin(raw)}
        with self.assertRaisesRegex(ValueError, 'selected Git source'):
            self.stage(bad)
        self.assertEqual(list(self.receipt.iterdir()), [])

    def test_stop_and_tuple_mismatch_block_staging_under_the_same_budget(self):
        with self.assertRaisesRegex(ValueError, 'tuple differs'):
            self.stage(runtime={'invented-mismatch': True})
        helpers.FakeBudget.stop_phase = 'preflight'
        with self.assertRaises(bridge.resources.ResourceStop):
            self.stage()
        self.assertEqual(list(self.receipt.iterdir()), [])

    def test_exclusive_write_failure_preserves_first_file_and_never_claims_checked(self):
        (self.receipt / 'audit-inventory-profile.json').write_bytes(b'prior')
        with self.assertRaises(FileExistsError):
            self.stage()
        self.assertEqual((self.receipt / 'analysis-inventory-profile.json').read_bytes(),
                         self.profiles['analysis']['raw'])
        self.assertEqual((self.receipt / 'audit-inventory-profile.json').read_bytes(), b'prior')
        self.assertFalse(self.result['arithmetic_runtime_observation_checked'])

    def test_actual_arithmetic_caller_passes_each_pin_to_owner_and_verifier(self):
        self.stage()
        calls, verified = [], []
        def supervise(role, root, input_pin, calculation_pin, budget, *, inventory_profile_pin):
            self.assertIs(budget, self.budget)
            calls.append((role, inventory_profile_pin))
            name = 'calculation.json' if role == 'analysis' else 'audit.json'
            value = {'draw_sha256': bridge.frozen.BOOTSTRAP_HASH}
            chain._write_value(root / name, value, chain.MAX_CONTROL)
            return {'status': 'complete', 'pid': 10 if role == 'analysis' else 11,
                    'worker_exit_confirmed': True, 'stop_reason': None}
        def verify(root, role, supervision, pin, *, inventory_profile_pin):
            verified.append((role, inventory_profile_pin))
        with patch.object(bridge, '_supervise', side_effect=supervise), \
             patch.object(bridge, '_verify_role', side_effect=verify), \
             patch.object(bridge.draw_budget, '_verify_audit_report'):
            chain._arithmetic(self.receipt, observation._pin(b'input'), self.budget, self.result)
        expected = [(role, self.profiles[role]['expected_pin']) for role in ('analysis', 'audit')]
        self.assertEqual(calls, expected)
        self.assertEqual(verified, expected)
        self.assertTrue(self.result['arithmetic_runtime_observation_checked'])
        self.assertEqual(set(self.budget.roles), {'analysis', 'audit'})

    def test_verifier_failure_blocks_the_next_role_and_never_claims_checked(self):
        self.stage()
        def supervise(role, root, *args, **kwargs):
            chain._write_value(root / 'calculation.json', {}, chain.MAX_CONTROL)
            return {'status': 'complete', 'pid': 10, 'worker_exit_confirmed': True, 'stop_reason': None}
        with patch.object(bridge, '_supervise', side_effect=supervise) as owner, \
             patch.object(bridge, '_verify_role', side_effect=ValueError('saved identity differs')), \
             self.assertRaisesRegex(ValueError, 'saved identity'):
            chain._arithmetic(self.receipt, observation._pin(b'input'), self.budget, self.result)
        self.assertEqual(owner.call_count, 1)
        self.assertFalse(self.result['arithmetic_runtime_observation_checked'])

    def test_postflight_detects_changed_phase_bytes_without_replaying_children(self):
        self.stage()
        for role in ('analysis', 'audit'):
            receipt = {}
            for phase in ('before', 'after'):
                raw = observation.v.canonical_json({'invented-phase': phase})
                (self.receipt / (role + '-runtime-' + phase + '.json')).write_bytes(raw)
                receipt[phase + '_pin'] = observation._pin(raw)
            raw = observation.v.canonical_json({'runtime_observation': receipt})
            (self.receipt / (role + '-stdout.json')).write_bytes(raw)
            self.result[role + '_supervision'] = {'stdout_pin': observation._pin(raw)}
        bridge.recheck_runtime_profiles(self.receipt, self.result)
        (self.receipt / 'audit-runtime-after.json').write_bytes(b'changed')
        with patch.object(bridge, '_supervise', side_effect=AssertionError('replayed')), \
             self.assertRaisesRegex(ValueError, 'pin differs'):
            bridge.recheck_runtime_profiles(self.receipt, self.result)

    def test_control_entrypoints_forward_the_external_bundle(self):
        options = dict(control_root=self.root, expected_control_pinset_pin=observation._pin(b'control'),
            expected_mode='fixture', expected_input_pins={}, expected_revision=REVISION,
            receipt_name='trial-one', arithmetic_runtime_profiles=self.profiles)
        with patch.object(saved, 'run_saved_rows', return_value={'test': True}) as run:
            saved.run_saved_control_files(**options)
            saved.run_saved_control_files_with_observation_subset(
                **options, observation_subset=[], expected_observation_subset={}, outer_budget=self.budget)
        for call in run.call_args_list:
            self.assertIs(call.kwargs['arithmetic_runtime_profiles'], self.profiles)
            self.assertTrue(call.kwargs['publish_document'])
        self.assertIs(run.call_args.kwargs['outer_budget'], self.budget)


if __name__ == '__main__':
    unittest.main()
